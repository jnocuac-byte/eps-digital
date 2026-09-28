-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.alembic_version_user (
  version_num character varying NOT NULL,
  CONSTRAINT alembic_version_user_pkey PRIMARY KEY (version_num)
);
CREATE TABLE public.alembic_version_citas (
  version_num character varying NOT NULL,
  CONSTRAINT alembic_version_citas_pkey PRIMARY KEY (version_num)
);
CREATE TABLE public.alembic_version_catalogo (
  version_num character varying NOT NULL,
  CONSTRAINT alembic_version_catalogo_pkey PRIMARY KEY (version_num)
);
CREATE TABLE public.alembic_version_notifications (
  version_num character varying NOT NULL,
  CONSTRAINT alembic_version_notifications_pkey PRIMARY KEY (version_num)
);
CREATE TABLE public.alembic_version_ainlp (
  version_num character varying NOT NULL,
  CONSTRAINT alembic_version_ainlp_pkey PRIMARY KEY (version_num)
);
CREATE TABLE public.credenciales (
  credencial_id uuid NOT NULL DEFAULT gen_random_uuid(),
  usuario_id uuid NOT NULL UNIQUE,
  correo character varying NOT NULL UNIQUE,
  password_hash character varying NOT NULL,
  rol character varying NOT NULL DEFAULT 'usuario'::character varying,
  activo boolean NOT NULL DEFAULT true,
  intentos_fallidos smallint NOT NULL DEFAULT 0,
  bloqueado_hasta timestamp without time zone,
  tiene_2fa boolean NOT NULL DEFAULT false,
  medico_id uuid,
  creado_en timestamp without time zone NOT NULL,
  actualizado_en timestamp without time zone NOT NULL,
  CONSTRAINT credenciales_pkey PRIMARY KEY (credencial_id)
);
CREATE TABLE public.log_autenticacion (
  log_id uuid NOT NULL DEFAULT gen_random_uuid(),
  credencial_id uuid NOT NULL,
  evento character varying NOT NULL,
  ip_origen character varying,
  agente_usuario text,
  creado_en timestamp without time zone NOT NULL,
  CONSTRAINT log_autenticacion_pkey PRIMARY KEY (log_id),
  CONSTRAINT log_autenticacion_credencial_id_fkey FOREIGN KEY (credencial_id) REFERENCES public.credenciales(credencial_id)
);
CREATE TABLE public.registro_2fa (
  registro_id uuid NOT NULL DEFAULT gen_random_uuid(),
  credencial_id uuid NOT NULL,
  codigo_hash character varying NOT NULL,
  expira_en timestamp without time zone NOT NULL,
  usado boolean NOT NULL DEFAULT false,
  creado_en timestamp without time zone NOT NULL,
  CONSTRAINT registro_2fa_pkey PRIMARY KEY (registro_id),
  CONSTRAINT registro_2fa_credencial_id_fkey FOREIGN KEY (credencial_id) REFERENCES public.credenciales(credencial_id)
);
CREATE TABLE public.token_recuperacion (
  token_id uuid NOT NULL DEFAULT gen_random_uuid(),
  credencial_id uuid NOT NULL,
  token_hash character varying NOT NULL UNIQUE,
  expira_en timestamp without time zone NOT NULL,
  usado boolean NOT NULL DEFAULT false,
  creado_en timestamp without time zone NOT NULL,
  CONSTRAINT token_recuperacion_pkey PRIMARY KEY (token_id),
  CONSTRAINT token_recuperacion_credencial_id_fkey FOREIGN KEY (credencial_id) REFERENCES public.credenciales(credencial_id)
);
CREATE TABLE public.usuarios (
  usuario_id uuid NOT NULL DEFAULT gen_random_uuid(),
  nombres character varying NOT NULL,
  apellidos character varying NOT NULL,
  tipo_documento character varying NOT NULL,
  numero_documento character varying NOT NULL UNIQUE,
  fecha_nacimiento date NOT NULL,
  telefono character varying,
  correo character varying NOT NULL UNIQUE,
  creado_en timestamp without time zone NOT NULL,
  actualizado_en timestamp without time zone NOT NULL,
  CONSTRAINT usuarios_pkey PRIMARY KEY (usuario_id)
);
CREATE TABLE public.afiliaciones (
  afiliacion_id uuid NOT NULL DEFAULT gen_random_uuid(),
  usuario_id uuid NOT NULL UNIQUE,
  tipo_afiliacion character varying NOT NULL,
  numero_poliza character varying NOT NULL UNIQUE,
  estado character varying NOT NULL DEFAULT 'activo'::character varying,
  fecha_afiliacion date NOT NULL,
  medico_asignado_id uuid,
  creado_en timestamp without time zone NOT NULL,
  actualizado_en timestamp without time zone NOT NULL,
  CONSTRAINT afiliaciones_pkey PRIMARY KEY (afiliacion_id),
  CONSTRAINT afiliaciones_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios(usuario_id)
);
CREATE TABLE public.informacion_medica (
  info_medica_id uuid NOT NULL DEFAULT gen_random_uuid(),
  usuario_id uuid NOT NULL UNIQUE,
  tipo_sangre character varying,
  alergias text,
  enfermedades_cronicas text,
  medicamentos_actuales text,
  actualizado_en timestamp without time zone NOT NULL,
  CONSTRAINT informacion_medica_pkey PRIMARY KEY (info_medica_id),
  CONSTRAINT informacion_medica_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios(usuario_id)
);
CREATE TABLE public.citas (
  cita_id uuid NOT NULL,
  usuario_id uuid NOT NULL,
  medico_id uuid NOT NULL,
  especialidad_id uuid,
  tipo_servicio character varying NOT NULL,
  fecha_cita date NOT NULL,
  hora_inicio time without time zone NOT NULL,
  hora_fin time without time zone NOT NULL,
  sede_id uuid NOT NULL,
  descripcion_sintomas text,
  estado character varying NOT NULL,
  creado_en timestamp without time zone NOT NULL,
  actualizado_en timestamp without time zone NOT NULL,
  CONSTRAINT citas_pkey PRIMARY KEY (cita_id)
);
CREATE TABLE public.historial_estado (
  historial_id uuid NOT NULL,
  cita_id uuid NOT NULL,
  estado_anterior character varying NOT NULL,
  estado_nuevo character varying NOT NULL,
  motivo text,
  realizado_por uuid NOT NULL,
  creado_en timestamp without time zone NOT NULL,
  CONSTRAINT historial_estado_pkey PRIMARY KEY (historial_id),
  CONSTRAINT historial_estado_cita_id_fkey FOREIGN KEY (cita_id) REFERENCES public.citas(cita_id)
);
CREATE TABLE public.recordatorios (
  recordatorio_id uuid NOT NULL,
  cita_id uuid NOT NULL,
  programado_para timestamp without time zone NOT NULL,
  enviado boolean NOT NULL,
  creado_en timestamp without time zone NOT NULL,
  CONSTRAINT recordatorios_pkey PRIMARY KEY (recordatorio_id),
  CONSTRAINT recordatorios_cita_id_fkey FOREIGN KEY (cita_id) REFERENCES public.citas(cita_id)
);
CREATE TABLE public.medicos (
  medico_id uuid NOT NULL,
  nombres character varying NOT NULL,
  apellidos character varying NOT NULL,
  numero_registro character varying NOT NULL UNIQUE,
  correo_institucional character varying NOT NULL UNIQUE,
  activo boolean NOT NULL,
  creado_en timestamp with time zone NOT NULL,
  CONSTRAINT medicos_pkey PRIMARY KEY (medico_id)
);
CREATE TABLE public.sedes (
  sede_id uuid NOT NULL,
  nombre character varying NOT NULL,
  direccion character varying NOT NULL,
  ciudad character varying NOT NULL,
  telefono character varying,
  activo boolean NOT NULL,
  creado_en timestamp with time zone NOT NULL,
  CONSTRAINT sedes_pkey PRIMARY KEY (sede_id)
);
CREATE TABLE public.servicios (
  servicio_id uuid NOT NULL,
  nombre character varying NOT NULL UNIQUE,
  descripcion text,
  icono character varying,
  activo boolean NOT NULL,
  creado_en timestamp with time zone NOT NULL,
  CONSTRAINT servicios_pkey PRIMARY KEY (servicio_id)
);
CREATE TABLE public.especialidades (
  especialidad_id uuid NOT NULL,
  servicio_id uuid NOT NULL,
  nombre character varying NOT NULL,
  descripcion text,
  duracion_cita_minutos smallint NOT NULL,
  activo boolean NOT NULL,
  creado_en timestamp with time zone NOT NULL,
  CONSTRAINT especialidades_pkey PRIMARY KEY (especialidad_id),
  CONSTRAINT especialidades_servicio_id_fkey FOREIGN KEY (servicio_id) REFERENCES public.servicios(servicio_id)
);
CREATE TABLE public.disponibilidades (
  disponibilidad_id uuid NOT NULL,
  medico_id uuid NOT NULL,
  especialidad_id uuid NOT NULL,
  sede_id uuid NOT NULL,
  dia_semana smallint NOT NULL CHECK (dia_semana >= 1 AND dia_semana <= 7),
  hora_inicio time without time zone NOT NULL,
  hora_fin time without time zone NOT NULL,
  activo boolean NOT NULL,
  creado_en timestamp with time zone NOT NULL,
  CONSTRAINT disponibilidades_pkey PRIMARY KEY (disponibilidad_id),
  CONSTRAINT disponibilidades_especialidad_id_fkey FOREIGN KEY (especialidad_id) REFERENCES public.especialidades(especialidad_id),
  CONSTRAINT disponibilidades_medico_id_fkey FOREIGN KEY (medico_id) REFERENCES public.medicos(medico_id),
  CONSTRAINT disponibilidades_sede_id_fkey FOREIGN KEY (sede_id) REFERENCES public.sedes(sede_id)
);
CREATE TABLE public.medico_especialidades (
  medico_especialidad_id uuid NOT NULL,
  medico_id uuid NOT NULL,
  especialidad_id uuid NOT NULL,
  es_principal boolean NOT NULL,
  CONSTRAINT medico_especialidades_pkey PRIMARY KEY (medico_especialidad_id),
  CONSTRAINT medico_especialidades_especialidad_id_fkey FOREIGN KEY (especialidad_id) REFERENCES public.especialidades(especialidad_id),
  CONSTRAINT medico_especialidades_medico_id_fkey FOREIGN KEY (medico_id) REFERENCES public.medicos(medico_id)
);
CREATE TABLE public.notificaciones (
  notif_id uuid NOT NULL DEFAULT gen_random_uuid(),
  medico_id uuid NOT NULL,
  tipo character varying NOT NULL,
  titulo character varying NOT NULL,
  descripcion text NOT NULL,
  leida boolean NOT NULL DEFAULT false,
  enlace character varying,
  creado_en timestamp without time zone NOT NULL,
  CONSTRAINT notificaciones_pkey PRIMARY KEY (notif_id)
);
CREATE TABLE public.conversacion (
  conversacion_id uuid NOT NULL,
  usuario_id uuid NOT NULL,
  estado character varying NOT NULL,
  iniciada_en timestamp with time zone NOT NULL,
  cerrada_en timestamp with time zone,
  estado_orquestador text,
  CONSTRAINT conversacion_pkey PRIMARY KEY (conversacion_id)
);
CREATE TABLE public.clasificacion_sintomas (
  clasificacion_id uuid NOT NULL,
  conversacion_id uuid NOT NULL UNIQUE,
  terminos_identificados ARRAY,
  especialidad_sugerida character varying,
  nivel_urgencia character varying NOT NULL,
  confianza_modelo numeric,
  creado_en timestamp with time zone NOT NULL,
  CONSTRAINT clasificacion_sintomas_pkey PRIMARY KEY (clasificacion_id),
  CONSTRAINT clasificacion_sintomas_conversacion_id_fkey FOREIGN KEY (conversacion_id) REFERENCES public.conversacion(conversacion_id)
);
CREATE TABLE public.mensaje (
  mensaje_id uuid NOT NULL,
  conversacion_id uuid NOT NULL,
  remitente character varying NOT NULL,
  contenido text NOT NULL,
  creado_en timestamp with time zone NOT NULL,
  CONSTRAINT mensaje_pkey PRIMARY KEY (mensaje_id),
  CONSTRAINT mensaje_conversacion_id_fkey FOREIGN KEY (conversacion_id) REFERENCES public.conversacion(conversacion_id)
);
CREATE TABLE public.alembic_version_auth (
  version_num character varying NOT NULL,
  CONSTRAINT alembic_version_auth_pkey PRIMARY KEY (version_num)
);