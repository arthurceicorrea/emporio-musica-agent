"""LangGraph ReAct orchestration with SQLite checkpoint persistence."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from src.agent.prompts import SYSTEM_PROMPT
from src.agent.tools import AGENT_TOOLS
from src.config import settings


def create_chat_model(
    provider: str | None = None,
    model_name: str | None = None,
    temperature: float | None = None,
) -> BaseChatModel:
    """Instantiate the configured LLM chat model (Google GenAI or OpenAI)."""
    resolved_provider = (provider or settings.llm_provider).lower().strip()
    resolved_model = model_name or settings.model_name
    resolved_temp = temperature if temperature is not None else settings.temperature

    if resolved_provider == "openai":
        from langchain_openai import ChatOpenAI

        if not settings.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set. Configure it in your .env file or switch LLM_PROVIDER=google."
            )
        return ChatOpenAI(
            model=resolved_model,
            temperature=resolved_temp,
            api_key=settings.openai_api_key,
        )

    if resolved_provider in {"google", "gemini", "google_genai"}:
        from langchain_google_genai import ChatGoogleGenerativeAI

        if not settings.google_api_key:
            raise ValueError(
                "GOOGLE_API_KEY is not set. Configure it in your .env file or switch LLM_PROVIDER=openai."
            )
        return ChatGoogleGenerativeAI(
            model=resolved_model,
            temperature=resolved_temp,
            google_api_key=settings.google_api_key,
        )

    raise ValueError(
        f"Unsupported LLM_PROVIDER '{resolved_provider}'. Expected 'google' or 'openai'."
    )


def _extract_text_content(content: Any) -> str:
    """Normalize string or multimodal block list message content into a clean string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
        return "
".join(parts).strip()
    return str(content)


def build_agent_graph(
    llm: BaseChatModel | None = None,
    checkpoint_db_path: Path | str | None = None,
):
    """Compile and return a stateful LangGraph ReAct agent with SQLite memory."""
    chat_model = llm or create_chat_model()
    model_with_tools = chat_model.bind_tools(AGENT_TOOLS)

    def call_model(state: MessagesState) -> dict[str, list[BaseMessage]]:
        messages = state["messages"]
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)
        response = model_with_tools.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: MessagesState) -> str:
        last_message = state["messages"][-1]
        if isinstance(last_message, AIMessage) and getattr(last_message, "tool_calls", None):
            return "tools"
        return END

    workflow = StateGraph(MessagesState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(AGENT_TOOLS))

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    workflow.add_edge("tools", "agent")

    db_target = str(checkpoint_db_path or settings.checkpoint_db_path)
    if db_target != ":memory:":
        Path(db_target).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_target, check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    return workflow.compile(checkpointer=checkpointer)


def run_agent_turn(
    user_message: str,
    thread_id: str = "default-session",
    graph=None,
) -> dict[str, Any]:
    """Execute a single conversational turn and return the reply plus tool execution trace."""
    compiled_graph = graph or build_agent_graph()
    config = {"configurable": {"thread_id": thread_id}}

    prior_state = compiled_graph.get_state(config)
    prior_messages = prior_state.values.get("messages", []) if prior_state and prior_state.values else []
    prior_len = len(prior_messages)

    result_state = compiled_graph.invoke(
        {"messages": [HumanMessage(content=user_message)]},
        config=config,
    )
    all_messages: list[BaseMessage] = result_state["messages"]
    new_messages = all_messages[prior_len:]

    tool_traces: list[dict[str, Any]] = []
    for msg in new_messages:
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                tool_traces.append(
                    {
                        "tool_name": tc.get("name"),
                        "args": tc.get("args"),
                        "tool_call_id": tc.get("id"),
                    }
                )
        elif isinstance(msg, ToolMessage):
            for trace in reversed(tool_traces):
                if trace.get("tool_call_id") == msg.tool_call_id and "output" not in trace:
                    trace["output"] = _extract_text_content(msg.content)
                    break

    final_ai_message = next(
        (m for m in reversed(new_messages) if isinstance(m, AIMessage)),
        all_messages[-1],
    )
    return {
        "reply": _extract_text_content(final_ai_message.content),
        "thread_id": thread_id,
        "tool_traces": tool_traces,
    }
