"""Server-confirmed logout, clean selection and same-connection reentry; disposable DB only."""
from qa_runtime import *
import sqlite3,subprocess,socket,time,hashlib,shutil,traceback

D=ROOT/'Reports/character_return';D.mkdir(exist_ok=True)
SOURCE=Path(os.environ.get('DAOC_BRIDGE_QA_GODOT',str(ROOT/'Godot')))
result={'passed':False,'real_protocol':True,'disposable_only':True,'checks':{},'errors':[]}
server=client=sock=None;logs=[];session='';snapshot={};buffer=b'';serial=0;backed=False
backup=ROOT/'Backups'/('CharacterReturnQA_'+time.strftime('%Y%m%d-%H%M%S'));backup.mkdir()
config=RUN/'bridge_config.json';config_bytes=config.read_bytes()
appearance_probe=os.environ.get('DAOC_BRIDGE_QA_APPEARANCE')=='1'
look_store=RUN/'appdata/Godot/app_userdata/MMOEngine/server_looks.json'
assert look_store.resolve().is_relative_to(RUN.resolve())
look_store_before=look_store.read_bytes() if appearance_probe and look_store.exists() else None
legacy_probe=appearance_probe and os.environ.get('DAOC_BRIDGE_QA_LEGACY_LOOK')=='1'
morph_catalog=os.environ.get('DAOC_BRIDGE_QA_MORPH_CATALOG','')
morph_probe=bool(morph_catalog)
native_catalog=RUN/'models.json'
native_catalog_before=native_catalog.read_bytes() if morph_probe and native_catalog.exists() else None
legacy_look={'face':15,'hair':15,'hair_color':15,'skin':15,'eyes':15,'sliders':[15,-1,4,8,12],'old_format':True}
def checked():
 db=sqlite3.connect(DB);db.row_factory=sqlite3.Row;assert db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0]==RUN.name;return db
def update(db,table,keyfield,key,values):db.execute('UPDATE '+table+' SET '+','.join('"'+k+'"=?' for k in values)+' WHERE "'+keyfield+'"=?',list(values.values())+[key])
def send(action,**values):
 global serial
 serial+=1;sock.sendall((json.dumps(dict(type='command',session=session,id='cloak:'+str(serial),action=action,**values))+'\n').encode())
def pump():
 global session,snapshot,buffer
 try:data=sock.recv(1048576)
 except socket.timeout:return
 if not data:raise RuntimeError('Private character bridge closed')
 buffer+=data
 while b'\n' in buffer:
  line,buffer=buffer.split(b'\n',1);v=json.loads(line)
  if v.get('type')=='hello':session=v['session']
  if v.get('type')=='snapshot':snapshot=v
def wait(test,label,seconds=30):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  pump()
  if test():return
 raise RuntimeError(label+'; inventory='+str(inv().get('feedback'))+'; flags='+str(gear()))
def settle(seconds=.8):
 end=time.monotonic()+seconds
 while time.monotonic()<end:pump()
def inv():return snapshot.get('inventory',{})
def gear():return inv().get('gear',{})
def item(slot):return next((i for i in inv().get('items',[]) if i['slot']==slot),None)
try:
 if legacy_probe:
  store=json.loads(look_store_before) if look_store_before else {}
  store['Codexdruid']=legacy_look;look_store.parent.mkdir(parents=True,exist_ok=True)
  look_store.write_text(json.dumps(store),encoding='utf-8')
 for port in [10351,19737]:
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=.2):raise RuntimeError('Private QA port already occupied')
  except (ConnectionRefusedError,socket.timeout):pass
 with checked() as db:
  dest=sqlite3.connect(backup/'before.sqlite3.db');db.backup(dest);dest.close();backed=True
  char=db.execute("SELECT * FROM DOLCharacters WHERE Name='Codexdruid'").fetchone();assert char
  update(db,'Account','Name',char['AccountName'],{'PrivLevel':3,'Realm':3})
  update(db,'DOLCharacters','DOLCharacters_ID',char['DOLCharacters_ID'],{'Class':53,'Level':1,'Experience':0,'SerializedSpecs':'','Health':10})
 if morph_probe:
  candidate=Path(morph_catalog).resolve();assert candidate.is_relative_to(ROOT.resolve())
  models=json.loads(candidate.read_text(encoding='utf-8-sig'))
  assert all(models.get(str(mid),{}).get('type')=='skeletal' for mid in (1883,1884,1885))
  assert native_catalog.resolve().is_relative_to(RUN.resolve())
  native_catalog.write_text(json.dumps(models),encoding='utf-8')
 cfg=json.loads(config_bytes);cfg['initial_spawn_m']=[(char['Xpos']-35*8192)*.025,char['Zpos']*.025,(char['Ypos']-51*8192)*.025];config.write_text(json.dumps(cfg),encoding='utf-8')
 for p in SOURCE.glob('*.gd'):shutil.copy2(p,RUN/'Godot'/p.name)
 if morph_probe:
  trace=RUN/'Godot/live_gateway.gd';text=trace.read_text(encoding='utf-8-sig')
  text=text.replace('func world_event(kind:String,data:Dictionary)->void:\n','func world_event(kind:String,data:Dictionary)->void:\n    if kind in ["you","region_changed","quit","model_change"]:print("QA_MODEL_PACKET "+kind+" "+JSON.stringify(data))\n')
  trace.write_text(text,encoding='utf-8')
 p=RUN/'Godot/visual_bridge.gd';p.write_text(p.read_text(encoding='utf-8-sig').replace('port: int = 19727','port: int = 19737'),encoding='utf-8')
 log=(D/'character_return_server.log').open('w',encoding='utf-8');logs.append(log)
 server=subprocess.Popen([str(dotnet),str(SERVER/'CoreServer.dll'),'--start'],cwd=SERVER,env=env,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
 end=time.monotonic()+40
 while time.monotonic()<end:
  try:
   with socket.create_connection(('127.0.0.1',10351),timeout=.2):break
  except OSError:time.sleep(.2)
 else:raise RuntimeError('Private QA server unavailable')
 game=INSTALL/'new-client';sdk=ENGINE/'Binaries/ThirdParty/DotNet/10.0/win-x64'
 account='codexqa'+hashlib.sha256(RUN.name.encode()).hexdigest()[:10];password=hashlib.sha256(('disposable-local-protocol-qa:'+RUN.name).encode()).hexdigest()[:24]
 ce=dict(env,DOTNET_ROOT=str(sdk),DOTNET_ROOT_X64=str(sdk),PATH=str(sdk)+os.pathsep+env['PATH'])
 (RUN/'Reports/live/logout.request').unlink(missing_ok=True)
 log=(D/'character_return_client.log').open('w',encoding='utf-8');logs.append(log)
 client=subprocess.Popen([str(game/'tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),'--headless','--path',str(RUN/'LobbyProject'),'--script',str(RUN/'Godot/gateway_main.gd'),'--','--server=127.0.0.1','--server-port=10351','--account='+account,'--password='+password,'--no-world','--bridge-character=Codexdruid'],cwd=RUN,env=ce,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 end=time.monotonic()+50
 while time.monotonic()<end:
  try:sock=socket.create_connection(('127.0.0.1',19737),timeout=.3);sock.settimeout(.1);break
  except OSError:time.sleep(.2)
 else:raise RuntimeError('Private character bridge unavailable')
 wait(lambda:snapshot.get('classic_ui',{}).get('skills_ready') and snapshot.get('player_status',{}).get('ready'),'Initial Naturalist world ready');settle(2)
 send('chat',text='/quit')
 wait(lambda:not snapshot.get('in_game') and snapshot.get('character_lobby',{}).get('ready'),'Saved quit returns selection',45)
 lobby=snapshot['character_lobby'];assert lobby['enabled'] and lobby['characters']
 result['checks']['quit_stays_connected']=True;result['roster_classes']=[dict(name=c['name'],class_name=c['class_name'],level=c['level']) for c in lobby['characters']]
 assert not snapshot.get('entities');result['checks']['old_world_cleared']=True
 if appearance_probe:
  selected=next(c for c in lobby['characters'] if c['name']=='Codexdruid');prefix=selected['prefix'];assert prefix in ['cel_m','cel_f','elf_m','elf_f','fir_m','fir_f','lur_m','lur_f','syl_m','syl_f']
  if legacy_probe:
   assert selected['look']['sliders']==[8,0,4,8] and 'old_format' not in selected['look']
   assert json.loads(look_store.read_text())['Codexdruid']==legacy_look
   result['checks']['legacy_editable_without_store_rewrite']=True
  meta=json.loads((INSTALL/'new-client/godot/content/characters/races'/prefix/'figure.json').read_text())
  expected={'size':2,'face':min(1,max(0,len(meta.get('faces',[]))-1)),'eyes':min(1,max(0,len(meta.get('eyes',[]))-1)),'skin':min(3,max(0,len(meta.get('skin_tones',[]))-1)),'hair':0,'hair_color':0,'tattoo':0,'sliders':[8 if i%2==0 else 0 for i in range(len(meta.get('sliders',[])))]}
  send('character_customize',name='Codexdruid',look=expected,lobby_revision=lobby['revision'])
  wait(lambda:any(c['name']=='Codexdruid' and c.get('look')==expected for c in snapshot.get('character_lobby',{}).get('characters',[])),'Original customization save updates selected roster',20)
  assert look_store.exists() and json.loads(look_store.read_text())['Codexdruid']==expected
  result['checks']['original_appearance_store_written']=True;lobby=snapshot['character_lobby']
 send('character_enter',name='Codexdruid',lobby_revision=lobby['revision'])
 wait(lambda:snapshot.get('in_game') and snapshot.get('player_status',{}).get('ready') and snapshot.get('classic_ui',{}).get('skills_ready'),'Re-enter from same character screen',30)
 result['checks']['same_connection_reentry']=True
 if appearance_probe:
  wait(lambda:any(e.get('id')=='player:local' and e.get('look')==expected for e in snapshot.get('entities',[])),'Chosen appearance reaches local world snapshot',20)
  result['checks']['chosen_appearance_reaches_world']=True
 if morph_probe:
  def local_player():return next((e for e in snapshot.get('entities',[]) if e.get('id')=='player:local'),{})
  original=dict(local_player());assert original and not original.get('morphed')
  base_model=original['model_id'];original_look=original.get('look',{})
  restore_model=int(char['CreationModel']) & 0x7fff
  assert restore_model>0
  morph_results=[]
  # The headless probe has no native pawn to send its initial position update.
  send('move',position_m=original['position_m'],forward_xz=original['forward_xz'],speed_mps=0)
  settle(2)
  send('target_self');settle(.3)
  for model in (1883,1884,1885):
   send('chat',text='/player model change '+str(model))
   wait(lambda:local_player().get('morphed') and local_player().get('model_id')==model,'Original server ModelChange reaches native form '+str(model),20)
   assert local_player().get('look',{})==original_look
   assert not local_player().get('missing_morph_model')
   morph_results.append(dict(model=model,source_model=local_player().get('source_model'),size=local_player().get('size')))
   send('chat',text='/player model reset')
   wait(lambda:not local_player().get('morphed') and local_player().get('model_id')==base_model,'Original server ModelChange restores equipped figure',20)
   assert local_player().get('look',{})==original_look
  result['morphs']=morph_results
  result['model_change_command']='original /player model change and reset; disposable DB restored'
  result['checks']['server_model_changes_and_equipped_return']=True
  result['checks']['appearance_preserved_across_morphs']=True
 (D/'returned_snapshot.json').write_text(json.dumps(snapshot),encoding='utf-8');result['passed']=True
 if appearance_probe:
  send('chat',text='/quit');wait(lambda:not snapshot.get('in_game') and snapshot.get('character_lobby',{}).get('ready'),'Second saved return before client restart',45)
  send('logout');client.wait(timeout=45);assert client.returncode==0
  sock.close();sock=None;buffer=b'';snapshot={};session='';serial=0
  (RUN/'Reports/live/logout.request').unlink(missing_ok=True)
  log=(D/'character_reopen_client.log').open('w',encoding='utf-8');logs.append(log)
  client=subprocess.Popen([str(game/'tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),'--headless','--path',str(RUN/'LobbyProject'),'--script',str(RUN/'Godot/gateway_main.gd'),'--','--server=127.0.0.1','--server-port=10351','--account='+account,'--password='+password,'--no-world','--bridge-character-menu'],cwd=RUN,env=ce,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  end=time.monotonic()+50
  while time.monotonic()<end:
   try:sock=socket.create_connection(('127.0.0.1',19737),timeout=.3);sock.settimeout(.1);break
   except OSError:time.sleep(.2)
  else:raise RuntimeError('Reopened private character bridge unavailable')
  wait(lambda:snapshot.get('character_lobby',{}).get('ready'),'Fresh client reloads original roster',45)
  assert any(c['name']=='Codexdruid' and c.get('look')==expected for c in snapshot['character_lobby']['characters'])
  result['checks']['appearance_reloaded_by_fresh_client']=True

except Exception:
 result['errors'].append(traceback.format_exc());(D/'character_return_failed.json').write_text(json.dumps(snapshot),encoding='utf-8')
finally:
 if sock and session:
  try:send('logout')
  except OSError:pass
 if client and client.poll() is None:
  (RUN/'Reports/live/logout.request').write_text('logout',encoding='utf-8')
  try:client.wait(timeout=90)
  except subprocess.TimeoutExpired:client.kill();client.wait();result['errors'].append('Private character client forced stop')
 if sock:sock.close()
 if server and server.poll() is None:
  server.stdin.write('exit\n');server.stdin.flush()
  try:server.wait(timeout=45)
  except subprocess.TimeoutExpired:server.kill();server.wait();result['errors'].append('Private server forced stop')
 for log in logs:log.close()
 if appearance_probe:
  assert look_store.resolve().is_relative_to(RUN.resolve())
  if look_store_before is None:look_store.unlink(missing_ok=True)
  else:look_store.write_bytes(look_store_before)
  result['appearance_profile_restored']=True
 if morph_probe:
  assert native_catalog.resolve().is_relative_to(RUN.resolve())
  if native_catalog_before is None:native_catalog.unlink(missing_ok=True)
  else:native_catalog.write_bytes(native_catalog_before)
  result['qa_native_catalogue_restored']=True
 if backed:
  assert DB.is_relative_to(RUN) and RUN.is_relative_to(ROOT/'ProtocolQA')
  with checked() as dst:
   src=sqlite3.connect(backup/'before.sqlite3.db');src.backup(dst);src.close()
  config.write_bytes(config_bytes);result['database_restored']=True
 result['normal_shutdown']=bool(client and server and client.returncode==0 and server.returncode==0)
 result['passed']=result['passed'] and result['normal_shutdown'] and not result['errors']
 (D/'quit_protocol.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result));assert result['passed']
