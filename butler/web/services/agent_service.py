"""Runs the agent for web chats: streaming turns, interrupts, history.

Framework-agnostic: yields plain dict events; the handler turns them into
Server-Sent Events.
"""

import asyncio

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from langgraph.types import Command

from butler.agent import build_graph, cancel_pending, pending_interrupt


class InterruptMismatch(Exception):
    """Resume was sent but the thread isn't waiting for that kind of answer."""


class AgentService:
    def __init__(self):
        self.graph = None
        self.swiggy_loaded = False
        self._lock = asyncio.Lock()

    async def start(self):
        await self.reload()

    async def reload(self):
        """(Re)build the agent, e.g. after connecting an integration.

        Conversation memory lives in the graph's checkpointer, so a reload
        starts every chat fresh.
        """
        async with self._lock:
            self.graph = await build_graph()
            tools = self.graph.get_graph().nodes["tools"].data.tools_by_name
            self.swiggy_loaded = "get_addresses" in tools

    @staticmethod
    def _config(thread_id):
        # The web UI is used by the instance owner, so Swiggy is allowed
        return {"configurable": {"thread_id": thread_id, "swiggy_allowed": True}}

    # ------------------------------------------------------------------
    # Turns
    # ------------------------------------------------------------------

    async def send_message(self, thread_id, text):
        config = self._config(thread_id)
        # A new message abandons any open question (picker/approval)
        await cancel_pending(self.graph, config)
        async for event in self._stream(
            {"messages": [{"role": "user", "content": text}]}, config
        ):
            yield event

    async def resume(self, thread_id, interrupt_type, answer):
        config = self._config(thread_id)
        payload = pending_interrupt(self.graph, config)
        if not payload or payload["type"] != interrupt_type:
            raise InterruptMismatch("Nothing is waiting for this answer.")

        async for event in self._stream(Command(resume=answer), config):
            yield event

    async def _stream(self, graph_input, config):
        text = []

        async for mode, chunk in self.graph.astream(
            graph_input, config, stream_mode=["messages", "updates"]
        ):
            if mode == "messages":
                message, metadata = chunk
                if metadata.get("langgraph_node") != "agent":
                    continue
                if not isinstance(message, AIMessageChunk):
                    continue
                if message.content:
                    text.append(message.content)
                    yield {"type": "token", "content": message.content}
                for call in message.tool_call_chunks or []:
                    if call.get("name"):
                        yield {"type": "tool", "name": call["name"]}

            elif mode == "updates" and "__interrupt__" in chunk:
                yield {"type": "interrupt", "payload": chunk["__interrupt__"][0].value}
                return

        yield {"type": "done", "content": "".join(text)}

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def history(self, thread_id):
        config = self._config(thread_id)
        state = self.graph.get_state(config)
        messages = []

        for message in state.values.get("messages", []):
            if isinstance(message, HumanMessage):
                messages.append({"role": "user", "content": message.content})
            elif isinstance(message, AIMessage) and message.content:
                messages.append({"role": "assistant", "content": message.content})

        return {
            "messages": messages,
            "pending": pending_interrupt(self.graph, config),
        }

    def reset(self, thread_id):
        self.graph.checkpointer.delete_thread(thread_id)
