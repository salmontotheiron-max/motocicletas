# Observatorio ANESDOR — prototipo inicial

## Qué incluye
- Web estática responsive.
- Selector de periodo (septiembre de 2025 o acumulado enero-septiembre de 2025).
- Filtro por tipo de propulsión.
- Indicadores y variación interanual calculados en el navegador.
- Exportación de la tabla filtrada a CSV.
- Impresión del informe / guardar como PDF desde el navegador.
- Enlace al PDF oficial utilizado.

## Datos incluidos
Transcripción de la tabla de matriculaciones de motocicletas por tipo de propulsión del informe oficial ANESDOR:
https://www.anesdor.com/wp-content/uploads/2025/10/250930-Propulsi%C3%B3n-vn-septiembre.pdf

Septiembre 2025:
- Gasolina: 22.533; septiembre 2024: 19.493
- Eléctrica: 369; septiembre 2024: 445
- Total: 22.902; septiembre 2024: 19.938

Acumulado enero-septiembre:
- Gasolina: 176.175; enero-septiembre 2024: 159.663
- Eléctrica: 4.766; enero-septiembre 2024: 3.954
- Total: 180.941; enero-septiembre 2024: 163.617

## Limitaciones
Es una muestra funcional de interfaz y cálculo, no todavía un sistema de actualización automática ni una serie histórica completa. No contiene modelos ni provincias. No se deben presentar estos datos como los datos actuales de 2026.

## Publicación gratuita sugerida
1. Crear un repositorio público en GitHub.
2. Subir `index.html` a la raíz.
3. En Settings → Pages, elegir desplegar desde la rama principal y carpeta raíz.
4. GitHub Pages publicará una URL pública del tipo `https://USUARIO.github.io/REPOSITORIO/`.

## Siguiente fase
- Auditar la serie mensual de PDF de ANESDOR.
- Descargar y versionar los documentos originales.
- Añadir los informes de cilindrada, modelos y geografía sólo cuando los PDF permitan verificar los datos.
- Programar comprobaciones el día 15 y 20 mediante GitHub Actions.
- Mantener una copia independiente del repositorio y exportaciones periódicas de los datos.
