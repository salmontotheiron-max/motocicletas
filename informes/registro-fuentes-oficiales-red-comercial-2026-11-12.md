# Registro abierto de fuentes y alcance de vigilancia del mercado motociclista

**Corte:** 12-11-2026  
**Ámbito:** España  
**Estado:** diseño de registro ampliado; la PR sigue en borrador y no se ha fusionado.

## Objetivo

El registro no representa un censo cerrado de marcas. Define fuentes para vigilar la red comercial conocida y mecanismos para descubrir fabricantes, marcas y establecimientos aún no registrados.

Se separan dos funciones:
- **Seguimiento primario:** fuentes oficiales de una marca para observar sus puntos de venta, posventa, operadores e implantación.
- **Descubrimiento de mercado:** fuentes que pueden revelar marcas, fabricantes, importadores, distribuidores o establecimientos nuevos. Pueden ser secundarias y generan pistas, no hechos históricos automáticos.

## Cobertura de acontecimientos

El registro declara cobertura abierta para:
- entrada y salida de fabricantes y marcas en España;
- apertura, cierre y traslado de puntos de venta;
- cambio de operador, importador o distribuidor;
- incorporación o retirada de marcas en establecimientos;
- cambios de alcance de venta y servicio posventa.

El catálogo inicial de tres marcas es solo un piloto. Se permiten marcas y fabricantes desconocidos y se mantiene una lista separada de fabricantes para no confundir marca comercial con entidad fabricante.

## Fuentes primarias iniciales

- Suzuki: https://moto.suzuki.es/concesionarios
- Zontes: https://zontesmotos.es/puntos-de-venta/
- ZXMOTO: https://zxmoto.es/puntos-de-venta/

## Fuentes de descubrimiento iniciales

| Fuente | URL | Utilidad | Limitación |
|---|---|---|---|
| ANESDOR - notas de prensa | https://www.anesdor.com/category/notas-de-prensa/ | Contexto sectorial, fabricantes e importadores, evolución del mercado | Representa a empresas asociadas; no es un censo completo ni prueba única de actividad individual |
| MOTOCICLISMO - industria | https://www.motociclismo.es/industria | Entradas de marcas, cambios de distribución y aperturas de concesionarios | Fuente periodística; contrastar con fuentes primarias |
| Posventa.com | https://www.posventa.com/ | Pista para movimientos empresariales y de distribución | Fuente candidata; sección y cobertura específica pendientes de evaluación |

Estas fuentes se registran con rol market_discovery, sin exigir una marca previamente conocida. Se clasifican como evidencia secundaria reputada y no sustituyen los directorios oficiales. La fuente de Posventa.com queda en estado not_assessed y con captura manual hasta completar su evaluación.

## Estados y regla probatoria

Los estados de marca distinguen anuncio, entrada reciente, actividad establecida, revisión, cese confirmado, inactividad no verificada y situación desconocida.

Un anuncio de lanzamiento no prueba actividad comercial efectiva. La ausencia de una marca en un directorio no prueba su retirada. Los errores de captura y los cambios de web son incidencias técnicas. Los candidatos se someten a revisión antes de actualizar el histórico.

## Próximos pasos

1. Evaluar cobertura, términos y estabilidad de cada fuente de descubrimiento.
2. Investigar carga dinámica de los localizadores Zontes y ZXMOTO.
3. Implementar capturas con fecha, URL final, estado HTTP, tipo de contenido, hash y evidencia.
4. Comparar capturas y generar candidatos, sin actualización automática del histórico.
5. Incorporar marcas y fabricantes nuevos conforme se descubran y verifiquen.
