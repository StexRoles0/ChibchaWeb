-- =====================================================================
-- ChibchaWEB — datos de desarrollo (se cargan después de schema.sql)
-- Solo para desarrollo y pruebas. No forma parte del modelo ER.
-- =====================================================================

-- Operaciones por rol (Dependent Mapping: rol_operacion)
INSERT INTO rol_operacion (id_rol, operacion)
SELECT r.id, o.op FROM rol r
JOIN (VALUES
  ('Gestión',       'GESTIONAR_EMPLEADOS'),
  ('Gestión',       'GESTIONAR_DISTRIBUIDORES'),
  ('Gestión',       'CONSULTAR_REGISTROS'),
  ('Gestión',       'REGISTRAR_TICKET'),
  ('Soporte',       'ATENDER_TICKETS'),
  ('Soporte',       'REGISTRAR_TICKET'),
  ('Administrador', 'MIGRAR_DATOS'),
  ('Administrador', 'GESTIONAR_CONTINGENCIA'),
  ('Administrador', 'REGISTRAR_TICKET')
) AS o(rol, op) ON o.rol = r.nombre;

-- Un empleado por rol. Sin cuenta de acceso: la vinculan en su primer
-- ingreso por correo verificado (RN-07). Con el proveedor simulado,
-- el código "dev:<correo>" autentica a ese correo.
WITH u AS (
  INSERT INTO usuario (tipo, nombre, correo, telefono) VALUES
    ('EMPLEADO', 'Gabriela Gestión', 'gestion@chibchaweb.co',  '3001112233'),
    ('EMPLEADO', 'Sergio Soporte',   'soporte@chibchaweb.co',  '3002223344'),
    ('EMPLEADO', 'Ana Administra',   'admin@chibchaweb.co',    '3003334455')
  RETURNING id, correo)
INSERT INTO empleado (id, documento, id_rol)
SELECT u.id,
       CASE u.correo WHEN 'gestion@chibchaweb.co' THEN 'E-1001' WHEN 'soporte@chibchaweb.co' THEN 'E-1002' ELSE 'E-1003' END,
       (SELECT id FROM rol WHERE nombre =
          CASE u.correo WHEN 'gestion@chibchaweb.co' THEN 'Gestión' WHEN 'soporte@chibchaweb.co' THEN 'Soporte' ELSE 'Administrador' END)
FROM u;

-- Un distribuidor para probar el código de referido en el registro.
WITH u AS (
  INSERT INTO usuario (tipo, nombre, correo, telefono)
  VALUES ('DISTRIBUIDOR', 'Andes Digital SAS', 'contacto@andesdigital.co', '6015556677')
  RETURNING id)
INSERT INTO distribuidor (id, documento, codigo) SELECT id, '900123456', 'DIS-ANDES1' FROM u;
