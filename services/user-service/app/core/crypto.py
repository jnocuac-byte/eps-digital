"""Cifrado a nivel de columna (HCE) para el User Service.

Implementa dos capacidades de la historia H-22:

1. Cifrado en reposo transparente para SQLAlchemy mediante ``EncryptedString``,
   un ``TypeDecorator`` que cifra al escribir y descifra al leer usando Fernet
   (cifrado simetrico autenticado con ``cryptography``). Soporta rotacion de
   llaves con ``MultiFernet``: la primera llave cifra y cualquiera de la lista
   descifra.

2. Indice ciego determinista (``blind_index``) basado en HMAC-SHA256. Permite
   seguir haciendo busquedas por igualdad y mantener restricciones UNIQUE sobre
   columnas cifradas sin descifrar en la base de datos (p. ej. numero de
   documento y correo).

Variables de entorno
--------------------
``HCE_ENCRYPTION_KEYS``
    Llaves Fernet separadas por coma. La **primera** es la llave primaria (con
    la que se cifra); las demas permiten descifrar datos cifrados con llaves
    anteriores durante una rotacion.
``HCE_BLIND_INDEX_KEY``
    Secreto independiente y estable para el indice ciego. **No** debe rotarse
    junto con las llaves Fernet; si cambia, todos los indices cambian y hay que
    re-indexar.
``HCE_ALLOW_PLAINTEXT_FALLBACK``
    ``true``/``1`` para permitir leer (solo durante una migracion) valores que
    aun no estan cifrados. Por defecto desactivado.

Generacion de llaves (ver tambien ``scripts/generate_keys.py``)::

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    python -c "import secrets; print(secrets.token_urlsafe(48))"
"""
from __future__ import annotations

import hashlib
import hmac
import os

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

ENV_ENCRYPTION_KEYS = "HCE_ENCRYPTION_KEYS"
ENV_BLIND_INDEX_KEY = "HCE_BLIND_INDEX_KEY"
ENV_ALLOW_PLAINTEXT = "HCE_ALLOW_PLAINTEXT_FALLBACK"

#: Valores que se interpretan como "verdadero" para las banderas de entorno.
_TRUTHY = {"1", "true", "yes", "on"}


class CryptoConfigurationError(RuntimeError):
	"""Configuracion de cifrado ausente o invalida."""


_fernet: MultiFernet | None = None
_blind_key: bytes | None = None


def _load_fernet() -> MultiFernet:
	"""Construye (una sola vez) el ``MultiFernet`` desde ``HCE_ENCRYPTION_KEYS``."""
	global _fernet
	if _fernet is not None:
		return _fernet

	raw = (os.getenv(ENV_ENCRYPTION_KEYS) or "").strip()
	if not raw:
		raise CryptoConfigurationError(
			f"{ENV_ENCRYPTION_KEYS} no esta configurada. Define al menos una llave "
			"Fernet (genera una con: python -c \"from cryptography.fernet import "
			"Fernet; print(Fernet.generate_key().decode())\")."
		)

	keys: list[Fernet] = []
	for candidate in raw.split(","):
		candidate = candidate.strip()
		if not candidate:
			continue
		try:
			keys.append(Fernet(candidate.encode("utf-8")))
		except (ValueError, TypeError) as exc:
			raise CryptoConfigurationError(
				f"{ENV_ENCRYPTION_KEYS} contiene una llave Fernet invalida: {exc}"
			) from exc

	if not keys:
		raise CryptoConfigurationError(
			f"{ENV_ENCRYPTION_KEYS} no contiene ninguna llave valida."
		)

	_fernet = MultiFernet(keys)
	return _fernet


def _load_blind_key() -> bytes:
	"""Obtiene (una sola vez) el secreto HMAC del indice ciego."""
	global _blind_key
	if _blind_key is not None:
		return _blind_key

	raw = (os.getenv(ENV_BLIND_INDEX_KEY) or "").strip()
	if not raw:
		raise CryptoConfigurationError(
			f"{ENV_BLIND_INDEX_KEY} no esta configurada. Define un secreto "
			"independiente (idealmente >= 32 bytes) para el indice ciego."
		)
	_blind_key = raw.encode("utf-8")
	return _blind_key


def _allow_plaintext_fallback() -> bool:
	"""Indica si se permite leer valores aun no cifrados (modo migracion)."""
	return (os.getenv(ENV_ALLOW_PLAINTEXT) or "").strip().lower() in _TRUTHY


def reset_cache() -> None:
	"""Limpia las llaves memorizadas (util en pruebas y tras cambiar el entorno)."""
	global _fernet, _blind_key
	_fernet = None
	_blind_key = None


def validate_crypto_config() -> None:
	"""Valida al arranque que la configuracion de cifrado este presente y sea correcta.

	Levanta ``CryptoConfigurationError`` si falta o es invalida, para fallar rapido
	en lugar de escribir datos sin proteger.
	"""
	_load_fernet()
	_load_blind_key()


def encrypt_value(value: str | None) -> str | None:
	"""Cifra un texto con Fernet. Devuelve ``None`` si el valor es ``None``."""
	if value is None:
		return None
	return _load_fernet().encrypt(str(value).encode("utf-8")).decode("ascii")


def decrypt_value(value: str | None) -> str | None:
	"""Descifra un token Fernet.

	Con ``HCE_ALLOW_PLAINTEXT_FALLBACK`` habilitado retorna el valor original si
	no es un token valido (util durante la transicion de datos sin cifrar).
	"""
	if value is None:
		return None
	try:
		return _load_fernet().decrypt(str(value).encode("ascii")).decode("utf-8")
	except (InvalidToken, ValueError, TypeError):
		if _allow_plaintext_fallback():
			return value
		raise


def is_encrypted(value: str | None) -> bool:
	"""Indica si el valor ya es un token Fernet valido (descifrable con la llave)."""
	if value is None:
		return False
	try:
		_load_fernet().decrypt(str(value).encode("ascii"))
		return True
	except (InvalidToken, ValueError, TypeError):
		return False


def blind_index(value: str | None, *, casefold: bool = False) -> str | None:
	"""Calcula el indice ciego (HMAC-SHA256 en hex) de un valor.

	Sirve para buscar por igualdad y para restricciones UNIQUE sobre columnas
	cifradas. La normalizacion debe ser identica al escribir y al consultar.

	Args:
		value: Valor en claro. Se le aplica ``strip()``.
		casefold: Si es ``True``, normaliza a minusculas (p. ej. correos).
	"""
	if value is None:
		return None
	normalized = str(value).strip()
	if casefold:
		normalized = normalized.lower()
	return hmac.new(
		_load_blind_key(),
		normalized.encode("utf-8"),
		hashlib.sha256,
	).hexdigest()


class EncryptedString(TypeDecorator):
	"""Tipo SQLAlchemy que cifra/descifra transparentemente con Fernet.

	El valor en Python (y en la API) sigue siendo texto plano; en la base de
	datos se almacena el token Fernet, por eso la columna subyacente es ``TEXT``.
	"""

	impl = Text
	cache_ok = True

	def process_bind_param(self, value, dialect):
		"""Cifra el valor antes de enviarlo a la base de datos."""
		return encrypt_value(value)

	def process_result_value(self, value, dialect):
		"""Descifra el valor leido desde la base de datos."""
		return decrypt_value(value)
