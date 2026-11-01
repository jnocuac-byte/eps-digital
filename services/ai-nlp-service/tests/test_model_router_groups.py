"""Pruebas del ModelRouter de scheduling: expansión de grupos y orden de candidatos.

Usa un pool SIMULADO con ambos grupos (gemini-N y gemini-lite-N); no realiza
llamadas reales a los LLM ni consume cuota de API keys.
"""

import pytest

from strands.models.model import Model
from strands.models.routing.router import RoutingCandidate

from app.core.model_provider import _expand_group_names, build_fallback_model


class _FakeModel(Model):
    """Model mínimo para simular candidatos sin llamar a ningún LLM."""

    def __init__(self, name: str):
        self.name = name

    def update_config(self, **model_config):
        pass

    def get_config(self):
        return {}

    def structured_output(self, output_model, prompt):
        raise NotImplementedError

    def stream(self, messages, tools):
        raise NotImplementedError

    def count_tokens(self, messages, tools=None):
        return 0


def _fake_candidate(name: str) -> RoutingCandidate:
    return RoutingCandidate(model=_FakeModel(name), name=name)


def _fake_pool() -> dict:
    """Pool simulado con ambos grupos desordenados y un proveedor no-Gemini."""
    return {
        "gemini-2": _fake_candidate("gemini-2"),
        "gemini-lite-1": _fake_candidate("gemini-lite-1"),
        "gemini-1": _fake_candidate("gemini-1"),
        "gemini-lite-2": _fake_candidate("gemini-lite-2"),
        "groq": _fake_candidate("groq"),
        "cerebras": _fake_candidate("cerebras"),
    }


class TestExpandGroupNames:
    def test_grupo_gemini_excluye_nombres_lite(self):
        # El bug antiguo: startswith("gemini-") casaba con "gemini-lite-1" y
        # int("lite-1") lanzaba ValueError. Los patrones exactos lo evitan.
        names = _expand_group_names(_fake_pool().keys(), ["gemini"])
        assert names == ["gemini-1", "gemini-2"]

    def test_grupo_gemini_lite_excluye_completos_y_ordena_por_n(self):
        names = _expand_group_names(_fake_pool().keys(), ["gemini-lite"])
        assert names == ["gemini-lite-1", "gemini-lite-2"]

    def test_order_scheduling_expande_ambos_grupos(self):
        names = _expand_group_names(
            _fake_pool().keys(), ["gemini-lite", "groq", "gemini"]
        )
        assert names == ["gemini-lite-1", "gemini-lite-2", "groq", "gemini-1", "gemini-2"]

    def test_nombres_exactos_se_copian_tal_cual(self):
        names = _expand_group_names(_fake_pool().keys(), ["cerebras", "groq"])
        assert names == ["cerebras", "groq"]

    def test_nombre_inexistente_se_ignora(self):
        names = _expand_group_names(_fake_pool().keys(), ["mistral", "groq"])
        assert names == ["groq"]

    def test_orden_numerico_con_dos_digitos(self):
        pool = ["gemini-10", "gemini-2", "gemini-lite-10", "gemini-lite-2"]
        assert _expand_group_names(pool, ["gemini", "gemini-lite"]) == [
            "gemini-2",
            "gemini-10",
            "gemini-lite-2",
            "gemini-lite-10",
        ]

    def test_duplicados_se_eliminan_preservando_orden(self):
        names = _expand_group_names(
            _fake_pool().keys(), ["groq", "gemini-lite", "groq"]
        )
        assert names == ["groq", "gemini-lite-1", "gemini-lite-2"]


class TestBuildFallbackModelConPoolSimulado:
    @pytest.fixture(autouse=True)
    def _patch_pool(self, monkeypatch):
        monkeypatch.setattr(
            "app.core.model_provider._build_provider_pool", _fake_pool
        )

    def test_order_scheduling_usa_candidatos_en_orden_real(self):
        router = build_fallback_model(order=["gemini-lite", "groq", "gemini"])
        assert [c.name for c in router.candidates] == [
            "gemini-lite-1",
            "gemini-lite-2",
            "groq",
            "gemini-1",
            "gemini-2",
        ]

    def test_order_triage_no_incluye_lite(self):
        router = build_fallback_model(order=["gemini", "groq", "cerebras", "mistral"])
        assert [c.name for c in router.candidates] == [
            "gemini-1",
            "gemini-2",
            "groq",
            "cerebras",
        ]

    def test_pool_sin_gemini_sigue_funcionando_con_groq(self, monkeypatch):
        monkeypatch.setattr(
            "app.core.model_provider._build_provider_pool",
            lambda: {"groq": _fake_candidate("groq")},
        )
        router = build_fallback_model(order=["gemini-lite", "groq", "gemini"])
        assert [c.name for c in router.candidates] == ["groq"]

    def test_sin_coincidencias_cae_al_pool_completo(self, monkeypatch):
        monkeypatch.setattr(
            "app.core.model_provider._build_provider_pool",
            lambda: {"groq": _fake_candidate("groq")},
        )
        router = build_fallback_model(order=["gemini-lite"])
        assert [c.name for c in router.candidates] == ["groq"]
