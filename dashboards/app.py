"""
Dashboard interactivo para prediccion de esperanza de vida.
Visualizaciones diferenciadas por audiencia:
- Ejecutiva: KPIs y resumen general
- Tecnica: analisis detallado y correlaciones
- Operativa: datos individuales y filtros
"""
import streamlit as st
import pandas as pd
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


def vista_ejecutiva(df):
    """Vista para audiencia ejecutiva con KPIs y resumen."""
    st.header("Vista Ejecutiva")
    st.markdown("Resumen general del estado de salud de la poblacion analizada.")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Participantes", f"{len(df):,}")
    with col2:
        edad_prom = df['edad'].mean()
        st.metric("Edad Promedio", f"{edad_prom:.1f} años")
    with col3:
        imc_prom = df['imc'].mean()
        st.metric("IMC Promedio", f"{imc_prom:.1f}")
    with col4:
        pct_buena_salud = (df['estado_salud_general'].isin(
            ['Excelente', 'Muy bueno', 'Bueno']
        )).mean() * 100
        st.metric("Salud Buena o Superior", f"{pct_buena_salud:.1f}%")

    st.subheader("Distribucion por Estado de Salud")
    salud_counts = df['estado_salud_general'].value_counts().reset_index()
    salud_counts.columns = ['Estado', 'Cantidad']
    fig = px.pie(
        salud_counts,
        values='Cantidad',
        names='Estado',
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Participantes por Periodo")
        periodo_counts = df['periodo'].value_counts().reset_index()
        periodo_counts.columns = ['Periodo', 'Cantidad']
        fig2 = px.bar(
            periodo_counts,
            x='Periodo',
            y='Cantidad',
            color='Periodo',
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        st.plotly_chart(fig2, use_container_width=True)

    with col2:
        st.subheader("Distribucion por Genero")
        genero_counts = df['genero'].value_counts().reset_index()
        genero_counts.columns = ['Genero', 'Cantidad']
        fig3 = px.bar(
            genero_counts,
            x='Genero',
            y='Cantidad',
            color='Genero',
            color_discrete_sequence=['#636EFA', '#EF553B']
        )
        st.plotly_chart(fig3, use_container_width=True)


def vista_tecnica(df):
    """Vista para audiencia tecnica con analisis detallado."""
    st.header("Vista Tecnica")
    st.markdown("Analisis estadistico detallado y correlaciones entre variables.")

    st.subheader("Estadisticas Descriptivas")
    cols_numericas = ['edad', 'imc', 'peso_kg', 'altura_cm', 'ratio_pobreza']
    cols_disponibles = [c for c in cols_numericas if c in df.columns]
    st.dataframe(df[cols_disponibles].describe().round(2), use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Distribucion de Edad por Genero")
        fig = px.box(
            df.dropna(subset=['edad', 'genero']),
            x='genero',
            y='edad',
            color='genero',
            color_discrete_sequence=['#636EFA', '#EF553B']
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Distribucion de IMC por Estado de Salud")
        fig2 = px.box(
            df.dropna(subset=['imc', 'estado_salud_general']),
            x='estado_salud_general',
            y='imc',
            color='estado_salud_general',
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Relacion entre Edad e IMC")
    fig3 = px.scatter(
        df.dropna(subset=['edad', 'imc', 'estado_salud_general']).sample(min(1000, len(df))),
        x='edad',
        y='imc',
        color='estado_salud_general',
        opacity=0.6,
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    st.plotly_chart(fig3, use_container_width=True)

    st.subheader("Matriz de Correlacion")
    corr = df[cols_disponibles].corr().round(2)
    fig4 = px.imshow(
        corr,
        color_continuous_scale='RdBu',
        zmin=-1, zmax=1
    )
    st.plotly_chart(fig4, use_container_width=True)


def vista_operativa(df):
    """Vista para audiencia operativa con filtros y datos individuales."""
    st.header("Vista Operativa")
    st.markdown("Exploracion interactiva de datos con filtros.")

    col1, col2, col3 = st.columns(3)
    with col1:
        generos = ['Todos'] + sorted(df['genero'].dropna().unique().tolist())
        genero_sel = st.selectbox("Genero", generos)
    with col2:
        periodos = ['Todos'] + sorted(df['periodo'].dropna().unique().tolist())
        periodo_sel = st.selectbox("Periodo", periodos)
    with col3:
        estados = ['Todos'] + sorted(df['estado_salud_general'].dropna().unique().tolist())
        estado_sel = st.selectbox("Estado de Salud", estados)

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

    st.metric("Registros filtrados", f"{len(df_filtrado):,}")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Distribucion de Edad")
        fig = px.histogram(
            df_filtrado.dropna(subset=['edad']),
            x='edad',
            nbins=20,
            color_discrete_sequence=['#636EFA']
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Distribucion de IMC")
        fig2 = px.histogram(
            df_filtrado.dropna(subset=['imc']),
            x='imc',
            nbins=20,
            color_discrete_sequence=['#EF553B']
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Datos filtrados")
    st.dataframe(df_filtrado.head(100), use_container_width=True)


def main():
    st.title("Dashboard - Prediccion Esperanza de Vida")
    st.markdown("Datos NHANES 2015-2016 y 2017-2018 | CDC/National Center for Health Statistics")

    df = cargar_datos()

    vista = st.sidebar.radio(
        "Selecciona la vista",
        ["Ejecutiva", "Tecnica", "Operativa"]
    )

    if vista == "Ejecutiva":
        vista_ejecutiva(df)
    elif vista == "Tecnica":
        vista_tecnica(df)
    elif vista == "Operativa":
        vista_operativa(df)


if __name__ == "__main__":
    main()