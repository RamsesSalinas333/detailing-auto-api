CREATE TABLE servicios (
  id SERIAL PRIMARY KEY,
  nombre TEXT UNIQUE NOT NULL,
  descripcion TEXT,
  precio NUMERIC(10,2) NOT NULL DEFAULT 0,
  activo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE clientes (
  id SERIAL PRIMARY KEY,
  nombre TEXT NOT NULL,
  telefono TEXT UNIQUE NOT NULL,
  auto TEXT,
  creado TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE cotizaciones (
  id SERIAL PRIMARY KEY,
  cliente_id INT NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
  servicio TEXT NOT NULL,
  auto TEXT,
  estado TEXT NOT NULL DEFAULT 'nueva',
  creado TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE citas (
  id SERIAL PRIMARY KEY,
  cliente_id INT NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
  servicio_id INT NOT NULL REFERENCES servicios(id),
  fecha_hora TIMESTAMPTZ NOT NULL,
  estado TEXT NOT NULL DEFAULT 'programada',
  notas TEXT,
  creado TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO servicios (nombre, descripcion, precio) VALUES
 ('Corrección de pintura', 'Pulido en una o varias etapas', 0),
 ('Recubrimiento cerámico', 'Protección de largo plazo', 0),
 ('PPF', 'Película de protección frontal, parcial o total', 0);
