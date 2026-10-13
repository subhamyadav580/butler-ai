"""The contract every integration implements.

An integration is one folder under butler/integrations/ with an
`integration.py` that defines a subclass of `Integration` and an instance
called `INTEGRATION`. Register it in butler/integrations/registry.py and
everything else (agent, prompt, CLI, web UI, Telegram) picks it up:

    agent          tools from load_tools(), prompt section from rules()
    CLI            login() as `python -m butler <login_command>`, plus cli_commands
    web UI         a card from status(), a Connect button running connect(),
                   switches from options(), status labels from tool_labels,
                   example prompts from examples
    Telegram       example prompts; `restricted` integrations only for the owner

See docs/internals/adding-tools.md for a walkthrough.
"""

from typing import Callable, Optional


class Integration:
    # --- Identity -------------------------------------------------------------
    name: str = ""                 # short id: "gmail", "web_search"
    title: str = ""                # shown in the UI: "Gmail"
    description: str = ""          # one line for the Integrations page

    # --- Access -----------------------------------------------------------------
    # Restricted integrations act on the owner's account in costly or risky ways
    # (orders, payments). On Telegram only TELEGRAM_OWNER_ID gets their tools.
    restricted: bool = False

    # --- Connecting ---------------------------------------------------------------
    login_command: Optional[str] = None   # CLI command for login(): "gmail-login"
    can_connect: bool = False             # show Connect/Reconnect in the web UI
    reload_on_connect: bool = False       # rebuild the agent after connecting

    # --- Presentation ---------------------------------------------------------------
    tool_labels: dict[str, str] = {}      # tool name → "Searching your mail"
    examples: list[str] = []              # example prompts for /start and the web UI
    # Extra CLI commands: {"gmail": main_function} → `python -m butler gmail …`
    cli_commands: dict[str, Callable[[], None]] = {}

    # ----------------------------------------------------------------------------
    # Agent
    # ----------------------------------------------------------------------------

    async def load_tools(self):
        """(tools, warning or None). Return [] tools to leave the integration out,
        e.g. when it isn't configured; the warning is printed at startup."""
        return self.tools(), None

    def tools(self):
        """Static tool list, for integrations that need no async setup."""
        return []

    def hides_tools(self) -> set[str]:
        """Tools of OTHER integrations to keep from the LLM while this one is
        loaded, because it replaces them (groceries' search_groceries replaces
        each app's own product search). Only asked when this integration
        loaded tools."""
        return set()

    def rules(self, tool_names: set[str]) -> str:
        """This integration's section of the system prompt, given the tools that
        actually loaded. Only called when at least one of its tools loaded."""
        return ""

    # ----------------------------------------------------------------------------
    # Connecting and status
    # ----------------------------------------------------------------------------

    def status(self, loaded_tool_names: set[str]) -> dict:
        """{"state": "connected" | "disconnected" | "needs_setup", "detail": str,
        optional "needs_reload": bool, plus any extra fields}. Must be quick:
        it runs every time the Integrations page loads."""
        return {"state": "connected", "detail": ""}

    def options(self) -> list[dict]:
        """On/off settings shown as switches on the integration's card:
        [{"key", "label", "description", "value": bool}]. Store values with
        butler.db.get_settings() so every process sees changes at once."""
        return []

    def set_option(self, key: str, value: bool):
        raise KeyError(key)

    async def connect(self):
        """Run the interactive login (may open a browser on this machine).
        Raise an exception with a readable message on failure."""
        raise NotImplementedError(f"{self.name} has no connect flow")

    def login(self):
        """CLI login (`python -m butler <login_command>`)."""
        raise NotImplementedError(f"{self.name} has no login")
