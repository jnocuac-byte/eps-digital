from html import escape

COLOR_AZUL_MARINO = "#2B3E59"


def _layout_email(titulo: str, saludo: str, contenido: str, pie: str) -> str:
	"""Construye un layout base para correos HTML con estilo institucional."""
	return f"""
<!DOCTYPE html>
<html lang="es">
<head>
	<meta charset="UTF-8" />
	<meta name="viewport" content="width=device-width, initial-scale=1.0" />
	<title>{titulo}</title>
</head>
<body style="margin:0; padding:0; background-color:#f4f7fb; font-family:Arial, sans-serif; color:#1f2937;">
	<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="padding:24px 12px;">
		<tr>
			<td align="center">
				<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:640px; background:#ffffff; border:1px solid #e5e7eb; border-radius:12px; overflow:hidden;">
					<tr>
						<td style="background:{COLOR_AZUL_MARINO}; padding:20px 24px; color:#ffffff; font-size:20px; font-weight:700;">
							EPS Digital
						</td>
					</tr>
					<tr>
						<td style="padding:24px; font-size:15px; line-height:1.6;">
							<p style="margin:0 0 14px 0;">{saludo}</p>
							{contenido}
							<p style="margin:18px 0 0 0;">{pie}</p>
						</td>
					</tr>
					<tr>
						<td style="padding:16px 24px; background:#f8fafc; font-size:12px; color:#6b7280;">
							Este es un mensaje automático de EPS Digital. Por favor, no responder este correo.
						</td>
					</tr>
				</table>
			</td>
		</tr>
	</table>
</body>
</html>
""".strip()


def confirmacion_cita(
	nombre: str, fecha: str, hora: str, especialidad: str, sede: str
) -> str:
	nombre_e = escape(nombre)
	fecha_e = escape(fecha)
	hora_e = escape(hora)
	especialidad_e = escape(especialidad)
	sede_e = escape(sede)

	contenido = f"""
<p style="margin:0 0 12px 0;">Tu cita ha sido confirmada con los siguientes datos:</p>
<table role="presentation" cellspacing="0" cellpadding="0" style="width:100%; border-collapse:collapse; margin:8px 0 12px 0;">
	<tr><td style="padding:8px; border:1px solid #e5e7eb;"><strong>Fecha</strong></td><td style="padding:8px; border:1px solid #e5e7eb;">{fecha_e}</td></tr>
	<tr><td style="padding:8px; border:1px solid #e5e7eb;"><strong>Hora</strong></td><td style="padding:8px; border:1px solid #e5e7eb;">{hora_e}</td></tr>
	<tr><td style="padding:8px; border:1px solid #e5e7eb;"><strong>Especialidad</strong></td><td style="padding:8px; border:1px solid #e5e7eb;">{especialidad_e}</td></tr>
	<tr><td style="padding:8px; border:1px solid #e5e7eb;"><strong>Sede</strong></td><td style="padding:8px; border:1px solid #e5e7eb;">{sede_e}</td></tr>
</table>
<p style="margin:0;">Te recomendamos llegar con al menos 15 minutos de anticipación.</p>
"""

	return _layout_email(
		titulo="Confirmación de cita",
		saludo=f"Hola {nombre_e},",
		contenido=contenido,
		pie="Gracias por confiar en nuestros servicios de salud.",
	)


def cancelacion_cita(nombre: str, fecha: str, hora: str, especialidad: str) -> str:
	nombre_e = escape(nombre)
	fecha_e = escape(fecha)
	hora_e = escape(hora)
	especialidad_e = escape(especialidad)

	contenido = f"""
<p style="margin:0 0 12px 0;">Te informamos que tu cita fue cancelada.</p>
<ul style="margin:0 0 12px 18px; padding:0;">
	<li><strong>Fecha:</strong> {fecha_e}</li>
	<li><strong>Hora:</strong> {hora_e}</li>
	<li><strong>Especialidad:</strong> {especialidad_e}</li>
</ul>
<p style="margin:0;">Si deseas, puedes agendar una nueva cita desde la plataforma.</p>
"""

	return _layout_email(
		titulo="Cancelación de cita",
		saludo=f"Hola {nombre_e},",
		contenido=contenido,
		pie="Lamentamos cualquier inconveniente.",
	)


def recordatorio_cita(
	nombre: str, fecha: str, hora: str, especialidad: str, sede: str
) -> str:
	nombre_e = escape(nombre)
	fecha_e = escape(fecha)
	hora_e = escape(hora)
	especialidad_e = escape(especialidad)
	sede_e = escape(sede)

	contenido = f"""
<p style="margin:0 0 12px 0;">Este es un recordatorio de tu cita médica en menos de 24 horas.</p>
<table role="presentation" cellspacing="0" cellpadding="0" style="width:100%; border-collapse:collapse; margin:8px 0 12px 0;">
	<tr><td style="padding:8px; border:1px solid #e5e7eb;"><strong>Fecha</strong></td><td style="padding:8px; border:1px solid #e5e7eb;">{fecha_e}</td></tr>
	<tr><td style="padding:8px; border:1px solid #e5e7eb;"><strong>Hora</strong></td><td style="padding:8px; border:1px solid #e5e7eb;">{hora_e}</td></tr>
	<tr><td style="padding:8px; border:1px solid #e5e7eb;"><strong>Especialidad</strong></td><td style="padding:8px; border:1px solid #e5e7eb;">{especialidad_e}</td></tr>
	<tr><td style="padding:8px; border:1px solid #e5e7eb;"><strong>Sede</strong></td><td style="padding:8px; border:1px solid #e5e7eb;">{sede_e}</td></tr>
</table>
<p style="margin:0;">Recuerda llevar tus documentos y orden médica si aplica.</p>
"""

	return _layout_email(
		titulo="Recordatorio de cita",
		saludo=f"Hola {nombre_e},",
		contenido=contenido,
		pie="Nos vemos pronto.",
	)


def recuperacion_password(nombre: str, token: str, link_base: str) -> str:
	nombre_e = escape(nombre)
	token_e = escape(token)
	link_base_limpio = link_base.rstrip("/")
	enlace = f"{link_base_limpio}/{token_e}"
	enlace_e = escape(enlace)

	contenido = f"""
<p style="margin:0 0 12px 0;">Recibimos una solicitud para restablecer tu contraseña.</p>
<p style="margin:0 0 16px 0;">Para continuar, haz clic en el siguiente botón:</p>
<p style="margin:0 0 16px 0;">
	<a href="{enlace_e}" style="display:inline-block; background:{COLOR_AZUL_MARINO}; color:#ffffff; text-decoration:none; padding:10px 16px; border-radius:8px; font-weight:600;">
		Restablecer contraseña
	</a>
</p>
<p style="margin:0 0 8px 0;">Si el botón no funciona, copia y pega este enlace en tu navegador:</p>
<p style="margin:0; word-break:break-all;"><a href="{enlace_e}">{enlace_e}</a></p>
"""

	return _layout_email(
		titulo="Recuperación de contraseña",
		saludo=f"Hola {nombre_e},",
		contenido=contenido,
		pie="Si no solicitaste este cambio, puedes ignorar este mensaje.",
	)


def bienvenida(nombre: str) -> str:
	nombre_e = escape(nombre)

	contenido = """
<p style="margin:0 0 12px 0;">Tu cuenta ha sido creada correctamente en EPS Digital.</p>
<p style="margin:0 0 12px 0;">Desde ahora podrás gestionar tus citas, revisar información de tus servicios y recibir notificaciones importantes.</p>
<p style="margin:0;">Estamos para ayudarte en tu proceso de atención en salud.</p>
"""

	return _layout_email(
		titulo="Bienvenida a EPS Digital",
		saludo=f"Hola {nombre_e},",
		contenido=contenido,
		pie="Gracias por registrarte.",
	)
