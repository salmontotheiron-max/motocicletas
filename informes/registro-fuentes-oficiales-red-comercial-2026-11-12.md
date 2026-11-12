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

## Estados y regla probatoria

Los estados de marca distinguen anuncio, entrada reciente, actividad establecida, revisión, cese confirmado, inactividad no verificada y situación desconocida.

Un anuncio de lanzamiento no prueba actividad comercial efectiva. La ausencia de una marca en un directorio no prueba su retirada. Los errores de captura y los cambios de web son incidencias técnicas. Los candidatos se someten a revisión antes de actualizar el histórico.

## Fuentes iniciales

Se mantienen las tres fuentes oficiales del piloto:
- Suzuki: https://moto.suzuki.es/concesionarios
- Zontes: https://zontesmotos.es/puntos-de-venta/
- ZXMOTO: https://zxmoto.es/puntos-de-venta/

No se añaden todavía fuentes secundarias concretas de descubrimiento sin completar su evaluación y documentación. El esquema ya permite incorporarlas con rol market_discovery, sin obligarlas a referir una marca conocida.

## Próximos pasos

1. Evaluar y registrar fuentes sectoriales y oficiales de descubrimiento de fabricantes/marcas.
2. Investigar carga dinámica de los localizadores Zontes y ZXMOTO.
3. Implementar capturas con fecha, URL final, estado HTTP, tipo de contenido, hash y evidencia.
4. Comparar capturas y generar candidatos, sin actualización automática del histórico.
