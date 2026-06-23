import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from pathlib import Path
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder

DATA_PATH = Path(__file__).resolve().parent.parent / "data/processed/nhanes_integrado.parquet"


@st.cache_data
def cargar_datos():
    return pd.read_parquet(DATA_PATH)


@st.cache_resource
def entrenar_modelo(df):
    """Entrena un RandomForest para estimar esperanza de vida restante."""
    df_modelo = df.dropna(subset=['edad', 'imc', 'estado_salud_general', 'genero']).copy()

    base = np.where(df_modelo['genero'] == 'Masculino', 79.0, 81.0)

    ajuste_salud = {
        'Excelente': 5.0, 'Muy bueno': 2.0, 'Bueno': 0.0,
        'Regular': -4.0, 'Malo': -8.0
    }
    df_modelo['ajuste_salud'] = df_modelo['estado_salud_general'].map(ajuste_salud)

    condiciones_imc = [
        df_modelo['imc'] < 18.5,
        (df_modelo['imc'] >= 18.5) & (df_modelo['imc'] <= 24.9),
        (df_modelo['imc'] >= 25.0) & (df_modelo['imc'] <= 29.9),
        (df_modelo['imc'] >= 30.0) & (df_modelo['imc'] <= 34.9),
        df_modelo['imc'] >= 35.0
    ]
    valores_imc = [-3.0, 0.0, -1.0, -3.0, -6.0]
    df_modelo['ajuste_imc'] = np.select(condiciones_imc, valores_imc, default=0.0)

    df_modelo['esperanza_vida_total'] = base + df_modelo['ajuste_salud'] + df_modelo['ajuste_imc']
    df_modelo['esperanza_vida_total'] = df_modelo['esperanza_vida_total'].clip(60, 100)

    le_genero = LabelEncoder()
    le_salud = LabelEncoder()

    df_modelo['genero_enc'] = le_genero.fit_transform(df_modelo['genero'])
    df_modelo['salud_enc'] = le_salud.fit_transform(df_modelo['estado_salud_general'])

    features = ['edad', 'imc', 'genero_enc', 'salud_enc']
    X = df_modelo[features]
    y = df_modelo['esperanza_vida_total'] - df_modelo['edad']

    modelo = RandomForestRegressor(n_estimators=100, random_state=42, max_depth=10)
    modelo.fit(X, y)

    return modelo, le_genero, le_salud


def predecir_esperanza_vida(modelo, le_genero, le_salud, edad, imc, estado_salud, genero):
    """Predice los años de vida restantes."""
    genero_enc = le_genero.transform([genero])[0]
    salud_enc = le_salud.transform([estado_salud])[0]

    X_pred = pd.DataFrame([[edad, imc, genero_enc, salud_enc]],
                          columns=['edad', 'imc', 'genero_enc', 'salud_enc'])
    años_restantes = modelo.predict(X_pred)[0]
    años_restantes = max(años_restantes, 1.0)
    return round(años_restantes, 1)


def vista_ejecutiva(df):
    st.header("Vista Ejecutiva")
    st.markdown("Indicadores clave y resumen estratégico del estudio NHANES 2015-2018.")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Participantes", f"{len(df):,}")
    with col2:
        st.metric("Edad Promedio", f"{df['edad'].mean():.1f} años")
    with col3:
        st.metric("IMC Promedio", f"{df['imc'].mean():.1f}")
    with col4:
        pct_mujeres = (df['genero'] == 'Femenino').mean() * 100
        st.metric("% Mujeres", f"{pct_mujeres:.1f}%")

    col1, col2 = st.columns(2)
    with col1:
        gen_counts = df['genero'].value_counts().reset_index()
        gen_counts.columns = ['genero', 'count']
        fig = px.bar(gen_counts, x='genero', y='count',
                     title="Distribucion por Genero",
                     color='genero',
                     color_discrete_map={'Masculino': '#636EFA', 'Femenino': '#EF553B'},
                     text_auto=True)
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, width='stretch')

    with col2:
        salud_counts = df['estado_salud_general'].value_counts().reset_index()
        salud_counts.columns = ['estado_salud_general', 'count']
        fig = px.pie(salud_counts, values='count', names='estado_salud_general',
                     title="Estado de Salud General",
                     color_discrete_sequence=px.colors.qualitative.Set2)
        st.plotly_chart(fig, width='stretch')

    col1, col2 = st.columns(2)
    with col1:
        fig = px.histogram(df.dropna(subset=['edad']), x='edad', nbins=30,
                           title="Distribucion de Edad",
                           labels={'edad': 'Edad (años)'},
                           color_discrete_sequence=['#636EFA'])
        st.plotly_chart(fig, width='stretch')

    with col2:
        fig = px.histogram(df.dropna(subset=['imc']), x='imc', nbins=30,
                           title="Distribucion de IMC",
                           labels={'imc': 'IMC (kg/m²)'},
                           color_discrete_sequence=['#00CC96'])
        fig.add_vline(x=df['imc'].mean(), line_dash="dash", line_color="red",
                      annotation_text=f"Media: {df['imc'].mean():.1f}")
        st.plotly_chart(fig, width='stretch')

    st.subheader("Comparacion por Periodo")
    resumen_periodo = df.groupby('periodo').agg(
        Total=('id_participante', 'count'),
        Edad_Promedio=('edad', 'mean'),
        IMC_Promedio=('imc', 'mean'),
        Peso_Promedio=('peso_kg', 'mean')
    ).round(1).reset_index()
    st.dataframe(resumen_periodo, width='stretch')


def vista_tecnica(df):
    st.header("Vista Técnica")
    st.markdown("Análisis estadístico detallado del dataset.")

    st.subheader("Estadisticas Descriptivas")
    cols_num = ['edad', 'imc', 'peso_kg', 'altura_cm', 'ratio_pobreza']
    stats = df[cols_num].describe().round(2)
    st.dataframe(stats, width='stretch')

    st.subheader("Matriz de Correlacion")
    corr = df[cols_num].corr().round(2)
    fig = px.imshow(corr, text_auto=True, aspect="auto",
                    color_continuous_scale='RdBu_r',
                    title="Correlacion entre variables numericas")
    st.plotly_chart(fig, width='stretch')

    col1, col2 = st.columns(2)
    with col1:
        fig = px.box(df.dropna(subset=['imc', 'genero']), x='genero', y='imc',
                     title="IMC por Genero", color='genero',
                     color_discrete_map={'Masculino': '#636EFA', 'Femenino': '#EF553B'})
        st.plotly_chart(fig, width='stretch')

    with col2:
        fig = px.box(df.dropna(subset=['edad', 'estado_salud_general']),
                     x='estado_salud_general', y='edad',
                     title="Edad por Estado de Salud",
                     color='estado_salud_general',
                     color_discrete_sequence=px.colors.qualitative.Set2)
        st.plotly_chart(fig, width='stretch')

    st.subheader("Relacion Edad vs IMC")
    fig = px.scatter(df.dropna(subset=['edad', 'imc']), x='edad', y='imc',
                     color='genero', opacity=0.3,
                     title="Edad vs IMC por Genero",
                     labels={'edad': 'Edad (años)', 'imc': 'IMC (kg/m²)'},
                     color_discrete_map={'Masculino': '#636EFA', 'Femenino': '#EF553B'})
    st.plotly_chart(fig, width='stretch')

    st.subheader("Analisis de Valores Nulos")
    nulos = df.isnull().sum().reset_index()
    nulos.columns = ['Columna', 'Valores Nulos']
    nulos['Porcentaje'] = (nulos['Valores Nulos'] / len(df) * 100).round(1)
    nulos = nulos[nulos['Valores Nulos'] > 0].sort_values('Valores Nulos', ascending=False)

    if len(nulos) > 0:
        fig = px.bar(nulos, x='Columna', y='Valores Nulos',
                     title="Valores Nulos por Columna",
                     text_auto=True, color='Porcentaje',
                     color_continuous_scale='Viridis')
        st.plotly_chart(fig, width='stretch')
        st.dataframe(nulos, width='stretch')
    else:
        st.success("No hay valores nulos en el dataset.")


def vista_operativa(df, modelo, le_genero, le_salud):
    st.header("Vista Operativa")
    st.markdown("Consulta y prediccion rapida para un participante.")

    tab1, tab2 = st.tabs(["Buscar Participante", "Prediccion Rapida"])

    with tab1:
        st.subheader("Buscar por ID de Participante")
        id_input = st.text_input("Ingresa ID del participante (SEQN)", placeholder="Ej: 83732")

        if id_input and id_input.isdigit():
            id_val = float(id_input)
            match = df[df['id_participante'] == id_val]
            if len(match) > 0:
                row = match.iloc[0]
                st.success(f"Participante encontrado: {row['id_participante']:.0f}")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Genero", row['genero'])
                with col2:
                    st.metric("Edad", f"{row['edad']:.0f} años")
                with col3:
                    st.metric("IMC", f"{row['imc']:.1f}" if pd.notna(row['imc']) else "N/A")
                with col4:
                    st.metric("Salud", row['estado_salud_general'] if pd.notna(row['estado_salud_general']) else "N/A")

                if pd.notna(row['imc']) and pd.notna(row['estado_salud_general']):
                    pred = predecir_esperanza_vida(modelo, le_genero, le_salud,
                                                   row['edad'], row['imc'],
                                                   row['estado_salud_general'], row['genero'])
                    st.metric("Esperanza de vida restante estimada", f"{pred} años")
            else:
                st.warning(f"No se encontro participante con ID {id_input}")

    with tab2:
        st.subheader("Prediccion Rapida")
        col1, col2 = st.columns(2)
        with col1:
            edad_pred = st.slider("Edad", 18, 100, 40)
            peso_pred = st.slider("Peso (kg)", 30.0, 200.0, 70.0, 0.1)
        with col2:
            genero_pred = st.selectbox("Genero", ["Masculino", "Femenino"])
            altura_pred = st.slider("Altura (cm)", 100.0, 220.0, 170.0, 0.1)
            salud_pred = st.selectbox("Estado de salud",
                                       ["Excelente", "Muy bueno", "Bueno", "Regular", "Malo"])

        imc_pred = round(peso_pred / ((altura_pred / 100) ** 2), 1)
        st.metric("IMC Calculado", f"{imc_pred}")

        pred = predecir_esperanza_vida(modelo, le_genero, le_salud,
                                       edad_pred, imc_pred, salud_pred, genero_pred)
        total = edad_pred + pred

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Años restantes", f"{pred} años")
        with col2:
            st.metric("Esperanza de vida total", f"{total:.0f} años")
        with col3:
            prom_pob = df['imc'].mean()
            st.metric("IMC vs Promedio poblacional",
                      f"{imc_pred:.1f}",
                      delta=f"{imc_pred - prom_pob:+.1f}")


def vista_personal(df, modelo, le_genero, le_salud):
    """Vista personalizada donde el usuario ingresa sus datos y se compara con la poblacion."""
    st.header("Vista Personal")
    st.markdown("Ingresa tus datos personales para obtener un analisis comparativo con la poblacion NHANES.")

    st.subheader("Ingresa tus datos")
    col1, col2 = st.columns(2)
    with col1:
        nombre = st.text_input("Nombre (opcional)", placeholder="Ej: Juan")
        edad = st.number_input("Edad", min_value=18, max_value=100, value=35)
        peso = st.number_input("Peso (kg)", min_value=30.0, max_value=200.0, value=70.0, step=0.1)
    with col2:
        genero = st.selectbox("Genero", ["Masculino", "Femenino"])
        altura = st.number_input("Altura (cm)", min_value=100.0, max_value=220.0, value=170.0, step=0.1)
        estado_salud = st.selectbox("Estado de salud general",
                                     ["Excelente", "Muy bueno", "Bueno", "Regular", "Malo"])

    imc_usuario = round(peso / ((altura / 100) ** 2), 1)

    if imc_usuario < 18.5:
        categoria_imc = "Bajo peso"
    elif imc_usuario <= 24.9:
        categoria_imc = "Normal"
    elif imc_usuario <= 29.9:
        categoria_imc = "Sobrepeso"
    elif imc_usuario <= 34.9:
        categoria_imc = "Obesidad I"
    else:
        categoria_imc = "Obesidad II+"

    años_restantes = predecir_esperanza_vida(
        modelo, le_genero, le_salud, edad, imc_usuario, estado_salud, genero
    )
    esperanza_total = edad + años_restantes

    st.markdown("---")
    nombre_mostrar = nombre if nombre else "Tu"
    st.subheader(f"Resultados para {nombre_mostrar}")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Tu IMC", f"{imc_usuario}", delta=f"{categoria_imc}")
    with col2:
        st.metric("Años de vida restantes", f"{años_restantes} años")
    with col3:
        st.metric("Esperanza de vida total", f"{esperanza_total:.0f} años")
    with col4:
        imc_prom_pob = df['imc'].mean()
        diferencia_imc = round(imc_usuario - imc_prom_pob, 1)
        st.metric("Tu IMC vs Poblacion", f"{imc_usuario}", delta=f"{diferencia_imc:+.1f} vs promedio")

    st.markdown("---")
    st.subheader("Comparacion con la Poblacion")

    df_genero = df[df['genero'] == genero].copy()

    col1, col2 = st.columns(2)
    with col1:
        fig = px.histogram(
            df_genero.dropna(subset=['imc']),
            x='imc',
            nbins=30,
            title=f"Tu IMC vs Poblacion {genero}",
            labels={'imc': 'IMC (kg/m²)', 'count': 'Frecuencia'},
            color_discrete_sequence=['#636EFA'],
            opacity=0.7
        )
        fig.add_vline(x=imc_usuario, line_dash="solid", line_color="red",
                      line_width=3, annotation_text=f"Tu IMC: {imc_usuario}",
                      annotation_position="top right")
        fig.add_vline(x=df_genero['imc'].mean(), line_dash="dash", line_color="green",
                      annotation_text=f"Promedio: {df_genero['imc'].mean():.1f}")
        st.plotly_chart(fig, width='stretch')

    with col2:
        fig2 = px.histogram(
            df_genero.dropna(subset=['edad']),
            x='edad',
            nbins=30,
            title=f"Tu Edad vs Poblacion {genero}",
            labels={'edad': 'Edad (años)', 'count': 'Frecuencia'},
            color_discrete_sequence=['#EF553B'],
            opacity=0.7
        )
        fig2.add_vline(x=edad, line_dash="solid", line_color="red",
                       line_width=3, annotation_text=f"Tu edad: {edad}",
                       annotation_position="top right")
        fig2.add_vline(x=df_genero['edad'].mean(), line_dash="dash", line_color="green",
                       annotation_text=f"Promedio: {df_genero['edad'].mean():.1f}")
        st.plotly_chart(fig2, width='stretch')

    st.subheader("Tu perfil de salud vs grupos de tu mismo genero y edad similar")
    rango = 5
    df_similar = df[
        (df['genero'] == genero) &
        (df['edad'] >= edad - rango) &
        (df['edad'] <= edad + rango)
    ].copy()

    if len(df_similar) > 0:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Personas similares en dataset", f"{len(df_similar):,}")
        with col2:
            st.metric("IMC promedio de tu grupo", f"{df_similar['imc'].mean():.1f}")
        with col3:
            pct_mejor_salud = (df_similar['estado_salud_general'].isin(
                ['Excelente', 'Muy bueno']
            )).mean() * 100
            st.metric("Con salud muy buena o excelente", f"{pct_mejor_salud:.1f}%")

        fig3 = px.pie(
            df_similar['estado_salud_general'].value_counts().reset_index(),
            values='count',
            names='estado_salud_general',
            title=f"Estado de salud de personas similares a ti ({genero}, {edad-rango}-{edad+rango} años)",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        st.plotly_chart(fig3, width='stretch')

        fig4 = px.histogram(
            df_similar.dropna(subset=['imc']),
            x='imc',
            nbins=20,
            title=f"Distribucion IMC de tu grupo ({genero}, {edad-rango}-{edad+rango} años)",
            color_discrete_sequence=['#9B59B6'],
            opacity=0.7
        )
        fig4.add_vline(x=imc_usuario, line_dash="solid", line_color="red",
                       line_width=3, annotation_text=f"Tu IMC: {imc_usuario}")
        st.plotly_chart(fig4, width='stretch')
    else:
        st.warning("No hay suficientes datos de personas con caracteristicas similares en el dataset.")


def main():
    st.set_page_config(page_title="Dashboard - Prediccion Esperanza de Vida",
                       page_icon="📊",
                       layout="wide")

    st.title("Dashboard - Prediccion Esperanza de Vida")
    st.markdown("**Datos NHANES 2015-2016 y 2017-2018** | CDC/National Center for Health Statistics | Proyecto EV3 - SCY1101")

    with st.spinner("Cargando datos y entrenando modelo..."):
        df = cargar_datos()
        modelo, le_genero, le_salud = entrenar_modelo(df)

    st.success(f"Datos cargados: {len(df):,} registros | Modelo listo")

    vista = st.sidebar.radio(
        "Selecciona la audiencia",
        ["Ejecutiva", "Tecnica", "Operativa", "Personal"],
        captions=[
            "KPIs y resumen estrategico",
            "Analisis estadistico detallado",
            "Consulta individual y prediccion",
            "Analisis comparativo personalizado"
        ]
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Total registros:** {len(df):,}")
    st.sidebar.markdown(f"**Periodos:** 2015-2016 y 2017-2018")
    st.sidebar.markdown(f"**Fuente:** CDC/NHANES")
    st.sidebar.markdown(f"**Edad promedio:** {df['edad'].mean():.1f} años")
    st.sidebar.markdown(f"**IMC promedio:** {df['imc'].mean():.1f}")

    if vista == "Ejecutiva":
        vista_ejecutiva(df)
    elif vista == "Tecnica":
        vista_tecnica(df)
    elif vista == "Operativa":
        vista_operativa(df, modelo, le_genero, le_salud)
    elif vista == "Personal":
        vista_personal(df, modelo, le_genero, le_salud)


if __name__ == "__main__":
    main()
