"""PR4b: propiedad de la cita en cancelar y reprogramar (pytest, sin servicios externos).

Cobertura:
- cancelar cita ajena  -> 404 con el MISMO mensaje que "cita no encontrada", BD sin cambios.
- cancelar cita propia -> 200 y estado 'cancelada' en BD.
- reprogramar cita ajena -> 404, la cita queda intacta y el cupo destino sigue libre.
- reprogramar cita propia -> 200 (el check no rompe el flujo legitimo).
- sin header X-User-ID -> 422 (validacion de FastAPI; el header es requerido).
"""

from __future__ import annotations

from datetime import date, time
from uuid import uuid4

from app.crud import es_horario_ocupado
from app.models import Cita

USUARIO_PROPIETARIO = uuid4()
USUARIO_AJENO = uuid4()

FECHA_ORIGINAL = date(2027, 5, 10)
FECHA_DESTINO = date(2027, 5, 11)


def _crear_cita(db, usuario_id=None) -> Cita:
    """Inserta una cita 'programada' de 08:00-08:30 directamente en la BD."""
    cita = Cita(
        usuario_id=usuario_id or USUARIO_PROPIETARIO,
        medico_id=uuid4(),
        tipo_servicio="medicina_general",
        fecha_cita=FECHA_ORIGINAL,
        hora_inicio=time(8, 0),
        hora_fin=time(8, 30),
        sede_id=uuid4(),
    )
    db.add(cita)
    db.commit()
    db.refresh(cita)
    return cita


def test_cancelar_cita_ajena_devuelve_404_y_bd_sin_cambios(db, client):
    cita = _crear_cita(db)
    otro_cita_id = uuid4()

    resp_ajena = client.post(
        f"/citas/{cita.cita_id}/cancelar",
        json={"motivo": "intruso"},
        headers={"X-User-ID": str(USUARIO_AJENO)},
    )
    resp_inexistente = client.post(
        f"/citas/{otro_cita_id}/cancelar",
        json={"motivo": "intruso"},
        headers={"X-User-ID": str(USUARIO_AJENO)},
    )

    # Mismo codigo y misma forma de detalle que una cita inexistente: no se
    # revela la existencia (el mensaje solo refleja el id solicitado).
    assert resp_ajena.status_code == 404
    assert resp_inexistente.status_code == 404
    assert resp_ajena.json()["detail"].startswith("No existe cita con id")
    assert resp_inexistente.json()["detail"].startswith("No existe cita con id")

    db.refresh(cita)
    assert cita.estado == "programada"
    assert cita.fecha_cita == FECHA_ORIGINAL
    assert len(cita.historial_estados) == 0


def test_cancelar_cita_propia_devuelve_200(db, client):
    cita = _crear_cita(db)

    resp = client.post(
        f"/citas/{cita.cita_id}/cancelar",
        json={"motivo": "ya no puedo"},
        headers={"X-User-ID": str(USUARIO_PROPIETARIO)},
    )

    assert resp.status_code == 200
    assert resp.json()["estado"] == "cancelada"
    db.refresh(cita)
    assert cita.estado == "cancelada"
    assert len(cita.historial_estados) == 1
    assert str(cita.historial_estados[0].realizado_por) == str(USUARIO_PROPIETARIO)


def test_reprogramar_cita_ajena_no_toca_la_cita_ni_el_cupo(db, client):
    cita = _crear_cita(db)
    payload = {
        "nueva_fecha": str(FECHA_DESTINO),
        "nueva_hora_inicio": "10:00",
        "nueva_hora_fin": "10:30",
        "motivo": "intruso",
    }

    resp = client.post(
        f"/citas/{cita.cita_id}/reprogramar",
        json=payload,
        headers={"X-User-ID": str(USUARIO_AJENO)},
    )

    assert resp.status_code == 404
    db.refresh(cita)
    # La cita original queda intacta...
    assert cita.fecha_cita == FECHA_ORIGINAL
    assert cita.hora_inicio == time(8, 0)
    assert cita.estado == "programada"
    assert len(cita.historial_estados) == 0
    # ...y el cupo destino sigue libre (no hubo UPDATE).
    assert not es_horario_ocupado(
        db=db,
        medico_id=cita.medico_id,
        fecha=FECHA_DESTINO,
        hora_inicio=time(10, 0),
        hora_fin=time(10, 30),
    )


def test_reprogramar_cita_propia_devuelve_200(db, client):
    cita = _crear_cita(db)
    payload = {
        "nueva_fecha": str(FECHA_DESTINO),
        "nueva_hora_inicio": "10:00",
        "nueva_hora_fin": "10:30",
        "motivo": "cambio de planes",
    }

    resp = client.post(
        f"/citas/{cita.cita_id}/reprogramar",
        json=payload,
        headers={"X-User-ID": str(USUARIO_PROPIETARIO)},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["fecha_cita"] == str(FECHA_DESTINO)
    assert body["hora_inicio"].startswith("10:00")
    db.refresh(cita)
    assert cita.fecha_cita == FECHA_DESTINO
    assert cita.hora_inicio == time(10, 0)


def test_sin_header_x_user_id_da_422(client):
    """El header es requerido en ambos endpoints (antes: 400 opcional)."""
    resp_cancelar = client.post(
        f"/citas/{uuid4()}/cancelar", json={"motivo": None}
    )
    resp_reprogramar = client.post(
        f"/citas/{uuid4()}/reprogramar",
        json={
            "nueva_fecha": str(FECHA_DESTINO),
            "nueva_hora_inicio": "10:00",
            "nueva_hora_fin": "10:30",
        },
    )

    assert resp_cancelar.status_code == 422
    assert resp_reprogramar.status_code == 422
