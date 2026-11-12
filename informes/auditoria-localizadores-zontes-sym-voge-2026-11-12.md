# Auditoría de localizadores oficiales: Zontes, SYM y Voge

**Fecha de revisión:** 12-11-2026  
**Ámbito:** España; preparación de la segunda ampliación de la matriz territorial de Barcelona, Málaga, Cádiz, Alicante y Murcia.

## Resultado ejecutivo

Se han revisado los localizadores oficiales de las tres marcas para preparar la incorporación de establecimientos a la matriz. Los tres disponen de mecanismos oficiales de búsqueda, pero la consulta pública recuperable no proporciona un listado estático de establecimientos con municipio, dirección y función que permita incorporarlos de forma reproducible en esta entrega.

**No se añaden puntos de venta a la matriz ni se marca ninguna provincia como carente de red.** La falta de resultados extraíbles no demuestra ausencia de concesionarios.

## Revisión por marca

| Marca | Fuente oficial | Resultado de auditoría | Tratamiento |
|---|---|---|---|
| Zontes | [Puntos de venta Zontes España](https://zontesmotos.es/puntos-de-venta/) | El localizador oficial está publicado, pero la consulta automatizada de la página devuelve HTTP 403; el resultado indexado solo expone el buscador y el mapa, no las fichas de establecimientos. | Mantener `locator_present_dynamic_content`; no incorporar direcciones de webs de distribuidores sin contraste individual con la marca. |
| SYM | [Concesionarios oficiales SYM](https://www.sym.com.es/concesionarios-scooter) | El localizador permite buscar por ciudad o código postal y radio de 100 km, y separa concesionarios oficiales de servicios oficiales. La vista HTML no contiene resultados de establecimientos. | Registrar la fuente primaria; clasificar como `locator_present_dynamic_content`. |
| Voge | [Puntos de venta Voge España](https://vogespain.es/puntos-de-venta-espana/) y [contacto con vendedor autorizado](https://vogespain.es/contacta-con-tu-dealer/) | El sitio oficial enlaza un localizador y un formulario de vendedor autorizado que requiere provincia y punto de venta; la extracción textual no expone las opciones ni las fichas. Voge declara una red nacional de más de 100 puntos de venta, pero esa cifra agregada no identifica ubicaciones concretas. | Mantener `locator_present_dynamic_content`; no convertir cifras agregadas ni listados de terceros en registros individuales verificados. |

## Pistas de investigación, no registros verificados

- **Zontes Murcia / Steel Center:** su web propia declara ser punto de venta y taller oficial en Av. del Progreso, 232 B, Murcia. Es una declaración del propio establecimiento, no una ficha individual recuperada del directorio oficial; permanece como pista pendiente de contraste.
- **Barcelona, Cádiz, Málaga y Murcia:** los resultados de directorios comerciales secundarios muestran candidatos para una o varias de estas marcas. No se incorporan porque el criterio de aceptación exige evidencia primaria individual o confirmación oficial de marca.
- **SYM:** el aviso legal del sitio identifica a Motos Bordoy, S.A. como titular de SYM España. Esto identifica al operador del sitio, no acredita por sí solo cada establecimiento.

## Implicaciones para el inventario

1. La matriz de la PR #44 permanece sin cambios: 20 entradas Honda/Yamaha.
2. Los localizadores Zontes, SYM y Voge quedan registrados como fuentes primarias a vigilar.
3. No se utilizan APIs privadas, no se eluden controles de acceso y no se automatizan búsquedas con datos personales o geolocalización.
4. Para añadir un establecimiento se exigirá ficha oficial individual o confirmación explícita de la marca, dirección pública, municipio, fecha de consulta y distinción entre venta y posventa.
5. Los candidatos hallados en fuentes secundarias se conservan como pistas de investigación, nunca como red oficial verificada.

## Fuentes

- [Zontes España — localizador](https://zontesmotos.es/puntos-de-venta/)
- [SYM España — concesionarios](https://www.sym.com.es/concesionarios-scooter)
- [SYM España — aviso legal](https://www.sym.com.es/legal)
- [Voge España — puntos de venta](https://vogespain.es/puntos-de-venta-espana/)
- [Voge España — vendedor autorizado](https://vogespain.es/contacta-con-tu-dealer/)
- [Voge España — compañía y presencia nacional](https://vogespain.es/compania/)
- [Zontes Murcia — web del establecimiento, autodeclaración pendiente de contraste](https://zontesmurcia.com/)
