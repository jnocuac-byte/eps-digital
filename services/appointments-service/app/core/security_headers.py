"""Cabeceras de seguridad HTTP para los microservicios (H-22).

Inyecta cabeceras de seguridad estandar en todas las respuestas, incluidas las
de error, mediante un middleware ASGI. Se registra despues del middleware CORS
(en ``main.py``) para quedar en el anillo externo de la pila de middlewares.

Cabeceras aplicadas:

- ``Strict-Transport-Security`` (HSTS): solo si la peticion llega por HTTPS y
  HSTS esta habilitado. Detecta el esquema real detras de un proxy leyendo
  ``X-Forwarded-Proto``.
- ``X-Content-Type-Options: nosniff``
- ``X-Frame-Options: DENY``
- ``X-XSS-Protection: 1; mode=block``
- ``Content-Security-Policy``: politica restrictiva para la API y una politica
  relajada para Swagger UI / ReDoc (que cargan recursos desde CDN).
- ``Referrer-Policy`` y ``Permissions-Policy``.

Variable de entorno
-------------------
``ENABLE_HSTS``
    ``false``/``0``/``no``/``off`` desactiva HSTS. Por defecto habilitado; aun
    asi HSTS solo se emite cuando la peticion es HTTPS.
"""
from __future__ import annotations

import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

_HSTS_VALUE = "max-age=31536000; includeSubDomains"

#: CSP para respuestas de API (JSON): no se carga ningun recurso.
_CSP_API = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"

#: CSP relajada para la documentacion interactiva (Swagger UI / ReDoc usan CDN).
_CSP_DOCS = (
	"default-src 'self'; "
	"script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
	"style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
	"img-src 'self' data: https://fastapi.tiangolo.com https://cdn.jsdelivr.net; "
	"font-src 'self' https://cdn.jsdelivr.net; "
	"frame-ancestors 'none'; base-uri 'self'"
)

_STATIC_HEADERS = {
	"X-Content-Type-Options": "nosniff",
	"X-Frame-Options": "DENY",
	"X-XSS-Protection": "1; mode=block",
	"Referrer-Policy": "strict-origin-when-cross-origin",
	"Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}

_DOCS_PREFIXES = ("/docs", "/redoc", "/openapi.json")


def _env_flag(name: str, default: bool) -> bool:
	"""Lee una bandera booleana del entorno."""
	raw = os.getenv(name)
	if raw is None:
		return default
	return raw.strip().lower() not in {"0", "false", "no", "off", ""}


def _is_https(request: Request) -> bool:
	"""Determina si la peticion original fue HTTPS (contempla proxies)."""
	forwarded = request.headers.get("x-forwarded-proto")
	if forwarded:
		return forwarded.split(",")[0].strip().lower() == "https"
	return request.url.scheme == "https"


def _is_docs_path(path: str) -> bool:
	"""Indica si la ruta corresponde a la documentacion interactiva."""
	return any(path == prefix or path.startswith(prefix) for prefix in _DOCS_PREFIXES)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
	"""Middleware que agrega cabeceras de seguridad a cada respuesta."""

	def __init__(self, app: ASGIApp, enable_hsts: bool | None = None) -> None:
		super().__init__(app)
		self.enable_hsts = _env_flag("ENABLE_HSTS", True) if enable_hsts is None else enable_hsts

	async def dispatch(self, request: Request, call_next):
		response = await call_next(request)

		for header, value in _STATIC_HEADERS.items():
			response.headers.setdefault(header, value)

		csp = _CSP_DOCS if _is_docs_path(request.url.path) else _CSP_API
		response.headers.setdefault("Content-Security-Policy", csp)

		if self.enable_hsts and _is_https(request):
			response.headers.setdefault("Strict-Transport-Security", _HSTS_VALUE)

		return response


def register_security_headers(app, enable_hsts: bool | None = None) -> None:
	"""Registra el middleware de cabeceras de seguridad en la app FastAPI.

	Debe invocarse despues de ``app.add_middleware(CORSMiddleware, ...)`` para
	quedar por fuera del CORS y decorar tambien respuestas de error y preflight.
	"""
	app.add_middleware(SecurityHeadersMiddleware, enable_hsts=enable_hsts)
