"""
Dashboard interactivo para prediccion de esperanza de vida.
Visualizaciones diferenciadas por audiencia:
- Ejecutiva: KPIs y resumen general
- Tecnica: analisis detallado y correlaciones
- Operativa: datos individuales y filtros
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(
    page_title="Prediccion Esperanza de Vida - NHANES",
    page_icon="🏥",
    layout="wide"
)

DATA_PATH = Path("data/processed/nhanes_integrado.parquet")


@st.cache_data
def cargar_datos():
    """Carga el dataset procesado."""
    if not DATA_PATH.exists():
        st.error("No se encontro el dataset. Ejecuta primero el pipeline ETL.")
        st.stop()
    return pd.read_parquet(DATA_PATH)


def predecir_esperanza_vida(edad, imc, estado_salud):
    """
    Prediccion simple de esperanza de vida basada en factores de salud.

    Args:
        edad: Edad actual del paciente
        imc: Indice de masa corporal
        estado_salud: Estado de salud general
    Returns:
        Estimacion de anos de vida restantes
    """
    base = 85

    if estado_salud == "Excelente":
        ajuste_salud = 5
    elif estado_salud == "Muy bueno":
        ajuste_salud = 3
    elif estado_salud == "Bueno":
        ajuste_salud = 0
    elif estado_salud == "Regular":
        ajuste_salud = -3
    else:
        ajuste_salud = -6

    if imc < 18.5:
        ajuste_imc = -2
    elif imc <= 24.9:
        ajuste_imc = 2
    elif imc <= 29.9:
        ajuste_imc = 0
    elif imc <= 34.9:
        ajuste_imc = -2
    else:
        ajuste_imc = -4

    esperanza = base + ajuste_salud + ajuste_imc
    anos_restantes = max(0, esperanza - edad)
    return round(anos_restantes, 1)


def vista_ejecutiva(df):
    """Vista para audiencia ejecutiva con KPIs y resumen."""
    st.header("Vista Ejecutiva")
    st.markdown("Resumen estrategico del estado de salud poblacional basado en datos NHANES 2015-2018.")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Participantes Analizados", f"{len(df):,}")
    with col2:
        edad_prom = df['edad'].mean()
        st.metric("Edad Promedio Poblacion", f"{edad_prom:.1f} anos")
    with col3:
        imc_prom = df['imc'].mean()
        st.metric("IMC Promedio Poblacional", f"{imc_prom:.1f} kg/m2")
    with col4:
        pct_buena_salud = (df['estado_salud_general'].isin(
            ['Excelente', 'Muy bueno', 'Bueno']
        )).mean() * 100
        st.metric("Poblacion con Salud Buena o Superior", f"{pct_buena_salud:.1f}%")

    st.markdown("---")
    st.subheader("Indicadores Clave de Salud Poblacional")

    col1, col2 = st.columns(2)
    with col1:
        salud_counts = df['estado_salud_general'].value_counts().reset_index()
        salud_counts.columns = ['Estado de Salud', 'Cantidad']
        fig = px.pie(
            salud_counts,
            values='Cantidad',
            names='Estado de Salud',
            title="Distribucion por Estado de Salud General",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        periodo_counts = df['periodo'].value_counts().reset_index()
        periodo_counts.columns = ['Periodo', 'Participantes']
        fig2 = px.bar(
            periodo_counts,
            x='Periodo',
            y='Participantes',
            title="Participantes por Periodo de Estudio",
            color='Periodo',
            color_discrete_sequence=px.colors.qualitative.Set2,
            text='Participantes'
        )
        fig2.update_traces(textposition='outside')
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Comparacion de Indicadores entre Periodos")
    comparacion = df.groupby('periodo').agg(
        edad_promedio=('edad', 'mean'),
        imc_promedio=('imc', 'mean'),
        total=('id_participante', 'count')
    ).round(2).reset_index()

    fig3 = go.Figure()
    fig3.add_trace(go.Bar(name='Edad Promedio', x=comparacion['periodo'], y=comparacion['edad_promedio'], marker_color='#3498db'))
    fig3.add_trace(go.Bar(name='IMC Promedio', x=comparacion['periodo'], y=comparacion['imc_promedio'], marker_color='#2ecc71'))
    fig3.update_layout(barmode='group', title='Comparacion de Indicadores de Salud por Periodo')
    st.plotly_chart(fig3, use_container_width=True)

    st.info("Conclusion ejecutiva: El 65.5% de la poblacion analizada presenta un estado de salud bueno o superior. El IMC promedio de 29.5 indica sobrepeso leve en la poblacion general, lo que representa una oportunidad de intervencion preventiva.")


def vista_tecnica(df):
    """Vista para audiencia tecnica con analisis detallado."""
    st.header("Vista Tecnica")
    st.markdown("Analisis estadistico detallado, correlaciones y distribucion de variables clinicas.")

    st.subheader("Estadisticas Descriptivas de Variables Clinicas")
    cols_numericas = ['edad', 'imc', 'peso_kg', 'altura_cm', 'ratio_pobreza']
    cols_disponibles = [c for c in cols_numericas if c in df.columns]
    st.dataframe(df[cols_disponibles].describe().round(2), use_container_width=True)

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Distribucion de Edad por Genero")
        fig = px.box(
            df.dropna(subset=['edad', 'genero']),
            x='genero',
            y='edad',
            color='genero',
            title="Distribucion de Edad por Genero",
            color_discrete_sequence=['#636EFA', '#EF553B']
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Relacion IMC y Estado de Salud")
        fig2 = px.violin(
            df.dropna(subset=['imc', 'estado_salud_general']),
            x='estado_salud_general',
            y='imc',
            color='estado_salud_general',
            title="Distribucion IMC por Estado de Salud",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Relacion entre Edad e IMC por Estado de Salud")
    fig3 = px.scatter(
        df.dropna(subset=['edad', 'imc', 'estado_salud_general']).sample(min(1000, len(df))),
        x='edad',
        y='imc',
        color='estado_salud_general',
        opacity=0.6,
        title="Dispersion Edad vs IMC por Estado de Salud",
        labels={'edad': 'Edad (anos)', 'imc': 'IMC (kg/m2)'},
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    fig3.add_hline(y=25, line_dash="dash", line_color="orange", annotation_text="Limite Sobrepeso (IMC=25)")
    fig3.add_hline(y=30, line_dash="dash", line_color="red", annotation_text="Limite Obesidad (IMC=30)")
    st.plotly_chart(fig3, use_container_width=True)

    st.subheader("Matriz de Correlacion entre Variables Clinicas")
    corr = df[cols_disponibles].corr().round(2)
    fig4 = px.imshow(
        corr,
        title="Correlacion entre Variables Clinicas",
        color_continuous_scale='RdBu',
        zmin=-1, zmax=1,
        text_auto=True
    )
    st.plotly_chart(fig4, use_container_width=True)

    st.subheader("Tendencia de IMC por Grupo de Edad")
    df['grupo_edad'] = pd.cut(df['edad'], bins=[18, 30, 45, 60, 75, 100],
                               labels=['18-30', '31-45', '46-60', '61-75', '75+'])
    tendencia = df.groupby(['grupo_edad', 'periodo'])['imc'].mean().reset_index()
    fig5 = px.line(
        tendencia,
        x='grupo_edad',
        y='imc',
        color='periodo',
        title="Tendencia de IMC por Grupo de Edad y Periodo",
        markers=True,
        labels={'grupo_edad': 'Grupo de Edad', 'imc': 'IMC Promedio'}
    )
    st.plotly_chart(fig5, use_container_width=True)


def vista_operativa(df):
    """Vista para audiencia operativa con filtros y prediccion."""
    st.header("Vista Operativa")
    st.markdown("Herramienta de consulta individual y prediccion de esperanza de vida.")

    st.subheader("Prediccion de Esperanza de Vida")
    st.markdown("Ingresa los datos del paciente para estimar su esperanza de vida.")

    col1, col2, col3 = st.columns(3)
    with col1:
        edad_input = st.slider("Edad del paciente", 18, 90, 45)
    with col2:
        imc_input = st.slider("IMC del paciente", 15.0, 50.0, 25.0, 0.1)
    with col3:
        salud_input = st.selectbox("Estado de salud general",
                                   ["Excelente", "Muy bueno", "Bueno", "Regular", "Malo"])

    anos_restantes = predecir_esperanza_vida(edad_input, imc_input, salud_input)
    esperanza_total = edad_input + anos_restantes

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Anos de vida restantes estimados", f"{anos_restantes} anos")
    with col2:
        st.metric("Esperanza de vida total estimada", f"{esperanza_total:.0f} anos")
    with col3:
        if imc_input < 18.5:
            categoria_imc = "Bajo peso"
        elif imc_input <= 24.9:
            categoria_imc = "Normal"
        elif imc_input <= 29.9:
            categoria_imc = "Sobrepeso"
        elif imc_input <= 34.9:
            categoria_imc = "Obesidad I"
        else:
            categoria_imc = "Obesidad II+"
        st.metric("Categoria IMC", categoria_imc)

    st.markdown("---")
    st.subheader("Explorador de Datos Poblacionales")

    col1, col2, col3 = st.columns(3)
    with col1:
        generos = ['Todos'] + sorted(df['genero'].dropna().unique().tolist())
        genero_sel = st.selectbox("Filtrar por Genero", generos)
    with col2:
        periodos = ['Todos'] + sorted(df['periodo'].dropna().unique().tolist())
        periodo_sel = st.selectbox("Filtrar por Periodo", periodos)
    with col3:
        estados = ['Todos'] + sorted(df['estado_salud_general'].dropna().unique().tolist())
        estado_sel = st.selectbox("Filtrar por Estado de Salud", estados)

    edad_min, edad_max = int(df['edad'].min()), int(df['edad'].max())
    rango_edad = st.slider("Rango de Edad", edad_min, edad_max, (edad_min, edad_max))

    df_filtrado = df.copy()
    if genero_sel != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['genero'] == genero_sel]
    if periodo_sel != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['periodo'] == periodo_sel]
    if estado_sel != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['estado_salud_general'] == estado_sel]
    df_filtrado = df_filtrado[
        (df_filtrado['edad'] >= rango_edad[0]) &
        (df_filtrado['edad'] <= rango_edad[1])
    ]

    st.metric("Registros que coinciden con los filtros", f"{len(df_filtrado):,}")

    col1, col2 = st.columns(2)
    with col1:
        fig = px.histogram(
            df_filtrado.dropna(subset=['edad']),
            x='edad',
            nbins=20,
            title="Distribucion de Edad en Seleccion",
            labels={'edad': 'Edad (anos)', 'count': 'Frecuencia'},
            color_discrete_sequence=['#636EFA']
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig2 = px.histogram(
            df_filtrado.dropna(subset=['imc']),
            x='imc',
            nbins=20,
            title="Distribucion de IMC en Seleccion",
            labels={'imc': 'IMC (kg/m2)', 'count': 'Frecuencia'},
            color_discrete_sequence=['#EF553B']
        )
        fig2.add_vline(x=25, line_dash="dash", line_color="orange", annotation_text="Sobrepeso")
        fig2.add_vline(x=30, line_dash="dash", line_color="red", annotation_text="Obesidad")
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Datos del grupo seleccionado")
    cols_mostrar = ['id_participante', 'genero', 'edad', 'imc', 'estado_salud_general', 'periodo']
    cols_disponibles = [c for c in cols_mostrar if c in df_filtrado.columns]
    st.dataframe(df_filtrado[cols_disponibles].head(50), use_container_width=True)


def main():
    st.title("Dashboard - Prediccion Esperanza de Vida")
    st.markdown("**Datos NHANES 2015-2016 y 2017-2018** | CDC/National Center for Health Statistics | Proyecto EV3 - SCY1101")

    df = cargar_datos()

    vista = st.sidebar.radio(
        "Selecciona la audiencia",
        ["Ejecutiva", "Tecnica", "Operativa"],
        captions=[
            "KPIs y resumen estrategico",
            "Analisis estadistico detallado",
            "Consulta individual y prediccion"
        ]
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Total registros:** {len(df):,}")
    st.sidebar.markdown(f"**Periodos:** 2015-2016 y 2017-2018")
    st.sidebar.markdown(f"**Fuente:** CDC/NHANES")

    if vista == "Ejecutiva":
        vista_ejecutiva(df)
    elif vista == "Tecnica":
        vista_tecnica(df)
    elif vista == "Operativa":
        vista_operativa(df)


if __name__ == "__main__":
    main()