"""Every integration Butler loads, in order.

Adding an integration: create butler/integrations/<name>/integration.py with
`INTEGRATION = <YourIntegration>()` (see base.py), then add it below. The
agent, prompt, CLI, web UI and Telegram all read this list.
"""

from .calendar.integration import INTEGRATION as calendar
from .gmail.integration import INTEGRATION as gmail
from .swiggy.integration import INTEGRATION as swiggy
from .todos.integration import INTEGRATION as todos
from .websearch.integration import INTEGRATION as web_search

# Order = order of their sections in the system prompt and cards in the UI
INTEGRATIONS = [gmail, calendar, todos, web_search, swiggy]


def get_integration(name):
    return next((i for i in INTEGRATIONS if i.name == name), None)


def all_tool_labels():
    """tool name → status label, across every integration (for the web UI)."""
    labels = {}
    for integration in INTEGRATIONS:
        labels.update(integration.tool_labels)
    return labels


def example_prompts(include_restricted=True):
    return [
        example
        for integration in INTEGRATIONS
        if include_restricted or not integration.restricted
        for example in integration.examples
    ]


def cli_commands():
    """Extra commands contributed by integrations, plus their login commands."""
    commands = {}
    for integration in INTEGRATIONS:
        if integration.login_command:
            commands[integration.login_command] = integration.login
        commands.update(integration.cli_commands)
    return commands
