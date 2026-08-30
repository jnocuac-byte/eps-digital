#!/usr/bin/env python3
"""
EPS Digital — Test interactivo del orquestador multi-agente (Fase 2).

Uso:
    cd services/ai-nlp-service
    python tests/interactive_cli.py

Requiere al menos una API key configurada (GROQ_API_KEY o GEMINI_API_KEY).
"""
from __future__ import annotations

import asyncio
import os
import sys
from uuid import uuid4

# Ajustar path para importar el paquete app/
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_APP_DIR = os.path.join(_SCRIPT_DIR, "..", "app")
sys.path.insert(0, _APP_DIR)

from core.conversation_state import ConversationState
from core.orchestrator import Orchestrator
from core.llm_provider import LLMProviderFactory


def _print_banner():
    print("=" * 60)
    print("  EPS Digital — Asistente IA Multi-Agente (CLI Test)")
    print("  Fase 2: Orchestrator + TriageAgent + SchedulingAgent")
    print("=" * 60)
    print()
    print("Comandos especiales:")
    print("  salir    — Terminar la conversación")
    print("  estado   — Ver el estado interno del orquestador")
    print("  reset    — Reiniciar la conversación")
    print("  historial — Ver mensajes intercambiados")
    print()


def _print_state(state: ConversationState):
    print(f"\n  [ Estado del orquestador ]")
    print(f"  Agente activo   : {state.active_agent}")
    print(f"  Especialidad    : {state.specialty_name or '—'}")
    print(f"  Síntomas        : {state.symptoms_summary or '—'}")
    print(f"  Urgencia        : {state.urgency_level or '—'}")
    print(f"  Bandera roja    : {'SÍ' if state.red_flag_detected else 'No'}")
    print(f"  Médico          : {state.selected_doctor_name or '—'}")
    print(f"  Sede            : {state.selected_sede_name or '—'}")
    print(f"  Fecha           : {state.selected_date or '—'}")
    print(f"  Hora            : {state.selected_time or '—'}")
    print(f"  Confirmación    : {'Pendiente' if state.pending_confirmation else 'No'}")
    print(f"  Mensajes        : {state.message_count}")
    print()


async def main():
    _print_banner()

    # Inicializar factory LLM
    try:
        factory = LLMProviderFactory()
    except ValueError as exc:
        print(f"ERROR: {exc}")
        print("Configura al menos GROQ_API_KEY o GEMINI_API_KEY en tu .env")
        return

    orchestrator = Orchestrator(factory)
    conv_id = str(uuid4())
    history: list[dict[str, str]] = []
    usuario_id = os.getenv("TEST_USUARIO_ID", str(uuid4()))

    print(f"Proveedor LLM : {', '.join(factory.provider_names)}")
    print(f"Conversación ID: {conv_id[:8]}...")
    print(f"Usuario ID     : {usuario_id[:8]}...")
    print()

    while True:
        try:
            user_input = input("Tú: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n¡Hasta luego!")
            break

        if not user_input:
            continue

        # Comandos especiales
        if user_input.lower() == "salir":
            print("\n¡Hasta luego!")
            break

        if user_input.lower() == "estado":
            state = orchestrator.get_state(conv_id)
            _print_state(state)
            continue

        if user_input.lower() == "reset":
            conv_id = str(uuid4())
            history.clear()
            print(f"\n  Conversación reiniciada. Nuevo ID: {conv_id[:8]}...")
            continue

        if user_input.lower() == "historial":
            if not history:
                print("\n  (sin mensajes)")
            else:
                for msg in history:
                    role = "Tú" if msg["role"] == "user" else "Asistente"
                    print(f"  {role}: {msg['content'][:120]}...")
            print()
            continue

        # Agregar mensaje al historial
        history.append({"role": "user", "content": user_input})

        # Procesar con el orquestador
        try:
            response, state = await orchestrator.process(
                conversation_id=conv_id,
                message=user_input,
                history=history,
                usuario_id=usuario_id,
            )
        except Exception as exc:
            print(f"\n  ERROR: {exc}\n")
            continue

        # Agregar respuesta al historial
        history.append({"role": "assistant", "content": response})

        # Mostrar respuesta
        print(f"\nAsistente: {response}")
        print(
            f"[ agente={state.active_agent} | "
            f"esp={state.specialty_name or '—'} | "
            f"urg={state.urgency_level or '—'} ]\n"
        )

    print("Conversación finalizada.")


if __name__ == "__main__":
    asyncio.run(main())
