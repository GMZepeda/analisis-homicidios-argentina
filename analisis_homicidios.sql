-- Tras un primer análisis, se decide excluir la data corrupta de 'Barrancas' y 'Las Ovejas'
-- por presentar volúmenes totalmente inconsistentes con los censos nacionales.

-- 1. ¿Cuáles son las 3 provincias con mayor cantidad de homicidios?

SELECT 
    p.provincia_nombre, 
    COUNT(h.hecho_id) AS cantidad_homicidios
FROM hecho h
JOIN localidad l ON h.localidad_id = l.localidad_id
JOIN provincia p ON l.provincia_id = p.provincia_id
WHERE l.localidad_nombre NOT IN ('Barrancas', 'Las Ovejas') -- Excluimos la data corrupta
GROUP BY p.provincia_nombre
ORDER BY cantidad_homicidios DESC
LIMIT 3;

-- a) De esas provincias, ¿cuál es su localidad más crítica?

-- creamos una tabla temporal para organizar y clasificar los datos
--- solo extramos la que quedó en el puesto 1.

WITH Ranking AS (
    SELECT 
        p.provincia_nombre, 
        l.localidad_nombre, 
        COUNT(h.hecho_id) AS cantidad_homicidios,
        ROW_NUMBER() OVER(PARTITION BY p.provincia_nombre ORDER BY COUNT(h.hecho_id) DESC) as fila
    FROM hecho h
    JOIN localidad l ON h.localidad_id = l.localidad_id
    JOIN provincia p ON l.provincia_id = p.provincia_id
    WHERE p.provincia_nombre IN ('Neuquén', 'Santa Fe', 'Salta')
      AND l.localidad_nombre NOT IN ('Barrancas', 'Las Ovejas') -- Acá excluimos los datos erróneos
    GROUP BY p.provincia_nombre, l.localidad_nombre
)
SELECT provincia_nombre, localidad_nombre, cantidad_homicidios
FROM Ranking
WHERE fila = 1
ORDER BY cantidad_homicidios DESC;
/* 
Se excluye Barrancas del análisis porque la cantidad 
de casos registrados (7991) supera ampliamente 
a su población real (1146 habitantes según Censo 2010).
Se procede también a expluir "Las Ovejas" por similitud con "Barracas"
*/

-- A nivel nacional
-- 2 Cuál es el grupo demográfico más vulnerable (sexo, género, edad)

SELECT 
    i.sexo, 
    i.identidad_genero, 
    i.tr_edad, 
    COUNT(i.involucrados_id) AS cantidad_victimas
FROM involucrados i
JOIN hecho h ON i.hecho_id = h.hecho_id
JOIN localidad l ON h.localidad_id = l.localidad_id
WHERE i.tipo_involucrado ILIKE '%victima%' 
  AND i.sexo NOT ILIKE '%No corresponde%'
  AND i.tr_edad NOT ILIKE '%Sin determinar%'
  AND i.identidad_genero NOT ILIKE '%Sin determinar%' 
  AND i.identidad_genero NOT ILIKE '%No corresponde%' 
  AND l.localidad_nombre NOT IN ('Barrancas', 'Las Ovejas') -- Excluimos la data corrupta
GROUP BY i.sexo, i.identidad_genero, i.tr_edad
ORDER BY cantidad_victimas DESC
LIMIT 1;

-- 3. ¿Existen meses o rangos horarios donde los casos se disparan?

-- meses con más casos

SELECT 
    h.mes, 
    COUNT(h.hecho_id) AS cantidad_casos
FROM hecho h
JOIN localidad l ON h.localidad_id = l.localidad_id
WHERE h.mes IS NOT NULL
  AND l.localidad_nombre NOT IN ('Barrancas', 'Las Ovejas') -- Excluimos la data corrupta
GROUP BY h.mes
ORDER BY cantidad_casos DESC
LIMIT 3;

-- horarios más críticos 
-- Excluímos "11:11:11", "11:11:00" y "00:00:00"
-- Parecen ser valores por defecto (placeholders)


SELECT 
    h.hora_hecho, 
    COUNT(h.hecho_id) AS cantidad_casos
FROM hecho h
JOIN localidad l ON h.localidad_id = l.localidad_id
WHERE h.hora_hecho NOT ILIKE '%Sin determinar%' 
  AND h.hora_hecho NOT ILIKE '%No corresponde%'
  AND h.hora_hecho NOT IN ('11:11:11', '11:11:00', '00:00:00') -- Excluimos los valores por defecto 
  AND l.localidad_nombre NOT IN ('Barrancas', 'Las Ovejas') -- Excluimos la data corrupta
GROUP BY h.hora_hecho
ORDER BY cantidad_casos DESC
LIMIT 5;

-- 4. ¿Los hechos suceden en el domicilio de la víctima o fuera del mismo?

SELECT 
    h.tipo_lugar, 
    COUNT(h.hecho_id) AS cantidad_casos
FROM hecho h
JOIN localidad l ON h.localidad_id = l.localidad_id
WHERE h.tipo_lugar NOT ILIKE '%Sin determinar%' 
  AND l.localidad_nombre NOT IN ('Barrancas', 'Las Ovejas') -- Excluimos la data corrupta
GROUP BY h.tipo_lugar
ORDER BY cantidad_casos DESC;

-- 5. ¿Cuál es el grupo demográfico más propenso a perpetuar el hecho delictivo (sexo, género, edad)?

SELECT 
    i.sexo, 
    i.identidad_genero, 
    i.tr_edad, 
    COUNT(i.involucrados_id) AS cantidad_victimarios
FROM involucrados i
JOIN hecho h ON i.hecho_id = h.hecho_id
JOIN localidad l ON h.localidad_id = l.localidad_id
WHERE i.tipo_involucrado ILIKE '%inculpado%' 
  AND i.sexo NOT ILIKE '%No corresponde%'
  AND i.tr_edad NOT ILIKE '%Sin determinar%'
  AND i.identidad_genero NOT ILIKE '%Sin determinar%' 
  AND i.identidad_genero NOT ILIKE '%No corresponde%' 
  AND l.localidad_nombre NOT IN ('Barrancas', 'Las Ovejas') -- Filtramos la data corrupta
GROUP BY i.sexo, i.identidad_genero, i.tr_edad
ORDER BY cantidad_victimarios DESC
LIMIT 1;

-- 6. ¿Cuál es el TOP 10 de localidades dónde sucede una mayor cantidad de femicidios?

SELECT 
    l.localidad_nombre, 
    p.provincia_nombre, 
    COUNT(DISTINCT h.hecho_id) AS cantidad_femicidios
FROM hecho h
JOIN localidad l ON h.localidad_id = l.localidad_id
JOIN provincia p ON l.provincia_id = p.provincia_id
JOIN involucrados i ON h.hecho_id = i.hecho_id
WHERE i.tipo_involucrado ILIKE '%victima%'
  AND (i.identidad_genero ILIKE '%Mujer%' OR (i.sexo = 'Femenino' AND i.identidad_genero NOT ILIKE '%Varón%'))
  AND l.localidad_nombre NOT IN ('Barrancas', 'Las Ovejas') -- omitir por inconsistencias 
GROUP BY l.localidad_nombre, p.provincia_nombre
ORDER BY cantidad_femicidios DESC
LIMIT 10;

-- 7. ¿Cuál es el TOP 5 de las provincias con mayor cantidad de femicidios?

SELECT 
    p.provincia_nombre, 
    COUNT(DISTINCT h.hecho_id) AS cantidad_femicidios
FROM hecho h
JOIN localidad l ON h.localidad_id = l.localidad_id
JOIN provincia p ON l.provincia_id = p.provincia_id
JOIN involucrados i ON h.hecho_id = i.hecho_id
WHERE i.tipo_involucrado ILIKE '%victima%'
  AND (i.identidad_genero ILIKE '%Mujer%' OR (i.sexo = 'Femenino' AND i.identidad_genero NOT ILIKE '%Varón%'))
  AND l.localidad_nombre NOT IN ('Barrancas', 'Las Ovejas') -- Excluimos la data corrupta
GROUP BY p.provincia_nombre
ORDER BY cantidad_femicidios DESC
LIMIT 5;