-- Migration: 001_create_initial_tables
-- Citas Service: crea las tablas principales
CREATE TABLE IF NOT EXISTS citas (
    cita_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id UUID NOT NULL,
    medico_id UUID NOT NULL,
    especialidad_id UUID,
    tipo_servicio VARCHAR(50) NOT NULL,
    fecha_cita DATE NOT NULL,
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    sede_id UUID NOT NULL,
    descripcion_sintomas TEXT,
    estado VARCHAR(20) NOT NULL DEFAULT 'programada',
    creado_en TIMESTAMP NOT NULL DEFAULT NOW(),
    actualizado_en TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_citas_usuario_id ON citas(usuario_id);
CREATE INDEX IF NOT EXISTS ix_citas_medico_id ON citas(medico_id);
CREATE INDEX IF NOT EXISTS ix_citas_fecha_cita ON citas(fecha_cita);
CREATE INDEX IF NOT EXISTS ix_citas_estado ON citas(estado);

CREATE TABLE IF NOT EXISTS historial_estado (
    historial_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cita_id UUID NOT NULL REFERENCES citas(cita_id) ON DELETE CASCADE,
    estado_anterior VARCHAR(20) NOT NULL,
    estado_nuevo VARCHAR(20) NOT NULL,
    motivo TEXT,
    realizado_por UUID NOT NULL,
    creado_en TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_historial_estado_cita_id ON historial_estado(cita_id);

CREATE TABLE IF NOT EXISTS recordatorios (
    recordatorio_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cita_id UUID NOT NULL REFERENCES citas(cita_id) ON DELETE CASCADE,
    programado_para TIMESTAMP NOT NULL,
    enviado BOOLEAN NOT NULL DEFAULT FALSE,
    creado_en TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_recordatorios_cita_id ON recordatorios(cita_id);