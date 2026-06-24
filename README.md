El README ya existe también. Abre el archivo `README.md` en VS Code y reemplaza todo el contenido con esto:

```markdown
# Proyecto Evaluación 3 - Predicción Esperanza de Vida
**SCY1101 - Programación para la Ciencia de Datos | DuocUC**

## Integrantes
- Alvaro Oyarzun (Alvarooyar) - Pipeline ETL
- Matias Caileo (matiasCaileo) - Dashboard
- Nelson Oyarzo (NelsonOyarzo) - API REST, Docker y AWS

---

## Descripción del Proyecto
Sistema de análisis y predicción de esperanza de vida basado en datos poblacionales NHANES (National Health and Nutrition Examination Survey) de los periodos 2015-2016 y 2017-2018 del CDC.

---

## Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────┐
│                      AWS EC2 (t3.micro)                  │
│                   IP: 100.57.182.71                      │
│                                                          │
│   ┌─────────────────┐      ┌─────────────────────────┐  │
│   │   Dashboard      │      │       API REST           │  │
│   │   Streamlit      │      │       FastAPI            │  │
│   │   Puerto 8501    │      │       Puerto 8000        │  │
│   └────────┬────────┘      └────────────┬────────────┘  │
│            │                            │                │
│            └──────────────┬─────────────┘               │
│                           │                             │
│              ┌────────────▼───────────┐                 │
│              │   data/processed/       │                 │
│              │   nhanes_integrado      │                 │
│              │   .parquet             │                 │
│              └────────────▲───────────┘                 │
│                           │                             │
│              ┌────────────┴───────────┐                 │
│              │   Pipeline ETL         │                 │
│              │   etl/etl_pipeline.py  │                 │
│              └────────────▲───────────┘                 │
└───────────────────────────┼─────────────────────────────┘
                            │
              ┌─────────────┴──────────┐
              │   Amazon S3            │
              │   proyecto-ev3-datos   │
              │   nhanes_integrado     │
              │   .parquet             │
              └────────────────────────┘
```

---

## URLs del Proyecto Desplegado

| Servicio | URL |
|----------|-----|
| Dashboard | http://100.57.182.71:8501 |
| API REST | http://100.57.182.71:8000 |
| Documentacion API | http://100.57.182.71:8000/docs |

---

## Estructura del Proyecto

```
-evaluacion3_cienciaDatos/
├── api/
│   └── main.py              # API REST con FastAPI
├── dashboards/
│   └── app.py               # Dashboard Streamlit 4 vistas
├── docker/
│   ├── Dockerfile           # Imagen contenedor API
│   └── Dockerfile.dashboard # Imagen contenedor Dashboard
├── etl/
│   └── etl_pipeline.py      # Pipeline ETL NHANES
├── tests/
│   ├── __init__.py
│   └── test_api.py          # 11 tests automatizados
├── data/
│   └── processed/           # Dataset procesado (no en Git)
├── docs/
│   └── README.md            # Este archivo
├── docker-compose.yml       # Orquestacion de contenedores
├── requirements.txt         # Dependencias Python
└── .gitignore              # Archivos excluidos de Git
```

---

## Componentes

### 1. Pipeline ETL (Alvaro)
- Carga archivos XPT desde CDC/NHANES
- Integra datos de 2 periodos (2015-2016 y 2017-2018)
- Validacion de esquemas y manejo de errores
- Genera reporte de calidad de datos
- Salida: `data/processed/nhanes_integrado.parquet`

### 2. Dashboard Streamlit (Matias)
4 vistas diferenciadas por audiencia:
- **Ejecutiva:** KPIs, distribucion por salud, comparacion periodos
- **Tecnica:** Estadisticas descriptivas, correlaciones, violin plots
- **Operativa:** Busqueda por ID, prediccion rapida con sliders
- **Personal:** Formulario individual con comparacion vs poblacion

### 3. API REST FastAPI (Nelson)
6 endpoints disponibles:
- `GET /` - Informacion de la API
- `GET /health` - Estado del servicio
- `GET /datos/resumen` - Resumen general
- `GET /datos/participantes` - Lista con filtros
- `GET /datos/estadisticas` - Estadisticas descriptivas
- `GET /datos/por-genero` - Agrupado por genero
- `GET /datos/por-periodo` - Agrupado por periodo

### 4. Docker
- 2 contenedores orquestados con docker-compose
- Volumen compartido para datos procesados
- Puertos 8000 (API) y 8501 (Dashboard)

### 5. Tests Automatizados
- 11 tests con pytest
- Cobertura de todos los endpoints
- Reporte HTML en `tests/coverage_report/`

---

## Instalacion Local

### Requisitos
- Python 3.12+
- Docker Desktop
- Git

### Pasos

```bash
# Clonar repositorio
git clone https://github.com/Alvarooyar/-evaluacion3_cienciaDatos.git
cd -evaluacion3_cienciaDatos

# Copiar dataset procesado a data/processed/
# (solicitar nhanes_integrado.parquet a integrantes del equipo)

# Ejecutar con Docker
docker-compose up --build

# O ejecutar localmente
pip install -r requirements.txt
python -m streamlit run dashboards/app.py
uvicorn api.main:app --reload
```

---

## Despliegue en AWS EC2

### Reactivar el proyecto

```bash
# 1. Iniciar instancia en consola AWS EC2
# 2. Conectar via EC2 Instance Connect
# 3. Ejecutar:
cd ./-evaluacion3_cienciaDatos
aws s3 cp s3://proyecto-ev3-datos/nhanes_integrado.parquet data/processed/nhanes_integrado.parquet
sudo docker-compose up -d

# 4. Acceder via:
# Dashboard: http://100.57.182.71:8501
# API: http://100.57.182.71:8000
```

---

## Datos NHANES

Los datos no estan incluidos en el repositorio. Para obtenerlos:
1. Descargar desde https://wwwn.cdc.gov/nchs/nhanes/
2. Periodos: 2015-2016 (sufijo _I) y 2017-2018 (sufijo _J)
3. Archivos necesarios: DEMO, BMX, HSQ de cada periodo
4. Organizar en `data/raw/nhanes2015-2016/` y `data/raw/nhanes2017-2018/`
5. Ejecutar `python etl/etl_pipeline.py`

---

## Tecnologias Utilizadas

| Tecnologia | Uso |
|------------|-----|
| Python 3.12 | Lenguaje principal |
| Streamlit | Dashboard interactivo |
| FastAPI | API REST |
| Pandas | Procesamiento de datos |
| Plotly | Visualizaciones |
| Scikit-learn | Modelo predictivo |
| Docker | Contenedorizacion |
| AWS EC2 | Despliegue en nube |
| AWS S3 | Almacenamiento de datos |
| pytest | Tests automatizados |
| Git/GitHub | Control de versiones |
```

Guarda con **`Ctrl + S`** y dime cuando este listo 😊
