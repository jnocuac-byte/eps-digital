import logging
import os
from typing import Optional

from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

logger = logging.getLogger(__name__)

_sendgrid_client: Optional[SendGridAPIClient] = None


def configurar_sendgrid() -> None:
	"""Configura el cliente de SendGrid usando SENDGRID_API_KEY desde .env."""
	global _sendgrid_client

	load_dotenv()
	api_key = os.getenv("SENDGRID_API_KEY")

	if not api_key:
		logger.error("No se encontró SENDGRID_API_KEY en las variables de entorno.")
		_sendgrid_client = None
		return

	try:
		client = SendGridAPIClient(api_key=api_key)
		# El cliente interno de python-http-client respeta este timeout en segundos.
		client.client.timeout = 30
		_sendgrid_client = client
		logger.info("Cliente de SendGrid configurado correctamente.")
	except Exception as exc:
		_sendgrid_client = None
		logger.exception("Error al configurar SendGrid: %s", exc)


def enviar_correo(destinatario: str, asunto: str, contenido_html: str) -> bool:
	"""Envía un correo HTML con SendGrid.

	Retorna:
		bool: True si el envío fue exitoso, False si ocurrió un error.
	"""
	global _sendgrid_client

	if _sendgrid_client is None:
		configurar_sendgrid()

	if _sendgrid_client is None:
		logger.error("No se pudo inicializar el cliente de SendGrid.")
		return False

	remitente = os.getenv("SENDGRID_FROM_EMAIL") or os.getenv("EMAIL_FROM")
	if not remitente:
		logger.error(
			"No se encontró remitente en SENDGRID_FROM_EMAIL o EMAIL_FROM."
		)
		return False

	try:
		message = Mail(
			from_email=remitente,
			to_emails=destinatario,
			subject=asunto,
			html_content=contenido_html,
		)
		response = _sendgrid_client.send(message)

		if 200 <= response.status_code < 300:
			logger.info(
				"Correo enviado a %s con estado HTTP %s.",
				destinatario,
				response.status_code,
			)
			return True

		logger.error(
			"SendGrid devolvió estado HTTP %s al enviar a %s. Respuesta: %s",
			response.status_code,
			destinatario,
			response.body,
		)
		return False
	except Exception as exc:
		logger.exception("Error enviando correo a %s: %s", destinatario, exc)
		return False
