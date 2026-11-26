import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from pistas import CATEGORICAS, NUMERICAS, OBJETIVO, preparar


MODELO_DIR = Path(__file__).resolve().parent
CSV_PATH = MODELO_DIR.parent.parent / "datos" / "SN_Compras_Enero_a_Junio_2025.csv"


def main():
    datos = pd.read_csv(CSV_PATH).dropna(subset=[OBJETIVO])
    aprender, examen = train_test_split(
        datos,
        test_size=0.20,
        random_state=42,
    )

    ingenua = aprender[OBJETIVO].mean()
    prediccion_ingenua = [ingenua] * len(examen)
    error_ingenuo = mean_absolute_error(
        examen[OBJETIVO],
        prediccion_ingenua,
    )

    preprocesado = ColumnTransformer(
        transformers=[
            ("numericas", SimpleImputer(strategy="median"), NUMERICAS),
            ("categoricas", Pipeline([
                ("imputar", SimpleImputer(strategy="most_frequent")),
                ("codificar", OneHotEncoder(handle_unknown="ignore")),
            ]), CATEGORICAS),
        ]
    )

    pipeline = Pipeline([
        ("preprocesado", preprocesado),
        ("modelo", Ridge(alpha=1.0)),
    ])

    pipeline.fit(preparar(aprender), aprender[OBJETIVO])
    predicciones = pipeline.predict(preparar(examen))
    error_modelo = mean_absolute_error(examen[OBJETIVO], predicciones)

    joblib.dump(pipeline, MODELO_DIR / "modelo.joblib")

    metricas = {
        "objetivo": OBJETIVO,
        "unidad": "EUR",
        "tipo": "regresion",
        "pistas": NUMERICAS + CATEGORICAS,
        "error_ingenuo_mae_eur": round(float(error_ingenuo), 2),
        "error_modelo_mae_eur": round(float(error_modelo), 2),
        "filas_aprendizaje": len(aprender),
        "filas_examen": len(examen),
        "random_state": 42,
    }
    (MODELO_DIR / "metricas.json").write_text(
        json.dumps(metricas, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Prediccion ingenua (media): MAE = {error_ingenuo:.2f} EUR")
    print(f"Modelo Ridge: MAE = {error_modelo:.2f} EUR")
    print(json.dumps(metricas, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
