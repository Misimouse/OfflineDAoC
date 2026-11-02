from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parent;D=R/'Reports/ui_integration';g=json.loads((D/'godot_tests.json').read_text(encoding='utf-8'));n=json.loads((D/'fixture.json.native.json').read_text(encoding='utf-8-sig'));live=json.loads((D/'real_effects_verification.json').read_text(encoding='utf-8'));visual=json.loads((D/'effects_render/visual_render.json').read_text(encoding='utf-8'));assert g['passed'] and n['passed'] and live['passed'] and visual['passed']
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert h(R/'Launcher/Program.cs')==h(R/'Backups/WorkHandoff_20261102/Program.cs')
dll=R/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll';candidate=R/'GMCombatTest/NativeHost/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll';assert h(dll)==h(candidate)
text=f'''# Efectos activos — 2 de noviembre de 2026

## Aclaración de alcance

El propietario aclaró que «adelante» significaba continuar las funciones del juego, no enlazar ahora el trabajo con WORK. No se ha instalado ningún plugin en DAoC-Enhanced-Unreal, ni modificado su proyecto/mapas/configuración. La preparación de traspaso se apartó en Backups/WorkHandoff_20261102. Launcher/Program.cs se restauró exactamente desde su copia y se recompiló correctamente. Integration/ESTADO.txt deja constancia de que el traspaso no está activo.

## Instalado en nuestro cliente

Franja de iconos de buffs/debuffs recibidos del servidor, con atlas/bordes originales. Los efectos negativos llevan marco rojo. Duración restante debajo del icono; los permanentes no muestran tiempo. Las renovaciones sustituyen la identidad anterior y las retiradas del servidor eliminan el icono. El reloj se actualiza sin reconstruir el catálogo por cada tick; llegar a cero no inventa una retirada del servidor.

Clic derecho en un icono solicita su descripción mediante Detail tipo5 e ID de efecto original, no el índice de su posición ni una habilidad. Los efectos no se pueden arrastrar a las barras ni ejecutar como acciones. La franja vacía se oculta y no intercepta cámara/selección; solo los iconos capturan el puntero. La información se invalida si cambia el efecto mientras se consulta.

Esto representa el estado y la información de los efectos. No implementa partículas, proyectiles ni todos los efectos visuales de lanzamiento.

## Comprobación y límites

{g['checks']} comprobaciones Godot y {n['checks']} nativas aprobadas, incluyendo temporales/permanentes, clasificación negativa, renovación/retirada, consulta original e interacción de widgets. Son comprobaciones con datos simulados; no se otorgaron buffs a una cuenta.

Prueba real: campos de efectos recibidos, Sprint activado y detenido con respuesta original, accesos restaurados, inventario intacto, cero órdenes de inventario, cero rechazos y cierre normal. Este personaje tenía cero efectos activos, por lo que no se afirma haber comprobado un buff temporizado real. Evidencia: Reports/ui_integration/real_effects_verification.json.

Cliente instalado renderizado con dos efectos simulados sobre una captura de estado real, en escena ligera y sin cuenta conectada; captura effects_render/Classic_character.png revisada. DLL instalada idéntica a la probada. Copia previa: Backups/ActiveEffects_20261102.

Para probar: cuando el servidor aplique un buff/debuff debe aparecer arriba a la izquierda. Clic derecho muestra su información; Esc cierra esa ventana. Sin efectos activos la franja permanece oculta. WORK sigue separado hasta que el propietario solicite expresamente el traspaso.
'''
(R/'CHECKPOINT-EFECTOS-ACTIVOS-20261102.md').write_text(text,encoding='utf-8')
update=f'\n\n## 2 de noviembre — efectos activos y alcance\n\nEl propietario aclaró que no solicita enlazar WORK ahora; preparación apartada y lanzador restaurado. No se ha modificado el proyecto de WORK. Continuación funcional: iconos de buffs/debuffs, duración, permanentes sin reloj y consulta Detail5 instalados en nuestro cliente. {g["checks"]} pruebas Godot y {n["checks"]} nativas aprobadas; sesión real con efectos vacíos y Sprint conservado, inventario intacto, cierre normal. Aparición/renovación/retirada e imagen comprobadas con datos simulados, no con un buff real concedido al personaje. CHECKPOINT-EFECTOS-ACTIVOS-20261102.md. Partículas/proyectiles y otras ventanas auxiliares siguen pendientes.\n'
for name in ['ESTADO-INTEGRACION.md','PAUSA-20261101.md']:
 p=R/name;p.write_text(p.read_text(encoding='utf-8')+update,encoding='utf-8')
(D/'effects_installation.json').write_text(json.dumps({'installed':True,'godot_checks':g['checks'],'native_checks':n['checks'],'sha256':h(dll),'real_session_passed':live['passed'],'real_timed_buff_tested':False,'visual_fixture_passed':visual['passed'],'work_linked':False,'launcher_source_restored':True},indent=2),encoding='utf-8');print('Effects installed and verified; WORK remains unchanged')
