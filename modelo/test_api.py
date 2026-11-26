import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = "http://127.0.0.1:8000"


def get_json(path):
    with urlopen(BASE_URL + path, timeout=30) as respuesta:
        return respuesta.status, json.loads(respuesta.read())


def post_json(path, body):
    request = Request(
        BASE_URL + path,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=30) as respuesta:
        return respuesta.status, json.loads(respuesta.read())


status, health = get_json("/health")
assert status == 200 and health == {"ok": True}

status, info = get_json("/info")
assert status == 200 and "error_modelo_mae_eur" in info

status, predict = post_json("/predict", {
    "cantidad": 14,
    "proveedor": "Proveedor Este",
    "categoria": "Servicios",
    "estado": "Pendiente",
})
assert status == 200
assert isinstance(predict["prediccion_eur"], float)
assert predict["error_medio_eur"] == info["error_modelo_mae_eur"]

try:
    get_json("/mcp")
except HTTPError as exc:
    assert exc.code == 401
else:
    raise AssertionError("El MCP debe rechazar una petición sin token")

print(json.dumps({
    "health": health,
    "info": info,
    "predict": predict,
    "mcp_sin_token": 401,
}, ensure_ascii=False))
