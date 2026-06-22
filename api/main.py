"""
API REST para prediccion de esperanza de vida.
Expone endpoints para consultar datos NHANES procesados.
"""
import logging
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="API Prediccion Esperanza de Vida",
    description="API REST para consultar datos NHANES 2015-2018",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_PATH = Path("data/processed/nhanes_integrado.parquet")


def cargar_datos() -> pd.DataFrame:
    """Carga el dataset procesado."""
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset no encontrado: {DATA_PATH}")
    return pd.read_parquet(DATA_PATH)


@app.get("/")
def root():
    """Endpoint raiz con informacion de la API."""
    return {
        "nombre": "API Prediccion Esperanza de Vida",
        "version": "1.0.0",
        "descripcion": "API REST para datos NHANES 2015-2018",
        "endpoints": [
            "/health",
            "/datos/resumen",
            "/datos/participantes",
            "/datos/estadisticas",
            "/datos/por-genero",
            "/datos/por-periodo",
        ]
    }


@app.get("/health")
def health_check():
    """Verifica el estado de la API."""
    try:
        df = cargar_datos()
        return {
            "estado": "saludable",
            "total_registros": len(df),
            "dataset": str(DATA_PATH)
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/datos/resumen")
def resumen():
    """Retorna un resumen general del dataset."""
    try:
        df = cargar_datos()
        return {
            "total_participantes": len(df),
            "periodos": df['periodo'].unique().tolist(),
            "edad_promedio": round(df['edad'].mean(), 2),
            "imc_promedio": round(df['imc'].mean(), 2),
            "distribucion_genero": df['genero'].value_counts().to_dict(),
            "distribucion_salud": df['estado_salud_general'].value_counts().to_dict(),
        }
    except Exception as e:
        logger.error(f"Error en resumen: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/datos/participantes")
def obtener_participantes(
    limite: int = Query(default=10, ge=1, le=100),
    periodo: Optional[str] = Query(default=None),
    genero: Optional[str] = Query(default=None),
):
    """
    Retorna lista de participantes con filtros opcionales.

    Args:
        limite: Numero maximo de registros a retornar (1-100)
        periodo: Filtrar por periodo (2015-2016 o 2017-2018)
        genero: Filtrar por genero (Masculino o Femenino)
    """
    try:
        df = cargar_datos()

        if periodo:
            df = df[df['periodo'] == periodo]
        if genero:
            df = df[df['genero'] == genero]

        df = df.head(limite)
        df = df.fillna("No disponible")

        return {
            "total": len(df),
            "participantes": df.to_dict(orient="records")
        }
    except Exception as e:
        logger.error(f"Error en participantes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/datos/estadisticas")
def estadisticas():
    """Retorna estadisticas descriptivas del dataset."""
    try:
        df = cargar_datos()
        cols = ['edad', 'imc', 'peso_kg', 'altura_cm', 'ratio_pobreza']
        cols_disponibles = [c for c in cols if c in df.columns]
        stats = df[cols_disponibles].describe().round(2)
        return stats.to_dict()
    except Exception as e:
        logger.error(f"Error en estadisticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/datos/por-genero")
def datos_por_genero():
    """Retorna estadisticas agrupadas por genero."""
    try:
        df = cargar_datos()
        resultado = df.groupby('genero').agg(
            total=('id_participante', 'count'),
            edad_promedio=('edad', 'mean'),
            imc_promedio=('imc', 'mean'),
        ).round(2).reset_index()
        return resultado.to_dict(orient="records")
    except Exception as e:
        logger.error(f"Error en datos por genero: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/datos/por-periodo")
def datos_por_periodo():
    """Retorna estadisticas agrupadas por periodo."""
    try:
        df = cargar_datos()
        resultado = df.groupby('periodo').agg(
            total=('id_participante', 'count'),
            edad_promedio=('edad', 'mean'),
            imc_promedio=('imc', 'mean'),
        ).round(2).reset_index()
        return resultado.to_dict(orient="records")
    except Exception as e:
        logger.error(f"Error en datos por periodo: {e}")
        raise HTTPException(status_code=500, detail=str(e))