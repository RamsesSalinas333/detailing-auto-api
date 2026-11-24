import os
import secrets
from datetime import datetime
from typing import Literal, Optional

import psycopg
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from psycopg.rows import dict_row
from pydantic import BaseModel, Field

DATABASE_URL = os.environ["DATABASE_URL"]
ADMIN_KEY = os.environ["ADMIN_KEY"]
ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]

app = FastAPI(title="Detailing Auto API")
app.add_middleware(
    CORSMiddleware, allow_origins=ORIGINS, allow_methods=["GET", "POST"], allow_headers=["*"]
)


def q(sql, params=(), one=False, fetch=True):
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        cur = conn.execute(sql, params)
        if not fetch:
            return None
        return cur.fetchone() if one else cur.fetchall()


def admin(x_admin_key: str = Header(default="")):
    if not secrets.compare_digest(x_admin_key.encode(), ADMIN_KEY.encode()):
        raise HTTPException(status_code=401, detail="Clave incorrecta")


# ---------- Modelos ----------
class CotizacionIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    telefono: str = Field(min_length=7, max_length=20)
    servicio: str = Field(max_length=60)
    auto: str = Field(max_length=100)


class EstadoCot(BaseModel):
    estado: Literal["nueva", "contactado", "agendada", "cancelada"]


class EstadoCita(BaseModel):
    estado: Literal["programada", "en_proceso", "terminada", "cancelada"]


class CitaIn(BaseModel):
    cliente_id: int
    servicio_id: int
    fecha_hora: datetime
    notas: Optional[str] = Field(default=None, max_length=500)


class ServicioIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)
    descripcion: Optional[str] = Field(default=None, max_length=300)
    precio: float = Field(ge=0)


class ServicioUpd(BaseModel):
    precio: float = Field(ge=0)
    activo: bool = True


# ---------- Rutas públicas (las usa tu página) ----------
@app.get("/api/salud")
def salud():
    return {"ok": True}


@app.get("/api/servicios")
def servicios_publicos():
    return q("SELECT id, nombre, descripcion, precio FROM servicios WHERE activo ORDER BY id")


@app.post("/api/cotizaciones", status_code=201)
def crear_cotizacion(c: CotizacionIn):
    cli = q(
        """INSERT INTO clientes (nombre, telefono, auto) VALUES (%s, %s, %s)
           ON CONFLICT (telefono) DO UPDATE SET nombre = EXCLUDED.nombre, auto = EXCLUDED.auto
           RETURNING id""",
        (c.nombre, c.telefono, c.auto),
        one=True,
    )
    q(
        "INSERT INTO cotizaciones (cliente_id, servicio, auto) VALUES (%s, %s, %s)",
        (cli["id"], c.servicio, c.auto),
        fetch=False,
    )
    return {"ok": True}


# ---------- Rutas del panel (requieren X-Admin-Key) ----------
@app.get("/api/admin/cotizaciones", dependencies=[Depends(admin)])
def admin_cotizaciones():
    return q(
        """SELECT c.id, c.servicio, c.auto, c.estado, c.creado, cl.nombre, cl.telefono
           FROM cotizaciones c JOIN clientes cl ON cl.id = c.cliente_id
           ORDER BY c.creado DESC"""
    )


@app.patch("/api/admin/cotizaciones/{id}", dependencies=[Depends(admin)])
def admin_estado_cotizacion(id: int, b: EstadoCot):
    q("UPDATE cotizaciones SET estado = %s WHERE id = %s", (b.estado, id), fetch=False)
    return {"ok": True}


@app.get("/api/admin/clientes", dependencies=[Depends(admin)])
def admin_clientes():
    return q("SELECT id, nombre, telefono, auto, creado FROM clientes ORDER BY nombre")


@app.get("/api/admin/citas", dependencies=[Depends(admin)])
def admin_citas():
    return q(
        """SELECT ci.id, ci.fecha_hora, ci.estado, ci.notas, cl.nombre, cl.telefono,
                  s.nombre AS servicio, s.precio
           FROM citas ci JOIN clientes cl ON cl.id = ci.cliente_id
           JOIN servicios s ON s.id = ci.servicio_id
           ORDER BY ci.fecha_hora DESC"""
    )


@app.post("/api/admin/citas", status_code=201, dependencies=[Depends(admin)])
def admin_crear_cita(b: CitaIn):
    q(
        "INSERT INTO citas (cliente_id, servicio_id, fecha_hora, notas) VALUES (%s, %s, %s, %s)",
        (b.cliente_id, b.servicio_id, b.fecha_hora, b.notas),
        fetch=False,
    )
    return {"ok": True}


@app.patch("/api/admin/citas/{id}", dependencies=[Depends(admin)])
def admin_estado_cita(id: int, b: EstadoCita):
    q("UPDATE citas SET estado = %s WHERE id = %s", (b.estado, id), fetch=False)
    return {"ok": True}


@app.get("/api/admin/servicios", dependencies=[Depends(admin)])
def admin_servicios():
    return q("SELECT * FROM servicios ORDER BY id")


@app.post("/api/admin/servicios", status_code=201, dependencies=[Depends(admin)])
def admin_crear_servicio(b: ServicioIn):
    q(
        "INSERT INTO servicios (nombre, descripcion, precio) VALUES (%s, %s, %s)",
        (b.nombre, b.descripcion, b.precio),
        fetch=False,
    )
    return {"ok": True}


@app.put("/api/admin/servicios/{id}", dependencies=[Depends(admin)])
def admin_actualizar_servicio(id: int, b: ServicioUpd):
    q("UPDATE servicios SET precio = %s, activo = %s WHERE id = %s", (b.precio, b.activo, id), fetch=False)
    return {"ok": True}


@app.get("/admin", include_in_schema=False)
def panel():
    return FileResponse("static/admin.html")
