from pathlib import Path
import json,hashlib,shutil
R=Path(__file__).resolve().parent;D=R/'Reports/spell_casting';live=json.loads((D/'native_live_spell_verification.json').read_text(encoding='utf-8'));assert live['passed'] and live['cast_while_moving_blocked'] and live['movement_interrupted'] and live['facing_away_rejected'] and live['damage_applied'] and live['native_exit']==0
assert live['line_of_sight']['near_replies']==0 and live['line_of_sight']['timeouts']==0
checks=json.loads((R/'Reports/ui_integration/regressions/acceptance.json').read_text(encoding='utf-8'));assert all(v['passed'] for v in checks.values()) and checks['classic']['checks']==56
native=sum(v['checks'] for v in checks.values());gd=0
for p in [R/'Reports/ui_integration/godot_tests.json',D/'godot_tests.json',D/'sight_tests.json',D/'heading_tests.json']:
 v=json.loads(p.read_text(encoding='utf-8'));assert v['passed'];gd+=v['checks']
source=R/'GMCombatTest/NativeHost/Plugins/DAoCVisualBridge';target=R/'Client/Plugins/DAoCVisualBridge'
for name in ['Source','Binaries']:shutil.copytree(source/name,target/name,dirs_exist_ok=True)
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();dll='Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll';assert h(source/dll)==h(target/dll)
text=f'''# Magia, movimiento y línea de visión — 2 de noviembre de 2026

## Instalado en nuestro cliente habitual

- Lanzamiento desde las listas/barras mediante UseSpell/UseSkill originales y los IDs reales de línea/nivel. Sin habilidades concedidas ni daño/maná local.
- Preparación confirmada por SpellCastAnimation, duración original en décimas de segundo, barra y animaciones originales de inicio/medio/final elegidas por SpellFx. Interrupt detiene la preparación; la expiración sin respuesta no inventa un acierto. Los instantáneos no ganan una preparación ficticia. Muerte, retirada y cambio de zona limpian el estado.
- Rumbo corregido: el adaptador de postura de las barras olvidaba los180° de la conversión de brújula de Godot. Ahora el rumbo enviado coincide con el real; prueba contra Server.heading_of original en diez orientaciones.
- La magia normal no se completa caminando; moverse durante la preparación la interrumpe. El puente no prohíbe por su cuenta todas las habilidades móviles: las excepciones por instrumento/MoveCast siguen en el servidor. No se ha ensayado todavía un personaje con esas excepciones.
- CheckLOSRequest/LosReply originales conectados a las colisiones de UE5. Tres alturas, exclusión de los propios cuerpos, correlación de consulta/token, prevención de duplicados y respuestas caducadas. No se concede visibilidad si faltan actores o no llega respuesta.
- A petición del propietario se eliminó la excepción original que declaraba visible todo objetivo a seis metros o menos: una pared bloquea también estando cerca. Tanto las consultas del servidor como los indicadores de visibilidad del cliente usan geometría. Una prueba anterior que esperaba atravesar paredes a seis metros se actualizó para exigir bloqueo.
- Orientación, detección, alcance, recursos y reglas concretas del hechizo continúan bajo autoridad del servidor.

## Prueba real con UE5 conectado

Personaje existente BridgeCaster, Magician1. Se probaron Lesser Powerward y Gleam Ray desde una barra real. El controlador de prueba usa los mismos comandos del cliente; el observador UE5 responde las consultas de visibilidad con la geometría de Ardee. El transporte de prueba solo reenvía esas respuestas/ping desde el observador y no inventa resultados de hechizos.

Solicitud mientras camina: no completa el hechizo ni aplica buff; comenzar quieto y moverse produce interrupción. Lesser Powerward completado consume maná25→23 y aplica/renueva su icono de20minutos y estado de armadura. Objetivo de espaldas rechazado; al orientarse con una línea despejada, Gleam Ray hizo6de daño a una large frog y su vida pasó100→80%.

UE5 contestó siete consultas reales de visibilidad, sin respuestas por proximidad, vencimientos ni rechazos. Inventario intacto, cero órdenes de inventario, barras anteriores restauradas, posición/protección GM restauradas y cierre normal de ambos procesos. No se editaron cuenta, puntos, saldo ni DB.

Evidencia principal: Reports/spell_casting/native_live_spell_verification.json y native_live_spell_trace.json. Capturas Spell_4101_casting.png y Spell_4301_released.png revisadas. Una reproducción anterior, sin cuenta conectada, verificó las seis animaciones originales cast_1h_circ_start/mid/end y cast_z_start/mid/end; no confundir esa reproducción con la sesión final en vivo.

## Comprobaciones y límites

{gd} comprobaciones Godot y {native} nativas aprobadas. Incluyen colisiones reales de prueba: pared entre actores a10m y a4–6m, un rayo libre, ausencia de actores, identidad/caducidad de respuestas, estado local, inventario, combate, GM/chat/cámara, postura/muerte y equipo. La prueba de pared usa geometría temporal del banco de pruebas, no afirma haber recorrido cada puerta/edificio de Ardee.

La sesión final también valida por primera vez un buff real para la franja de efectos del bloque anterior, que solo tenía comprobación visual con datos simulados.

Partículas, proyectiles, sonidos de magia y modernización visual de efectos siguen pendientes. No se certifican todas las clases/curas/RA/concentración/cantos ni todos los casos de distancia y geometría. Solo Connacht207; la variante actualizada es Editor -game, no un paquete Shipping nuevo. WORK no se ha enlazado ni modificado.

## Para probar

Abrir INICIAR-ARDEE-MAGIA.cmd (BridgeCaster). El CMD habitual sigue abriendo BridgeFighter. Abrir M y arrastrar Lesser Powerward/Gleam Ray a huecos de las barras. Si está oculto como GM, Enter → /gmstealth off → Enter permite probar visible conservando los permisos/protección GM. F6 se reserva para recibir combate real; F1 restaura protección y ocultación.

Sin objetivo, probar Lesser Powerward quieto y luego moverse para comprobar la interrupción. Para Gleam Ray, elegir un mob visible, ponerse de frente y dentro de alcance. Girarse o situarse tras una pared debe impedir la ejecución. Los mensajes del servidor aparecen en el chat. Salir con Esc hasta que termine de guardar.

Copia previa: Backups/SpellCasting_20261102. Fuentes principales: Godot/spell_cast_state.gd, line_of_sight.gd, ui_player_pose.gd y live_gateway.gd; DAoCBridgeAnimation.cpp, DAoCBridgeClassicUI.cpp y DAoCBridgeSpellSight.cpp.
'''
(R/'CHECKPOINT-MAGIA-Y-VISIBILIDAD-20261102.md').write_text(text,encoding='utf-8')
update=f'\n\n## 2 de noviembre — magia y visibilidad instaladas\n\nMagician existente BridgeCaster probado con UE5 conectado: magia normal no se completa moviéndose, se interrumpe al moverse, Lesser Powerward aplica buff real y consume maná, Gleam Ray causa6de daño, orientación incorrecta rechazada. CheckLOS original conectado a geometría UE5 sin excepción de proximidad; siete respuestas reales sin vencimientos/rechazos. Animaciones originales y barra conectadas; rumbo de barras corregido180°. {gd} pruebas Godot y {native} nativas aprobadas. Inventario/barras conservados y cierre normal. Nuevo INICIAR-ARDEE-MAGIA.cmd, arranque habitual intacto. CHECKPOINT-MAGIA-Y-VISIBILIDAD-20261102.md recoge evidencia y límites. Partículas/proyectiles/sonidos y cobertura de todas las clases siguen pendientes. WORK sin enlazar ni modificar.\n'
for name in ['ESTADO-INTEGRACION.md','PAUSA-20261101.md']:
 p=R/name;p.write_text(p.read_text(encoding='utf-8')+update,encoding='utf-8')
(D/'installation.json').write_text(json.dumps({'installed':True,'godot_checks':gd,'native_checks':native,'sha256':h(target/dll),'live_native_passed':live['passed'],'movement_restriction_passed':live['cast_while_moving_blocked'],'facing_restriction_passed':live['facing_away_rejected'],'geometry_queries':live['line_of_sight'],'work_linked':False},indent=2),encoding='utf-8');print('Magic and strict sight installed; evidence, hashes and checkpoint verified')
