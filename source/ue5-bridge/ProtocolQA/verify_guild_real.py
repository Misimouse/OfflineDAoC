from qa_runtime import *
import sqlite3,subprocess,socket,time,hashlib,shutil,traceback

restricted=os.environ.get('DAOC_GUILD_QA_RESTRICTED')=='1'
D=ROOT/'GuildWindowLab/RealProtocol'/time.strftime('%Y%m%d-%H%M%S');D.mkdir(parents=True)
SOURCE=Path(os.environ.get('DAOC_BRIDGE_QA_SOURCE',str(ROOT/'Godot')))
assert (SOURCE/'guild_state.gd').exists()
result={'passed':False,'real_protocol':True,'disposable_only':True,'checks':{},'errors':[],'restricted_member':restricted,'source_inputs':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCE.glob('*.gd')}}
server=client=sock=None;logs=[];session='';snapshot={};buffer=b'';serial=0;backed=False
normal_targets=[Path(r['target']) for r in json.loads((ROOT/'ExpansionRaceLab/CentralDelivery/MinotaurActivation/installed.json').read_text())['files'] if Path(r['target']).name in ['GameServer.dll','CoreBase.dll','CoreDatabase.dll','live_gateway.gd']] + [ROOT/'Godot/visual_bridge.gd',ROOT/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll']
normal_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in normal_targets}
candidate_files=[]
backup=ROOT/'Backups'/('GuildProtocolQA_'+time.strftime('%Y%m%d-%H%M%S'));backup.mkdir()
config=RUN/'bridge_config.json';config_bytes=config.read_bytes()
def checked():
 db=sqlite3.connect(DB);db.row_factory=sqlite3.Row;assert db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0]==RUN.name;return db
def update(db,table,keyfield,key,values):db.execute('UPDATE '+table+' SET '+','.join('"'+k+'"=?' for k in values)+' WHERE "'+keyfield+'"=?',list(values.values())+[key])
def send(action,**values):
 global serial
 serial+=1;sock.sendall((json.dumps(dict(type='command',session=session,id='guild:'+str(serial),action=action,**values))+'\n').encode())
def pump():
 global session,snapshot,buffer
 try:data=sock.recv(1048576)
 except socket.timeout:return
 if not data:raise RuntimeError('Private cloak bridge closed')
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
 raise RuntimeError(label+'; guild='+repr(guild()))
def settle(seconds=.8):
 end=time.monotonic()+seconds
 while time.monotonic()<end:pump()
def guild():return snapshot.get('guild',{})
def inv():return snapshot.get('inventory',{})
def gear():return inv().get('gear',{})
def item(slot):return next((i for i in inv().get('items',[]) if i['slot']==slot),None)
try:
 for port in [10351,19737]:
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=.2):raise RuntimeError('Private QA port already occupied')
  except (ConnectionRefusedError,socket.timeout):pass
 with checked() as db:
  dest=sqlite3.connect(backup/'before.sqlite3.db');db.backup(dest);dest.close();backed=True
  char=db.execute("SELECT * FROM DOLCharacters WHERE Name='Codexdruid'").fetchone();assert char
  update(db,'Account','Name',char['AccountName'],{'PrivLevel':1,'Realm':3})
  template=dict(db.execute('SELECT * FROM Guild LIMIT 1').fetchone());template.update(GuildID='codex-private-guild',Guild_ID='codex-private-guild',GuildName='Codex Private Guild',Realm=3,AllianceID='',Motd='Private QA MOTD',IsStartingGuild=0)
  def insert(table,row):db.execute('INSERT INTO '+table+' ('+','.join('"'+k+'"' for k in row)+') VALUES ('+','.join('?' for k in row)+')',list(row.values()))
  insert('Guild',template)
  rank_template=dict(db.execute('SELECT * FROM GuildRank LIMIT 1').fetchone())
  for rank in range(10):
   row=dict(rank_template);row.update(GuildID='codex-private-guild',GuildRank_ID='codex-private-rank-'+str(rank),RankLevel=rank,Title='Private Rank '+str(rank))
   for key in ['Promote','Remove','Invite','View']:row[key]=1 if rank==0 or key=='View' else 0
   insert('GuildRank',row)
  update(db,'DOLCharacters','DOLCharacters_ID',char['DOLCharacters_ID'],{'GuildID':'codex-private-guild','GuildRank':9 if restricted else 0,'GuildNote':'Guard, west gate'})
  friend=dict(db.execute("SELECT * FROM DOLCharacters WHERE Name='Codexfriend'").fetchone());assert friend
  for i,suffix in enumerate('ABCDEFGHIJK'):
   row=dict(friend);row.update(DOLCharacters_ID='codex-private-member-'+suffix,Name='Qaguild'+suffix.lower(),GuildID='codex-private-guild',GuildRank=8,GuildNote='Offline, test '+suffix)
   insert('DOLCharacters',row)
 cfg=json.loads(config_bytes);cfg['initial_spawn_m']=[(char['Xpos']-35*8192)*.025,char['Zpos']*.025,(char['Ypos']-51*8192)*.025];config.write_text(json.dumps(cfg),encoding='utf-8')
 for p in SOURCE.glob('*.gd'):shutil.copy2(p,RUN/'Godot'/p.name)
 p=RUN/'Godot/visual_bridge.gd';p.write_text(p.read_text(encoding='utf-8-sig').replace('port: int = 19727','port: int = 19737'),encoding='utf-8')
 candidate_root=ROOT/'GuildWindowLab/ServerCandidate';candidate=json.loads((candidate_root/'build_receipt.json').read_text());assert candidate['passed'] and 'guild_roster_cache' in candidate['candidate_features']
 for folder in [SERVER,SERVER/'lib',SERVER/'win-x64']:
  for name,expected in candidate['binaries_sha256'].items():
   target=folder/name
   if not target.exists():continue
   assert target.resolve().is_relative_to(RUN)
   origin=Path(candidate['libraries'])/name;assert hashlib.sha256(origin.read_bytes()).hexdigest()==expected
   saved=backup/('server_'+str(len(candidate_files))+'_'+name);shutil.copy2(target,saved);candidate_files.append((target,saved));shutil.copy2(origin,target)
 result['candidate_server_build_sha256']=hashlib.sha256((candidate_root/'build_receipt.json').read_bytes()).hexdigest()
 log=(D/'server.log').open('w',encoding='utf-8');logs.append(log)
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
 log=(D/'client.log').open('w',encoding='utf-8');logs.append(log)
 client=subprocess.Popen([str(game/'tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),'--headless','--path',str(RUN/'LobbyProject'),'--script',str(RUN/'Godot/gateway_main.gd'),'--','--server=127.0.0.1','--server-port=10351','--account='+account,'--password='+password,'--no-world','--bridge-character=Codexdruid'],cwd=RUN,env=ce,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 end=time.monotonic()+50
 while time.monotonic()<end:
  try:sock=socket.create_connection(('127.0.0.1',19737),timeout=.3);sock.settimeout(.1);break
  except OSError:time.sleep(.2)
 else:raise RuntimeError('Private cloak bridge unavailable')
 wait(lambda:snapshot.get('classic_ui',{}).get('skills_ready') and snapshot.get('classic_ui',{}).get('info',{}).get('guild')=='Codex Private Guild','Private guild character ready')
 send('guild_open',open=True)
 wait(lambda:guild().get('visible') and not guild().get('pending') and len(guild().get('members',[]))==1,'Original online roster packet')
 result['checks']['online_roster']=guild()['members'][0]['name']=='Codexdruid'
 settle(.65);send('guild_refresh',guild_token=guild()['token'],show_offline=True)
 wait(lambda:not guild().get('pending') and guild().get('total')==12 and len(guild().get('members',[]))==10,'Original offline members and page one')
 result['checks']['quoted_note_and_offline']=any(m['note']=='Guard, west gate' for m in guild()['members']) and any(not m['online'] and m['note'].startswith('Offline, test') for m in guild()['members'])
 settle(.65);send('guild_refresh',guild_token=guild()['token'],page=2)
 wait(lambda:not guild().get('pending') and guild().get('page')==2 and len(guild().get('members',[]))==2,'Original second page')
 result['checks']['pagination']=all(m['position'] in [11,12] for m in guild()['members'])
 settle(.65);send('guild_refresh',guild_token=guild()['token'],page=1)
 wait(lambda:not guild().get('pending') and guild().get('page')==1 and len(guild().get('members',[]))==10,'Return first page')
 if restricted:
  target=next(m for m in guild()['members'] if m['name']!='Codexdruid');name=target['name'];settle(.65)
  send('guild_member',guild_token=guild()['token'],member_token=target['token'],verb='promote')
  wait(lambda:any('You do not have high enough privilege' in str(e) for e in snapshot.get('chat',{}).get('entries',[])),'DOL denies insufficient rank')
  wait(lambda:not guild().get('pending') and any(m['name']==name and m['rank']==8 for m in guild()['members']),'Denied promotion retains original server rank')
  result['checks']['server_rank_permission_denied']=True
  with checked() as db:result['checks']['denied_rank_not_saved']=db.execute('SELECT GuildRank FROM DOLCharacters WHERE Name=?',(name,)).fetchone()[0]==8
 else:
  target=next(m for m in guild()['members'] if m['name']!='Codexdruid');name=target['name'];settle(.65);settle(.65);send('guild_member',guild_token=guild()['token'],member_token=target['token'],verb='promote')
  wait(lambda:not guild().get('pending') and any(m['name']==name and m['rank']==7 for m in guild()['members']),'Server-authorized promotion')
  result['checks']['server_promotion']=True
  target=next(m for m in guild()['members'] if m['name']==name);settle(.65);send('guild_member',guild_token=guild()['token'],member_token=target['token'],verb='demote')
  wait(lambda:not guild().get('pending') and any(m['name']==name and m['rank']==8 for m in guild()['members']),'Server-authorized demotion')
  result['checks']['server_demotion']=True
  target=next(m for m in guild()['members'] if m['name']==name);settle(.65);send('guild_member',guild_token=guild()['token'],member_token=target['token'],verb='remove')
  settle(1.1);result['checks']['unconfirmed_remove_rejected']=guild()['total']==12
  send('guild_member',guild_token=guild()['token'],member_token=target['token'],verb='remove',confirmed=True)
  wait(lambda:not guild().get('pending') and guild().get('total')==11 and not any(m['name']==name for m in guild()['members']),'Server removes only confirmed member')
  result['checks']['confirmed_server_removal']=True
  settle(.65);send('guild_refresh',guild_token=guild()['token'],tab='alliance',page=1,sort=1)
  wait(lambda:not guild().get('pending') and guild().get('tab')=='alliance' and guild().get('total')==0,'No-alliance safely ends bounded request')
  result['checks']['no_alliance_keeps_no_stale_guild_rows']=not guild()['members'] and guild()['stale']
  settle(.65);send('guild_refresh',guild_token=guild()['token'],tab='guild',page=1,sort=1)
  wait(lambda:not guild().get('pending') and guild().get('total')==11,'Return guild roster')
  send('guild_leave',guild_token=guild()['token'],confirmed=False);settle(.4);result['checks']['unconfirmed_leave_rejected']=guild()['guild']=='Codex Private Guild'
  settle(.65);send('guild_leave',guild_token=guild()['token'],confirmed=True)
  wait(lambda:bool(snapshot.get('interaction',{}).get('dialogs')),'Original server leave confirmation')
  dialog=snapshot['interaction']['dialogs'][0];result['checks']['server_leave_confirmation']=dialog['text']=='Do you really want to leave Codex Private Guild?'
  send('dialog_response',dialog_id=dialog['id'],answer=1)
  wait(lambda:guild().get('guild')=='','Original leave acknowledgement')
  result['checks']['confirmed_server_leave']=not guild()['members']
  result['checks']['social_not_duplicated_in_chat']=all('TE,' not in str(v) and 'E,1,12' not in str(v) for v in snapshot.get('messages',[]))
  (D/'snapshot.json').write_text(json.dumps(snapshot),encoding='utf-8')
 result['passed']=all(result['checks'].values())
except Exception:
 result['errors'].append(traceback.format_exc());(D/'failed_snapshot.json').write_text(json.dumps(snapshot),encoding='utf-8')
finally:
 if sock and session:
  try:send('logout')
  except OSError:pass
 if client and client.poll() is None:
  (RUN/'Reports/live/logout.request').write_text('logout',encoding='utf-8')
  try:client.wait(timeout=90)
  except subprocess.TimeoutExpired:client.kill();client.wait();result['errors'].append('Private client forced stop')
 if sock:sock.close()
 if server and server.poll() is None:
  server.stdin.write('exit\n');server.stdin.flush()
  try:server.wait(timeout=45)
  except subprocess.TimeoutExpired:server.kill();server.wait();result['errors'].append('Private server forced stop')
 for log in logs:log.close()
 for target,saved in reversed(candidate_files):
  assert target.resolve().is_relative_to(RUN);shutil.copy2(saved,target)
 if candidate_files:result["candidate_server_restored"]=True
 if backed:
  assert DB.is_relative_to(RUN) and RUN.is_relative_to(ROOT/'ProtocolQA')
  with checked() as dst:
   src=sqlite3.connect(backup/'before.sqlite3.db');src.backup(dst);src.close()
  config.write_bytes(config_bytes);result['database_restored']=True
 result['normal_runtime_unchanged']=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in normal_hashes.items())
 result['normal_shutdown']=bool(client and server and client.returncode==0 and server.returncode==0)
 result['passed']=result['passed'] and result['normal_shutdown'] and result['normal_runtime_unchanged'] and not result['errors'] and all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in result['source_inputs'].items())
 (D/'real_protocol.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='source_inputs'}));assert result['passed']
