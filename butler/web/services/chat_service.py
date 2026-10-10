"""Chats as the user sees them: the sidebar list and saved transcripts.

Two kinds of storage, on purpose:
- The database keeps the thread list and the visible messages (user text
  and Butler's replies), so chats survive restarts and show on any device.
- The agent's working memory (tool calls, results, open questions) stays
  in RAM inside AgentService, as before. After a restart old chats are
  readable, but the agent continues without their context.
"""

from .agent_service import AgentService

TITLE_LENGTH = 60
NEW_CHAT_TITLE = "New chat"


class ThreadNotFound(Exception):
    pass


class ChatService:
    def __init__(self, agent: AgentService, threads, messages):
        self.agent = agent
        self.threads = threads
        self.messages = messages

    # ------------------------------------------------------------------
    # Threads
    # ------------------------------------------------------------------

    def list_threads(self):
        return self.threads.list()

    def history(self, thread_id):
        """Saved transcript plus any open question. Unknown ids are an empty
        draft (the UI creates threads lazily on the first message)."""
        return {
            "messages": self.messages.list(thread_id),
            "pending": self.agent.pending(thread_id),
        }

    def rename(self, thread_id, title):
        if not self.threads.get(thread_id):
            raise ThreadNotFound(thread_id)
        self.threads.rename(thread_id, title.strip()[:TITLE_LENGTH] or NEW_CHAT_TITLE)
        return self.threads.get(thread_id)

    def delete(self, thread_id):
        self.threads.delete(thread_id)
        self.agent.reset(thread_id)

    # ------------------------------------------------------------------
    # Turns
    # ------------------------------------------------------------------

    async def send_message(self, thread_id, text):
        # The first message creates the thread and names it
        self.threads.create(thread_id, _title_from(text))
        self.messages.add(thread_id, "user", text)
        self.threads.touch(thread_id)

        async for event in self._saving_replies(
            thread_id, self.agent.send_message(thread_id, text)
        ):
            yield event

    async def resume(self, thread_id, interrupt_type, answer):
        async for event in self._saving_replies(
            thread_id, self.agent.resume(thread_id, interrupt_type, answer)
        ):
            yield event

    async def _saving_replies(self, thread_id, events):
        """Pass events through; save each assistant reply when it completes.

        A reply ends at "done" or when the agent pauses ("interrupt"); text
        streamed before a pause is saved too, so the transcript matches what
        the user saw.
        """
        text = []

        def save():
            content = "".join(text).strip()
            if content:
                self.messages.add(thread_id, "assistant", content)
                self.threads.touch(thread_id)
            text.clear()

        try:
            async for event in events:
                if event["type"] == "token":
                    text.append(event["content"])
                elif event["type"] in ("done", "interrupt"):
                    save()
                yield event
        finally:
            # Stream cut short (error / client gone): keep what was shown
            save()


def _title_from(text):
    title = " ".join(text.split())
    if len(title) > TITLE_LENGTH:
        title = title[: TITLE_LENGTH - 1].rstrip() + "…"
    return title or NEW_CHAT_TITLE
