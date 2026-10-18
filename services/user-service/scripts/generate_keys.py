"""Genera las llaves de cifrado HCE (H-22) para el User Service.

Uso::

    python services/user-service/scripts/generate_keys.py

Imprime las lineas listas para pegar en el archivo ``.env`` del servicio. No
escribe archivos: la gestion de secretos (Render/K8s) es responsabilidad del
despliegue.

- ``HCE_ENCRYPTION_KEYS``: llaves Fernet separadas por coma. La primera cifra;
  las siguientes permiten descifrar durante una rotacion.
- ``HCE_BLIND_INDEX_KEY``: secreto independiente y estable para el indice ciego.
"""
from __future__ import annotations

import secrets

from cryptography.fernet import Fernet


def main() -> None:
    fernet_key = Fernet.generate_key().decode()
    blind_index_key = secrets.token_urlsafe(48)

    print("# --- Cifrado en reposo HCE (H-22) ---")
    print(f"HCE_ENCRYPTION_KEYS={fernet_key}")
    print(f"HCE_BLIND_INDEX_KEY={blind_index_key}")
    print("HCE_ALLOW_PLAINTEXT_FALLBACK=false")
    print()
    print("# Rotacion: anteponer la nueva llave y conservar las anteriores, p. ej.:")
    print("# HCE_ENCRYPTION_KEYS=<llave_nueva>,<llave_actual>")


if __name__ == "__main__":
    main()
