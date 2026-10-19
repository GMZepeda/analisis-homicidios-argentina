import re
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# ----------------------------------------------------------------------
# Configuración general
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="Análisis de Homicidios en Argentina",
    page_icon="📊",
    layout="wide",
)

BASE_DIR = Path(__file__).parent / "data"
HECHOS_PATH = BASE_DIR / "homicidios_limpio.csv"
POBLACION_PATH = BASE_DIR / "censo_limpio.xlsx"

# ----------------------------------------------------------------------
# Paleta: celeste pastel (general) + violeta pastel (violencia de género)
# ----------------------------------------------------------------------
AZUL = "#A8CDE8"          # celeste pastel base
AZUL_FUERTE = "#6FA3CB"   # celeste más profundo (énfasis / segunda categoría)
AZUL_SUAVE = "#D3E6F4"    # celeste muy claro
VIOLETA = "#B9A3D6"       # violeta pastel base (simbología)
VIOLETA_FUERTE = "#9279BE"
VIOLETA_SUAVE = "#DDD2EE"
GRIS = "#E4E7EB"
TEXTO = "#3A4756"
TEXTO_SUAVE = "#7A8795"

COLORES_SEXO = {"Masculino": AZUL, "Femenino": AZUL_FUERTE}
SEXOS_VALIDOS = list(COLORES_SEXO)

COLORES_AMBITO_AZUL = {
    "Domicilio particular": AZUL_FUERTE,
    "Fuera del domicilio": AZUL_SUAVE,
    "Sin determinar": GRIS,
}
COLORES_AMBITO_VIOLETA = {
    "Domicilio particular": VIOLETA_FUERTE,
    "Fuera del domicilio": VIOLETA_SUAVE,
    "Sin determinar": GRIS,
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
# Estilos (CSS) y helper de gráficos
# ----------------------------------------------------------------------
st.markdown(
    f"""
    <style>
    .block-container {{ padding-top: 2rem; max-width: 1250px; }}
    h1, h2, h3 {{ color: {TEXTO}; font-weight: 600; letter-spacing: -0.01em; }}
    [data-testid="stMetric"] {{
        background: #F6FAFD; border: 1px solid {AZUL_SUAVE};
        border-radius: 14px; padding: 14px 18px;
    }}
    [data-testid="stMetricLabel"] p {{ color: {TEXTO_SUAVE}; font-size: 0.85rem; }}
    [data-testid="stMetricValue"] {{ color: {TEXTO}; font-weight: 600; }}
    .rank-card {{
        background: linear-gradient(160deg, #F6FAFD 0%, {AZUL_SUAVE} 100%);
        border: 1px solid {AZUL_SUAVE}; border-radius: 18px;
        padding: 20px 22px; height: 100%;
    }}
    .rank-pos {{
        display: inline-block; width: 30px; height: 30px; line-height: 30px;
        text-align: center; border-radius: 50%; background: {AZUL};
        color: white; font-weight: 600; font-size: 0.9rem;
    }}
    .rank-prov {{ color: {TEXTO}; font-size: 1.15rem; font-weight: 600; margin-left: 10px; }}
    .rank-rate {{ color: {AZUL_FUERTE}; font-size: 2.2rem; font-weight: 700; margin: 10px 0 0 0; line-height: 1.1; }}
    .rank-unit {{ color: {TEXTO_SUAVE}; font-size: 0.8rem; margin-bottom: 8px; }}
    .rank-meta {{ color: {TEXTO_SUAVE}; font-size: 0.82rem; border-top: 1px solid rgba(111,163,203,0.25); padding-top: 8px; }}
    .hallazgo {{
        background: #F6FAFD; border-left: 4px solid {AZUL};
        border-radius: 8px; padding: 14px 18px; color: {TEXTO}; margin-bottom: 1rem;
    }}
    .hallazgo-v {{ background: #F8F5FC; border-left-color: {VIOLETA}; }}
    </style>
    """,
    unsafe_allow_html=True,
)


def estilizar(fig, altura=380, leyenda=True):
    """Aplica un estilo limpio y consistente a todos los gráficos."""
    fig.update_layout(
        template="plotly_white",
        height=altura,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", color=TEXTO, size=13),
        title=dict(font=dict(size=15, color=TEXTO), x=0, xanchor="left"),
        margin=dict(l=10, r=10, t=55, b=10),
        showlegend=leyenda,
        legend=dict(title_text="", orientation="h", y=-0.2, x=0),
        bargap=0.35,
    )
    fig.update_xaxes(showgrid=False, linecolor="#E4E7EB", title_font=dict(size=12, color=TEXTO_SUAVE))
    fig.update_yaxes(gridcolor="#EEF1F4", zeroline=False, title_font=dict(size=12, color=TEXTO_SUAVE))
    return fig


def mostrar(fig, **kwargs):
    st.plotly_chart(estilizar(fig, **kwargs), use_container_width=True, config={"displayModeBar": False})


def marcar_maximo(df: pd.DataFrame, col: str, color_base: str, color_max: str):
    """Devuelve lista de colores: resalta el valor máximo."""
    mx = df[col].max()
    return [color_max if v == mx else color_base for v in df[col]]


# ----------------------------------------------------------------------
# Carga y procesamiento de datos (cacheado)
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
        "genero", "lugar_hecho", "categoria_femicidio", "edad_rango",
    )
    for col in cols_texto:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()

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


def pct(parte: int, total: int) -> str:
    return f"{parte / total * 100:.0f}%" if total else "s/d"


# ----------------------------------------------------------------------
# Encabezado y barra lateral
# ----------------------------------------------------------------------
st.title("Análisis de Homicidios en Argentina (2017-2025)")
st.caption(
    "Datos del Sistema de Alerta Temprana (Ministerio de Seguridad) "
    "cruzados con el Censo Nacional INDEC 2022."
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

# --- KPIs ---------------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Víctimas (filtro actual)", fmt(len(dff)))
c2.metric("Promedio anual", fmt(len(dff) / n_anios))
if hay_sexo:
    c3.metric("Víctimas mujeres", fmt(int((dff_base["sexo"] == "Femenino").sum())))
if "categoria_femicidio" in dff_base.columns:
    c4.metric(
        "Femicidios íntimos",
        fmt(int((dff_base["categoria_femicidio"] == "Femicidio íntimo según el vínculo").sum())),
    )

# --- Navegación persistente --------------------------------------------
st.markdown("---")
secciones = [
    "Metodología y calidad",
    "Riesgo provincial y temporal",
    "Demografía y lugar",
    "Violencia de género / Femicidios",
]

if "seccion_activa" not in st.session_state:
    st.session_state.seccion_activa = secciones[0]

st.sidebar.markdown("---")
st.sidebar.subheader("Navegación")
seccion = st.sidebar.radio("Ir a sección:", secciones, key="seccion_activa")

# =====================================================================
# SECCIÓN 1: Metodología y calidad del dato
# =====================================================================
if seccion == secciones[0]:
    st.header("Metodología y calidad del dato")
    st.write("Criterios aplicados sobre el dataset original para garantizar consistencia estadística:")
    st.markdown(
        "- **Víctimas únicas:** el archivo crudo incluye víctimas e imputados. Se filtraron las filas "
        "con `victima_sexo != 'No corresponde'` y se preservó `tipo_persona_id` para no perder homicidios múltiples.\n"
        "- **Desambiguación geográfica:** se combinó provincia + departamento + localidad para evitar "
        "solapamientos entre localidades homónimas.\n"
        "- **Depuración horaria (`11:11:11` y `11:11:00`):** 7.352 registros con valores por defecto "
        "para hora desconocida. Se conservan en el volumen general pero se excluyen del análisis de franjas horarias."
    )
    stats = {**DQ_STATS, "Total víctimas analizadas": fmt(len(df))}
    for col, (k, v) in zip(st.columns(len(stats)), stats.items()):
        col.metric(k, v)

# =====================================================================
# SECCIÓN 2: P1 (tasas y focos) y P3 (meses y horarios)
# =====================================================================
elif seccion == secciones[1]:
    st.header("Provincias con mayor tasa de homicidios")
    st.caption("Riesgo poblacional: víctimas cada 100.000 habitantes, promedio anual del período seleccionado.")

    if poblacion is not None:
        tasas = calcular_tasas(dff, poblacion, n_anios)
        top3_prov = tasas.head(3)

        cols_top3 = st.columns(3)
        for i, (_, row) in enumerate(top3_prov.iterrows()):
            cols_top3[i].markdown(
                f'<div class="rank-card">'
                f'<span class="rank-pos">{i + 1}</span>'
                f'<span class="rank-prov">{row["provincia"]}</span>'
                f'<div class="rank-rate">{row["tasa_anual"]:.2f}</div>'
                f'<div class="rank-unit">víctimas cada 100 mil hab. por año</div>'
                f'<div class="rank-meta">{fmt(row["homicidios"])} casos · tasa acumulada {row["tasa_acumulada"]:.1f}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )

        st.write("")
        top3_nombres = top3_prov["provincia"].tolist()
        tasas_graf = tasas.copy()
        tasas_graf["color"] = np.where(tasas_graf["provincia"].isin(top3_nombres), "Top 3", "Resto")
        fig_tasas = px.bar(
            tasas_graf,
            x="provincia",
            y="tasa_anual",
            color="color",
            color_discrete_map={"Top 3": AZUL_FUERTE, "Resto": AZUL_SUAVE},
            hover_data={"homicidios": True, "poblacion": ":,", "tasa_anual": ":.2f", "color": False},
            title="Tasa anual promedio por provincia (cada 100.000 habitantes)",
            labels={"tasa_anual": "Tasa anual x 100k", "provincia": ""},
        )
        fig_tasas.update_layout(xaxis_tickangle=-45, xaxis={"categoryorder": "total descending"})
        mostrar(fig_tasas, altura=420, leyenda=False)

        st.subheader("Localidades más críticas dentro de las 3 provincias principales")
        st.caption("Volumen de casos (focos de conflicto), no tasa.")
        df_loc = dff[
            dff["provincia"].isin(top3_nombres) & (dff["localidad"] != "Localidad sin determinar")
        ]
        top_loc = (
            df_loc.groupby(["provincia", "departamento", "localidad"], observed=True)
            .size()
            .reset_index(name="casos")
            .sort_values("casos", ascending=False)
            .head(10)
        )
        top_loc["etiqueta"] = top_loc["localidad"] + " · " + top_loc["provincia"]
        fig_focos = px.bar(
            top_loc,
            x="casos",
            y="etiqueta",
            orientation="h",
            text="casos",
            title="Top 10 localidades por cantidad de víctimas",
            labels={"casos": "Víctimas", "etiqueta": ""},
            color_discrete_sequence=[AZUL],
        )
        fig_focos.update_layout(yaxis={"categoryorder": "total ascending"})
        fig_focos.update_traces(textposition="outside", cliponaxis=False)
        mostrar(fig_focos, altura=420, leyenda=False)
    else:
        st.warning("Revisá el archivo `censo_limpio.xlsx` para visualizar las tasas.")

    st.markdown("---")
    st.header("Meses y rangos horarios con más casos")
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
                title="Casos por mes (el más alto resaltado)",
                labels={"mes_nombre": "", "casos": "Víctimas"},
            )
            fig_mes.update_traces(
                marker_color=marcar_maximo(por_mes, "casos", AZUL_SUAVE, AZUL_FUERTE),
                textposition="outside",
                cliponaxis=False,
            )
            mostrar(fig_mes, leyenda=False)

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
                title="Casos por franja horaria (la más alta resaltada)",
                labels={"franja_horaria": "", "casos": "Víctimas"},
            )
            fig_hora.update_traces(
                marker_color=marcar_maximo(por_franja, "casos", AZUL_SUAVE, AZUL_FUERTE),
                textposition="outside",
                cliponaxis=False,
            )
            mostrar(fig_hora, leyenda=False)

            st.caption(
                f"Se excluyeron {fmt(excluidos_11)} casos con hora `11:11:11` / `11:11:00` "
                "(códigos por defecto) para evitar distorsiones."
            )

            por_hora_exacta = dff_hora.groupby("hora_num").size().reset_index(name="casos")
            with st.expander("Ver detalle por hora exacta (00 a 23 hs)"):
                fig_curva_h = px.area(
                    por_hora_exacta,
                    x="hora_num",
                    y="casos",
                    labels={"hora_num": "Hora del día", "casos": "Víctimas"},
                    color_discrete_sequence=[AZUL],
                )
                fig_curva_h.update_traces(line=dict(color=AZUL_FUERTE, width=2))
                fig_curva_h.update_xaxes(dtick=2)
                mostrar(fig_curva_h, altura=300, leyenda=False)

# =====================================================================
# SECCIÓN 3: P2 (demografía) y P4 (lugar)
# =====================================================================
elif seccion == secciones[2]:
    st.header("Grupo demográfico más vulnerable")
    st.caption("Sexo, identidad de género y edad sobre el total seleccionado.")

    base_v = dff_base[dff_base["sexo"].isin(SEXOS_VALIDOS)]
    c_sexo, c_gen = st.columns(2)

    with c_sexo:
        por_sexo = base_v["sexo"].value_counts().reset_index(name="casos")
        fig_sexo = px.pie(
            por_sexo,
            names="sexo",
            values="casos",
            hole=0.55,
            title="Distribución por sexo",
            color="sexo",
            color_discrete_map=COLORES_SEXO,
        )
        fig_sexo.update_traces(textinfo="percent+label", marker=dict(line=dict(color="white", width=2)))
        mostrar(fig_sexo, leyenda=False)

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
                title="Víctimas por identidad de género",
                labels={"genero": "", "casos": "Víctimas"},
                color_discrete_sequence=[AZUL],
            )
            fig_gen.update_layout(xaxis={"categoryorder": "total descending"})
            fig_gen.update_traces(textposition="outside", cliponaxis=False)
            mostrar(fig_gen, leyenda=False)

    if "edad_rango" in base_v.columns:
        dff_edad = base_v[base_v["edad_rango"].str.lower() != "sin determinar"].dropna(subset=["edad_rango"])
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
            title="Distribución por rango etario y sexo",
            category_orders={"edad_rango": orden},
            color_discrete_map=COLORES_SEXO,
            labels={"edad_rango": "Rango de edad", "casos": "Víctimas", "sexo": ""},
        )
        mostrar(fig_edad, altura=400)

    st.markdown("---")
    st.header("¿Domicilio particular o fuera del domicilio?")

    df_mujeres = dff_base[dff_base["sexo"] == "Femenino"]
    df_varones = dff_base[dff_base["sexo"] == "Masculino"]
    pm = pct((df_mujeres["ambito_lugar"] == "Domicilio particular").sum(), len(df_mujeres))
    pv = pct((df_varones["ambito_lugar"] == "Fuera del domicilio").sum(), len(df_varones))
    st.markdown(
        f'<div class="hallazgo"><b>Hallazgo:</b> el {pm} de las víctimas mujeres fue atacada en un domicilio '
        f"particular, mientras que el {pv} de las víctimas varones lo fue fuera del domicilio.</div>",
        unsafe_allow_html=True,
    )

    col_amb1, col_amb2 = st.columns(2)
    for col, data, titulo in (
        (col_amb1, df_mujeres, "Ámbito del hecho · víctimas mujeres"),
        (col_amb2, df_varones, "Ámbito del hecho · víctimas varones"),
    ):
        with col:
            por_ambito = data["ambito_lugar"].value_counts().reset_index(name="casos")
            fig_amb = px.pie(
                por_ambito,
                names="ambito_lugar",
                values="casos",
                hole=0.55,
                title=titulo,
                color="ambito_lugar",
                color_discrete_map=COLORES_AMBITO_AZUL,
            )
            fig_amb.update_traces(textinfo="percent+label", marker=dict(line=dict(color="white", width=2)))
            mostrar(fig_amb, leyenda=False)

    with st.expander("Ver desglose detallado por tipo de lugar"):
        det = dff_base[dff_base["sexo"].isin(SEXOS_VALIDOS)]
        por_lugar_det = (
            det.groupby(["lugar_hecho", "sexo"], observed=True)
            .size()
            .reset_index(name="casos")
        )
        por_lugar_det["porcentaje"] = (
            por_lugar_det["casos"]
            / por_lugar_det.groupby("sexo")["casos"].transform("sum")
            * 100
        )
        fig_lug_det = px.bar(
            por_lugar_det,
            x="porcentaje",
            y="lugar_hecho",
            color="sexo",
            barmode="group",
            orientation="h",
            text=por_lugar_det["porcentaje"].round(0).astype(int).astype(str) + "%",
            title="Dónde ocurren los hechos (% de las víctimas de cada sexo)",
            labels={"lugar_hecho": "Lugar", "porcentaje": "% de víctimas", "sexo": ""},
            color_discrete_map=COLORES_SEXO,
            hover_data={"casos": True, "porcentaje": ":.1f"},
        )
        fig_lug_det.update_layout(yaxis={"categoryorder": "total ascending"})
        fig_lug_det.update_traces(textposition="outside", cliponaxis=False)
        mostrar(fig_lug_det, altura=500)

# =====================================================================
# SECCIÓN 4: Femicidios (P5 a P8) — paleta violeta
# =====================================================================
elif seccion == secciones[3]:
    st.header("Femicidios")
    st.caption(
        "Clasificación exploratoria a partir de la identidad de género de la víctima "
        "(Mujer / Mujer trans/travesti) y su vínculo con el inculpado."
    )

    criterio_fem = st.radio(
        "Alcance metodológico:",
        [
            "Criterio estricto: femicidio íntimo (pareja / ex pareja)",
            "Criterio ampliado: femicidio íntimo + posible femicidio familiar",
        ],
        horizontal=True,
    )

    if "estricto" in criterio_fem:
        cats_fem = ["Femicidio íntimo según el vínculo"]
    else:
        cats_fem = ["Femicidio íntimo según el vínculo", "Posible femicidio familiar"]

    df_fem = dff_base[dff_base["categoria_femicidio"].isin(cats_fem)]

    if df_fem.empty:
        st.warning("No hay registros de femicidios para los filtros seleccionados.")
    else:
        col_f1, col_f2 = st.columns(2)

        with col_f1:
            st.subheader("Top 10 localidades")
            top10_loc_fem = (
                df_fem[df_fem["localidad"] != "Localidad sin determinar"]
                .groupby(["provincia", "departamento", "localidad"], observed=True)
                .size()
                .reset_index(name="casos")
                .sort_values("casos", ascending=False)
                .head(10)
            )
            top10_loc_fem["etiqueta"] = top10_loc_fem["localidad"] + " · " + top10_loc_fem["provincia"]
            fig_f5 = px.bar(
                top10_loc_fem,
                x="casos",
                y="etiqueta",
                orientation="h",
                text="casos",
                title="Localidades con más femicidios",
                labels={"casos": "Víctimas", "etiqueta": ""},
                color_discrete_sequence=[VIOLETA],
            )
            fig_f5.update_layout(yaxis={"categoryorder": "total ascending"})
            fig_f5.update_traces(textposition="outside", cliponaxis=False)
            mostrar(fig_f5, altura=420, leyenda=False)

        with col_f2:
            st.subheader("Top 5 provincias")
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
                title="Provincias con más femicidios",
                labels={"casos": "Víctimas", "provincia": ""},
                color_discrete_sequence=[VIOLETA],
            )
            fig_f6.update_layout(yaxis={"categoryorder": "total ascending"})
            fig_f6.update_traces(textposition="outside", cliponaxis=False)
            mostrar(fig_f6, altura=420, leyenda=False)

        st.markdown("---")
        col_f3, col_f4 = st.columns(2)

        with col_f3:
            st.subheader("Evolución anual")
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
                title="Femicidios por año",
                labels={"anio": "", "casos": "Víctimas", "categoria_femicidio": ""},
                color_discrete_map={
                    "Femicidio íntimo según el vínculo": VIOLETA_FUERTE,
                    "Posible femicidio familiar": VIOLETA,
                },
            )
            fig_f7.update_traces(line=dict(width=3), marker=dict(size=8))
            fig_f7.update_xaxes(tickmode="linear", dtick=1)
            mostrar(fig_f7, altura=380)

        with col_f4:
            st.subheader("Lugar de ocurrencia")
            lugar_fem = df_fem["ambito_lugar"].value_counts().reset_index(name="casos")
            fig_f8 = px.pie(
                lugar_fem,
                names="ambito_lugar",
                values="casos",
                hole=0.55,
                title="Domicilio particular vs. fuera del domicilio",
                color="ambito_lugar",
                color_discrete_map=COLORES_AMBITO_VIOLETA,
            )
            fig_f8.update_traces(textinfo="percent+label", marker=dict(line=dict(color="white", width=2)))
            mostrar(fig_f8, altura=380, leyenda=False)