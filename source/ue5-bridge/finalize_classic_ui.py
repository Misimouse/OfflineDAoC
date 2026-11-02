from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parent;D=R/'Reports/ui_integration'
result=json.loads((D/'installed_live.json').read_text(encoding='utf-8'));assert result['passed'],result
text='''# UI de Godot integrada en UE5 — 1 de noviembre de 2026

Instalado en el cliente habitual (UnrealEditor -game). Esta actualización sustituye la nota anterior de «localizado, no migrado».

## Disponible

- Panel original con seis pestañas: personaje, inventario/equipo, habilidades, estilos, magia y grupo. Gráficos clásicos, iconos y fuente originales; datos recibidos del servidor.
- Personaje: nivel, puntos, estadísticas, resistencias y valores de armas. Inventario: 19 posiciones de equipo, cinco bolsas, monedas/peso y figura equipada real.
- Tres barras, diez páginas de diez huecos por barra. Arrastrar habilidades/objetos a las barras; mover accesos; clic derecho o arrastre fuera para borrar el acceso. Doble clic en la lista solicita usar la habilidad. La asignación no concede habilidades ni altera objetos.
- Teclas: P personaje, I inventario, H habilidades, J estilos, M magia, G grupo. 1–0 primera barra, Alt+1–0 segunda, Ctrl+1–0 tercera. Shift+1–0 cambia página de la primera barra. Flechas de cada barra cambian su página; ↔ cambia orientación. Arrastre por la esquina superior izquierda mueve ventanas/barras.
- Distribución y accesos guardados por personaje. Lectura inicial compatible con las barras originales; el archivo original de Godot no se sobrescribe.
- Validación de identidad/revisión del objeto, listas completas del servidor, estado muerto, región y tiempos de reutilización. Sin cambios anticipados de inventario, estadísticas o resultados de habilidades.

## Comprobación

29 comprobaciones Godot y 199 nativas de interfaz, inventario, combate, GM, chat, cámara, postura y equipo. Las 31 específicas de UI se repitieron tras los últimos ajustes. Capturas renderizadas de las seis pestañas con datos reales revisadas. Prueba real de Sprint: respuesta del servidor «You prepare to sprint!»; protección GM y accesos anteriores restaurados, inventario intacto y salida normal.

Prueba final con el cliente instalado: seis pestañas y tres barras visibles, seis capturas nuevas, sin órdenes de inventario ni rechazos del puente, cierre normal. Evidencia: Reports/ui_integration/installed_live.json y installed_*.png. La prueba automática usa una distribución separada para conservar las preferencias del usuario.

## Para probar

Entrar con el CMD habitual. Abrir I y comprobar equipo/bolsas/figura; abrir P y H. Arrastrar Sprint a un hueco vacío y activarlo con su número o clic. Usar las flechas para cambiar página; salir con Esc y entrar otra vez para comprobar persistencia. No todos los personajes tienen estilos/hechizos: las pestañas muestran solo lo que recibe realmente el personaje.

## Límites

Esto integra el panel principal y las barras; no acredita toda la UI de Godot al 100 %. Opciones completas, diario, ventanas especializadas y acciones completas de grupo siguen pendientes; conversación/comercio conservan su integración previa. Los efectos visuales/proyectiles y todas las clases/hechizos requieren trabajo y pruebas posteriores. No se ha modificado el mapa ni el editor de WORK. Instalación final en la variante habitual Editor; no se ha actualizado en este bloque un paquete Shipping independiente.

Copia previa del módulo: Backups/ClassicUI_20261101. Fuentes: Godot/classic_ui_state.gd, Godot/ui_player_pose.gd y UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeClassicUI.cpp.
'''
(R/'CHECKPOINT-UI-CLASICA-20261101.md').write_text(text,encoding='utf-8')
update='\n\n## UI clásica instalada y comprobada\n\nPanel principal de seis pestañas y tres barras integrado con datos reales, gráficos/fuente/iconos originales, equipo/figura, arrastre y persistencia por personaje. 29 pruebas Godot,199 nativas; Sprint confirmado por servidor y prueba final renderizada del cliente instalado con las seis pestañas, tres barras, cero órdenes de inventario, cero rechazos y cierre normal. Ver CHECKPOINT-UI-CLASICA-20261101.md para controles, evidencia y límites. Esta actualización prevalece sobre la nota anterior «localizado, no migrado». Ventanas auxiliares y efectos de habilidades siguen pendientes. WORK intacto.\n'
for name in ['ESTADO-INTEGRACION.md','PAUSA-20261101.md']:
 p=R/name;p.write_text(p.read_text(encoding='utf-8')+update,encoding='utf-8')
paths=[R/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll',R/'GMCombatTest/NativeHost/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll']
h=[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths];assert h[0]==h[1]
(D/'installation.json').write_text(json.dumps({'installed':True,'sha256':h[0],'installed_live':result,'work_map_modified':False},indent=2),encoding='utf-8')
print('Checkpoint and installation hashes verified')
