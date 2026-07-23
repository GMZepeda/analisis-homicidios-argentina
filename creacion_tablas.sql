-- Creamos la tabla PROVINCIA
CREATE TABLE provincia (
	provincia_id INT PRIMARY KEY,
	provincia_nombre VARCHAR(100)
);

-- Creamos la tabla LOCALIDAD (depende de PROVINCIA)
CREATE TABLE localidad (
	localidad_id INT PRIMARY KEY,
	localidad_nombre VARCHAR(100),
	prinvincia_id INT REFERENCES provincia(provincia_id)

);

-- Creamos la tabla HECHO (depende de LOCALIDAD)
CREATE TABLE hecho (
	hecho_id VARCHAR(50) PRIMARY KEY,
	localidad_id INT REFERENCES localidad(localidad_id),
	anio INT,
	mes INT,
	fecha_hecho VARCHAR(50),
	hora_hecho VARCHAR(50),
	tipo_lugar VARCHAR(100),
	tipo_lugar_otro VARCHAR(100),
	tipo_lugar_ampliado VARCHAR(100),
	motivo_origen_registro VARCHAR(300),
	motivo_origen_registro_otro VARCHAR(300)
);

-- Creamos la tabla INVOLUCRADOS (depende de HECHO)
CREATE TABLE involucrados (
    involucrados_id SERIAL PRIMARY KEY,
    tipo_involucrado VARCHAR(50), 
    sexo VARCHAR(50),
    identidad_genero VARCHAR(50),
    identidad_genero_otro VARCHAR(100),
    tr_edad VARCHAR(50),
    mayor_18_anios VARCHAR(50),
    hecho_id VARCHAR(50) REFERENCES hecho(hecho_id)
);

-- se elimina para que coincida con el csv
ALTER TABLE localidad DROP COLUMN prinvincia_id;