-- 1. ¿Cuáles son las 3 provincias con mayor cantidad de homicidios?

SELECT p.provincia_nombre, COUNT(h.hecho_id) AS cantidad_homicidios
FROM hecho h
JOIN localidad l ON h.localidad_id = l.localidad_id
JOIN provincia p ON l.provincia_id = p.provincia_id
GROUP BY p.provincia_nombre
ORDER BY cantidad_homicidios DESC
LIMIT 3;

-- a) De esas provincias, ¿cuál es su localidad más crítica?

-- creamos una tabla temporal para organizar y clasificar los datos
-- solo extramos la que quedó en el puesto 1.

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
*/

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
      AND l.localidad_nombre != 'Barrancas' -- Acá excluimos el dato erróneo
    GROUP BY p.provincia_nombre, l.localidad_nombre
)
SELECT provincia_nombre, localidad_nombre, cantidad_homicidios
FROM Ranking
WHERE fila = 1
ORDER BY cantidad_homicidios DESC;

-- A nivel nacional
-- 2 Cuál es el grupo demográfico más vulnerable (sexo, género, edad)

SELECT sexo, identidad_genero, tr_edad, COUNT(involucrados_id) AS cantidad_victimas
FROM involucrados
WHERE tipo_involucrado ILIKE '%victima%'
  AND sexo NOT ILIKE '%No corresponde%'
  AND tr_edad NOT ILIKE '%Sin determinar%'
GROUP BY sexo, identidad_genero, tr_edad
ORDER BY cantidad_victimas DESC
LIMIT 1;

-- 3. ¿Existen meses o rangos horarios donde los casos se disparan?

-- meses con más casos
SELECT mes, COUNT(hecho_id) AS cantidad_casos
FROM hecho
WHERE mes IS NOT NULL
GROUP BY mes
ORDER BY cantidad_casos DESC
LIMIT 3;

-- horarios más críticos 
SELECT hora_hecho, COUNT(hecho_id) AS cantidad_casos
FROM hecho
WHERE hora_hecho NOT ILIKE '%Sin determinar%' 
  AND hora_hecho NOT ILIKE '%No corresponde%'
GROUP BY hora_hecho
ORDER BY cantidad_casos DESC
LIMIT 5;


/* Excluímos "11:11:11", "11:11:00" y "00:00:00"

Parecen ser valores por defecto (placeholders)

*/

SELECT hora_hecho, COUNT(hecho_id) AS cantidad_casos
FROM hecho
WHERE hora_hecho NOT ILIKE '%Sin determinar%' 
  AND hora_hecho NOT ILIKE '%No corresponde%'
  AND hora_hecho NOT IN ('11:11:11', '11:11:00', '00:00:00') -- Excluimos los valores por defecto 
GROUP BY hora_hecho
ORDER BY cantidad_casos DESC
LIMIT 5;

-- 4. ¿Los hechos suceden en el domicilio de la víctima o fuera del mismo?
SELECT tipo_lugar, COUNT(hecho_id) AS cantidad_casos
FROM hecho
WHERE tipo_lugar NOT ILIKE '%Sin determinar%' 
GROUP BY tipo_lugar
ORDER BY cantidad_casos DESC;

-- 5. ¿Cuál es el grupo demográfico más propenso a perpetuar el hecho delictivo (sexo, género, edad)?
SELECT sexo, identidad_genero, tr_edad, COUNT(involucrados_id) AS cantidad_victimarios
FROM involucrados
WHERE tipo_involucrado ILIKE '%inculpado%' 
  AND sexo NOT ILIKE '%No corresponde%'
  AND tr_edad NOT ILIKE '%Sin determinar%'
GROUP BY sexo, identidad_genero, tr_edad
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
  AND l.localidad_nombre != 'Barrancas' -- omitir Barrancas
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
  AND l.localidad_nombre != 'Barrancas' -- Excluimos el error de carga
GROUP BY p.provincia_nombre
ORDER BY cantidad_femicidios DESC
LIMIT 5;