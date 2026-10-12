"""Todos as a Butler integration: a local todo list, no setup."""

from butler.integrations.base import Integration

from .tools import TODO_TOOLS

RULES = (
    "Todos (Butler's own todo list, stored locally; not Google Tasks):\n"
    "- 'Add to my todo/list', 'remind me to…', 'I need to…' → add_todo. Set "
    "due when a date or time is mentioned, a list when one is named "
    "(reuse names from todo_lists), and priority high only when the user "
    "says it's urgent or important.\n"
    "- 'What's on my list / what do I need to do' → list_todos (open). For "
    "'today' or 'this week', pass due_by. Show todos as '#id title — due "
    "(list)', overdue ones first.\n"
    "- 'Done with X' / 'mark X done' → find it with list_todos (query), then "
    "complete_todo. Only delete when the user asks to remove it; delete "
    "asks for approval automatically.\n"
    "- Butler can't send notifications. When the user says 'remind me', "
    "add the todo with its due time and offer to also put it on their "
    "Google Calendar (which can alert them).\n"
)


class TodosIntegration(Integration):
    name = "todos"
    title = "Todos"
    description = "Butler's own todo list: due dates, lists, priorities. Stored locally, no setup."
    tool_labels = {
        "add_todo": "Adding your todo",
        "list_todos": "Checking your todos",
        "complete_todo": "Updating your todo",
        "update_todo": "Updating your todo",
        "delete_todo": "Deleting your todo",
        "todo_lists": "Checking your lists",
    }
    examples = ["Remind me to pay rent on Friday"]

    def tools(self):
        return TODO_TOOLS

    def rules(self, tool_names):
        return RULES

    def status(self, loaded_tool_names):
        return {"state": "connected", "detail": "Ready. Stored in data/butler.db."}


INTEGRATION = TodosIntegration()
