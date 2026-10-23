# R5: remate del suelo de Ardee y laderas

Estado posterior: R5 fue rechazada por el propietario por introducir surcos. Se sustituye por R6, basada en R4, con filtrado del grano fino por tamaño de píxel. Véase `GROUND-R6-NO-FURROWS-20261024.md`. Este documento conserva el historial de R5; sus pruebas aisladas no constituyeron una aprobación visual real.

El propietario valora R4 como prácticamente perfecta, pero pide resolver ahora los pequeños encajes y cuadros restantes, antes de plantas/césped/arena. Esta revisión completa el remate técnico del material base de la prueba; no se remite a una lista de tareas futuras.

Dos causas corregidas: el detalle de tierra/grava restaba siempre el mip 6, que a distancia podía ser MÁS FINO que la muestra visible y reintroducir marcas/aliasing; ahora se calcula el tamaño de muestreo deformado y la muestra restada siempre es más gruesa. Además, la variación de color y la deformación procedían de una rejilla de ruido interpolado: se sustituye por un campo analítico suave en tres direcciones oblicuas, sin celdas cuadradas ni bordes de interpolación. Se calcula la matriz exacta de derivadas de la deformación, compartida por color, rugosidad y normales; se conserva el grano y el tono medio de R4.

Los campos del material y el límite de la prueba se anclan a coordenadas UV de la zona, no a la posición global, evitando deslizamientos al desplazar/cargar zonas. La comparación de un recorte de suelo antes/después de trasladar la zona 409,6/-204,8 m da una diferencia media de 0,76 niveles RGB sobre 255, percentil 99 de 3, con TAA y sombras activas.

Se mantienen las mismas imágenes y máscaras de R4, trazado general, cuatro sectores y transición de 45 m hacia el exterior. No se extiende el cambio a toda Connacht ni a otras zonas de Hibernia. No hay nueva geometría, objetos, colisiones, plantas o animaciones. Bosque (1404 elementos), setas (82), agua, piedras y sus punteros permanecen intactos.

Renderizador aislado: cuatro comparaciones R4/R5 (plaza cercana, media, lejana y camino), uniones, borde, desplazamiento de zona, igualdad de geometría/colisiones, restauración, recarga y modo pintado. Sin errores de script/shader. Medias orientativas de 36 fotogramas R4/R5: camino 11,01/11,97 ms; cercano 10,84/10,99; medio 11,14/10,69; lejano 18,90/18,77. Mismas llamadas de dibujo por vista. No equivalen a una garantía de FPS durante el juego. El juego y el servidor no se iniciaron ni reiniciaron.

Se activa el manifiesto privado finish_r5_20261023. LAB informa R5, modo y material aplicado a 4/4 sectores. Ctrl+F10 conserva la comparación con el suelo anterior al primer piloto. `work/seal_ground_finish.py undo` recupera exactamente el puntero de R4 y rechaza activaciones posteriores. Archivo privado local ground-finish-r5-20261023, dependiente de ground-continuous-detail-20261023. Capturas y registros: outputs/Suelos_Acabado_Final_20261023 del espacio de trabajo. Sin publicación ni envíos.

El remate está implementado y comprobado en el renderizador; la apreciación final en la sesión real corresponde al propietario. La siguiente fase prevista es plantas, césped y arena.
