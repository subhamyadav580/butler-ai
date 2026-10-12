"""Terminal chat with the agent: `python -m butler chat`.

Replies stream in live as formatted Markdown, with a status line while tools
run. Email pickers become numbered tables and approvals become highlighted
panels. Commands: /help, /new, /integrations, /exit.

Keys: ↑/↓ recall earlier messages (kept between sessions), Ctrl+C stops the
current answer, Ctrl+D quits.
"""

import asyncio
import contextlib
import signal
import uuid

from langgraph.types import Command
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

from butler.agent import build_graph, cancel_pending, format_args, loaded_tool_names, show_raw_args
from butler.agent.stream import stream_events
from butler.config import DATA_DIR, OPENAI_MODEL
from butler.integrations.registry import INTEGRATIONS, all_tool_labels

console = Console()

HELP = """\
**Commands**

| | |
|---|---|
| `/help` | Show this help |
| `/new` | Start a fresh conversation (Butler forgets this one) |
| `/integrations` | What's connected |
| `/exit` | Quit (or **Ctrl+D**) |

**Keys:** ↑/↓ recall earlier messages · **Ctrl+C** stops the current answer.
"""

STATE_ICONS = {"connected": "[green]✓[/]", "disconnected": "[yellow]○[/]", "needs_setup": "[red]✗[/]"}


class Chat:
    def __init__(self, graph, notes):
        self.graph = graph
        self.notes = notes
        self.labels = all_tool_labels()
        self.thread_id = self._new_thread_id()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.session = PromptSession(history=FileHistory(str(DATA_DIR / "cli_history")))

    @staticmethod
    def _new_thread_id():
        return f"cli-{uuid.uuid4().hex[:8]}"

    @property
    def config(self):
        # The terminal is used by the owner: restricted integrations allowed
        return {"configurable": {"thread_id": self.thread_id, "allow_restricted": True}}

    # ------------------------------------------------------------------
    # Screens
    # ------------------------------------------------------------------

    def banner(self):
        tools = loaded_tool_names(self.graph)
        lines = Text.from_markup(
            f"[bold]Butler[/]  [dim]· {OPENAI_MODEL} · /help for commands · Ctrl+D to quit[/]\n"
        )
        for integration in INTEGRATIONS:
            state = integration.status(tools).get("state", "connected")
            lines.append_text(Text.from_markup(f"{STATE_ICONS.get(state, '·')} {integration.title}   "))
        console.print(Panel(lines, border_style="cyan", padding=(0, 1)))
        for note in self.notes:
            console.print(f"[dim]{note.removeprefix('NOTE: ')}[/]")

    def integrations(self):
        tools = loaded_tool_names(self.graph)
        table = Table(show_header=True, header_style="bold", box=None, padding=(0, 2))
        table.add_column("")
        table.add_column("Integration")
        table.add_column("Status", overflow="fold")
        for integration in INTEGRATIONS:
            status = integration.status(tools)
            table.add_row(STATE_ICONS.get(status.get("state"), "·"), integration.title, status.get("detail", ""))
        console.print(table)
        console.print("[dim]Connect or reconnect with `python -m butler <name>-login`, or in the web UI.[/]")

    # ------------------------------------------------------------------
    # Asking the human (pickers, approvals)
    # ------------------------------------------------------------------

    async def ask(self, prompt):
        return (await self.session.prompt_async(HTML(prompt))).strip()

    async def pick_email(self, payload):
        emails = payload["emails"]
        table = Table(title=payload["question"], title_style="bold", title_justify="left",
                      box=None, padding=(0, 1), expand=True)
        # Fixed widths: long subjects must never squeeze the numbers away
        table.add_column("#", style="bold cyan", justify="right", width=3, no_wrap=True)
        table.add_column("", width=1, no_wrap=True)
        table.add_column("From", width=24, overflow="ellipsis", no_wrap=True)
        table.add_column("Subject", ratio=1, overflow="ellipsis", no_wrap=True)
        for i, email in enumerate(emails, start=1):
            sender = email["from"].split("<")[0].strip().strip('"') or email["from"]
            table.add_row(str(i), "[cyan]●[/]" if email["unread"] else "", sender, email["subject"] or "(no subject)")
        console.print(table)

        while True:
            choice = await self.ask(f"<b>Pick</b> 1-{len(emails)}, or 0 to cancel › ")
            if choice.isdigit() and 0 <= int(choice) <= len(emails):
                break
            console.print(f"[red]Enter a number from 0 to {len(emails)}.[/]")
        return {"email_id": emails[int(choice) - 1]["id"] if int(choice) else None}

    async def confirm(self, payload):
        body = [Text(payload["details"])] if payload.get("details") else []
        if show_raw_args(payload):
            body.append(Text(format_args(payload["args"]), style="dim"))
        console.print(Panel(
            Group(*body) if body else Text(payload["tool"].replace("_", " "), style="dim"),
            title=f"⚠️  {payload['question']}", title_align="left", border_style="yellow",
        ))
        answer = (await self.ask("<b>Approve?</b> [y/N] › ")).lower()
        approved = answer in ("y", "yes")
        console.print("[green]Approved.[/]" if approved else "[yellow]Rejected. Nothing was changed.[/]")
        return {"approved": approved}

    async def answer_interrupt(self, payload):
        if payload["type"] == "pick_email":
            return await self.pick_email(payload)
        if payload["type"] == "confirm_action":
            return await self.confirm(payload)
        console.print(f"[red]Butler asked something this terminal can't show ({payload['type']}); cancelling.[/]")
        return None

    # ------------------------------------------------------------------
    # One turn
    # ------------------------------------------------------------------

    async def turn(self, text):
        graph_input = {"messages": [{"role": "user", "content": text}]}
        console.print()
        while True:
            payload = await self.stream(graph_input)
            if payload is None:
                return
            answer = await self.answer_interrupt(payload)
            if answer is None:
                return
            graph_input = Command(resume=answer)

    async def stream(self, graph_input):
        """Show one streamed run; return an interrupt payload if it paused."""
        reply, status = "", "Thinking…"

        def view():
            parts = [Markdown(reply)] if reply else []
            if status:
                parts.append(Spinner("dots", text=Text(status, style="dim")))
            return Group(*parts)

        with Live(view(), console=console, refresh_per_second=15, transient=False) as live:
            async for event in stream_events(self.graph, graph_input, self.config):
                if event["type"] == "token":
                    reply += event["content"]
                    status = None
                elif event["type"] == "tool":
                    label = self.labels.get(event["name"], f"Using {event['name'].replace('_', ' ')}")
                    status = f"{label}…"
                elif event["type"] == "interrupt":
                    status = None
                    live.update(view())
                    return event["payload"]
                live.update(view())
            status = None
            live.update(view())
        console.print()           # end the answer on its own line
        return None

    # ------------------------------------------------------------------
    # Loop
    # ------------------------------------------------------------------

    async def command(self, text):
        """Handle a /command. Returns False to quit."""
        name = text.split()[0].lower()
        if name in ("/exit", "/quit"):
            return False
        if name == "/help":
            console.print(Markdown(HELP))
        elif name == "/new":
            self.graph.checkpointer.delete_thread(self.thread_id)
            self.thread_id = self._new_thread_id()
            console.print("[dim]New conversation started.[/]")
        elif name == "/integrations":
            self.integrations()
        else:
            console.print(f"[red]Unknown command {name}.[/] Try /help.")
        return True

    async def run(self):
        self.banner()
        loop = asyncio.get_running_loop()
        while True:
            try:
                text = (await self.session.prompt_async(HTML("\n<b><ansicyan>You</ansicyan></b> › "))).strip()
            except KeyboardInterrupt:
                continue                     # Ctrl+C at the prompt: clear the line
            except EOFError:
                break                        # Ctrl+D
            if not text:
                continue
            if text.lower() in ("exit", "quit"):
                break
            if text.startswith("/"):
                if not await self.command(text):
                    break
                continue

            # Run the answer as a task so Ctrl+C can stop just this answer
            task = asyncio.ensure_future(self.turn(text))
            loop.add_signal_handler(signal.SIGINT, task.cancel)
            try:
                await task
            except asyncio.CancelledError:
                console.print("\n[yellow]Stopped.[/]")
                await self.recover()
            except Exception as error:  # noqa: BLE001 — show it, keep chatting
                console.print(Panel(f"{type(error).__name__}: {error}", title="Something went wrong",
                                    border_style="red", title_align="left"))
            finally:
                loop.remove_signal_handler(signal.SIGINT)
        console.print("[dim]Bye![/]")

    async def recover(self):
        """After Ctrl+C mid-answer, a paused question may be left open: cancel it."""
        with contextlib.suppress(Exception):     # best effort
            await cancel_pending(self.graph, self.config)


async def main():
    notes = []
    with console.status("[dim]Starting Butler…[/]", spinner="dots"):
        graph = await build_graph(on_note=notes.append)
    await Chat(graph, notes).run()


if __name__ == "__main__":
    asyncio.run(main())
