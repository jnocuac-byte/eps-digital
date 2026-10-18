"""Carga datos de demostracion (catalogo + usuario de prueba) a traves del Ingress.

Uso:  python k8s/seed_demo.py https://<codespace>-8080.app.github.dev
Es idempotente: si ya hay servicios cargados, no repite el catalogo.
"""
import json
import sys
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080").rstrip("/")

DEMO_USER = {
    "nombres": "Paciente",
    "apellidos": "Demo",
    "tipo_documento": "CC",
    "numero_documento": "1234567890",
    "fecha_nacimiento": "1995-05-20",
    "correo": "paciente.demo@example.com",
    "telefono": "3001234567",
    "password": "Demo2026*Eps",
    "confirm_password": "Demo2026*Eps",
    "acepta_terminos": True,
}


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]


def post(path, body):
    status, res = call("POST", path, body)
    if status >= 300:
        raise SystemExit(f"POST {path} -> {status}: {res}")
    return res


def seed_catalogo():
    status, servicios = call("GET", "/api/catalogo/servicios")
    if status == 200 and servicios:
        print("Catalogo ya cargado: se omite.")
        return
    servicio = post("/api/catalogo/servicios", {
        "nombre": "Consulta Médica",
        "descripcion": "Consultas de medicina general y especializada",
        "icono": "stethoscope",
    })
    sedes = [
        post("/api/catalogo/sedes", s) for s in (
            {"nombre": "Sede Norte", "direccion": "Calle 100 # 15-20", "ciudad": "Bogotá", "telefono": "6015550101"},
            {"nombre": "Sede Centro", "direccion": "Carrera 7 # 32-10", "ciudad": "Bogotá", "telefono": "6015550102"},
        )
    ]
    especialidades = [
        ("Medicina General", "Atención primaria y valoración inicial", "Laura", "Gómez", "RM-10001"),
        ("Pediatría", "Atención médica de niños y adolescentes", "Carlos", "Ramírez", "RM-10002"),
        ("Cardiología", "Enfermedades del corazón y sistema circulatorio", "Andrea", "Torres", "RM-10003"),
        ("Dermatología", "Enfermedades de la piel", "Julián", "Herrera", "RM-10004"),
        ("Ginecología", "Salud de la mujer", "Marcela", "Ortiz", "RM-10005"),
        ("Ortopedia", "Huesos, articulaciones y músculos", "Felipe", "Castro", "RM-10006"),
    ]
    for i, (nombre, desc, nom, ape, reg) in enumerate(especialidades):
        esp = post("/api/catalogo/especialidades", {
            "servicio_id": servicio["servicio_id"], "nombre": nombre,
            "descripcion": desc, "duracion_cita_minutos": 30,
        })
        medico = post("/api/catalogo/medicos", {
            "nombres": nom, "apellidos": ape, "numero_registro": reg,
            "correo_institucional": f"{nom.lower()}.{ape.lower()}@epsdigital.example.com".replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u"),
        })
        post(f"/api/catalogo/medicos/{medico['medico_id']}/especialidades/{esp['especialidad_id']}?es_principal=true", None)
        sede = sedes[i % len(sedes)]
        for dia in range(1, 6):  # lunes a viernes
            post("/api/catalogo/disponibilidades", {
                "medico_id": medico["medico_id"], "especialidad_id": esp["especialidad_id"],
                "sede_id": sede["sede_id"], "dia_semana": dia,
                "hora_inicio": "08:00:00", "hora_fin": "17:00:00",
            })
        print(f"  + {nombre}: Dr(a). {nom} {ape} en {sede['nombre']}")
    print("Catalogo cargado.")


def crear_perfil(usuario_id):
    """Replica el 2do paso del registro del frontend: perfil en user-service."""
    perfil = {k: DEMO_USER[k] for k in ("nombres", "apellidos", "tipo_documento",
                                        "numero_documento", "fecha_nacimiento", "correo", "telefono")}
    perfil["usuario_id"] = usuario_id
    status, res = call("POST", "/api/user/usuarios", perfil)
    print(f"Perfil de usuario: HTTP {status}" + ("" if status < 300 else f" {res}"))


def seed_usuario(usuario_id=None):
    if usuario_id is None:
        status, res = call("POST", "/api/auth/auth/register", DEMO_USER)
        if status < 300:
            usuario_id = res["usuario_id"]
            print("Credencial demo creada.")
        else:
            print(f"Credencial demo: {status} {res} (puede que ya exista; pasa el usuario_id como 2do argumento)")
    if usuario_id:
        crear_perfil(usuario_id)
    status, res = call("POST", "/api/auth/auth/login/documento", {
        "tipo_documento": DEMO_USER["tipo_documento"],
        "numero_documento": DEMO_USER["numero_documento"],
        "password": DEMO_USER["password"],
    })
    print(f"Login de prueba: HTTP {status}")


if __name__ == "__main__":
    seed_catalogo()
    seed_usuario(sys.argv[2] if len(sys.argv) > 2 else None)
    print(f"\nListo. Entra a {BASE}  (CC 1234567890 / Demo2026*Eps)")
