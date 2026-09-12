import os
from typing import Optional

from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from .core.logger import log_event

_sendgrid_client: Optional[SendGridAPIClient] = None


def configurar_sendgrid() -> None:
	"""Configura el cliente de SendGrid usando SENDGRID_API_KEY desde .env."""
	global _sendgrid_client

	load_dotenv()
	api_key = os.getenv("SENDGRID_API_KEY")

	if not api_key:
		log_event("NOTIF", "SENDGRID", "error", "No se encontro SENDGRID_API_KEY en variables de entorno")
		_sendgrid_client = None
		return

	try:
		client = SendGridAPIClient(api_key=api_key)
		client.client.timeout = 30
		_sendgrid_client = client
		log_event("NOTIF", "SENDGRID", "info", "Cliente SendGrid configurado correctamente")
	except Exception as exc:
		_sendgrid_client = None
		log_event("NOTIF", "SENDGRID", "error", f"Error configurando SendGrid: {exc}")


def enviar_correo(destinatario: str, asunto: str, contenido_html: str) -> bool:
	"""Envia un correo HTML con SendGrid.

	Retorna:
		bool: True si el envio fue exitoso, False si ocurrio un error.
	"""
	global _sendgrid_client

	if _sendgrid_client is None:
		configurar_sendgrid()

	if _sendgrid_client is None:
		log_event("NOTIF", "SENDGRID", "error", "No se pudo inicializar cliente SendGrid")
		return False

	remitente = os.getenv("SENDGRID_FROM_EMAIL") or os.getenv("EMAIL_FROM")
	if not remitente:
		log_event("NOTIF", "SENDGRID", "error", "No se encontro remitente en SENDGRID_FROM_EMAIL o EMAIL_FROM")
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
			log_event("NOTIF", "SENDGRID", "info", f"Correo enviado a {destinatario}, status={response.status_code}")
			return True

		log_event("NOTIF", "SENDGRID", "error", f"SendGrid status={response.status_code} para {destinatario}: {response.body}")
		return False
	except Exception as exc:
		log_event("NOTIF", "SENDGRID", "error", f"Error enviando correo a {destinatario}: {exc}")
		return False
