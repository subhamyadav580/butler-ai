"""Run one turn of the agent as a stream of simple events.

Shared by every interface that shows replies live (web UI, terminal):

    {"type": "token", "content": "…"}     a piece of the reply text
    {"type": "tool", "name": "get_emails"} the LLM decided to call a tool
    {"type": "interrupt", "payload": {…}}  paused for the human (picker/approval)
    {"type": "done", "content": "…"}      the full reply text
"""

from langchain_core.messages import AIMessageChunk


async def stream_events(graph, graph_input, config):
    text = []

    async for mode, chunk in graph.astream(
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
