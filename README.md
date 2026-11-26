# Sacha-Aponte

## API del modelo

- Servicio gratuito en Render: https://sacha-aponte-modelo.onrender.com
- Salud: https://sacha-aponte-modelo.onrender.com/health
- Información: https://sacha-aponte-modelo.onrender.com/info
- Documentación: https://sacha-aponte-modelo.onrender.com/docs
- MCP protegido: https://sacha-aponte-modelo.onrender.com/mcp

La app Python está en `modelo/`. El modelo y las métricas se incluyen en el repositorio; el CSV privado y el entorno virtual no se publican.

## Evidencia de auditoría

- `/health` devuelve HTTP 200.
- `/predict` devuelve HTTP 200 con un ejemplo verificado.
- `/mcp` rechaza peticiones sin token con HTTP 401.
- La prueba local `modelo/test_api.py` verifica `/health`, `/info`, `/predict` y el rechazo sin token de `/mcp`.
- `buscar_compras` usa la clave publicable de Supabase y respeta RLS; no acepta claves `service_role` ni `sb_secret_`.