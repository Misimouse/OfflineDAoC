# Ardee: corrección de las máscaras cuadriculadas

Tras las capturas de las 22:08–22:09 del 23-10-2026, se confirma que la revisión anterior no resolvía los cuadrados. Las pruebas aisladas separaron texturas, normales, color regional y coeficientes de mezcla. La vista de máscaras en falso color revela bloques rectangulares en los pesos originales; quitar el color regional o las normales no elimina el defecto del resultado. El cambio anterior atacaba la repetición de imágenes, pero dejaba estos bloques intactos.

Se prepara una COPIA numérica de los coeficientes: filtro gaussiano separable de sigma 2 m y radio 6,4 m, almacenado en coma flotante de 16 bits. Una perturbación suave y estática de hasta 0,9 m por eje evita alinear los contornos con los ejes del mapa. No es animación. Se conservan las imágenes y el trazado general de tierra, caminos y praderas; las fronteras pequeñas se suavizan, por lo que no se afirma que todos los pesos y bordes sean idénticos. El cambio absoluto medio de coeficiente es 0,0177. Los originales y sus hashes permanecen intactos.

Mismo ámbito: cuatro sectores de Ardee y laderas (16,78 ha), transición de 45 m al exterior. Se conserva la mezcla de texturas de la revisión anterior. No se agregan plantas, animaciones, mallas ni colisiones; no se modifican árboles, agua, setas o piedras aprobadas. Ocho vistas comparadas, incluida la posición de cámara del camino reportado. «Anterior» muestra la segunda revisión con máscaras sin suavizar; «nuevo» muestra esta tercera revisión.

Comprobaciones del renderizador aislado: igualdad de mallas y colisiones, 1404 elementos del bosque y 82 setas intactos, restauración exacta, recarga y modo pintado. Se verifican los formatos nuevos RGBAH y anteriores RGBA8, el puntero activo y la configuración de la versión previa. El juego y el servidor no se iniciaron ni reiniciaron. La valoración final dentro del juego sigue pendiente del propietario.

Próxima apertura de LAB: `.enhanced-session/ground_patterns/smooth_masks_20261023/manifest.json`. Ctrl+F10 conserva la comparación con el terreno anterior al primer piloto. `work/seal_smooth_ground.py undo` recupera el puntero exacto de la segunda revisión y se niega a sobrescribir una activación posterior. Recursos y capturas se archivan en privado local; sin publicación.

Diagnóstico completo: `outputs/Diagnostico_Cuadricula_20261023`. Comparaciones y verificaciones: `outputs/Suelos_Mezclas_Suaves_20261023` del espacio de trabajo. El archivo privado depende de `ground-antitiling-20261023` y, a través de él, del primer piloto. Fuera de estos cuatro sectores no se corrige el terreno.

## Rechazo visual del propietario — 22:24

El propietario confirma con nuevas capturas que los cuadrados siguen prácticamente igual. La revisión NO está validada y el defecto principal permanece pendiente. Las mejoras observadas en el renderizador aislado no demostraron resolver su caso. Se añade diagnóstico de la revisión cargada, modo de terreno y shaders realmente aplicados en Inspector; LAB muestra R1/R2/R3 y el número de sectores con el material nuevo. Comprobado con el puntero activo: R3, RGBAH, shader smooth y 4/4 sectores; comparación anterior y modo pintado reportan 0 sectores nuevos. No se cambian recursos del terreno en este paso ni se inicia el juego. Es instrumentación para aislar la discrepancia, no otra corrección visual.
