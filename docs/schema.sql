-- =====================================================================
-- ChibchaWEB — Modelo relacional (PostgreSQL)
-- Proyecto semestral 2026-III · Fundamentos de Ingeniería de Software
-- Derivado del modelo de dominio (DC-MDO-01) con:
--   · Identity Field: id SERIAL como llave primaria
--   · Class Table Inheritance: usuario → cliente/empleado/distribuidor
--                              medio_pago → tarjeta_credito
--   · Foreign Key Mapping para asociaciones 1:1 y 1:N
--   · Dependent Mapping para Rol.operaciones (rol_operacion)
--   · Enumeraciones como VARCHAR con restricción CHECK
--   · Sin borrado en cascada: las bajas son lógicas (usuario.activo)
-- =====================================================================

-- ---------------------------------------------------------------------
-- Catálogos
-- ---------------------------------------------------------------------
CREATE TABLE rol (
    id      SERIAL PRIMARY KEY,
    nombre  VARCHAR(40) NOT NULL UNIQUE
);

CREATE TABLE rol_operacion (
    id_rol     INTEGER     NOT NULL REFERENCES rol (id),
    operacion  VARCHAR(60) NOT NULL,
    PRIMARY KEY (id_rol, operacion)
);

CREATE TABLE franquicia (
    id             SERIAL PRIMARY KEY,
    nombre         VARCHAR(20)  NOT NULL UNIQUE,
    patron_numero  VARCHAR(100) NOT NULL
);

CREATE TABLE paquete_hosting (
    id              SERIAL PRIMARY KEY,
    nombre          VARCHAR(40)   NOT NULL UNIQUE,
    tarifa_mensual  NUMERIC(10,2) NOT NULL CHECK (tarifa_mensual > 0),
    descripcion     TEXT
);

CREATE TABLE plan_pago (
    id         SERIAL PRIMARY KEY,
    nombre     VARCHAR(20)  NOT NULL UNIQUE,
    meses      SMALLINT     NOT NULL CHECK (meses IN (1, 3, 6, 12)),
    descuento  NUMERIC(4,2) NOT NULL CHECK (descuento BETWEEN 0 AND 1)
);

CREATE TABLE nivel_servicio (
    id         SERIAL PRIMARY KEY,
    nombre     VARCHAR(40) NOT NULL UNIQUE,
    orden      SMALLINT    NOT NULL UNIQUE,
    es_ultimo  BOOLEAN     NOT NULL DEFAULT FALSE
);

-- ---------------------------------------------------------------------
-- Cuentas y perfiles
-- ---------------------------------------------------------------------
CREATE TABLE usuario (
    id                  SERIAL PRIMARY KEY,
    tipo                VARCHAR(15)  NOT NULL CHECK (tipo IN ('CLIENTE', 'EMPLEADO', 'DISTRIBUIDOR')),
    nombre              VARCHAR(120) NOT NULL,
    correo              VARCHAR(120) NOT NULL UNIQUE,
    telefono            VARCHAR(20),
    activo              BOOLEAN      NOT NULL DEFAULT TRUE,
    fecha_registro      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE distribuidor (
    id         INTEGER     PRIMARY KEY REFERENCES usuario (id),
    documento  VARCHAR(20) NOT NULL UNIQUE,
    codigo     VARCHAR(20) NOT NULL UNIQUE
);

CREATE TABLE empleado (
    id         INTEGER     PRIMARY KEY REFERENCES usuario (id),
    documento  VARCHAR(20) NOT NULL UNIQUE,
    id_rol     INTEGER     NOT NULL REFERENCES rol (id)
);

CREATE TABLE cuenta_acceso (
    id                     SERIAL PRIMARY KEY,
    id_titular             INTEGER      NOT NULL UNIQUE REFERENCES usuario (id),
    identificador_externo  VARCHAR(255) NOT NULL,
    proveedor              VARCHAR(50)  NOT NULL,
    fecha_vinculacion      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ultimo_acceso          TIMESTAMP,
    UNIQUE (proveedor, identificador_externo)
);

CREATE TABLE direccion (
    id             SERIAL PRIMARY KEY,
    linea          VARCHAR(150) NOT NULL,
    ciudad         VARCHAR(80)  NOT NULL,
    codigo_postal  VARCHAR(10)  NOT NULL,
    pais           VARCHAR(60)  NOT NULL
);

CREATE TABLE medio_pago (
    id    SERIAL PRIMARY KEY,
    tipo  VARCHAR(15) NOT NULL CHECK (tipo IN ('TARJETA'))
);

-- codigoSeguridad no tiene columna: se usa solo para validar o cobrar.
CREATE TABLE tarjeta_credito (
    id                 INTEGER     PRIMARY KEY REFERENCES medio_pago (id),
    numero_cifrado     TEXT        NOT NULL,
    algoritmo_cifrado  VARCHAR(20) NOT NULL,
    ultimos_digitos    CHAR(4)     NOT NULL,
    vencimiento        DATE        NOT NULL,
    id_franquicia      INTEGER     NOT NULL REFERENCES franquicia (id)
);

CREATE TABLE cliente (
    id               INTEGER PRIMARY KEY REFERENCES usuario (id),
    id_residencia    INTEGER NOT NULL UNIQUE REFERENCES direccion (id),
    id_facturacion   INTEGER NOT NULL UNIQUE REFERENCES direccion (id),
    id_medio_pago    INTEGER NOT NULL UNIQUE REFERENCES medio_pago (id),
    id_distribuidor  INTEGER REFERENCES distribuidor (id),
    CHECK (id_residencia <> id_facturacion)
);

-- ---------------------------------------------------------------------
-- Hospedaje
-- ---------------------------------------------------------------------
CREATE TABLE sitio_web (
    id              SERIAL PRIMARY KEY,
    subdominio      VARCHAR(120) NOT NULL UNIQUE,
    dominio_propio  VARCHAR(255) UNIQUE,
    plataforma      VARCHAR(10)  NOT NULL CHECK (plataforma IN ('WINDOWS', 'UNIX'))
);

CREATE TABLE suscripcion (
    id            SERIAL PRIMARY KEY,
    id_titular    INTEGER NOT NULL REFERENCES cliente (id),
    id_sitio      INTEGER NOT NULL UNIQUE REFERENCES sitio_web (id),
    id_paquete    INTEGER NOT NULL REFERENCES paquete_hosting (id),
    id_plan       INTEGER NOT NULL REFERENCES plan_pago (id),
    fecha_inicio  DATE    NOT NULL,
    fecha_corte   DATE    NOT NULL,
    activa        BOOLEAN NOT NULL DEFAULT TRUE,
    CHECK (fecha_corte >= fecha_inicio)
);

-- ---------------------------------------------------------------------
-- Facturación y comisiones
-- ---------------------------------------------------------------------
CREATE TABLE comision (
    id                  SERIAL PRIMARY KEY,
    id_beneficiario     INTEGER      NOT NULL REFERENCES distribuidor (id),
    fecha_inicio        DATE         NOT NULL,
    fecha_fin           DATE         NOT NULL,
    clientes_referidos  INTEGER      NOT NULL CHECK (clientes_referidos >= 0),
    nombre_categoria    VARCHAR(20)  NOT NULL,
    porcentaje          NUMERIC(4,2) NOT NULL CHECK (porcentaje BETWEEN 0 AND 1),
    CHECK (fecha_fin >= fecha_inicio)
);

CREATE TABLE pago (
    id                     SERIAL PRIMARY KEY,
    id_suscripcion         INTEGER       NOT NULL REFERENCES suscripcion (id),
    monto                  NUMERIC(10,2) NOT NULL CHECK (monto > 0),
    fecha                  TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    estado                 VARCHAR(10)   NOT NULL CHECK (estado IN ('EXITOSO', 'FALLIDO')),
    referencia_franquicia  VARCHAR(100),
    comisionado            BOOLEAN       NOT NULL DEFAULT FALSE,
    id_comision            INTEGER       REFERENCES comision (id),
    CHECK (id_comision IS NULL OR (estado = 'EXITOSO' AND comisionado)),
    CHECK (estado = 'EXITOSO' OR referencia_franquicia IS NULL)
);

CREATE TABLE cheque (
    id             SERIAL PRIMARY KEY,
    id_comision    INTEGER       NOT NULL UNIQUE REFERENCES comision (id),
    numero         VARCHAR(30)   NOT NULL UNIQUE,
    beneficiario   VARCHAR(120)  NOT NULL,
    monto          NUMERIC(12,2) NOT NULL CHECK (monto > 0),
    fecha_emision  DATE          NOT NULL
);

-- ---------------------------------------------------------------------
-- Dominios web
-- ---------------------------------------------------------------------
CREATE TABLE solicitud_dominio (
    id               SERIAL PRIMARY KEY,
    id_solicitante   INTEGER     NOT NULL REFERENCES cliente (id),
    nombre           VARCHAR(63) NOT NULL,
    extension        VARCHAR(20) NOT NULL,
    fecha_solicitud  TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_envio      TIMESTAMP,
    estado           VARCHAR(12) NOT NULL CHECK (estado IN ('REGISTRADA', 'ENVIADA', 'FALLIDA')),
    CHECK (estado <> 'ENVIADA' OR fecha_envio IS NOT NULL)
);

-- ---------------------------------------------------------------------
-- Soporte técnico
-- ---------------------------------------------------------------------
CREATE TABLE ticket (
    id                 SERIAL PRIMARY KEY,
    id_reportante      INTEGER     NOT NULL REFERENCES usuario (id),
    id_sitio_afectado  INTEGER     REFERENCES sitio_web (id),
    id_nivel_actual    INTEGER     NOT NULL REFERENCES nivel_servicio (id),
    descripcion        TEXT        NOT NULL,
    fecha_creacion     TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    categoria          VARCHAR(15) NOT NULL CHECK (categoria IN ('RENDIMIENTO', 'CORREO', 'BASE_DATOS', 'DOMINIO', 'OTRA')),
    estado             VARCHAR(10) NOT NULL CHECK (estado IN ('ABIERTO', 'ESCALADO', 'RESUELTO'))
);

CREATE TABLE movimiento_ticket (
    id                   SERIAL PRIMARY KEY,
    id_ticket            INTEGER     NOT NULL REFERENCES ticket (id),
    id_responsable       INTEGER     NOT NULL REFERENCES empleado (id),
    id_nivel_resultante  INTEGER     NOT NULL REFERENCES nivel_servicio (id),
    fecha                TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    observacion          TEXT,
    estado_resultante    VARCHAR(10) NOT NULL CHECK (estado_resultante IN ('ABIERTO', 'ESCALADO', 'RESUELTO'))
);

-- ---------------------------------------------------------------------
-- Migración de datos legados
-- ---------------------------------------------------------------------
CREATE TABLE proceso_migracion (
    id            SERIAL PRIMARY KEY,
    id_ejecutor   INTEGER     NOT NULL REFERENCES empleado (id),
    fecha_inicio  TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_fin     TIMESTAMP,
    estado        VARCHAR(10) NOT NULL CHECK (estado IN ('CREADA', 'SIMULADA', 'APROBADA', 'EJECUTADA', 'REVERTIDA', 'CANCELADA'))
);

CREATE TABLE entrada_log (
    id                    SERIAL PRIMARY KEY,
    id_proceso            INTEGER     NOT NULL REFERENCES proceso_migracion (id),
    fecha                 TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    nivel                 VARCHAR(12) NOT NULL CHECK (nivel IN ('INFO', 'ADVERTENCIA', 'ERROR')),
    mensaje               TEXT        NOT NULL,
    identificador_legado  VARCHAR(50),
    tipo_registro         VARCHAR(20)
);

-- ---------------------------------------------------------------------
-- Índices para las consultas frecuentes
-- ---------------------------------------------------------------------
CREATE INDEX idx_suscripcion_corte       ON suscripcion (fecha_corte) WHERE activa;
CREATE INDEX idx_pago_suscripcion_estado ON pago (id_suscripcion, estado);
CREATE INDEX idx_ticket_estado           ON ticket (estado);
CREATE INDEX idx_ticket_fecha            ON ticket (fecha_creacion);
CREATE INDEX idx_ticket_reportante       ON ticket (id_reportante);
CREATE INDEX idx_solicitud_solicitante   ON solicitud_dominio (id_solicitante);
CREATE INDEX idx_cliente_distribuidor    ON cliente (id_distribuidor);

-- ---------------------------------------------------------------------
-- Datos de catálogo (supuestos documentados: precios en USD)
-- ---------------------------------------------------------------------
INSERT INTO paquete_hosting (nombre, tarifa_mensual, descripcion) VALUES
    ('Chibcha-Plata',   5.00,  'Paquete básico'),
    ('Chibcha-Oro',     10.00, 'Paquete intermedio'),
    ('Chibcha-Platino', 20.00, 'Paquete completo');

INSERT INTO plan_pago (nombre, meses, descuento) VALUES
    ('Mensual',    1,  0.00),
    ('Trimestral', 3,  0.05),
    ('Semestral',  6,  0.10),
    ('Anual',      12, 0.15);

INSERT INTO franquicia (nombre, patron_numero) VALUES
    ('VISA',       '^4[0-9]{12}([0-9]{3})?$'),
    ('MASTERCARD', '^(5[1-5][0-9]{14}|2[2-7][0-9]{14})$'),
    ('DINERS',     '^3(0[0-5]|[68][0-9])[0-9]{11}$');

INSERT INTO nivel_servicio (nombre, orden, es_ultimo) VALUES
    ('Soporte',    1, FALSE),
    ('Gestión',    2, FALSE),
    ('Desarrollo', 3, TRUE);

INSERT INTO rol (nombre) VALUES ('Gestión'), ('Soporte'), ('Administrador');
