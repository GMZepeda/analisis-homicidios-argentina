

# ==================================================
# ANÁLISIS DE HOMICIDIOS Y FEMICIDIOS - ARGENTINA
# ==================================================

# 1. Preparación
rm(list = ls())

setwd("C:/PROYECTOS/SQL/homicidios/data")

library(tidyverse)


# 2. Importación de datos
mis_datos <- read_delim(
  "homicidios_limpio.csv",
  delim = ";",
  na = c("", "NA"),
  show_col_types = FALSE
)


# 3. Clasificación del ámbito
mis_datos <- mis_datos %>%
  mutate(
    ambito_lugar = case_when(
      tipo_lugar == "Domicilio particular" ~ "Domicilio particular",
      tipo_lugar == "Sin determinar" ~ "Sin determinar",
      is.na(tipo_lugar) ~ NA_character_,
      TRUE ~ "Fuera del domicilio"
    )
  )


# 4. Distribución general por ámbito
distribucion_general <- mis_datos %>%
  filter(!is.na(ambito_lugar)) %>%
  count(ambito_lugar, name = "casos") %>%
  mutate(porcentaje = round(casos / sum(casos) * 100, 1)) %>%
  arrange(desc(casos))

print(distribucion_general)


# 5. Distribución por sexo
distribucion_por_sexo <- mis_datos %>%
  filter(
    victima_sexo %in% c("Femenino", "Masculino"),
    !is.na(ambito_lugar)
  ) %>%
  count(victima_sexo, ambito_lugar, name = "casos") %>%
  group_by(victima_sexo) %>%
  mutate(porcentaje = round(casos / sum(casos) * 100, 1)) %>%
  ungroup()

print(distribucion_por_sexo)


# 6. Clasificación exploratoria de víctimas mujeres
df_mujeres <- mis_datos %>%
  filter(victima_sexo == "Femenino")

femicidios_resumen <- df_mujeres %>%
  count(categoria_femicidio, name = "casos") %>%
  mutate(porcentaje = round(casos / sum(casos) * 100, 1)) %>%
  arrange(desc(casos))

print(femicidios_resumen)


# 7. Criterios de femicidio
df_fem_estricto <- mis_datos %>%
  filter(categoria_femicidio == "Femicidio íntimo según el vínculo")

df_fem_ampliado <- mis_datos %>%
  filter(categoria_femicidio %in% c(
    "Femicidio íntimo según el vínculo",
    "Posible femicidio familiar"
  ))

total_mujeres <- nrow(df_mujeres)
femicidio_intimo <- nrow(df_fem_estricto)

femicidio_familiar <- sum(
  df_mujeres$categoria_femicidio == "Posible femicidio familiar",
  na.rm = TRUE
)

if (total_mujeres > 0) {
  resumen_criterios <- tibble(
    criterio = c("Estricto", "Ampliado"),
    casos = c(
      femicidio_intimo,
      femicidio_intimo + femicidio_familiar
    ),
    porcentaje = round(
      casos / total_mujeres * 100, 1
    )
  )
  
  print(resumen_criterios)
}


# 8. Femicidios según ámbito
femicidios_por_ambito <- bind_rows(
  df_fem_estricto %>% mutate(criterio = "Estricto"),
  df_fem_ampliado %>% mutate(criterio = "Ampliado")
) %>%
  filter(!is.na(ambito_lugar)) %>%
  count(criterio, ambito_lugar, name = "casos") %>%
  group_by(criterio) %>%
  mutate(porcentaje = round(casos / sum(casos) * 100, 1)) %>%
  ungroup()

print(femicidios_por_ambito)


# 9. Femicidios en domicilio particular
resumen_hogar <- bind_rows(
  df_fem_estricto %>% mutate(criterio = "Estricto"),
  df_fem_ampliado %>% mutate(criterio = "Ampliado")
) %>%
  group_by(criterio) %>%
  summarise(
    total_casos = n(),
    casos_en_domicilio = sum(
      ambito_lugar == "Domicilio particular",
      na.rm = TRUE
    ),
    porcentaje_en_domicilio = round(
      casos_en_domicilio / total_casos * 100, 1
    ),
    .groups = "drop"
  )

print(resumen_hogar)


# 10. Vínculo con el inculpado
vinculos_mujeres <- df_mujeres %>%
  count(victima_relacion_inculpado, name = "casos") %>%
  mutate(porcentaje = round(casos / sum(casos) * 100, 1)) %>%
  arrange(desc(casos))

print(vinculos_mujeres)

# 11. Verificación: mujeres asesinadas en su domicilio, según vínculo
base_casa <- df_mujeres %>%
  filter(ambito_lugar == "Domicilio particular")

parejas    <- c("Cónyuge/Pareja", "Ex cónyuge/Ex pareja")
familiares <- c("Padre/Madre", "Hijo/a", "Hermano/a", "Otros vínculos familiares")

# Detalle por categoría (denominador: 1.887)
detalle_casa <- base_casa %>%
  count(victima_relacion_inculpado, name = "casos") %>%
  mutate(porcentaje = round(casos / sum(casos) * 100, 1)) %>%
  arrange(desc(casos))
print(detalle_casa)

# Agrupado
casa_vinculo <- base_casa %>%
  mutate(
    grupo_vinculo = case_when(
      victima_relacion_inculpado %in% parejas ~ "Pareja o ex pareja",
      victima_relacion_inculpado %in% familiares ~ "Familiar (padre/madre, hijo/a, hermano/a, otros)",
      victima_relacion_inculpado == "Sin determinación" ~ "Sin determinar",
      victima_relacion_inculpado %in% c("Sin relación", "Otras relaciones no familiares",
                                        "Empleador", "Empleado", "Cliente/Proveedor",
                                        "Socio (relación comercial)") ~ "Sin vínculo familiar",
      TRUE ~ "Otro"
    )
  ) %>%
  count(grupo_vinculo, name = "casos") %>%
  mutate(porcentaje = round(casos / sum(casos) * 100, 1)) %>%
  arrange(desc(casos))
print(casa_vinculo)

# Control: las partes suman el total
n_casa <- nrow(base_casa)
tibble(
  grupo = c("Pareja/ex pareja", "Familiares", "Pareja/ex + familiares",
            "Sin vínculo familiar", "Sin determinar", "Total"),
  casos = c(
    sum(base_casa$victima_relacion_inculpado %in% parejas),
    sum(base_casa$victima_relacion_inculpado %in% familiares),
    sum(base_casa$victima_relacion_inculpado %in% c(parejas, familiares)),
    sum(base_casa$victima_relacion_inculpado %in% c("Sin relación",
                                                    "Otras relaciones no familiares", "Empleador", "Empleado",
                                                    "Cliente/Proveedor", "Socio (relación comercial)")),
    sum(base_casa$victima_relacion_inculpado == "Sin determinación", na.rm = TRUE),
    n_casa
  )
) %>%
  mutate(porcentaje = round(casos / n_casa * 100, 1)) %>%
  print()

# Control cruzado sobre todas las mujeres (debe dar 1.831 = 57,2 %)
cat("Todas las mujeres:",
    sum(df_mujeres$victima_relacion_inculpado %in% c(parejas, familiares)),
    "de", nrow(df_mujeres), "\n")



# ============================================================
# INFOGRAFÍA · VIOLENCIA DE GÉNERO EN ARGENTINA  (v3)
# 1080 x 1920 px, paleta violeta
# Solo necesita: ggplot2 y ragg
# ============================================================

library(ggplot2)
library(ragg)

# ---------------- 1. DATOS ----------------
n_total <- 19086; n_fuera <- 11903; n_dom <- 5654; n_sd <- 1529
pct_fuera <- 62.4; pct_dom <- 29.6; pct_sd <- 8.0

n_muj <- 3200; n_muj_casa <- 1887; pct_muj <- 59.0
n_hom <- 15879; n_hom_casa <- 3765; pct_hom <- 23.7

n_autor <- 1294; pct_autor <- 68.6
anios <- "2017 a 2025"

# ---------------- 2. FORMATO ----------------
f1 <- function(x) formatC(x, format = "f", digits = 1, decimal.mark = ",")
fm <- function(x) format(x, big.mark = ".", decimal.mark = ",", trim = TRUE, scientific = FALSE)

V_DARK  <- "#2E0A38"
V_MAIN  <- "#6A1B9A"
V_MID   <- "#9C4DCC"
V_LIGHT <- "#D9B8E8"
V_PALE  <- "#F3E9F7"
V_BG    <- "#FBF8FC"
TEXTO   <- "#3F3246"
TEXTO_2 <- "#4A3A52"
PIE     <- "#5B4B66"
GRIS    <- "#8A7F95"

S <- function(px) px * 0.75 / (72.27 / 25.4)

# ---------------- 3. LIENZO ----------------
W <- 1080; H <- 1920

p <- ggplot() +
  coord_cartesian(xlim = c(0, W), ylim = c(0, H), expand = FALSE, clip = "off") +
  theme_void() +
  theme(plot.background = element_rect(fill = V_BG, colour = NA),
        plot.margin = margin(0, 0, 0, 0))

txt <- function(x, y, label, px, colour = V_DARK, face = "plain",
                hjust = 0, vjust = 0, lh = 1.15) {
  annotate("text", x = x, y = y, label = label, size = S(px), colour = colour,
           fontface = face, hjust = hjust, vjust = vjust,
           family = "Arial", lineheight = lh)
}

# ---------------- 4. ENCABEZADO (centrado) ----------------
p <- p +
  annotate("rect", xmin = 0, xmax = W, ymin = 1630, ymax = H, fill = V_DARK, colour = NA) +
  txt(540, 1884, "VIOLENCIA DE GÉNERO  ·  DATOS DE ARGENTINA", 19, V_LIGHT, "bold", 0.5) +
  txt(540, 1780, "«Llegamos a casa,", 100, "white", "bold.italic", 0.5, lh = 1.05) +
  txt(540, 1696, "podemos descansar...»", 100, "white", "bold.italic", 0.5, lh = 1.05) +
  txt(540, 1652, "Una frase que en nuestro país no se aplica a las mujeres", 22, "#EBDCF4", hjust = 0.5)

# ---------------- 5. DÓNDE OCURREN ----------------
p <- p +
  txt(64, 1582, "¿DÓNDE OCURREN LOS HOMICIDIOS (2017 - 2025)?", 23, V_MAIN, "bold") +
  txt(64, 1540, paste0("El ", f1(pct_fuera), " % de los homicidios ocurre fuera del domicilio particular y el ",
                       f1(pct_dom), " % en el mismo. En el ", f1(pct_sd),
                       " % restante, el lugar no quedó registrado."), 18, TEXTO)

x0 <- 64; ancho <- 952; gap <- 4
w1 <- ancho * pct_fuera / 100
w2 <- ancho * pct_dom / 100
w3 <- ancho - w1 - w2
xa <- x0 + w1; xb <- xa + w2; xc <- xb + w3

p <- p +
  annotate("rect", xmin = x0, xmax = xa - gap, ymin = 1436, ymax = 1498, fill = V_MAIN,  colour = NA) +
  annotate("rect", xmin = xa, xmax = xb - gap, ymin = 1436, ymax = 1498, fill = V_MID,   colour = NA) +
  annotate("rect", xmin = xb, xmax = xc,       ymin = 1436, ymax = 1498, fill = V_LIGHT, colour = NA) +
  txt(x0 + w1 / 2, 1467, paste0(f1(pct_fuera), " %"), 27, "white", "bold", 0.5, 0.5) +
  txt(xa + w2 / 2, 1467, paste0(f1(pct_dom), " %"),   27, "white", "bold", 0.5, 0.5) +
  txt(xb + w3 / 2, 1467, paste0(f1(pct_sd), " %"),    22, V_DARK, "bold", 0.5, 0.5)

leg <- function(x, col, label) {
  list(
    annotate("rect", xmin = x, xmax = x + 15, ymin = 1380, ymax = 1395, fill = col, colour = NA),
    txt(x + 23, 1387.5, label, 16, TEXTO_2, vjust = 0.5)
  )
}
p <- p +
  leg(x0,  V_MAIN,  paste0("Fuera del domicilio · ",  fm(n_fuera))) +
  leg(448, V_MID,   paste0("Domicilio particular · ", fm(n_dom))) +
  leg(792, V_LIGHT, paste0("Sin registrar · ",        fm(n_sd)))

# ---------------- 6. POR SEXO ----------------
p <- p +
  txt(64, 1302, "SI SEPARAMOS POR SEXO, LOS DATOS SON ALARMANTES", 23, V_MAIN, "bold") +
  txt(64, 1266, "Porcentaje de las muertes que ocurren en el domicilio particular.", 18, TEXTO)

card <- function(xmin, titulo, pct, color, base, pie) {
  list(
    annotate("rect", xmin = xmin, xmax = xmin + 460, ymin = 1106, ymax = 1248, fill = V_PALE, colour = NA),
    annotate("rect", xmin = xmin, xmax = xmin + 6, ymin = 1106, ymax = 1248, fill = color, colour = NA),
    txt(xmin + 30, 1224, titulo, 16, color, "bold"),
    txt(xmin + 30, 1190, paste0(f1(pct), " %"), 46, color, "bold", lh = 1),
    txt(xmin + 30, 1136, base, 16, TEXTO),
    txt(xmin + 30, 1113, pie, 16, TEXTO)
  )
}
p <- p +
  card(64, "MUJERES", pct_muj, V_MAIN,
       paste0("de las mujeres asesinadas (", fm(n_muj_casa), " de ", fm(n_muj), ")"),
       "murió en su domicilio.") +
  card(556, "HOMBRES", pct_hom, GRIS,
       paste0("de los hombres asesinados (", fm(n_hom_casa), " de ", fm(n_hom), ")"),
       "murió en su domicilio: menos de la mitad.")

# ---------------- 7. AUTORÍA ----------------
p <- p +
  annotate("rect", xmin = 64, xmax = 1016, ymin = 946, ymax = 1058, fill = "#EFE1F5", colour = NA) +
  annotate("rect", xmin = 64, xmax = 70,   ymin = 946, ymax = 1058, fill = V_MAIN, colour = NA) +
  txt(96, 1002, paste0(f1(pct_autor), " %"), 48, V_MAIN, "bold", vjust = 0.5, lh = 1) +
  txt(300, 1012, paste0("de las ", fm(n_muj_casa), " mujeres asesinadas en el domicilio particular murió a manos de su pareja,"), 21, TEXTO) +
  txt(300, 978, "ex pareja, cónyuge, ex cónyuge o un allegado familiar (padre/madre, hijo/a, hermano/a, etc.).", 21, TEXTO)

# ---------------- 8. PREGUNTAS (en caja, centradas) ----------------
p <- p +
  annotate("rect", xmin = 64, xmax = 1016, ymin = 620, ymax = 925, fill = V_PALE, colour = NA) +
  annotate("rect", xmin = 64, xmax = 70,   ymin = 620, ymax = 925, fill = V_MID, colour = NA) +
  txt(540, 886, "«Llegamos a casa, podemos descansar...» pareciera", 19.5, TEXTO_2, "italic", 0.5) +
  txt(540, 858, "ser una utopía para las mujeres.", 19.5, TEXTO_2, "italic", 0.5) +
  txt(540, 802, "¿Qué estamos haciendo como sociedad para que todos", 20.5, V_DARK, "bold", 0.5) +
  txt(540, 772, "no solo nos sintamos, sino que de hecho estemos seguros en casa?", 20.5, V_DARK, "bold", 0.5) +
  txt(540, 730, "¿Qué políticas públicas se están llevando adelante?", 20.5, V_DARK, "bold", 0.5) +
  txt(540, 678, "Podemos cambiar la realidad de alguien para que no se", 18, V_MAIN, hjust = 0.5) +
  txt(540, 654, "convierta en un número más de la estadística.", 18, V_MAIN, hjust = 0.5)

# ---------------- 9. AYUDA ----------------
p <- p +
  annotate("rect", xmin = 64, xmax = 1016, ymin = 285, ymax = 596, fill = V_DARK, colour = NA) +
  txt(96, 566, "SI ESTÁS O CONOCÉS A ALGUIEN EN SITUACIÓN DE VIOLENCIA", 17, V_LIGHT, "bold") +
  txt(96, 538, "Pedí o brindá ayuda. Canales oficiales, gratuitos y confidenciales:", 15.5, "#EBDCF4") +
  txt(96, 494, "911", 26, "white", "bold", vjust = 0.5) +
  txt(168, 494, "Emergencias · peligro inminente", 17, "#EBDCF4", vjust = 0.5) +
  txt(96, 452, "144", 26, "white", "bold", vjust = 0.5) +
  txt(168, 452, "Asesoramiento y contención · 24 h", 17, "#EBDCF4", vjust = 0.5) +
  txt(96, 414, "WhatsApp", 15, "white", "bold", vjust = 0.5) +
  txt(190, 414, "11-2771-6463", 17, "#EBDCF4", vjust = 0.5) +
  txt(96, 380, "Correo", 15, "white", "bold", vjust = 0.5) +
  txt(168, 380, "linea144@mingeneros.gob.ar", 17, "#EBDCF4", vjust = 0.5) +
  txt(96, 330, "Todos los días del año, en todo el país.", 14, V_LIGHT, "italic")

# ---------------- 10. PIE ----------------
p <- p +
  txt(540, 206, "Que nosotras también podamos sentirnos seguras en casa.", 24, V_MAIN, "bold", 0.5, 0.5) +
  txt(540, 152, paste0("Fuente: registro de homicidios ", anios, " (n = ", fm(n_total), "). Elaboración propia."),
      14, PIE, hjust = 0.5, vjust = 0.5) +
  txt(540, 124, "Las cifras pueden variar según el criterio de clasificación del ámbito y del vínculo.",
      12.5, PIE, hjust = 0.5, vjust = 0.5)

# ---------------- 11. EXPORTAR ----------------
out_dir <- Sys.getenv("INFOGRAFIA_OUT", unset = "C:/PROYECTOS/SQL/homicidios/docs")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

agg_png(file.path(out_dir, "infografia_violencia.png"),
        width = W, height = H, units = "px", background = V_BG, scaling = 1)
print(p)
invisible(dev.off())