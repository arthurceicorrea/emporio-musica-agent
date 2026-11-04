"""Streamlit WhatsApp-inspired web interface for the Emporio da Musica AI Agent."""

from __future__ import annotations

import uuid
from typing import Any

import streamlit as st

from src.agent.graph import build_agent_graph, run_agent_turn
from src.database.ingest_csv import init_and_seed_database
from src.rag.ingest_pdf import index_policies_to_chroma

st.set_page_config(
    page_title="Empório da Música | Atendimento WhatsApp",
    page_icon="🎸",
    layout="wide",
)


@st.cache_resource(show_spinner="Inicializando base de dados e índice vetorial...")
def bootstrap_knowledge_bases() -> dict[str, Any]:
    """Ensure SQLite and ChromaDB stores are populated before handling chats."""
    db_counts = init_and_seed_database(force_reseed=False)
    policy_chunks = index_policies_to_chroma(force_reindex=False)
    return {"db_counts": db_counts, "policy_chunks": policy_chunks}


@st.cache_resource(show_spinner="Carregando grafo do agente...")
def get_cached_graph():
    """Compile and cache the LangGraph agent workflow."""
    return build_agent_graph()


def _init_session_state() -> None:
    """Initialize Streamlit session state variables for multi-turn conversation."""
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = f"wa-session-{uuid.uuid4().hex[:8]}"
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {
                "role": "assistant",
                "content": (
                    "Olá! 🎶 Bem-vindo(a) ao WhatsApp da **Empório da Música**! "
                    "Sou o assistente virtual da loja. Como posso te ajudar hoje? "
                    "Você pode consultar instrumentos no catálogo, preços, formas de pagamento, "
                    "rastreamento de pedidos ou nossas políticas de troca e entrega!"
                ),
                "tool_traces": [],
            }
        ]


def main() -> None:
    """Render the Streamlit WhatsApp customer service interface."""
    _init_session_state()
    kb_stats = bootstrap_knowledge_bases()

    # Sidebar controls and quick test prompts
    with st.sidebar:
        st.title("🎸 Empório da Música")
        st.caption("Sua música começa aqui — Campo Grande/MS")
        st.markdown("---")

        st.subheader("Sessão de Atendimento")
        st.code(f"Thread ID: {st.session_state.thread_id}", language="text")

        if st.button("🔄 Nova Conversa (Resetar Sessão)", use_container_width=True):
            st.session_state.thread_id = f"wa-session-{uuid.uuid4().hex[:8]}"
            st.session_state.chat_history = [
                {
                    "role": "assistant",
                    "content": (
                        "Olá! 🎶 Novo atendimento iniciado na **Empório da Música**. "
                        "Como posso te ajudar com instrumentos ou pedidos hoje?"
                    ),
                    "tool_traces": [],
                }
            ]
            st.rerun()

        st.markdown("---")
        st.subheader("Cenários Rápidos de Teste")
        quick_prompts = [
            "Quais opções de violões disponíveis custando até R$ 1.000?",
            "Quanto custa o Takamine GD20 no PIX e parcelado?",
            "O Taylor 110e tem promoção ativa? Como fica no PIX?",
            "Qual o endereço e horário de funcionamento da loja?",
            "Me arrependi da minha compra no pedido #7, posso devolver?",
            "Vocês vendem encordoamento de violão, palhetas e cabo P10?",
        ]
        selected_prompt: str | None = None
        for qp in quick_prompts:
            if st.button(qp, use_container_width=True):
                selected_prompt = qp

        st.markdown("---")
        with st.expander("📊 Status da Base de Conhecimento", expanded=False):
            st.write("**Tabelas SQL (SQLite):**", kb_stats["db_counts"])
            st.write("**Chunks de Políticas (ChromaDB):**", kb_stats["policy_chunks"])

    # Main chat header
    st.markdown(
        """
        <div style="background-color:#075E54;padding:14px 20px;border-radius:10px;color:white;margin-bottom:16px;">
            <h3 style="margin:0;color:white;">💬 Empório da Música — Canal Oficial WhatsApp</h3>
            <small>Rua 14 de Maio, 3200 - Centro, Campo Grande/MS | Seg-Sex 09h-18h, Sáb 09h-13h</small>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Render conversation messages
    for msg in st.session_state.chat_history:
        avatar = "🎸" if msg["role"] == "assistant" else "🧑"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])
            traces = msg.get("tool_traces") or []
            if traces:
                with st.expander(f"🛠️ Ferramentas acionadas ({len(traces)})", expanded=False):
                    for idx, trace in enumerate(traces, start=1):
                        st.markdown(f"**{idx}. `{trace.get('tool_name')}`**")
                        st.json(trace.get("args", {}))
                        if "output" in trace:
                            st.code(trace["output"][:1500], language="json")

    # Handle user input from chat box or sidebar quick scenario button
    user_input = st.chat_input("Digite sua mensagem para a Empório da Música...")
    active_query = selected_prompt or user_input

    if active_query:
        st.session_state.chat_history.append(
            {"role": "user", "content": active_query, "tool_traces": []}
        )
        with st.chat_message("user", avatar="🧑"):
            st.markdown(active_query)

        with st.chat_message("assistant", avatar="🎸"):
            with st.spinner("Consultando sistema da Empório da Música..."):
                try:
                    graph = get_cached_graph()
                    turn_result = run_agent_turn(
                        user_message=active_query,
                        thread_id=st.session_state.thread_id,
                        graph=graph,
                    )
                    reply_text = turn_result["reply"]
                    traces = turn_result.get("tool_traces", [])
                except Exception as exc:
                    reply_text = (
                        "⚠️ Não foi possível processar a resposta no momento. "
                        f"Verifique a configuração da sua chave de API no arquivo `.env`. Detalhe: `{exc}`"
                    )
                    traces = []

            st.markdown(reply_text)
            if traces:
                with st.expander(f"🛠️ Ferramentas acionadas ({len(traces)})", expanded=False):
                    for idx, trace in enumerate(traces, start=1):
                        st.markdown(f"**{idx}. `{trace.get('tool_name')}`**")
                        st.json(trace.get("args", {}))
                        if "output" in trace:
                            st.code(trace["output"][:1500], language="json")

        st.session_state.chat_history.append(
            {"role": "assistant", "content": reply_text, "tool_traces": traces}
        )
        if selected_prompt:
            st.rerun()


if __name__ == "__main__":
    main()
