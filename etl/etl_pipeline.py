"""
Pipeline ETL principal para datos NHANES.
Integra datos demograficos, de examen y cuestionario
de los periodos 2015-2016 y 2017-2018.
"""
import os
import logging
import pandas as pd
import numpy as np
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

DATA_RAW = Path("data/raw")
DATA_PROCESSED = Path("data/processed")
DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

ARCHIVOS_NHANES = {
    "2015-2016": {
        "demographics": DATA_RAW / "nhanes2015-2016/Demographics Data/DEMO_I.xpt",
        "examination": DATA_RAW / "nhanes2015-2016/Examination Data/BMX_I.xpt",
        "questionnaire": DATA_RAW / "nhanes2015-2016/Questionnaire Data/HSQ_I.xpt",
    },
    "2017-2018": {
        "demographics": DATA_RAW / "nhanes2017-2018/Demographics Data/DEMO_J.xpt",
        "examination": DATA_RAW / "nhanes2017-2018/Examination Data/BMX_J.xpt",
        "questionnaire": DATA_RAW / "nhanes2017-2018/Questionnaire Data/HSQ_J.xpt",
    },
}

def cargar_xpt(filepath: Path, periodo: str, tipo: str) -> pd.DataFrame:
    """
    Carga un archivo XPT de NHANES.

    Args:
        filepath: Ruta al archivo XPT
        periodo: Periodo del dataset (2015-2016 o 2017-2018)
        tipo: Tipo de dataset (demographics, examination, questionnaire)
    Returns:
        DataFrame cargado
    """
    try:
        if not filepath.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {filepath}")
        df = pd.read_sas(filepath, format="xport", encoding="utf-8")
        df["periodo"] = periodo
        df["tipo_fuente"] = tipo
        logger.info(f"Cargado {tipo} {periodo}: {df.shape[0]} filas, {df.shape[1]} columnas")
        return df
    except FileNotFoundError as e:
        logger.error(str(e))
        raise
    except Exception as e:
        logger.error(f"Error al cargar {filepath}: {e}")
        raise


def validar_esquema(df: pd.DataFrame, columnas_requeridas: list, nombre: str) -> bool:
    """
    Valida que el DataFrame tenga las columnas requeridas.

    Args:
        df: DataFrame a validar
        columnas_requeridas: Lista de columnas que deben existir
        nombre: Nombre del dataset para logging
    Returns:
        True si el esquema es valido
    """
    columnas_faltantes = [c for c in columnas_requeridas if c not in df.columns]
    if columnas_faltantes:
        logger.warning(f"{nombre}: columnas faltantes: {columnas_faltantes}")
        return False
    logger.info(f"{nombre}: esquema validado correctamente")
    return True


def limpiar_demographics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia y transforma el dataset de demograficos.

    Args:
        df: DataFrame de demograficos
    Returns:
        DataFrame limpio
    """
    columnas_utiles = [
        "SEQN", "RIAGENDR", "RIDAGEYR", "RIDRETH3",
        "DMDEDUC2", "INDFMPIR", "periodo"
    ]
    columnas_disponibles = [c for c in columnas_utiles if c in df.columns]
    df = df[columnas_disponibles].copy()

    rename_map = {
        "SEQN": "id_participante",
        "RIAGENDR": "genero",
        "RIDAGEYR": "edad",
        "RIDRETH3": "etnia",
        "DMDEDUC2": "nivel_educacion",
        "INDFMPIR": "ratio_pobreza",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    if "genero" in df.columns:
        df["genero"] = df["genero"].map({1: "Masculino", 2: "Femenino"})

    if "edad" in df.columns:
        df["edad"] = pd.to_numeric(df["edad"], errors="coerce")
        df = df[df["edad"] >= 18]

    logger.info(f"Demographics limpio: {df.shape[0]} filas")
    return df


def limpiar_examination(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia y transforma el dataset de examinacion fisica.

    Args:
        df: DataFrame de examinacion
    Returns:
        DataFrame limpio
    """
    columnas_utiles = ["SEQN", "BMXWT", "BMXHT", "BMXBMI", "periodo"]
    columnas_disponibles = [c for c in columnas_utiles if c in df.columns]
    df = df[columnas_disponibles].copy()

    rename_map = {
        "SEQN": "id_participante",
        "BMXWT": "peso_kg",
        "BMXHT": "altura_cm",
        "BMXBMI": "imc",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    for col in ["peso_kg", "altura_cm", "imc"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    logger.info(f"Examination limpio: {df.shape[0]} filas")
    return df


def limpiar_questionnaire(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia y transforma el dataset de cuestionario de salud.

    Args:
        df: DataFrame de cuestionario
    Returns:
        DataFrame limpio
    """
    columnas_utiles = ["SEQN", "HSD010", "periodo"]
    columnas_disponibles = [c for c in columnas_utiles if c in df.columns]
    df = df[columnas_disponibles].copy()

    rename_map = {
        "SEQN": "id_participante",
        "HSD010": "estado_salud_general",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    if "estado_salud_general" in df.columns:
        df["estado_salud_general"] = df["estado_salud_general"].map({
            1: "Excelente",
            2: "Muy bueno",
            3: "Bueno",
            4: "Regular",
            5: "Malo",
        })

    logger.info(f"Questionnaire limpio: {df.shape[0]} filas")
    return df


def integrar_datasets(demo: pd.DataFrame, exam: pd.DataFrame, quest: pd.DataFrame) -> pd.DataFrame:
    """
    Integra los 3 datasets usando id_participante como clave.

    Args:
        demo: DataFrame de demograficos
        exam: DataFrame de examinacion
        quest: DataFrame de cuestionario
    Returns:
        DataFrame integrado
    """
    df = demo.merge(
        exam.drop(columns=["periodo"], errors="ignore"),
        on="id_participante",
        how="left"
    )
    df = df.merge(
        quest.drop(columns=["periodo"], errors="ignore"),
        on="id_participante",
        how="left"
    )
    logger.info(f"Dataset integrado: {df.shape[0]} filas, {df.shape[1]} columnas")
    return df


def guardar_procesado(df: pd.DataFrame, nombre: str) -> None:
    """
    Guarda el dataset procesado en formato Parquet.

    Args:
        df: DataFrame a guardar
        nombre: Nombre del archivo
    """
    filepath = DATA_PROCESSED / f"{nombre}.parquet"
    df.to_parquet(filepath, index=False)
    logger.info(f"Dataset guardado en: {filepath}")


def ejecutar_pipeline() -> pd.DataFrame:
    """
    Ejecuta el pipeline ETL completo.

    Returns:
        DataFrame final integrado
    """
    logger.info("Iniciando pipeline ETL NHANES")
    dfs_integrados = []

    for periodo, archivos in ARCHIVOS_NHANES.items():
        logger.info(f"Procesando periodo: {periodo}")

        demo_raw = cargar_xpt(archivos["demographics"], periodo, "demographics")
        exam_raw = cargar_xpt(archivos["examination"], periodo, "examination")
        quest_raw = cargar_xpt(archivos["questionnaire"], periodo, "questionnaire")

        demo = limpiar_demographics(demo_raw)
        exam = limpiar_examination(exam_raw)
        quest = limpiar_questionnaire(quest_raw)

        validar_esquema(demo, ["id_participante", "edad", "genero"], "demographics")
        validar_esquema(exam, ["id_participante", "imc"], "examination")
        validar_esquema(quest, ["id_participante"], "questionnaire")

        df_periodo = integrar_datasets(demo, exam, quest)
        df_periodo["periodo"] = periodo
        dfs_integrados.append(df_periodo)

    df_final = pd.concat(dfs_integrados, ignore_index=True)
    df_final = df_final.drop_duplicates(subset=["id_participante"])

    guardar_procesado(df_final, "nhanes_integrado")

    logger.info(f"Pipeline completado. Dataset final: {df_final.shape[0]} filas")
    return df_final


def validar_esquema_completo(df: pd.DataFrame, nombre: str) -> dict:
    """
    Realiza validacion completa del esquema del dataset.

    Args:
        df: DataFrame a validar
        nombre: Nombre del dataset
    Returns:
        Diccionario con resultados de validacion
    """
    resultado = {
        "dataset": nombre,
        "filas": df.shape[0],
        "columnas": df.shape[1],
        "nulos_total": int(df.isnull().sum().sum()),
        "porcentaje_nulos": round(df.isnull().sum().sum() / (df.shape[0] * df.shape[1]) * 100, 2),
        "duplicados": int(df.duplicated().sum()),
        "tipos_datos": df.dtypes.astype(str).to_dict(),
        "validacion_ok": True,
        "errores": []
    }

    if df.shape[0] == 0:
        resultado["validacion_ok"] = False
        resultado["errores"].append("Dataset vacio")
        logger.error(f"{nombre}: Dataset vacio")

    if df.isnull().sum().sum() / (df.shape[0] * df.shape[1]) > 0.5:
        resultado["validacion_ok"] = False
        resultado["errores"].append("Mas del 50% de valores nulos")
        logger.warning(f"{nombre}: Alto porcentaje de nulos")

    if df.duplicated().sum() > df.shape[0] * 0.3:
        resultado["validacion_ok"] = False
        resultado["errores"].append("Mas del 30% de duplicados")
        logger.warning(f"{nombre}: Alto porcentaje de duplicados")

    if resultado["validacion_ok"]:
        logger.info(f"{nombre}: Validacion de esquema exitosa")
    else:
        logger.error(f"{nombre}: Validacion de esquema fallida - {resultado['errores']}")

    return resultado


def generar_reporte_calidad(df_final: pd.DataFrame) -> dict:
    """
    Genera reporte final de calidad del dataset integrado.

    Args:
        df_final: DataFrame final integrado
    Returns:
        Diccionario con reporte de calidad
    """
    reporte = {
        "total_registros": len(df_final),
        "total_columnas": df_final.shape[1],
        "nulos_restantes": int(df_final.isnull().sum().sum()),
        "duplicados_restantes": int(df_final.duplicated().sum()),
        "periodos": df_final['periodo'].unique().tolist(),
        "distribucion_genero": df_final['genero'].value_counts().to_dict(),
        "edad_promedio": round(df_final['edad'].mean(), 2),
        "imc_promedio": round(df_final['imc'].mean(), 2),
        "calidad_ok": True
    }

    if reporte["nulos_restantes"] > 0:
        logger.warning(f"Reporte final: {reporte['nulos_restantes']} nulos restantes")

    if reporte["duplicados_restantes"] > 0:
        logger.warning(f"Reporte final: {reporte['duplicados_restantes']} duplicados restantes")

    logger.info(f"Reporte de calidad generado: {reporte['total_registros']} registros")
    print("\nReporte de Calidad Final:")
    for k, v in reporte.items():
        print(f"  {k}: {v}")

    return reporte

    if __name__ == "__main__":
    df = ejecutar_pipeline()

    validar_esquema_completo(df, "dataset_final")
    reporte = generar_reporte_calidad(df)

    print("\nPipeline ETL completado exitosamente")
    print(df.head())
    print(df.dtypes)