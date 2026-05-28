-- Migration: 001_add_usuario_id_to_medicos
-- Catalog Service: agrega columna usuario_id a medicos para vincular con Auth
ALTER TABLE medicos ADD COLUMN IF NOT EXISTS usuario_id UUID;