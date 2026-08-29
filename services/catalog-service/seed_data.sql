-- Datos de prueba para catalog-service (idempotente: se puede correr varias veces).
--
-- Uso:
--   psql "postgresql://eps_user:eps_password@localhost:5432/eps_catalogo" -f seed_data.sql
--   (o el equivalente docker exec -i eps-catalogo-db psql ... < seed_data.sql)
--
-- Crea: 1 servicio, 7 especialidades, 9 medicos, 4 sedes, sus relaciones
-- medico<->especialidad y disponibilidad semanal (lunes a viernes, 8am-4pm)
-- en cada sede. Suficiente variedad para probar el chatbot y el agendado por
-- formulario sin quedarse sin opciones para elegir.

-- 1) Servicio base
INSERT INTO servicios (servicio_id, nombre, descripcion, icono, activo, creado_en)
SELECT gen_random_uuid(), 'Consulta Especializada', 'Servicios de consulta con especialistas', 'stethoscope', true, now()
WHERE NOT EXISTS (SELECT 1 FROM servicios WHERE nombre = 'Consulta Especializada');

-- 2) Especialidades
INSERT INTO especialidades (especialidad_id, servicio_id, nombre, descripcion, duracion_cita_minutos, activo, creado_en)
SELECT gen_random_uuid(), (SELECT servicio_id FROM servicios WHERE nombre = 'Consulta Especializada' LIMIT 1),
       t.nombre, t.descripcion, t.duracion, true, now()
FROM (VALUES
    ('Cardiologia', 'Especialidad del corazon', 30),
    ('Medicina General', 'Consulta general de primer nivel', 20),
    ('Pediatria', 'Atencion medica para ninos', 25),
    ('Odontologia', 'Salud oral y dental', 30),
    ('Neurologia', 'Sistema nervioso', 30),
    ('Ginecologia', 'Salud femenina', 30),
    ('Oftalmologia', 'Salud visual', 20)
) AS t(nombre, descripcion, duracion)
WHERE NOT EXISTS (SELECT 1 FROM especialidades e WHERE e.nombre = t.nombre);

-- 3) Sedes
INSERT INTO sedes (sede_id, nombre, direccion, ciudad, telefono, activo, creado_en)
SELECT gen_random_uuid(), t.nombre, t.direccion, t.ciudad, t.telefono, true, now()
FROM (VALUES
    ('Centro Medico Santa Ana', 'Calle 100 # 15-20', 'Bogota', '6015551234'),
    ('Sede Norte', 'Calle 140 # 20-30', 'Bogota', '6015552345'),
    ('Sede Sur', 'Carrera 30 # 45-10', 'Bogota', '6015553456'),
    ('Sede Chapinero', 'Carrera 13 # 60-25', 'Bogota', '6015554567')
) AS t(nombre, direccion, ciudad, telefono)
WHERE NOT EXISTS (SELECT 1 FROM sedes s WHERE s.nombre = t.nombre);

-- 4) Medicos
INSERT INTO medicos (medico_id, nombres, apellidos, numero_registro, correo_institucional, activo, creado_en)
SELECT gen_random_uuid(), t.nombres, t.apellidos, t.numero_registro, t.correo, true, now()
FROM (VALUES
    ('Alejandro', 'Martinez', 'REG-0001', 'alejandro.martinez@epsdigital.com'),
    ('Camila', 'Torres', 'REG-0002', 'camila.torres@epsdigital.com'),
    ('Daniel', 'Rojas', 'REG-0003', 'daniel.rojas@epsdigital.com'),
    ('Valentina', 'Suarez', 'REG-0004', 'valentina.suarez@epsdigital.com'),
    ('Andres', 'Gomez', 'REG-0005', 'andres.gomez@epsdigital.com'),
    ('Laura', 'Perez', 'REG-0006', 'laura.perez@epsdigital.com'),
    ('Miguel', 'Castro', 'REG-0007', 'miguel.castro@epsdigital.com'),
    ('Sofia', 'Ramirez', 'REG-0008', 'sofia.ramirez@epsdigital.com'),
    ('Juan', 'Herrera', 'REG-0009', 'juan.herrera@epsdigital.com')
) AS t(nombres, apellidos, numero_registro, correo)
WHERE NOT EXISTS (SELECT 1 FROM medicos m WHERE m.numero_registro = t.numero_registro);

-- 5) Relacion medico <-> especialidad (dos medicos en Cardiologia y Medicina
--    General para dar opcion real de elegir; uno en el resto)
INSERT INTO medico_especialidades (medico_especialidad_id, medico_id, especialidad_id, es_principal)
SELECT gen_random_uuid(), m.medico_id, e.especialidad_id, true
FROM medicos m
JOIN especialidades e ON (
  (m.numero_registro = 'REG-0001' AND e.nombre = 'Cardiologia') OR
  (m.numero_registro = 'REG-0008' AND e.nombre = 'Cardiologia') OR
  (m.numero_registro = 'REG-0002' AND e.nombre = 'Medicina General') OR
  (m.numero_registro = 'REG-0009' AND e.nombre = 'Medicina General') OR
  (m.numero_registro = 'REG-0003' AND e.nombre = 'Pediatria') OR
  (m.numero_registro = 'REG-0004' AND e.nombre = 'Odontologia') OR
  (m.numero_registro = 'REG-0005' AND e.nombre = 'Neurologia') OR
  (m.numero_registro = 'REG-0006' AND e.nombre = 'Ginecologia') OR
  (m.numero_registro = 'REG-0007' AND e.nombre = 'Oftalmologia')
)
WHERE NOT EXISTS (
  SELECT 1 FROM medico_especialidades me
  WHERE me.medico_id = m.medico_id AND me.especialidad_id = e.especialidad_id
);

-- 6) Disponibilidad: lunes a viernes, 8am-4pm, en las 4 sedes, para cada
--    relacion medico<->especialidad que aun no tenga disponibilidad cargada.
INSERT INTO disponibilidades (disponibilidad_id, medico_id, especialidad_id, sede_id, dia_semana, hora_inicio, hora_fin, activo, creado_en)
SELECT gen_random_uuid(), me.medico_id, me.especialidad_id, s.sede_id, dia, '08:00', '16:00', true, now()
FROM medico_especialidades me
CROSS JOIN sedes s
CROSS JOIN generate_series(1, 5) AS dia
WHERE NOT EXISTS (
  SELECT 1 FROM disponibilidades d
  WHERE d.medico_id = me.medico_id AND d.sede_id = s.sede_id AND d.dia_semana = dia
);
