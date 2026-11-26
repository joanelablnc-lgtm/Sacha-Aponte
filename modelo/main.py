import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mcp.server import MCPServer
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from pistas import preparar


MODELO_DIR = Path(__file__).resolve().parent
pipeline = joblib.load(MODELO_DIR / "modelo.joblib")
metricas = json.loads((MODELO_DIR / "metricas.json").read_text(encoding="utf-8"))


class PrediccionInput(BaseModel):
    cantidad: int = Field(ge=1, le=100000, description="Número de unidades compradas")
    proveedor: str = Field(min_length=1, max_length=100, description="Nombre del proveedor")
    categoria: str = Field(min_length=1, max_length=100, description="Categoría de la compra")
    estado: str = Field(min_length=1, max_length=100, description="Estado de la compra")


@asynccontextmanager
async def lifespan(app):
    async with app_mcp.router.lifespan_context(app_mcp):
        yield


app = FastAPI(
    title="API del modelo de compras",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://web-omega-six-v7c2vgocas.vercel.app"],
    allow_origin_regex=r"https?://localhost(:[0-9]+)?",
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/info")
def info():
    return metricas


@app.post("/predict")
def predict(datos: PrediccionInput):
    tabla = pd.DataFrame([datos.model_dump()])
    importe = float(pipeline.predict(preparar(tabla))[0])
    return {
        "prediccion_eur": round(importe, 2),
        "error_medio_eur": metricas["error_modelo_mae_eur"],
    }


class PideToken(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/mcp"):
            token = os.getenv("MCP_TOKEN")
            if not token:
                return JSONResponse(
                    {"error": "El servidor no tiene token"},
                    status_code=500,
                )
            autorizacion = request.headers.get("authorization", "")
            if autorizacion != f"Bearer {token}":
                return JSONResponse(
                    {"error": "Token invalido"},
                    status_code=401,
                )
        return await call_next(request)


app.add_middleware(PideToken)

servidor_mcp = MCPServer(
    name="compras",
    description="Herramientas de búsqueda y predicción del proyecto de compras",
)


@servidor_mcp.tool(
    name="buscar_compras",
    description="Busca compras por proveedor, categoría o estado. Devuelve hasta 50 coincidencias.",
)
def buscar_compras(
    proveedor: str = "",
    categoria: str = "",
    estado: str = "",
    importe_minimo: float = 0,
    importe_maximo: float = 100000,
) -> dict:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    tabla = os.getenv("SUPABASE_TABLE", "compras")
    if not url or not key:
        return {
            "error": "Faltan SUPABASE_URL y SUPABASE_KEY",
            "filas": [],
        }
    if key.startswith("sb_secret_") or "service_role" in key:
        return {
            "error": "SUPABASE_KEY debe ser publicable; no se admite una clave secreta",
            "filas": [],
        }
    if importe_maximo < importe_minimo:
        return {
            "error": "importe_maximo debe ser mayor o igual que importe_minimo",
            "filas": [],
        }

    import httpx

    cabeceras = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }
    parametros = {"select": "*", "limit": "50"}
    if proveedor:
        parametros["proveedor"] = f"ilike.*{proveedor}*"
    if categoria:
        parametros["categoria"] = f"ilike.*{categoria}*"
    if estado:
        parametros["estado"] = f"ilike.*{estado}*"

    try:
        with httpx.Client(timeout=30) as cliente:
            consulta = [(clave, valor) for clave, valor in parametros.items()]
            consulta.append(("importe_eur", f"gte.{importe_minimo}"))
            consulta.append(("importe_eur", f"lte.{importe_maximo}"))
            respuesta = cliente.get(
                f"{url.rstrip('/')}/rest/v1/{tabla}",
                headers=cabeceras,
                params=consulta,
            )
            respuesta.raise_for_status()
            filas = respuesta.json()
    except httpx.HTTPStatusError as exc:
        return {
            "error": f"Supabase rechazó la consulta: HTTP {exc.response.status_code}",
            "filas": [],
        }
    except httpx.RequestError as exc:
        return {
            "error": f"No se pudo consultar Supabase: {type(exc).__name__}",
            "filas": [],
        }
    return {"filas": filas[:50]}


@servidor_mcp.tool(
    name="predecir_importe",
    description="Predice el importe esperado de una compra con el modelo entrenado.",
)
def predecir_importe(
    cantidad: int,
    proveedor: str,
    categoria: str,
    estado: str,
) -> dict:
    tabla = pd.DataFrame([{
        "cantidad": cantidad,
        "proveedor": proveedor,
        "categoria": categoria,
        "estado": estado,
    }])
    importe = float(pipeline.predict(preparar(tabla))[0])
    return {
        "prediccion_eur": round(importe, 2),
        "error_medio_eur": metricas["error_modelo_mae_eur"],
    }


app_mcp = servidor_mcp.streamable_http_app(
    streamable_http_path="/",
)
app.mount("/mcp", app_mcp)
