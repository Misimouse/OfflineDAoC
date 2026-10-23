# Connacht LAB: bases continuas, setas atenuadas y piedra de vinculación

Revisión local del 23 de octubre de 2026 a partir de las capturas de las 15:37–15:41. Sustituye el ajuste de bases de `CONNACHT-CANOPY-MUSHROOMS-20261023.md`. No se ha publicado ni se ha iniciado o reiniciado el juego o el servidor. Se carga al volver a abrir LAB y queda pendiente de valoración visual del propietario.

## Resultado

- Se retiran de la revisión activa los faldones que producían franjas, cilindros inferiores y uniones visibles. Se ajustan los vértices originales de la base a la misma cuadrícula de alturas que utiliza Connacht. Los extremos inferiores llegan bajo el suelo con un margen de 24 cm. La transición solo afecta al tramo basal; las copas mantienen su altura. No se añaden piezas ni UV nuevas y no se modifica la física. Los abedules conservan su textura y formas aprobadas.
- El primer olmo utiliza la corteza mate de la familia ya aprobada para el segundo olmo y el roble, con proyección continua que elimina el patrón simétrico anterior. Su fuente para Inspector contiene también la textura nueva.
- Las setas conservan su geometría aprobada, incluido el ejemplar gigante. El material del sombrero reduce la intensidad del albedo a 0,48 y mezcla un 23 % de gris para contener la saturación. No utiliza emisión ni reflejo especular. Responde a la iluminación diurna y nocturna; no se reduce artificialmente su distancia de visibilidad.
- Las tres piedras de vinculación de Connacht utilizan mármol gris cálido mate con pátina discreta en la base. Conservan la silueta, posición y colisión originales. El emblema celta se ha reinterpretado a partir del motivo original en una textura de mayor detalle y relieve geométrico de unos milímetros. Se subdivide su superficie; el conjunto visible de piedra tiene 21.025 triángulos.

## Comprobaciones

Prueba aislada en Godot 4.7.2, Forward+, 1440×900, GTX 1080 Ti. Se verifican los 1.404 árboles y elementos de madera, 2.633 mallas de madera con el material basal, 81 setas pequeñas y la gigante, y los seis componentes de las tres piedras. Las 15 partes originales afectadas por piedra/setas y los originales del bosque se restauran exactamente. El recuento de colisiones no cambia.

El mapa de alturas empleado por el material conserva exactamente los valores de la cuadrícula de zona. No hay geometría basal añadida. Las capturas revisadas incluyen bases de olmo, roble y abedules en pendientes, la unión de ramas, piedra y emblema de cerca y setas de día y de noche. No hay errores de shader o script en la pasada final. Las dos vistas generales midieron 19,75 y 20,24 ms por fotograma, aproximadamente 49–51 FPS; no es una medición de una sesión real con personaje.

Inspector lee las once fuentes de árboles sin errores UTF-8 ni texturas ausentes. Sus filas de piedra enlazan los materiales actuales, sin presentar la textura antigua como si siguiera visible. Las huellas de los recursos aprobados de agua, hiedra de rocas y puntero anterior de olmos permanecen intactas.

## Recursos y recuperación

Recursos nuevos: `.enhanced-session/finish_revision_20261023`. Sus manifiestos `forest_manifest.json` y `mushroom_manifest.json` se activan mediante los punteros existentes del bosque y de la prueba de setas. Los materiales nuevos de mármol y emblema están en `materiales/`; se generaron con ImageGen integrado. Los prompts y copias de las imágenes se conservan en `outputs/Acabado_Arboles_Vinculo_20261023/materiales` del espacio de trabajo, junto con capturas e informes.

`work/activate_finish_revision.py --undo` restaura los dos punteros exactos anteriores y rechaza sobrescribir una activación posterior. No se modifican archivos originales del juego, JSON de zona, bases de datos ni otras zonas. Los recursos previos se conservan para recuperación.

Archivo privado local: `Remasters/graphics/zone207/connacht-finish-20261023`, con inventario de huellas. Depende de `connacht-canopy-mushrooms-20261023`, `connacht-replant-20261023` y `forest-detail-review-20261023`. Todo se conserva solo en local.
