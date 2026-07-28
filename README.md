# Análisis de homicidios en Argentina desde 2017 - 2024

En este proyecto se busca responder a las siguientes interrogantes:

1. ¿Cuáles son las tres provincias con mayor **tasa de homicidios** (riesgo poblacional)?
   * De esas provincias principales, ¿cuáles son las localidades más críticas en cuanto a **cantidad de casos** (volumen/focos de conflicto)?

#### A nivel nacional
  
2. Cuál es el grupo demográfico más vulnerable (sexo, género, edad)
3. ¿Existen meses o rangos horarios donde los casos se disparan?
4. ¿Los hechos suceden en el domicilio de la víctima o fuera del mismo?
5. ¿Cuál es el grupo demográfico más propenso a perpetuar el hecho delictivo (sexo, género, edad)?
6. ¿Cuál es el TOP 10 de localidades dónde sucede una mayor cantidad de femicidios?
7. ¿Cuál es el TOP 5 de las provincias con mayor cantidad de femicidios?
8. ¿Cuál es la tendencia o evolución de femicidios a lo largo del tiempo (por año)
9. ¿En qué lugar suceden los femicidios con mayor frecuencia (hogar, fuera del mismo)?

## ETL

Se extraen los datos de https://datos.gob.ar/ 

link: https://datos.gob.ar/dataset/seguridad-homicidios-dolosos-sistema-alerta-temprana-estadisticas-criminales-republica-argentina/archivo/seguridad_6.2

El proceso de ETL y limpieza inicial se realiza con Python.

### Tecnologías:
* **Python (Pandas):** Extracción, limpieza, normalización y estandarización de los datasets.
* **PostgreSQL:** Modelado relacional inicial, diagrama Entidad-Relación y auditoría de calidad de datos (*Data Quality*).
* **Power BI:** Creación del modelo de datos final y desarrollo de la visualización interactiva.

## Diagrama de Entidad-Relación (DER)
Previo al análisis con PostgreSQL se plantea el siguiente diagrama Entidad-Relación para poder estructurar los datos de la mejor manera posible:

![Diagrama de la base de datos](docs/diagrama_er.png)

## Estructura de Datos (Tablas)
Luego del proceso de ETL, se divide el dataset original en 4 archivos CSV normalizados para su ingesta en la base de datos:

- `provincia.csv`
- `localidad.csv`
- `hecho.csv`
- `involucrados.csv`

### Normalización de Datos (Melt)
Para alinear los datos exactamente con el Diagrama Entidad-Relación, se aplicó una transformación (Melt) sobre la tabla `involucrados`. Se separó a las víctimas y a los inculpados en filas individuales, agregando la columna `tipo_involucrado` y asignando un ID único autoincremental en preparación para SQL.

## Base de Datos y Análisis
El análisis de los datos y la resolución de las interrogantes se realizará utilizando **PostgreSQL**.
  
### Hallazgos de Data Quality y Decisión Arquitectónica
Durante la fase de modelado relacional en PostgreSQL, se auditaron los datos y se descubrieron fallas estructurales graves de origen en el dataset gubernamental:
* **Integridad Referencial Rota:** El campo `localidad_id` contenía homónimos (mismo ID para múltiples ciudades distintas), lo que generaba multiplicaciones erróneas al cruzar tablas.
* **Llaves Primarias Duplicadas:** Se detectaron múltiples registros con el mismo `id_hecho` pero con atributos contradictorios (ej. un mismo hecho con dos lugares diferentes).

**Solución aplicada:** 
Para no comprometer la veracidad de la información forzando una normalización que eliminaría casos reales, se decidió utilizar SQL exclusivamente para el análisis exploratorio inicial y detección de anomalías. El tablero final en Power BI fue desarrollado consumiendo directamente el dataset consolidado y limpiado previamente con Python (`homicidios_limpio.csv`), garantizando así el 100% de exactitud en las métricas.

## Integración de Datos Censales y Cálculo de Tasas

En esta etapa se incorporaron datos de población para normalizar las métricas y calcular el riesgo relativo:

* **Fuente de datos:** Se descargaron los datos oficiales de población del Censo 2022 (INDEC - Link: https://www.indec.gob.ar/indec/web/Nivel4-Tema-2-41-165).
* **Limpieza y Estandarización:** Se limpiaron los registros y se normalizaron los nombres de las provincias para asegurar un cruce exacto con la base de homicidios y preparar el modelo relacional para Power BI.
* **Cálculo de Tasa:** Se unieron los dataframes (`homicidios_limpio.csv` y `censo_limpio.xlsx`) para calcular la tasa de homicidios por cada 100.000 habitantes a nivel provincial.
* **Análisis Focalizado:** Se identificó el Top 3 de provincias con la mayor tasa de homicidios, estableciendo el punto de partida para un análisis más profundo a nivel de localidades.

## Estructura del Reporte (Power BI)
El tablero interactivo cuenta con una página de **Portada** y tres secciones principales:
1. **Contexto Geográfico:** Tasas provinciales, mapa de calor y localidades críticas.
2. **Perfil Demográfico y Temporal:** Análisis de víctimas, victimarios y evolución mensual.
3. **Femicidios:** Evolución histórica, distribución territorial y tipología del lugar del hecho.

### Cómo visualizar el proyecto
* Si querés interactuar con el reporte completo en Power BI Desktop, podés descargar el archivo fuente desde el siguiente enlace:
[Descargar Reporte en Power BI (.pbix)](analisis_homicidios_argentina.pbix)