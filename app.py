import re
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# ----------------------------------------------------------------------
# Configuración General y Paleta Pastel Profesional
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="Análisis de Homicidios en Argentina",
    page_icon="📊",
    layout="wide",
)

BASE_DIR = Path(__file__).parent / "data"
HECHOS_PATH = BASE_DIR / "homicidios_limpio.csv"
POBLACION_PATH = BASE_DIR / "censo_limpio.xlsx"

# Paleta de colores pastel profesional
COLOR_MUJER = "#F4D06F"          # Amarillo ámbar pastel
COLOR_HOMBRE = "#88D49E"         # Verde menta/salvia pastel
COLOR_FEMICIDIO_1 = "#957DAD"    # Violeta/Lavanda pastel profundo
COLOR_FEMICIDIO_2 = "#D291BC"    # Lila rosado pastel
COLOR_NEUTRO = "#A2C4E0"         # Azul cielo pastel
PALETA_PASTEL = ["#D291BC", "#957DAD", "#88D49E", "#F4D06F", "#A2C4E0", "#F7A072"]

COLORES_SEXO = {"Masculino": COLOR_HOMBRE, "Femenino": COLOR_MUJER}
SEXOS_VALIDOS = list(COLORES_SEXO)

COLORES_AMBITO = {
    "Domicilio particular": "#957DAD",
    "Fuera del domicilio": "#A2C4E0",
    "Sin determinar": "#E0E0E0",
}

COLS = {
    "anio": "anio",
    "mes": "mes",
    "hora": "hora_hecho",
    "provincia": "provincia_nombre",
    "departamento": "departamento_nombre",
    "localidad": "localidad_nombre",
    "sexo": "victima_sexo",
    "genero": "victima_identidad_genero",
    "edad_rango": "victima_tr_edad",
    "lugar_hecho": "tipo_lugar",
    "categoria_femicidio": "categoria_femicidio",
}
REQUIRED = ("anio", "provincia")
COLS_POB = {"provincia": "provincia_nombre", "poblacion": "poblacion"}

DQ_STATS = {
    "Víctimas múltiples rescatadas": "107",
    "Localidades con ID homónimo": "38",
    "Registros hora 11:11 (desconocida)": "7.352",
}

MESES_NOMBRES = {
    1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic",
}

OPC_AMBOS = "Ambos sexos"
OPC_MUJERES = "Solo mujeres víctimas"
OPC_HOMBRES = "Solo hombres víctimas"


# ----------------------------------------------------------------------
# Carga y Procesamiento de Datos (Cacheado)
# ----------------------------------------------------------------------
@st.cache_data(show_spinner="Cargando y procesando datos...")
def cargar_hechos(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";")
    faltantes = [COLS[k] for k in REQUIRED if COLS[k] not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas obligatorias en el CSV: {faltantes}")

    df = df.rename(columns={v: k for k, v in COLS.items() if v in df.columns})

    df["anio"] = pd.to_numeric(df["anio"], errors="coerce")
    df = df.dropna(subset=["anio", "provincia"]).copy()
    df["anio"] = df["anio"].astype(int)

    cols_texto = (
        "provincia", "departamento", "localidad", "sexo",
        "genero", "lugar_hecho", "categoria_femicidio", "edad_rango"
    )
    for col in cols_texto:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()

    # Clasificación Domicilio vs. Fuera del domicilio (Preguntas 4 y 8)
    if "lugar_hecho" in df.columns:
        condiciones_lugar = [
            df["lugar_hecho"] == "Domicilio particular",
            df["lugar_hecho"] == "Sin determinar",
        ]
        df["ambito_lugar"] = np.select(
            condiciones_lugar,
            ["Domicilio particular", "Sin determinar"],
            default="Fuera del domicilio",
        )

    # Procesamiento de hora y franja horaria (Pregunta 3)
    if "hora" in df.columns:
        es_11_11 = df["hora"].isin(["11:11:11", "11:11:00"])
        df["es_hora_desconocida"] = es_11_11
        horas_validas = df["hora"].where(~es_11_11, pd.NA)
        df["hora_num"] = pd.to_datetime(
            horas_validas, format="%H:%M:%S", errors="coerce"
        ).dt.hour
        df["franja_horaria"] = pd.cut(
            df["hora_num"],
            bins=[-1, 5, 11, 17, 23],
            labels=[
                "Madrugada (00-05 hs)",
                "Mañana (06-11 hs)",
                "Tarde (12-17 hs)",
                "Noche (18-23 hs)",
            ],
        )

    return df


@st.cache_data
def cargar_poblacion(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    pob = pd.read_excel(path)
    if not all(c in pob.columns for c in COLS_POB.values()):
        return None
    pob = pob.rename(columns={v: k for k, v in COLS_POB.items()})[
        ["provincia", "poblacion"]
    ]
    pob["provincia"] = pob["provincia"].astype("string").str.strip()
    pob["poblacion"] = pd.to_numeric(pob["poblacion"], errors="coerce")
    return pob.dropna()


@st.cache_data
def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def calcular_tasas(df: pd.DataFrame, pob: pd.DataFrame, n_anios: int) -> pd.DataFrame:
    conteo = (
        df.groupby("provincia", observed=True)
        .size()
        .rename("homicidios")
        .reset_index()
    )
    tasas = conteo.merge(pob, on="provincia", how="inner")
    tasas["tasa_acumulada"] = tasas["homicidios"] / tasas["poblacion"] * 100_000
    tasas["tasa_anual"] = tasas["tasa_acumulada"] / n_anios
    return tasas.sort_values("tasa_anual", ascending=False)


def clave_rango(r: str) -> int:
    m = re.search(r"\d+", str(r))
    return int(m.group()) if m else 10_000


def fmt(n: float) -> str:
    return f"{n:,.0f}".replace(",", ".")


# ----------------------------------------------------------------------
# Inicialización y Barra Lateral
# ----------------------------------------------------------------------
st.title("Análisis de Homicidios en Argentina (2017-2025)")
st.markdown(
    "Exploración analítica cruzando datos del Sistema de Alerta Temprana "
    "(Ministerio de Seguridad) con el Censo Nacional INDEC 2022."
)

try:
    df = cargar_hechos(HECHOS_PATH)
except FileNotFoundError:
    st.error(f"No se encontró el archivo de datos: `{HECHOS_PATH}`")
    st.stop()
except ValueError as e:
    st.error(str(e))
    st.stop()

poblacion = cargar_poblacion(POBLACION_PATH)
hay_sexo = "sexo" in df.columns

st.sidebar.title("Filtros")

anio_min, anio_max = int(df["anio"].min()), int(df["anio"].max())
rango = st.sidebar.slider("Años", anio_min, anio_max, (anio_min, anio_max))

provincias = sorted(df["provincia"].dropna().unique().tolist())
sel_prov = st.sidebar.multiselect("Provincias", provincias, placeholder="Todas")

tipo_victima = OPC_AMBOS
if hay_sexo:
    tipo_victima = st.sidebar.radio(
        "Sexo de la víctima", [OPC_AMBOS, OPC_MUJERES, OPC_HOMBRES]
    )

mask = df["anio"].between(*rango)
if sel_prov:
    mask &= df["provincia"].isin(sel_prov)
dff_base = df[mask]

dff = dff_base
if tipo_victima == OPC_MUJERES:
    dff = dff_base[dff_base["sexo"] == "Femenino"]
elif tipo_victima == OPC_HOMBRES:
    dff = dff_base[dff_base["sexo"] == "Masculino"]

if dff.empty:
    st.warning("No hay datos para los filtros seleccionados.")
    st.stop()

n_anios = rango[1] - rango[0] + 1

st.sidebar.download_button(
    "Descargar datos filtrados (CSV)",
    to_csv_bytes(dff),
    file_name="homicidios_filtrado.csv",
    mime="text/csv",
)

# --- KPIs Principales ------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Víctimas (Filtro Actual)", fmt(len(dff)))
c2.metric("Promedio anual", fmt(len(dff) / n_anios))
if hay_sexo:
    mujeres = int((dff_base["sexo"] == "Femenino").sum())
    c3.metric("Víctimas Mujeres (en selección)", fmt(mujeres))
if "categoria_femicidio" in dff_base.columns:
    fem_intimos = int(
        (dff_base["categoria_femicidio"] == "Femicidio íntimo según el vínculo").sum()
    )
    c4.metric("Femicidios Íntimos (en selección)", fmt(fem_intimos))

# --- Navegación Persistente (Evita reseteo al filtrar) ----------------
st.markdown("---")
secciones = [
    "Metodología y Calidad",
    "Riesgo Provincial y Temporal (P1 y P3)",
    "Demografía y Lugar (P2 y P4)",
    "Violencia de Género / Femicidios (P5 a P8)",
]

if "seccion_activa" not in st.session_state:
    st.session_state.seccion_activa = secciones[0]

st.sidebar.markdown("---")
st.sidebar.subheader("Navegación")
seccion = st.sidebar.radio("Ir a sección:", secciones, key="seccion_activa")

st.markdown(f"### {seccion}")

# =====================================================================
# SECCIÓN 1: Metodología y Calidad del Dato
# =====================================================================
if seccion == secciones[0]:
    st.header("Auditoría y Limpieza de Datos (ETL)")
    st.write(
        "Criterios metodológicos aplicados sobre el dataset original para garantizar "
        "la consistencia estadística:"
    )
    st.markdown(
        "- **Aislamiento de víctimas únicas:** El archivo crudo incluye tanto a víctimas como a imputados. Se filtraron las filas donde `victima_sexo != 'No corresponde'` y se preservó `tipo_persona_id` para no perder registros de homicidios múltiples[cite: 1].\n"
        "- **Desambiguación geográfica:** Se combinó `provincia_nombre + departamento_nombre + localidad_nombre` para evitar solapamientos por localidades homónimas[cite: 1].\n"
        "- **Depuración horaria (`11:11:11` y `11:11:00`):** Se identificaron 7.352 registros con valores por defecto para horas desconocidas. Se conservan para el volumen general pero se excluyen del análisis de franjas horarias para evitar sesgos en el período matutino[cite: 1]."
    )
    stats = {**DQ_STATS, "Total víctimas analizadas": fmt(len(df))}
    for col, (k, v) in zip(st.columns(len(stats)), stats.items()):
        col.metric(k, v)

# =====================================================================
# SECCIÓN 2: Pregunta 1 (Tasas y Focos) y Pregunta 3 (Meses y Horarios)
# =====================================================================
elif seccion == secciones[1]:
    st.header("1. ¿Cuáles son las tres provincias con mayor tasa de homicidios?")

    if poblacion is not None:
        tasas = calcular_tasas(dff, poblacion, n_anios)
        top3_prov = tasas.head(3)

        cols_top3 = st.columns(3)
        for i, (_, row) in enumerate(top3_prov.iterrows()):
            cols_top3[i].metric(
                label=f"Posición #{i+1}: {row['provincia']}",
                value=f"{row['tasa_anual']:.2f} c/100k (anual)",
                delta=f"Tasa acumulada: {row['tasa_acumulada']:.1f} | Casos: {fmt(row['homicidios'])}",
                delta_color="off",
            )

        fig_tasas = px.bar(
            tasas,
            x="provincia",
            y="tasa_anual",
            hover_data={
                "homicidios": True,
                "poblacion": ":,",
                "tasa_anual": ":.2f",
                "tasa_acumulada": ":.2f",
            },
            title="Tasa anual promedio cada 100.000 habitantes por provincia (ordenadas de mayor a menor)",
            labels={"tasa_anual": "Tasa anual x 100k", "provincia": "Provincia"},
            color_discrete_sequence=[COLOR_NEUTRO],
        )
        fig_tasas.update_layout(xaxis_tickangle=-45, xaxis={"categoryorder": "total descending"})
        st.plotly_chart(fig_tasas, use_container_width=True)

        st.subheader("1b. Localidades más críticas dentro de esas 3 provincias principales")
        prov_criticas = top3_prov["provincia"].tolist()
        df_loc_criticas = dff[
            (dff["provincia"].isin(prov_criticas))
            & (dff["localidad"] != "Localidad sin determinar")
        ]
        top_loc_3prov = (
            df_loc_criticas.groupby(
                ["provincia", "departamento", "localidad"], observed=True
            )
            .size()
            .reset_index(name="casos")
            .sort_values("casos", ascending=False)
            .head(10)
        )
        top_loc_3prov["etiqueta"] = (
            top_loc_3prov["localidad"]
            + " - Dpto. "
            + top_loc_3prov["departamento"]
            + " ("
            + top_loc_3prov["provincia"]
            + ")"
        )
        
        # Gráfico ordenado de mayor a menor con degradado lavanda/violeta elegante
        fig_focos = px.bar(
            top_loc_3prov,
            x="casos",
            y="etiqueta",
            orientation="h",
            text="casos",
            title=f"Top 10 localidades con mayor volumen de casos en {', '.join(prov_criticas)}",
            labels={"casos": "Cantidad de víctimas", "etiqueta": "Localidad"},
            color="casos",
            color_continuous_scale=["#D291BC", "#957DAD", "#685785"],
        )
        fig_focos.update_layout(
            yaxis={"categoryorder": "total ascending"},
            coloraxis_showscale=False
        )
        fig_focos.update_traces(textposition="outside")
        st.plotly_chart(fig_focos, use_container_width=True)
    else:
        st.warning("Revisá el archivo `censo_limpio.xlsx` para visualizar las tasas.")

    st.markdown("---")
    st.header("3. ¿Existen meses o rangos horarios donde los casos se disparan?")
    col_mes, col_hora = st.columns(2)

    with col_mes:
        if "mes" in dff.columns:
            por_mes = dff.groupby("mes", observed=True).size().reset_index(name="casos")
            por_mes["mes_nombre"] = por_mes["mes"].map(MESES_NOMBRES)
            fig_mes = px.bar(
                por_mes,
                x="mes_nombre",
                y="casos",
                text="casos",
                title="Evolución mensual de casos (Estacionalidad)",
                labels={"mes_nombre": "Mes", "casos": "Víctimas"},
                color_discrete_sequence=[COLOR_NEUTRO],
            )
            fig_mes.update_traces(textposition="outside")
            st.plotly_chart(fig_mes, use_container_width=True)

    with col_hora:
        if "franja_horaria" in dff.columns:
            excluidos_11 = int(dff["es_hora_desconocida"].sum())
            dff_hora = dff.dropna(subset=["franja_horaria"])

            por_franja = (
                dff_hora.groupby("franja_horaria", observed=False)
                .size()
                .reset_index(name="casos")
            )
            fig_hora = px.bar(
                por_franja,
                x="franja_horaria",
                y="casos",
                text="casos",
                title="Casos por franja horaria (con hora conocida)",
                labels={"franja_horaria": "Franja Horaria", "casos": "Víctimas"},
                color="franja_horaria",
                color_discrete_sequence=["#B5EAD7", "#FFDAC1", "#FFB7B2", "#C7CEEA"],
            )
            fig_hora.update_layout(showlegend=False, xaxis={"categoryorder": "total descending"})
            fig_hora.update_traces(textposition="outside")
            st.plotly_chart(fig_hora, use_container_width=True)

            st.caption(
                f"Nota metodológica: Se excluyeron {fmt(excluidos_11)} casos "
                f"con hora `11:11:11` y `11:11:00` (códigos por defecto) para evitar distorsiones[cite: 1]."
            )

            por_hora_exacta = (
                dff_hora.groupby("hora_num").size().reset_index(name="casos")
            )
            with st.expander("Ver detalle por hora exacta (00 a 23 hs)"):
                fig_curva_h = px.area(
                    por_hora_exacta,
                    x="hora_num",
                    y="casos",
                    markers=True,
                    labels={"hora_num": "Hora del día", "casos": "Víctimas"},
                    color_discrete_sequence=[COLOR_FEMICIDIO_1],
                )
                st.plotly_chart(fig_curva_h, use_container_width=True)

# =====================================================================
# SECCIÓN 3: Pregunta 2 (Demografía) y Pregunta 4 (Lugar Nacional)
# =====================================================================
elif seccion == secciones[2]:
    st.header("2. ¿Cuál es el grupo demográfico más vulnerable (sexo, género, edad)?")
    st.caption("Comparativa demográfica sobre el total seleccionado.")

    base_v = dff_base[dff_base["sexo"].isin(SEXOS_VALIDOS)]
    c_sexo, c_gen = st.columns(2)

    with c_sexo:
        por_sexo = base_v["sexo"].value_counts().reset_index(name="casos")
        fig_sexo = px.pie(
            por_sexo,
            names="sexo",
            values="casos",
            hole=0.45,
            title="Distribución por Sexo Biológico",
            color="sexo",
            color_discrete_map=COLORES_SEXO,
        )
        fig_sexo.update_traces(textinfo="percent+label")
        st.plotly_chart(fig_sexo, use_container_width=True)

    with c_gen:
        if "genero" in dff_base.columns:
            por_gen = (
                dff_base[dff_base["genero"] != "Sin determinar"]["genero"]
                .value_counts()
                .reset_index(name="casos")
            )
            fig_gen = px.bar(
                por_gen,
                x="genero",
                y="casos",
                text="casos",
                title="Víctimas por Identidad de Género (ordenadas de mayor a menor)",
                labels={"genero": "Identidad de Género", "casos": "Víctimas"},
                color="genero",
                color_discrete_map={
                    "Varón": COLOR_HOMBRE,
                    "Mujer": COLOR_MUJER,
                    "Mujer trans/travesti": COLOR_FEMICIDIO_1,
                    "Varón trans": COLOR_NEUTRO,
                },
            )
            fig_gen.update_layout(showlegend=False, xaxis={"categoryorder": "total descending"})
            fig_gen.update_traces(textposition="outside")
            st.plotly_chart(fig_gen, use_container_width=True)

    if "edad_rango" in base_v.columns:
        dff_edad = base_v[
            base_v["edad_rango"].str.lower() != "sin determinar"
        ].dropna(subset=["edad_rango"])
        orden = sorted(dff_edad["edad_rango"].unique(), key=clave_rango)
        por_edad = (
            dff_edad.groupby(["edad_rango", "sexo"], observed=True)
            .size()
            .reset_index(name="casos")
        )
        fig_edad = px.bar(
            por_edad,
            x="edad_rango",
            y="casos",
            color="sexo",
            barmode="group",
            title="Distribución por Rango Etario y Sexo",
            category_orders={"edad_rango": orden},
            color_discrete_map=COLORES_SEXO,
            labels={"edad_rango": "Rango de edad", "casos": "Víctimas", "sexo": "Sexo"},
        )
        st.plotly_chart(fig_edad, use_container_width=True)

    st.markdown("---")
    st.header("4. ¿Los hechos suceden en un domicilio particular o fuera del mismo?")
    
    st.info(
        "📌 **Hallazgo analítico clave:** Los datos demuestran una divergencia categórica según el sexo de la víctima. "
        "Las **mujeres** corren mayor peligro en el **domicilio particular** (el 59% de los casos registrados ocurren allí), "
        "mientras que los **varones** son predominantemente víctimas **fuera del domicilio** (68%, vinculados mayormente a espacios públicos o conflictos interpersonales externos)."
    )

    col_amb1, col_amb2 = st.columns(2)

    with col_amb1:
        df_mujeres = dff_base[dff_base["sexo"] == "Femenino"]
        por_ambito_m = df_mujeres["ambito_lugar"].value_counts().reset_index(name="casos")
        fig_amb_m = px.pie(
            por_ambito_m,
            names="ambito_lugar",
            values="casos",
            hole=0.45,
            title="Ámbito del hecho: Víctimas MUJERES",
            color="ambito_lugar",
            color_discrete_map=COLORES_AMBITO,
        )
        fig_amb_m.update_traces(textinfo="percent+label")
        st.plotly_chart(fig_amb_m, use_container_width=True)

    with col_amb2:
        df_varones = dff_base[dff_base["sexo"] == "Masculino"]
        por_ambito_v = df_varones["ambito_lugar"].value_counts().reset_index(name="casos")
        fig_amb_v = px.pie(
            por_ambito_v,
            names="ambito_lugar",
            values="casos",
            hole=0.45,
            title="Ámbito del hecho: Víctimas VARONES",
            color="ambito_lugar",
            color_discrete_map=COLORES_AMBITO,
        )
        fig_amb_v.update_traces(textinfo="percent+label")
        st.plotly_chart(fig_amb_v, use_container_width=True)

    por_lugar_det = (
        dff_base.groupby(["lugar_hecho", "sexo"], observed=True)
        .size()
        .reset_index(name="casos")
    )
    fig_lug_det = px.bar(
        por_lugar_det,
        x="casos",
        y="lugar_hecho",
        color="sexo",
        orientation="h",
        title="Desglose detallado por tipo de lugar y sexo de la víctima",
        labels={"lugar_hecho": "Lugar del hecho", "casos": "Víctimas", "sexo": "Sexo"},
        color_discrete_map=COLORES_SEXO,
    )
    fig_lug_det.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig_lug_det, use_container_width=True)

# =====================================================================
# SECCIÓN 4: Femicidios / Violencia de Género (Preguntas 5 a 8)
# =====================================================================
elif seccion == secciones[3]:
    st.header("Análisis de Femicidios (Preguntas 5 a 8)")
    st.markdown(
        "Clasificación exploratoria construida a partir de la identidad de género de la víctima "
        "(`Mujer` / `Mujer trans/travesti`) y su vínculo con el inculpado[cite: 1]."
    )

    criterio_fem = st.radio(
        "Seleccionar alcance metodológico:",
        [
            "Criterio Estricto: Femicidio íntimo según el vínculo (Pareja / Ex pareja)",
            "Criterio Ampliado: Femicidio íntimo + Posible femicidio familiar",
        ],
        horizontal=True,
    )

    if "Estricto" in criterio_fem:
        cats_fem = ["Femicidio íntimo según el vínculo"]
    else:
        cats_fem = ["Femicidio íntimo según el vínculo", "Posible femicidio familiar"]

    df_fem = dff_base[dff_base["categoria_femicidio"].isin(cats_fem)]

    if df_fem.empty:
        st.warning("No hay registros de femicidios para los filtros seleccionados.")
    else:
        col_f1, col_f2 = st.columns(2)

        # Pregunta 5: TOP 10 localidades con más femicidios
        with col_f1:
            st.subheader("5. TOP 10 localidades con más femicidios")
            top10_loc_fem = (
                df_fem[df_fem["localidad"] != "Localidad sin determinar"]
                .groupby(["provincia", "departamento", "localidad"], observed=True)
                .size()
                .reset_index(name="casos")
                .sort_values("casos", ascending=False)
                .head(10)
            )
            top10_loc_fem["etiqueta"] = (
                top10_loc_fem["localidad"] + " (" + top10_loc_fem["provincia"] + ")"
            )
            fig_f5 = px.bar(
                top10_loc_fem,
                x="casos",
                y="etiqueta",
                orientation="h",
                text="casos",
                title="10 localidades con mayor cantidad de casos (ordenadas)",
                labels={"casos": "Víctimas", "etiqueta": "Localidad"},
                color_discrete_sequence=[COLOR_FEMICIDIO_1],
            )
            fig_f5.update_layout(yaxis={"categoryorder": "total ascending"})
            fig_f5.update_traces(textposition="outside")
            st.plotly_chart(fig_f5, use_container_width=True)

        # Pregunta 6: TOP 5 provincias con más femicidios
        with col_f2:
            st.subheader("6. TOP 5 provincias con más femicidios")
            top5_prov_fem = (
                df_fem.groupby("provincia", observed=True)
                .size()
                .reset_index(name="casos")
                .sort_values("casos", ascending=False)
                .head(5)
            )
            fig_f6 = px.bar(
                top5_prov_fem,
                x="casos",
                y="provincia",
                orientation="h",
                text="casos",
                title="5 provincias con mayor volumen de casos (ordenadas)",
                labels={"casos": "Víctimas", "provincia": "Provincia"},
                color_discrete_sequence=[COLOR_FEMICIDIO_2],
            )
            fig_f6.update_layout(yaxis={"categoryorder": "total ascending"})
            fig_f6.update_traces(textposition="outside")
            st.plotly_chart(fig_f6, use_container_width=True)

        st.markdown("---")
        col_f3, col_f4 = st.columns(2)

        # Pregunta 7: Evolución de los femicidios por año
        with col_f3:
            st.subheader("7. Evolución anual de femicidios")
            evol_fem = (
                df_fem.groupby(["anio", "categoria_femicidio"], observed=True)
                .size()
                .reset_index(name="casos")
            )
            fig_f7 = px.line(
                evol_fem,
                x="anio",
                y="casos",
                color="categoria_femicidio",
                markers=True,
                title="Tendencia histórica por año (2017-2025)[cite: 1]",
                labels={
                    "anio": "Año",
                    "casos": "Víctimas",
                    "categoria_femicidio": "Tipología",
                },
                color_discrete_map={
                    "Femicidio íntimo según el vínculo": COLOR_FEMICIDIO_1,
                    "Posible femicidio familiar": COLOR_FEMICIDIO_2,
                },
            )
            fig_f7.update_traces(line=dict(width=3), marker=dict(size=8))
            fig_f7.update_layout(xaxis=dict(tickmode="linear"))
            st.plotly_chart(fig_f7, use_container_width=True)

        # Pregunta 8: Lugar de ocurrencia de los femicidios
        with col_f4:
            st.subheader("8. Lugar de ocurrencia (Domicilio vs. Fuera)")
            lugar_fem = df_fem["ambito_lugar"].value_counts().reset_index(name="casos")
            fig_f8 = px.pie(
                lugar_fem,
                names="ambito_lugar",
                values="casos",
                hole=0.45,
                title="Femicidios: Domicilio particular vs. Fuera del mismo",
                color="ambito_lugar",
                color_discrete_map={
                    "Domicilio particular": COLOR_FEMICIDIO_1,
                    "Fuera del domicilio": COLOR_MUJER,
                    "Sin determinar": "#E0E0E0",
                },
            )
            fig_f8.update_traces(textinfo="percent+label")
            st.plotly_chart(fig_f8, use_container_width=True)