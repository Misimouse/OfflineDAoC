# Suelos de Ardee y laderas: prueba local

Prueba solicitada el 23-10-2026 para conservar la distribución del suelo del juego y comparar un acabado vegetal nuevo. Se limita a los sectores 5_5, 5_6, 6_5 y 6_6 de Connacht: un cuadrado de 409,6 m de lado (16,78 ha), con transición interior de 45 m hacia el acabado anterior. Pendiente de valoración visual del propietario.

## Materiales y distribución

Tres albedos nuevos de ImageGen integrado: hierba corta densa (2,5 m por repetición), vegetación dispersa sobre tierra y hierba pedregosa (3 m). La tierra y la grava conservan los materiales PBR aprobados; no se rediseña la carretera. El trébol y la roca nativos se conservan. El color regional Connacht se usa como matiz de baja frecuencia: no constituye un quinto mosaico intercambiable. Así se distinguen cinco familias visuales sin inventar cinco identificadores nativos.

Los pesos de todas las parcelas se convierten a coeficientes equivalentes al mezclado secuencial original y se reúnen en un atlas continuo de 1024². Los cuatro sectores de prueba leen las mismas posiciones originales; no se repinta la distribución. Cuantización RGBA8 máxima ±0,001961 por coeficiente; el filtrado continuo interpola entre bordes en lugar de sujetar cada parcela por separado. Se normalizan las capas físicas y se aplica el matiz regional aparte, por lo que se preservan las ubicaciones y proporciones de partida, no el color compuesto original.

Dos muestreos con giro y mezcla gradual reducen la repetición en cada nueva superficie. Los mipmaps mantienen el acabado nuevo a distancia dentro de la prueba; el borde enlaza gradualmente con el material anterior. No se promete eliminar toda repetición del terreno fuera de estos sectores ni la de las capas nativas retenidas.

## Uso y reversión

El siguiente inicio de LAB carga el puntero privado `.enhanced-session/ground_patterns/active.json`. Ctrl+F10 alterna suelo anterior (incluida la tierra/grava PBR) y patrones nuevos. Inspector presenta «Suelo: Ardee», «Suelo: ladera» y «Suelo: hierba pedregosa», con sus imágenes actuales. La fila bajo los pies refleja el modo elegido. El modo pintado de F1 conserva su comportamiento.

El juego y el servidor no se iniciaron ni reiniciaron. No se añaden mallas, árboles ni colisiones. Fuentes del terreno, punteros de bosque, setas/piedras, agua, hiedra y caminos permanecen intactos. La prueba sustituye materiales en las mallas existentes. La integración definitiva en todas las zonas de Hibernia sigue pendiente de validación.

`work/activate_ground_patterns.py undo` en el espacio de trabajo recupera el puntero anterior, comprobando que nadie lo haya cambiado después. La ausencia del puntero devuelve LAB al controlador previo de caminos. Recursos y verificaciones se archivan localmente en `Remasters/graphics/zone207/ground-patterns-ardeeladeras-20261023`; no se envían a GitHub.

## Validación

Renderizador aislado con 1404 elementos de bosque y 82 setas. Cuatro vistas antes/después, unión de parcelas y borde de prueba. Igualdad de mallas y colisiones, comparación exacta con material previo, restauración, recarga y modo pintado comprobados. Compilación de LAB e Inspector y configuración del puntero activo correctas.

En la pasada final, las llamadas de dibujo fueron iguales por vista (895, 596, 812, 730). Promedios orientativos de 36 fotogramas, anterior/nuevo: Ardee 13,92/16,23 ms; ladera 14,54/14,19; pedregoso 14,68/16,10; panorámica 12,84/12,68. Son medidas breves del renderizador aislado, no una garantía de FPS durante el juego. El material nuevo tiene más muestreos y puede aumentar el coste gráfico.

Originales de ImageGen, prompts exactos, capturas y registros: `outputs/Suelos_Ardee_Laderas_20261023` del espacio de trabajo.
