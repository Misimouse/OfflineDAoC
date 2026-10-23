# Connacht LAB: bases, segundo olmo, pinos y setas

Revisión local del 23 de octubre de 2026, autorizada a partir de las siete capturas del propietario. No se ha subido a GitHub ni se ha iniciado o reiniciado el juego o el servidor. La revisión se carga al volver a abrir LAB.

## Cambios

- Los 1.404 árboles y elementos de madera siguen en sus fixtures originales. El controlador añade prolongaciones bajo las secciones reales de los troncos, adaptadas al terreno en cada extremo; conserva la altura y transformación de las copas. LOG queda excluido. Los anclajes y las formas aprobadas de los abedules se conservan.
- ELM2: corteza natural de la misma familia mate utilizada en el roble. El cilindro escalonado anterior se sustituye por un tronco con reducción continua y uniones soldadas por superficie implícita. Las hojas y brotes cortos conservan exactamente sus posiciones. La superficie principal soldada tiene 62.688 triángulos, sin aristas no manifold. La fuente de Inspector lleva también la corteza nueva.
- GROVE: 30 niveles y siete ramas principales por nivel, frente a 24 y cinco. 806.400 acículas frente a 460.800; misma altura de 44,145 m antes de la escala del fixture. Los niveles de distancia conservan mayor cobertura con muestras 1/2, 1/6, 1/16 y 1/32 y compensación de longitud y anchura.
- Setas: prueba reversible de 81 ejemplares pequeños, nueve por cada una de las tres piedras de vinculación y los seis grupos independientes. La piedra y sus grabados permanecen intactos. Sombrero redondeado, láminas geométricas, pie curvado y materiales mates texturizados en tonos rojizos, crema y malva.
- Una seta gigante adicional junto a la piedra de Ardee, x=1310, z=1248, diámetro aproximado 10,22 m y borde a unos 6,3 m. Inspector la lista como **Seta gigante · prueba**, con destino y texturas actuales. Es un prototipo visual sin tenderos ni colisiones añadidas. No se han cambiado setas de otras zonas.

## Comprobaciones realizadas

Renderizador aislado Godot 4.7.2, Forward+, 1440×900, GTX 1080 Ti; no corresponde a una sesión real con personaje. Se verificaron la población completa, las 1.972 prolongaciones y sus 777.806 extremos inferiores, todos bajo el suelo; el recuento de colisiones no cambia y los originales se restauran exactamente. En la pendiente más exigente revisada, fixture 870, la base llega al terreno sin desplazar la copa. Las prolongaciones son geometría pequeña por ejemplar; no se duplican las mallas completas de los árboles.

Las ocho capturas incluyen el olmo, la pendiente, pino aislado cerca y lejos, setas pequeñas y gigante por debajo. Las dos vistas generales finales midieron aproximadamente 21,92 y 22,02 ms por fotograma (unos 45 FPS), con 20,35 y 19,19 millones de primitivas. El rendimiento real depende de cámara, equipo y actividad del juego.

Los once modelos que usa Inspector se leen sin errores UTF-8 ni texturas ausentes. Las huellas del agua aprobada, la hiedra de roca y el anterior puntero de olmos no cambian. Esta nueva pasada queda pendiente de valoración visual del propietario.

## Archivos privados y vuelta atrás

Los nuevos recursos están en `.enhanced-session/forest_revision_20261023`. El puntero del bosque está en `.enhanced-session/forest_population/active.json`; el de las setas, en `forest_revision_20261023/mushroom/active.json`. Los otros nueve modelos siguen utilizando sus escenas aprobadas anteriores.

Las capturas, informes y texturas con sus prompts exactos están en `outputs/Bosque_Setas_20261023` del espacio de trabajo. Las dos texturas se generaron mediante la herramienta integrada ImageGen y se conservaron sin edición de píxeles. El registro `activation.json` contiene la copia exacta del puntero anterior. `work/activate_canopy_revision.py --undo` lo restaura y retira el puntero de setas; rechaza cualquier cambio posterior. Los originales del juego y el JSON de zona permanecen intactos.

Archivo privado local: `Remasters/graphics/zone207/connacht-canopy-mushrooms-20261023`, con huellas por archivo. Depende de los archivos privados anteriores `connacht-replant-20261023` y `forest-detail-review-20261023`, que contienen los nueve modelos retenidos y la escena original de hojas del segundo olmo. No se ha publicado.
