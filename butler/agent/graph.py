"""The agent: one LLM with every tool, looping agent <-> tools."""

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition

from butler.config import OPENAI_MODEL
from butler.integrations.calendar import CALENDAR_TOOLS
from butler.integrations.gmail import GMAIL_TOOLS
from butler.integrations.todos import TODO_TOOLS
from butler.integrations.swiggy import load_swiggy_tools, services_of

from .prompts import system_prompt


llm = ChatOpenAI(model=OPENAI_MODEL, temperature=0)


INCOMPLETE_TOOL_CALL = (
    "This tool call did not complete (it failed or was interrupted). "
    "Do not assume it succeeded; retry or tell the user if needed."
)


def with_tool_results(messages):
    """Give every tool call a result before sending history to the LLM.

    OpenAI rejects a history where an assistant tool call has no matching
    tool message. That happens if a run crashed mid-tool; without this the
    conversation would fail on every later message.
    """
    answered = {m.tool_call_id for m in messages if isinstance(m, ToolMessage)}

    fixed = []
    for message in messages:
        fixed.append(message)
        if isinstance(message, AIMessage):
            for call in message.tool_calls:
                if call["id"] not in answered:
                    fixed.append(ToolMessage(
                        content=INCOMPLETE_TOOL_CALL,
                        tool_call_id=call["id"],
                        name=call["name"],
                    ))
    return fixed


async def build_graph():
    """Load every tool (Swiggy needs async MCP calls) and compile the agent."""
    swiggy_tools, swiggy_error = await load_swiggy_tools()
    if swiggy_error:
        suffix = "" if swiggy_tools else " Continuing without Swiggy."
        print(f"WARNING: {swiggy_error}.{suffix}")

    # Every capability the agent has. Add new tool lists here.
    base_tools = GMAIL_TOOLS + CALENDAR_TOOLS + TODO_TOOLS   # available to every user
    all_tools = base_tools + swiggy_tools
    swiggy_services = services_of(swiggy_tools)   # e.g. {"food", "instamart", "dineout"}

    # Users without Swiggy access never even see the Swiggy tools
    llm_with_swiggy = llm.bind_tools(all_tools)
    llm_without_swiggy = llm.bind_tools(base_tools)

    async def agent(state: MessagesState, config: RunnableConfig):
        swiggy_enabled = bool(swiggy_tools) and config["configurable"].get(
            "swiggy_allowed", True
        )
        agent_llm = llm_with_swiggy if swiggy_enabled else llm_without_swiggy
        services = swiggy_services if swiggy_enabled else ()

        response = await agent_llm.ainvoke(
            [{"role": "system", "content": system_prompt(services)}]
            + with_tool_results(state["messages"])
        )
        return {"messages": [response]}

    graph = StateGraph(MessagesState)

    graph.add_node("agent", agent)
    # A failing tool becomes an error ToolMessage the LLM can react to,
    # instead of crashing the run and leaving an unanswered tool call
    graph.add_node("tools", ToolNode(all_tools, handle_tool_errors=True))

    graph.add_edge(START, "agent")
    # Loop agent <-> tools until the LLM answers without calling a tool
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")

    # Checkpointer is required for interrupt() (human-in-the-loop) and keeps
    # conversation history per thread_id
    return graph.compile(checkpointer=InMemorySaver())
