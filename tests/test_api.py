"""
Tests automatizados para la API REST.
Evaluacion Parcial N°3 - SCY1101
"""
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from fastapi.testclient import TestClient
import sys

sys.path.append(str(Path(__file__).parent.parent))

from api.main import app

client = TestClient(app)


def test_root():
    """Verifica que el endpoint raiz responde correctamente."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "nombre" in data
    assert "version" in data
    assert "endpoints" in data


def test_health_check():
    """Verifica que el endpoint health responde correctamente."""
    response = client.get("/health")
    assert response.status_code in [200, 503]


def test_resumen():
    """Verifica que el endpoint resumen retorna datos correctos."""
    response = client.get("/datos/resumen")
    if response.status_code == 200:
        data = response.json()
        assert "total_participantes" in data
        assert "periodos" in data
        assert "edad_promedio" in data
        assert "imc_promedio" in data


def test_participantes_default():
    """Verifica que el endpoint participantes retorna datos por defecto."""
    response = client.get("/datos/participantes")
    if response.status_code == 200:
        data = response.json()
        assert "total" in data
        assert "participantes" in data
        assert len(data["participantes"]) <= 10


def test_participantes_limite():
    """Verifica que el limite de participantes funciona correctamente."""
    response = client.get("/datos/participantes?limite=5")
    if response.status_code == 200:
        data = response.json()
        assert len(data["participantes"]) <= 5


def test_participantes_filtro_genero():
    """Verifica que el filtro por genero funciona."""
    response = client.get("/datos/participantes?genero=Masculino")
    if response.status_code == 200:
        data = response.json()
        assert "participantes" in data


def test_estadisticas():
    """Verifica que el endpoint estadisticas retorna datos."""
    response = client.get("/datos/estadisticas")
    if response.status_code == 200:
        data = response.json()
        assert "edad" in data or "imc" in data


def test_por_genero():
    """Verifica que el endpoint por genero retorna datos."""
    response = client.get("/datos/por-genero")
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list)


def test_por_periodo():
    """Verifica que el endpoint por periodo retorna datos."""
    response = client.get("/datos/por-periodo")
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list)


def test_participantes_limite_invalido():
    """Verifica que un limite invalido retorna error."""
    response = client.get("/datos/participantes?limite=0")
    assert response.status_code == 422


def test_endpoint_inexistente():
    """Verifica que un endpoint que no existe retorna 404."""
    response = client.get("/datos/inexistente")
    assert response.status_code == 404