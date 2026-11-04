"""Interactive command-line interface (CLI) for the Emporio da Musica AI Agent."""

from __future__ import annotations

import argparse
import uuid

from src.agent.graph import build_agent_graph, run_agent_turn
from src.database.ingest_csv import init_and_seed_database
from src.rag.ingest_pdf import index_policies_to_chroma


def main() -> None:
    """Run an interactive multi-turn CLI session with the Emporio da Musica agent."""
    parser = argparse.ArgumentParser(
        description="Empório da Música — Assistente Virtual de Atendimento (CLI)"
    )
    parser.add_argument(
        "--thread-id",
        type=str,
        default=f"cli-{uuid.uuid4().hex[:8]}",
        help="Session thread ID for SQLite conversation memory persistence.",
    )
    parser.add_argument(
        "--show-tools",
        action="store_true",
        help="Display intermediate tool invocations and arguments in the terminal.",
    )
    args = parser.parse_args()

    print("=" * 72)
    print("🎸 EMPÓRIO DA MÚSICA — Assistente Virtual via WhatsApp (Modo CLI)")
    print("Inicializando banco de dados relacional (SQLite) e políticas (ChromaDB)...")
    init_and_seed_database(force_reseed=False)
    index_policies_to_chroma(force_reindex=False)
    graph = build_agent_graph()

    print(f"Sessão ativa: {args.thread_id}")
    print("Comandos: '/novo' para reiniciar sessão | '/sair' ou 'exit' para encerrar.")
    print("=" * 72)
    print(
        "
Assistente: Olá! 🎶 Bem-vindo(a) à Empório da Música! "
        "Como posso te ajudar com instrumentos musicais, pedidos ou dúvidas hoje?
"
    )

    thread_id = args.thread_id
    while True:
        try:
            user_input = input("Cliente: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("
Encerrando atendimento. Até logo! 🎶")
            break

        if not user_input:
            continue

        if user_input.lower() in {"/sair", "sair", "exit", "quit"}:
            print("Assistente: Obrigado pelo contato com a Empório da Música! Até a próxima! 🎶")
            break

        if user_input.lower() in {"/novo", "/reset", "reset"}:
            thread_id = f"cli-{uuid.uuid4().hex[:8]}"
            print(f"
[Nova sessão iniciada: {thread_id}]
")
            continue

        turn = run_agent_turn(user_message=user_input, thread_id=thread_id, graph=graph)

        if args.show_tools and turn.get("tool_traces"):
            print("
  [Ferramentas Acionadas]:")
            for trace in turn["tool_traces"]:
                print(f"   -> {trace.get('tool_name')}({trace.get('args')})")

        print(f"
Assistente: {turn['reply']}
")


if __name__ == "__main__":
    main()
