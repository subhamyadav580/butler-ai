"""The agent: one LLM with every tool, looping agent <-> tools."""

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition

from butler.config import OPENAI_MODEL
from butler.integrations.registry import INTEGRATIONS

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


async def build_graph(on_note=print):
    """Load every integration's tools and compile the agent.

    on_note: called with each startup note (e.g. "Swiggy: not connected…");
    printed by default, collected by the terminal chat for its banner.
    """
    loaded = []                      # [(integration, tools)] that have tools
    for integration in INTEGRATIONS:
        tools, warning = await integration.load_tools()
        if warning:
            on_note(f"NOTE: {integration.title}: {warning}.")
        if tools:
            loaded.append((integration, tools))

    # An integration can replace other integrations' tools (see hides_tools)
    hidden = set().union(*(i.hides_tools() for i, _ in loaded))
    loaded = [(i, [t for t in tools if t.name not in hidden]) for i, tools in loaded]

    def toolset(pairs):
        return [tool for _, tools in pairs for tool in tools]

    # Restricted integrations (e.g. Swiggy: orders on the owner's account) are
    # hidden from users who aren't allowed them; see allow_restricted below
    everyone = [(i, t) for i, t in loaded if not i.restricted]
    all_tools = toolset(loaded)
    llm_full = llm.bind_tools(all_tools)
    llm_open = llm.bind_tools(toolset(everyone))

    def sections(pairs):
        return [i.rules({tool.name for tool in tools}) for i, tools in pairs]

    async def agent(state: MessagesState, config: RunnableConfig):
        allowed = config["configurable"].get("allow_restricted", True)
        pairs, agent_llm = (loaded, llm_full) if allowed else (everyone, llm_open)

        response = await agent_llm.ainvoke(
            [{"role": "system", "content": system_prompt(sections(pairs))}]
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


def loaded_tool_names(graph):
    """Names of every tool the compiled agent can run."""
    return set(graph.get_graph().nodes["tools"].data.tools_by_name)
