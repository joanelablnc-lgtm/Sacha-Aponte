NUMERICAS = ["cantidad"]
CATEGORICAS = ["proveedor", "categoria", "estado"]
COLUMNAS = NUMERICAS + CATEGORICAS
OBJETIVO = "importe_eur"


def preparar(tabla):
    tabla = tabla.copy()
    return tabla[COLUMNAS]
