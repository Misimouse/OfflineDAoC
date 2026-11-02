from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parent;D=R/'Reports/ui_integration';real=json.loads((D/'real_details.json').read_text(encoding='utf-8'));assert real['passed']
for kind in ['item','ability']:
 v=json.loads((D/('details_'+kind)/'visual_render.json').read_text(encoding='utf-8'));assert v['passed']
tests=json.loads((D/'regressions/acceptance.json').read_text(encoding='utf-8-sig'));assert all(v['passed'] for v in tests.values());native=sum(v['checks'] for v in tests.values())
gd=json.loads((D/'godot_tests.json').read_text(encoding='utf-8'));assert gd['passed']
a=R/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll';b=R/'GMCombatTest/NativeHost/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll';digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert digest(a)==digest(b)
text=f'''# Información de objetos y habilidades — 1 de noviembre de 2026

Instalado en el cliente habitual (Editor -game), continuando el panel clásico y las tres barras.

## Uso

- Clic derecho sobre el icono de un objeto del inventario/equipo o una habilidad/estilo/hechizo de las listas: abrir su información.
- Shift + clic derecho sobre un acceso de las barras: consultar información conservando el acceso. El clic derecho sin Shift sigue borrando el acceso.
- Shift+I consulta el objeto seleccionado. Esc o × cierra primero la información y deja abierto el panel principal.
- Ventana con texto original del servidor y desplazamiento para descripciones largas. Los clics dentro de la interfaz no seleccionan objetos del escenario ni giran la cámara.

## Comportamiento

Se usa el Detail original y su correspondencia original de tipos para objetos, habilidades, estilos y hechizos. La consulta no usa habilidades ni mueve objetos. Cada petición valida la identidad actual y conserva la respuesta bajo una clave que incluye la versión de la entrada. Si el objeto o la lista cambian, la información se invalida. Sin respuesta se indica que no se ha recibido información; no se inventan propiedades.

La ventana no recibe confirmaciones locales de daño, puntos o inventario. Los detalles técnicos que devuelve el servidor a un GM se conservan como parte del texto original. Esto no incorpora todavía el resto de ventanas auxiliares ni efectos/proyectiles de hechizos.

## Verificación

{gd['checks']} pruebas Godot y {native} nativas aprobadas, incluyendo inventario, combate, GM/chat/cámara, postura y equipo. Consulta real de training sword y Sprint aprobada, texto de ambas recibido, inventario intacto, cero órdenes de inventario, cero rechazos y cierre normal. Evidencia: Reports/ui_integration/real_details.json.

Cliente instalado renderizado con esas dos respuestas reales grabadas, en modo de solo lectura y sin cuenta conectada: details_item/Classic_character.png y details_ability/Classic_character.png. No confundir esa comprobación visual con otra sesión de juego en vivo. DLL instalada idéntica a la comprobada. WORK y sus mapas no se modificaron.

Copia previa: Backups/UIDetails_20261101. Fuentes principales: Godot/classic_ui_state.gd; UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private/DAoCBridgeClassicUI.cpp; DAoCBridgeInteraction.cpp evita clics a través de la UI.
'''
(R/'CHECKPOINT-UI-INFORMACION-20261101.md').write_text(text,encoding='utf-8')
update=f'\n\n## Información de objetos y habilidades instalada\n\nClic derecho en listas/inventario y Shift+clic derecho en barras consultan el Detail original del servidor. Ventana con desplazamiento; Esc cierra primero esa ventana. Identidad/versiones validadas y clics a través de la UI corregidos. {gd["checks"]} pruebas Godot y {native} nativas; espada y Sprint consultados realmente sin alterar inventario, cierre normal. Dos respuestas reales renderizadas con el cliente instalado en solo lectura. CHECKPOINT-UI-INFORMACION-20261101.md. WORK intacto; ventanas auxiliares y efectos de magia pendientes.\n'
for name in ['ESTADO-INTEGRACION.md','PAUSA-20261101.md']:
 p=R/name;p.write_text(p.read_text(encoding='utf-8')+update,encoding='utf-8')
(D/'details_installation.json').write_text(json.dumps({'installed':True,'native_checks':native,'godot_checks':gd['checks'],'sha256':digest(a),'real_details_passed':real['passed'],'rendered_real_responses':['item','ability'],'work_map_modified':False},indent=2),encoding='utf-8');print('Details installed, evidence and checkpoint verified')
