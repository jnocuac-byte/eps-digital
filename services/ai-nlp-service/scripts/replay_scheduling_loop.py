"""Replay manual del guion de bucle con proveedores reales.

Uso:
    cd services/ai-nlp-service
    PYTHONPATH=. uv run python scripts/replay_scheduling_loop.py

Requiere las variables de proveedor y las URLs de Catalog/Citas configuradas.
"""

from __future__ import annotations

import asyncio
from collections import Counter
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

from app.agents.scheduling_agent import build_scheduling_agent
from app.agents.triage_agent import build_triage_agent
from app.agents import tools
from app.core.model_provider import build_fallback_model
from app.core.orchestrator import Orchestrator


MESSAGES = [
	"Tengo mucha fiebre y dolor de garganta",
	"Buscar disponibilidad",
	"Y tengo escalofríos",
	"Buscar disponibilidad",
	"Agéndame una cita con un médico general el día más pronto en cualquier sede",
	"Para las 7:20 de la mañana",
	"Cualquier sede",
	"Confirmo la cita, agéndala por favor",
	"SI CONFIRMO",
]


async def main() -> None:
	catalog_calls: list[tuple[int, str]] = []
	current_turn = 0
	original_catalog_call = tools._consultar_catalog_service

	def counted_catalog_call(endpoint, params=None):
		catalog_calls.append((current_turn, endpoint))
		return original_catalog_call(endpoint, params)

	tools._CATALOG_CACHE.clear()
	tools._consultar_catalog_service = counted_catalog_call
	try:
		triage_model = build_fallback_model(
			order=["gemini-1", "gemini-2", "gemini-3", "groq", "cerebras", "mistral"]
		)
		scheduling_model = build_fallback_model(
			order=["gemini-1", "gemini-2", "gemini-3", "cerebras", "mistral"]
		)
		orchestrator = Orchestrator(
			build_triage_agent(triage_model),
			build_scheduling_agent(scheduling_model),
		)
		conversation_id = str(uuid4())
		usuario_id = str(uuid4())
		history: list[dict[str, str]] = []

		for current_turn, message in enumerate(MESSAGES, start=1):
			before = len(catalog_calls)
			response, _ = await orchestrator.process(
				conversation_id,
				message,
				history,
				usuario_id=usuario_id,
			)
			turn_calls = catalog_calls[before:]
			print(f"\nTURN {current_turn}: {message}")
			print(f"CATALOG HTTP: {[endpoint for _, endpoint in turn_calls] or 'none'}")
			print(response)
			history.extend(
				[
					{"role": "user", "content": message},
					{"role": "assistant", "content": response},
				]
			)

		print("\nCATALOG HTTP COUNT BY TURN")
		for turn, count in sorted(Counter(turn for turn, _ in catalog_calls).items()):
			print(f"turn {turn}: {count}")
	finally:
		tools._consultar_catalog_service = original_catalog_call


if __name__ == "__main__":
	asyncio.run(main())
