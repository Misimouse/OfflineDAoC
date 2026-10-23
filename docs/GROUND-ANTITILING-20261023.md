# Repetición del terreno: segunda revisión de Ardee

Corrección solicitada tras las capturas del propietario de las 18:14–18:17 del 23-10-2026. El primer piloto seguía repitiendo tierra y trébol en una cuadrícula regular; sus dos muestreos globales de hierba y suelo pedregoso tampoco bastaban para ocultar el patrón a distancia.

## Resultado

Se conservan las mismas imágenes, máscaras, alturas y cuatro sectores del piloto (16,78 ha). El nuevo material mezcla tres muestras por triángulo, con desplazamientos y giros distintos por vértice y pesos continuos. Se aplica a hierba, vegetación dispersa, suelo pedregoso, trébol, roca, tierra y grava. Las derivadas explícitas mantienen el filtrado entre regiones; normal y rugosidad de tierra/grava comparten transformaciones y los vectores normales compensan el giro. No se muestrean capas cuyo peso es despreciable, para contener el coste gráfico.

Las filas de tierra de la plaza y la repetición de manchas claras disminuyen en las comparaciones revisadas. No se repinta el mapa, ni se desdibujan las imágenes originales. El borde de 45 m del piloto sigue mezclando hacia el acabado anterior: fuera de estos cuatro sectores no se cambia el terreno. No se afirma que toda Connacht esté corregida.

## Comprobación y uso

Renderizador aislado: siete vistas antes/después, incluyendo plaza lejana y césped cercano, además de unión interna y borde. Las capturas «anterior» de esta revisión muestran el PRIMER PILOTO, no el terreno original. Mallas, colisiones, bosque (1404 elementos), setas (82), restauración, recarga y modo pintado verificados. LAB e Inspector compilan. Los punteros de otros acabados permanecen idénticos; el juego y el servidor no se iniciaron.

Al volver a abrir LAB se carga `.enhanced-session/ground_patterns/antitile_20261023/manifest.json`. Ctrl+F10 sigue comparando con el terreno anterior al primer piloto. El material de la primera revisión se conserva intacto; el controlador selecciona el shader declarado por cada manifiesto y comprueba su hash. `work/seal_ground_tiling.py undo` restaura el puntero exacto del primer piloto y rechaza activaciones posteriores.

## Rendimiento orientativo

36 fotogramas por estado en la pasada final del renderizador aislado; anterior = primer piloto. No es una medida del rendimiento real con conexión y personajes. Mismo número de llamadas de dibujo, más trabajo por material.

| Vista | Primer piloto ms | Revisión ms | Llamadas de dibujo |
|---|---:|---:|---:|
| ardee | 15.51 | 17.76 | 895 |
| ladera | 14.05 | 13.21 | 596 |
| pedregoso | 15.11 | 16.10 | 812 |
| panoramica | 12.56 | 12.03 | 730 |
| plaza | 13.16 | 13.62 | 725 |
| plaza_lejos | 17.23 | 17.16 | 1047 |
| trebol_cerca | 11.01 | 13.01 | 331 |

## Después

Césped con volumen, plantas y viento quedan pendientes de validar el suelo. La idea se registra en PENDIENTES.md: detalle próximo, menor densidad y detalle a distancia. No se han añadido ni animaciones ni plantas en esta revisión.

Capturas, verificaciones y activación: `outputs/Suelos_Sin_Cuadricula_20261023` del espacio de trabajo. Archivo privado local dependiente del primer piloto: `Remasters/graphics/zone207/ground-antitiling-20261023`. Sin publicación ni envío a GitHub.
