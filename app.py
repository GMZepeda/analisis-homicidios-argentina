import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# ----------------------------------------------------------------------
# Configuración
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="Análisis de Homicidios en Argentina",
    page_icon="📊",
    layout="wide",
)

BASE_DIR = Path(__file__).parent / "data"
HECHOS_PATH = BASE_DIR / "homicidios_limpio.csv"
POBLACION_PATH = BASE_DIR / "censo_limpio.xlsx"

COLS = {
    "anio": "anio",
    "provincia": "provincia_nombre",
    "localidad": "localidad_nombre",
    "sexo": "victima_sexo",
    "edad_rango": "victima_tr_edad",
    "lugar_hecho": "tipo_lugar",
}
REQUIRED = ("anio", "provincia")

COLS_POB = {"provincia": "provincia_nombre", "poblacion": "poblacion"}

DQ_STATS = {
    "Registros con id_hecho duplicado": "124",
    "Localidades con ID homónimo": "38",
}

COLORES_SEXO = {"Masculino": "#3366CC", "Femenino": "#DC3912"}
SEXOS_VALIDOS = list(COLORES_SEXO)

OPC_AMBOS = "Ambos sexos"
OPC_MUJERES = "Solo mujeres víctimas"
OPC_HOMBRES = "Solo hombres víctimas"

# ----------------------------------------------------------------------
# Carga de datos (cacheada)
# ----------------------------------------------------------------------
@st.cache_data(show_spinner="Cargando datos...")
def cargar_hechos(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";")
    faltantes = [COLS[k] for k in REQUIRED if COLS[k] not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas obligatorias en el CSV: {faltantes}")

    df = df.rename(columns={v: k for k, v in COLS.items() if v in df.columns})

    df["anio"] = pd.to_numeric(df["anio"], errors="coerce")
    df = df.dropna(subset=["anio", "provincia"]).copy()
    df["anio"] = df["anio"].astype(int)

    for col in ("provincia", "localidad", "sexo", "lugar_hecho"):
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip().str.title()
            df[col] = df[col].astype("category")

    if "edad_rango" in df.columns:
        df["edad_rango"] = df["edad_rango"].astype("string").str.strip()

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
    pob["provincia"] = pob["provincia"].astype("string").str.strip().str.title()
    pob["provincia"] = pob["provincia"].str.replace("Rio Negro", "Río Negro", regex=False)
    pob["poblacion"] = pd.to_numeric(pob["poblacion"], errors="coerce")
    return pob.dropna()

@st.cache_data
def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")

def calcular_tasas(df: pd.DataFrame, pob: pd.DataFrame, n_anios: int) -> pd.DataFrame:
    conteo = df.groupby("provincia", observed=True).size().rename("homicidios").reset_index()
    conteo["provincia"] = conteo["provincia"].astype("string")
    tasas = conteo.merge(pob, on="provincia", how="inner")
    tasas["tasa"] = tasas["homicidios"] / n_anios / tasas["poblacion"] * 100_000
    return tasas.sort_values("tasa", ascending=False)

def clave_rango(r: str) -> int:
    m = re.search(r"\d+", str(r))
    return int(m.group()) if m else 10_000

def fmt(n: float) -> str:
    return f"{n:,.0f}".replace(",", ".")

# ----------------------------------------------------------------------
# App
# ----------------------------------------------------------------------
st.title("Análisis de Homicidios en Argentina (2017-2025)")
st.markdown(
    "Exploración interactiva cruzando datos del Sistema de Alerta Temprana "
    "(Min. Seguridad) con el Censo INDEC 2022."
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

# --- Filtros ---------------------------------------------------------
st.sidebar.title("Filtros")

anio_min, anio_max = int(df["anio"].min()), int(df["anio"].max())
if anio_min == anio_max:
    rango = (anio_min, anio_max)
    st.sidebar.caption(f"Año disponible: {anio_min}")
else:
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

# --- Métricas --------------------------------------------------------
c1, c2, c3 = st.columns(3)
c1.metric("Víctimas (Filtro Actual)", fmt(len(dff)))
c2.metric("Promedio anual", fmt(len(dff) / n_anios))
if hay_sexo:
    mujeres = int((dff_base["sexo"] == "Femenino").sum())
    c3.metric("Víctimas Mujeres (Histórico sin filtro)", fmt(mujeres))

tab1, tab2, tab3 = st.tabs(
    ["Contexto y Data Quality", "Contexto Geográfico y Temporal", "Perfil Demográfico y Tipología"]
)

# --- Tab 1 -----------------------------------------------------------
with tab1:
    st.header("Metodología y Resolución de Datos")
    st.write(
        "Durante el modelado relacional en PostgreSQL se auditaron los datos y se "
        "detectaron fallas estructurales en el dataset gubernamental:"
    )
    st.markdown(
        "- **Integridad referencial rota:** `localidad_id` contenía homónimos "
        "(mismo ID para ciudades distintas).\n"
        "- **Llaves primarias duplicadas:** múltiples registros con el mismo "
        "`id_hecho` y atributos contradictorios."
    )
    stats = {**DQ_STATS, "Registros finales tras limpieza": fmt(len(df))}
    for col, (k, v) in zip(st.columns(len(stats)), stats.items()):
        col.metric(k, v)

# --- Tab 2 -----------------------------------------------------------
with tab2:
    st.header("Evolución Histórica")
    
    tendencia = dff.groupby("anio", observed=True).size().reset_index(name="casos")
    
    if tipo_victima == OPC_MUJERES:
        color_linea = COLORES_SEXO["Femenino"]
    elif tipo_victima == OPC_HOMBRES:
        color_linea = COLORES_SEXO["Masculino"]
    else:
        color_linea = "#636EFA"

    fig_tendencia = px.line(
        tendencia,
        x="anio",
        y="casos",
        markers=True,
        title=f"Evolución anual de casos ({tipo_victima})",
        labels={"anio": "Año", "casos": "Cantidad de víctimas"},
    )
    fig_tendencia.update_traces(line_color=color_linea, marker_color=color_linea)
    fig_tendencia.update_layout(xaxis=dict(tickmode="linear"))
    fig_tendencia.update_yaxes(rangemode="normal")
    st.plotly_chart(fig_tendencia, use_container_width=True)

    st.markdown("---")
    st.header("Tasas Provinciales y Localidades Críticas")

    fig = None
    tasas = pd.DataFrame()
    if poblacion is None:
        st.info("Revisá el archivo del censo. Se muestran conteos absolutos temporales.")
        por_prov = (
            dff.groupby("provincia", observed=True).size().rename("homicidios")
            .reset_index().sort_values("homicidios", ascending=False)
        )
        fig = px.bar(por_prov, x="provincia", y="homicidios", title="Víctimas por provincia")
    else:
        tasas = calcular_tasas(dff, poblacion, n_anios)
        if tasas.empty:
            st.warning("Los nombres de provincia no coinciden con el archivo de población.")
        else:
            fig = px.bar(
                tasas,
                x="provincia",
                y="tasa",
                hover_data={"homicidios": True, "poblacion": ":,", "tasa": ":.2f"},
                title="Tasa anual promedio de víctimas cada 100.000 habitantes",
                labels={"tasa": "Tasa x 100k", "provincia": "Provincia"},
            )
            if tipo_victima != OPC_AMBOS:
                st.caption(
                    "Con filtro de sexo, la tasa divide por la población total de la provincia. "
                    "Sirve para ver impacto geográfico, pero no es una tasa específica por género."
                )
    if fig is not None:
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    if not tasas.empty:
        if sel_prov and len(sel_prov) == 1:
            prov_data = tasas.iloc[0]
            st.info(
                f"📍 **Foco en {prov_data['provincia']}:** Registra un total de **{prov_data['homicidios']}** víctimas "
                f"para los filtros aplicados, lo que representa una tasa anual promedio de **{prov_data['tasa']:.2f}** "
                f"cada 100.000 habitantes."
            )
        else:
            menor = tasas.nsmallest(1, "tasa").iloc[0]
            contexto = "a nivel nacional" if not sel_prov else "entre las seleccionadas"
            
            st.success(
                f"🏆 **Dato destacado:** La provincia con menor tasa anual promedio {contexto} es "
                f"**{menor['provincia']}**, con **{menor['tasa']:.2f}** víctimas cada 100.000 habitantes."
            )
            
            titulo = "Top 5 provincias con menor tasa (Más seguras)" if not sel_prov else "Ranking comparativo de tasas"
            top_n = 5 if not sel_prov else len(sel_prov)
            
            st.subheader(titulo)
            st.caption("Los homicidios miden un solo tipo de violencia; no equivalen a seguridad urbana en general.")
            st.dataframe(
                tasas.nsmallest(top_n, "tasa")[["provincia", "homicidios", "poblacion", "tasa"]]
                .round(2)
                .rename(columns={"tasa": "tasa x 100k"}),
                hide_index=True,
                use_container_width=True,
            )

    st.markdown("---")
    if "localidad" in dff.columns:
        top = (
            dff.groupby(["provincia", "localidad"], observed=True)
            .size().rename("homicidios").reset_index().nlargest(15, "homicidios")
        )
        top["lugar"] = top["localidad"].astype(str) + " (" + top["provincia"].astype(str) + ")"
        st.plotly_chart(
            px.bar(
                top.sort_values("homicidios"),
                x="homicidios",
                y="lugar",
                orientation="h",
                title="15 localidades con mayor volumen de casos (conteo absoluto)",
            ),
            use_container_width=True,
        )

# --- Tab 3 -----------------------------------------------------------
with tab3:
    st.header("Análisis Demográfico y Tipología del Lugar")
    st.caption("Esta pestaña compara ambos sexos, por lo que ignora el filtro de la barra lateral.")

    base_v = dff_base[dff_base["sexo"].isin(SEXOS_VALIDOS)] if hay_sexo else pd.DataFrame()

    if hay_sexo and "lugar_hecho" in dff_base.columns and not base_v.empty:
        st.markdown("### Hallazgo: tipología del lugar según el sexo de la víctima")

        por_lugar_sexo = (
            base_v.groupby(["lugar_hecho", "sexo"], observed=True)
            .size().reset_index(name="Cantidad")
        )
        total_por_sexo = por_lugar_sexo.groupby("sexo", observed=True)["Cantidad"].transform("sum")
        por_lugar_sexo["Porcentaje"] = (por_lugar_sexo["Cantidad"] / total_por_sexo * 100).round(1)

        mas_frecuente = (
            por_lugar_sexo.sort_values("Porcentaje", ascending=False)
            .groupby("sexo", observed=True).head(1)
        )
        frases = [
            f"**{r.sexo}**: {r.lugar_hecho} ({r.Porcentaje:.1f}%)"
            for r in mas_frecuente.itertuples()
        ]
        st.info("Lugar más frecuente del hecho según el sexo de la víctima: " + " · ".join(frases) + ".")

        top_lugares = (
            por_lugar_sexo.groupby("lugar_hecho", observed=True)["Cantidad"].sum().nlargest(4).index
        )
        datos_top = por_lugar_sexo[por_lugar_sexo["lugar_hecho"].isin(top_lugares)]

        fig_lugar = px.bar(
            datos_top,
            x="Porcentaje",
            y="lugar_hecho",
            color="sexo",
            barmode="group",
            orientation="h",
            text="Porcentaje",
            title="Lugar del hecho (% dentro de cada sexo, top 4 lugares)",
            labels={
                "lugar_hecho": "Lugar del suceso",
                "Porcentaje": "% de víctimas dentro de su sexo",
                "sexo": "Sexo",
            },
            color_discrete_map=COLORES_SEXO,
        )
        fig_lugar.update_layout(
            yaxis={"categoryorder": "total ascending"},
            xaxis_ticksuffix="%",
        )
        fig_lugar.update_traces(
            texttemplate="%{text}%",
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>%{fullData.name}: %{x}%<extra></extra>",
        )
        st.plotly_chart(fig_lugar, use_container_width=True)

    st.markdown("---")
    left, right = st.columns(2)

    if hay_sexo:
        if not base_v.empty:
            por_sexo = base_v["sexo"].value_counts().rename_axis("sexo").reset_index(name="n")
            left.plotly_chart(
                px.pie(
                    por_sexo, names="sexo", values="n",
                    title="Distribución total por sexo", hole=0.4,
                    color="sexo", color_discrete_map=COLORES_SEXO,
                ),
                use_container_width=True,
            )
        else:
            left.info("No hay datos de sexo disponibles.")

    if "edad_rango" in dff_base.columns:
        base_e = base_v if hay_sexo else dff_base
        dff_edad = base_e[base_e["edad_rango"].str.lower() != "sin determinar"].dropna(
            subset=["edad_rango"]
        )
        if not dff_edad.empty:
            orden = sorted(dff_edad["edad_rango"].unique(), key=clave_rango)
            grupo = ["edad_rango", "sexo"] if hay_sexo else ["edad_rango"]
            por_edad = dff_edad.groupby(grupo, observed=True).size().reset_index(name="n")
            right.plotly_chart(
                px.bar(
                    por_edad,
                    x="edad_rango",
                    y="n",
                    color="sexo" if hay_sexo else None,
                    title="Distribución por rango etario",
                    category_orders={"edad_rango": orden},
                    color_discrete_map=COLORES_SEXO,
                ),
                use_container_width=True,
            )
        else:
            right.info("No hay datos de edad disponibles.")