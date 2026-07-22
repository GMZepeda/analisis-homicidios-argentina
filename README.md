# Análisis de homicidios en Argentina desde 2017 - 2023

En este proyecto se busca responder a las siguientes interrogantes:

1. ¿Cuáles son las tres provincias con mayor índice de homicidios?
   
    a) De esas provincias, ¿cuál es la localidad más crítica?
  
3. Cuál es el grupo demográfico más vulnerable (sexo, género, edad)
4. ¿Existen meses o rangos horarios donde los casos se disparan?
5. ¿Los hechos suceden en el domicilio de la víctima o fuera del mismo?
6. ¿Cuál es el grupo demográfico más propenso a perpetuar el hecho delictivo (sexo, género, edad)?
   
   a) ¿Cuál es la principal motivación del homicidio?

## ETL

Se extraen los datos de https://datos.gob.ar/ 

link: https://datos.gob.ar/dataset/seguridad-homicidios-dolosos-sistema-alerta-temprana-estadisticas-criminales-republica-argentina/archivo/seguridad_6.2

El proceso de ETL y limpieza inicial se realiza con Python.

### Tecnologías:
- Pandas

## Diagrama de Entidad-Relación (DER)
Previo al análisis con PostgreSQL se plantea el siguiente diagrama Entidad-Relación para poder estructurar los datos de la mejor manera posible:

![Diagrama de la base de datos](docs/diagrama_er.png)

  
