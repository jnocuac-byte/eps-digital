from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RedFlagDetection(BaseModel):
    """Resultado de detección de banderas rojas de urgencia vital."""

    detected: bool = Field(
        description="True si se detectó una bandera roja de urgencia vital."
    )
    sintoma_critico: str | None = Field(
        default=None,
        description="Descripción del síntoma crítico que activó la alerta.",
    )


class TriageAnalysis(BaseModel):
    """
    Salida estructurada del agente de triaje.
    Se usa como intermedio; luego se transforma a ClasificacionSintomasResponse
    para el contrato con el Frontend.
    """

    nivel_urgencia: Literal["urgente", "prioritario", "programable"] = Field(
        description="Nivel de clasificación del triaje según gravedad."
    )
    especialidad_sugerida_id: str = Field(
        description="ID exacto de la especialidad (ej. 'medicina_general')."
    )
    especialidad_sugerida_nombre: str = Field(
        description="Nombre legible de la especialidad."
    )
    resumen_clinico: str = Field(
        description="Síntesis técnica corta de los síntomas para el médico."
    )
    red_flag: RedFlagDetection = Field(
        description="Información sobre banderas rojas detectadas."
    )
    confianza: float = Field(
        ge=0.0,
        le=1.0,
        description="Grado de certidumbre en la clasificación.",
    )
    explicacion_al_paciente: str = Field(
        description="Explicación empática para el paciente."
    )
