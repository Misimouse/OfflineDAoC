"""Exercise original merchant lifecycle with ordinary disposable accounts; restore private data and libraries."""
from qa_runtime import *
import subprocess,socket,time,hashlib,traceback,sqlite3,shutil
import sys
source_qa=Path(os.environ.get("DAOC_BRIDGE_SOURCE_QA",str(ROOT.parent/"DAoC-Enhanced-Godot/source/ue5-bridge/ProtocolQA"))).resolve();assert (source_qa/"central_activation_receipts.py").is_file();sys.path.insert(0,str(source_qa))
from central_activation_receipts import verify_files
from prepare_combined_expansion_data import digest
SOURCE=ROOT/'Godot'
D=ROOT/'MerchantLifecycleLab/RealProtocol'/time.strftime('%Y%m%d-%H%M%S');D.mkdir(parents=True)
BACKUP=ROOT/'Backups'/('MerchantLifecycle_'+time.strftime('%Y%m%d-%H%M%S'));BACKUP.mkdir()
config_backups=[];candidate_files=[];backed=False
normal=verify_files(ROOT)
normal_paths=[ROOT/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll',INSTALL/'runtime/server/GameServer.dll',INSTALL/'runtime/server/lib/GameServer.dll']
normal_hashes={str(p):digest(p) for p in normal_paths}
def checked():
 db=sqlite3.connect(DB);db.row_factory=sqlite3.Row;assert db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0]==RUN.name;return db
class Peer:
 def __init__(self,port):
  deadline=time.monotonic()+30
  while time.monotonic()<deadline:
   try:self.sock=socket.create_connection(('127.0.0.1',port),timeout=.2);break
   except OSError:time.sleep(.2)
  else:raise RuntimeError('QA bridge unavailable')
  self.sock.settimeout(.03);self.buffer=b'';self.snapshot={};self.session='';self.serial=0;self.trace=[]
 def send(self,action,**values):
  self.serial+=1;self.sock.sendall((json.dumps(dict(type='command',session=self.session,id='qa-group:'+str(self.serial),action=action,**values))+'\n').encode())
 def pump(self):
  try:chunk=self.sock.recv(1048576)
  except socket.timeout:return
  if not chunk:raise RuntimeError('QA bridge closed')
  self.buffer+=chunk
  while b'\n' in self.buffer:
   line,self.buffer=self.buffer.split(b'\n',1);value=json.loads(line)
   if value.get('type')=='hello':self.session=value['session']
   if value.get('type')=='snapshot':self.snapshot=value;self.trace.append(value)
 def party(self):return self.snapshot.get('classic_ui',{}).get('party',{})
peers=[];clients=[];handles=[];server=None
result={'passed':False,'real_protocol':True,'disposable_only':True,'checks':{},'errors':[],'source_inputs':{str(p):digest(p) for p in SOURCE.glob('*.gd')}}
def wait(test,label,seconds=20):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  for peer in peers:peer.pump()
  if test():return
 raise RuntimeError(label+'; '+repr([p.snapshot.get('messages',[]) for p in peers]))
def settle(seconds):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  for peer in peers:peer.pump()
try:
 for port in [10351,19737,19738]:
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=.2):raise RuntimeError('Private QA port occupied')
  except (ConnectionRefusedError,socket.timeout):pass
 with checked() as db:
  dest=sqlite3.connect(BACKUP/'before.sqlite3.db');db.backup(dest);dest.close();backed=True
  rows=db.execute("SELECT * FROM DOLCharacters WHERE Name IN ('Codexdruid','Codexfriend')").fetchall();assert len(rows)==2
  reference=ROOT/'MerchantLifecycleLab/Reference/original_vendor.json';world=json.loads(reference.read_text(encoding='utf-8'));assert world['source_read_only'] and world['npc']['ClassType']=='DOL.GS.GameMerchant'
  result['source_inputs'][str(reference)]=digest(reference)
  for table,items in [('Mob',[world['npc']]),('MerchantItem',world['merchant_rows']),('ItemTemplate',world['items'])]:
   columns={r[1] for r in db.execute('pragma table_info("'+table+'")')}
   for item in items:
    assert set(item)==columns,(table,'original row schema differs')
    keys=list(item);db.execute('INSERT OR REPLACE INTO "'+table+'" ('+','.join('"'+k+'"' for k in keys)+') VALUES ('+','.join('?' for k in keys)+')',[item[k] for k in keys])
  leader=dict(next(c for c in rows if c['Name']=='Codexdruid'));leader.update(Region=200,Xpos=world['npc']['X']+100,Ypos=world['npc']['Y'],Zpos=world['npc']['Z'])
  for c in rows:
   db.execute('UPDATE Account SET PrivLevel=1,Realm=3 WHERE Name=?',(c['AccountName'],))
   db.execute('UPDATE DOLCharacters SET Region=?,Xpos=?,Ypos=?,Zpos=?,HCFlag=0 WHERE DOLCharacters_ID=?',(leader['Region'],leader['Xpos']+(10 if c['Name']=='Codexfriend' else 0),leader['Ypos'],leader['Zpos'],c['DOLCharacters_ID']))
  funded=db.execute("UPDATE AccountXMoney SET Gold=1,Silver=0,Copper=0,Platinum=0,Mithril=0 WHERE Realm=3 AND AccountId=?",(leader['AccountName'],));assert funded.rowcount==1
  result['checks']['ordinary_accounts_only']=all(db.execute('SELECT PrivLevel FROM Account WHERE Name=?',(c['AccountName'],)).fetchone()[0]==1 for c in rows)
 for n,root in enumerate([RUN,RUN/'friend-session']):
  assert root.resolve().is_relative_to(RUN)
  config=root/'bridge_config.json';config_backups.append((config,config.read_bytes()))
  cfg=json.loads(config.read_text());cfg['initial_spawn_m']=[(leader['Xpos']-35*8192)*.025,leader['Zpos']*.025,(leader['Ypos']-51*8192)*.025];config.write_text(json.dumps(cfg),encoding='utf-8')
  for q in SOURCE.glob('*.gd'):shutil.copy2(q,root/'Godot'/q.name)
  q=root/'Godot/visual_bridge.gd';q.write_text(q.read_text(encoding='utf-8-sig').replace('port: int = 19727','port: int = '+str(19737+n)),encoding='utf-8')
 candidate_root=ROOT/'GuildWindowLab/ServerCandidate';candidate=json.loads((candidate_root/'build_receipt.json').read_text());assert candidate['passed']
 for folder in [SERVER,SERVER/'lib',SERVER/'win-x64']:
  for name,expected in candidate['binaries_sha256'].items():
   target=folder/name
   if not target.exists():continue
   assert target.resolve().is_relative_to(RUN);origin=Path(candidate['libraries'])/name;assert digest(origin)==expected
   saved=BACKUP/('server_'+str(len(candidate_files))+'_'+name);shutil.copy2(target,saved);candidate_files.append((target,saved));shutil.copy2(origin,target)
 output=(D/'server.log').open('w',encoding='utf-8');handles.append(output)
 server=subprocess.Popen([str(dotnet),str(SERVER/'CoreServer.dll'),'--start'],cwd=SERVER,env=env,stdin=subprocess.PIPE,stdout=output,stderr=subprocess.STDOUT,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
 deadline=time.monotonic()+40
 while time.monotonic()<deadline:
  try:
   with socket.create_connection(('127.0.0.1',10351),timeout=.2):break
  except OSError:time.sleep(.2)
 else:raise RuntimeError('Isolated server unavailable')
 game=INSTALL/'new-client';sdk=ENGINE/'Binaries/ThirdParty/DotNet/10.0/win-x64'
 for character,suffix,root,port in [('Codexdruid','',RUN,19737),('Codexfriend',':friend',RUN/'friend-session',19738)]:
  account='codexqa'+hashlib.sha256((RUN.name+suffix).encode()).hexdigest()[:10];password=hashlib.sha256(('disposable-local-protocol-qa:'+RUN.name+suffix).encode()).hexdigest()[:24]
  ce=dict(env,DOTNET_ROOT=str(sdk),DOTNET_ROOT_X64=str(sdk),PATH=str(sdk)+os.pathsep+env['PATH'],APPDATA=str(root/'appdata'))
  log=(D/(character+'_client.log')).open('w',encoding='utf-8');handles.append(log);(root/'Reports/live/logout.request').unlink(missing_ok=True)
  client=subprocess.Popen([str(game/'tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),'--headless','--path',str(RUN/'LobbyProject'),'--script',str(root/'Godot/gateway_main.gd'),'--','--server=127.0.0.1','--server-port=10351','--account='+account,'--password='+password,'--no-world','--bridge-character='+character],cwd=root,env=ce,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  clients.append((client,root));peers.append(Peer(port))
 wait(lambda:all(p.snapshot.get('classic_ui',{}).get('skills_ready') for p in peers),'Both ordinary players ready',40)
 a,b=peers
 def inventory(peer=a):return peer.snapshot.get('inventory',{})
 def merchant(peer=a):return peer.snapshot.get('interaction',{}).get('merchant',{})
 def money(peer=a):
  coins=inventory(peer)['money'];return sum(coins.get(k,0)*n for k,n in [('copper',1),('silver',100),('gold',10000),('platinum',10000000),('mithril',10000000000)])
 def carried(name,peer=a):return [it for it in inventory(peer)['items'] if 40<=it['slot']<=79 and it['name']==name]
 wait(lambda:any(e.get('name')==world['npc']['Name'] for e in a.snapshot.get('entities',[])),'Original merchant appears')
 npc=next(e for e in a.snapshot['entities'] if e.get('name')==world['npc']['Name'])
 def open_shop(peer):
  peer.send('interact',entity_id=npc['id']);wait(lambda:merchant(peer).get('pages',{}).get('0'),'Original merchant catalogue')
 open_shop(a);open_shop(b)
 offer=dict(merchant()['pages']['0'][0]);template=next(it for it in world['items'] if it['Name']==offer['name'])
 result['checks']['original_catalogue_names_prices_and_icons']=offer['name']==world['items'][0]['Name'] and offer['price']==template['Price'] and offer['icon']>=0
 def payload(peer=a):return dict(page=0,index=offer['index'],count=1,inventory_revision=inventory(peer)['state_revision'],merchant_id=npc['id'],merchant_revision=merchant(peer)['catalog_revision'])
 before=money();assert before==10000 and not carried(offer['name'])
 b.send('merchant_buy',**payload(b));settle(.3)
 result['checks']['insufficient_money_refused']=money(b)==0 and not carried(offer['name'],b) and 'enough money' in inventory(b).get('feedback','').lower()
 invalid=payload();invalid['count']=2;a.send('merchant_buy',**invalid);settle(.3)
 result['checks']['invalid_pack_count_refused']=money()==before and not carried(offer['name']) and 'one pack' in inventory().get('feedback','').lower()
 invalid=payload();invalid['merchant_revision']=-1;a.send('merchant_buy',**invalid);settle(.3)
 result['checks']['stale_catalogue_refused']=money()==before and not carried(offer['name']) and 'catalogue has changed' in inventory().get('feedback','').lower()
 a.send('merchant_buy',**payload());wait(lambda:len(carried(offer['name']))==1 and not inventory()['pending'] and money()==before-offer['price'],'Original purchase and money acknowledgement',20)
 item=dict(carried(offer['name'])[0]);after_buy=money()
 result['checks']['server_purchase_delivers_one_original_item']=item['count']==1
 result['checks']['server_purchase_deducts_exact_catalogue_price']=after_buy==before-offer['price']
 invalid=dict(slot=item['slot'],item_token='stale',inventory_revision=inventory()['state_revision'],merchant_id=npc['id'],merchant_revision=merchant()['catalog_revision']);a.send('merchant_sell',**invalid);settle(.3)
 result['checks']['stale_item_cannot_be_sold']=len(carried(offer['name']))==1 and money()==after_buy
 (D/'active_snapshot.json').write_text(json.dumps(a.snapshot),encoding='utf-8')
 a.send('merchant_sell',slot=item['slot'],item_token=item['token'],inventory_revision=inventory()['state_revision'],merchant_id=npc['id'],merchant_revision=merchant()['catalog_revision'])
 with checked() as db:ratio=int(db.execute("select Value from ServerProperty where Key='item_sell_ratio'").fetchone()[0])
 proceeds=template['Price']*item['count']//max(1,template['PackSize'])*ratio//100
 wait(lambda:not carried(offer['name']) and not inventory()['pending'] and money()==after_buy+proceeds,'Original sale and money acknowledgement',20)
 result['checks']['server_sale_removes_actual_item']=True
 result['checks']['server_sale_pays_original_configured_ratio']=money()==after_buy+proceeds
 final=money();a.send('merchant_sell',slot=item['slot'],item_token=item['token'],inventory_revision=inventory()['state_revision'],merchant_id=npc['id'],merchant_revision=merchant()['catalog_revision']);settle(.3)
 result['checks']['sold_item_cannot_be_sold_again']=money()==final and not carried(offer['name'])
 old=payload();a.send('dismiss_interaction');wait(lambda:not merchant(),'Merchant dialogue closed')
 old['inventory_revision']=inventory()['state_revision'];a.send('merchant_buy',**old);settle(.3)
 result['checks']['closed_catalogue_cannot_buy']=money()==final and not carried(offer['name'])
 result['expected_saved_copper']=final
 result['passed']=all(result['checks'].values())
except Exception:result['errors'].append(traceback.format_exc())
finally:
 for i,peer in enumerate(peers):
  (D/('snapshot_'+str(i)+'.json')).write_text(json.dumps(peer.snapshot),encoding='utf-8')
  if peer.session:
   try:peer.send('logout')
   except OSError:pass
 for client,root in clients:
  if client.poll() is None:
   (root/'Reports/live/logout.request').write_text('logout',encoding='utf-8')
   try:client.wait(timeout=100)
   except subprocess.TimeoutExpired:client.kill();client.wait();result['errors'].append('Private client forced stop')
 for peer in peers:peer.sock.close()
 if server and server.poll() is None:
  server.stdin.write('exit\n');server.stdin.flush()
  try:server.wait(timeout=45)
  except subprocess.TimeoutExpired:server.kill();server.wait();result['errors'].append('Private server forced stop')
 for handle in handles:handle.close()
 for target,saved in reversed(candidate_files):assert target.resolve().is_relative_to(RUN);shutil.copy2(saved,target)
 for config,raw in config_backups:config.write_bytes(raw)
 if backed and result['passed']:
  with checked() as db:
   coins=db.execute("select Copper,Silver,Gold,Platinum,Mithril from AccountXMoney where Realm=3 AND AccountId=?",(leader['AccountName'],)).fetchone()
   saved=sum(int(v)*n for v,n in zip(coins,[1,100,10000,10000000,10000000000]))
   result['checks']['original_logout_saves_transaction_balance']=saved==result['expected_saved_copper'];result['passed']=result['passed'] and result['checks']['original_logout_saves_transaction_balance']
 if backed:
  with checked() as db:
   src=sqlite3.connect(BACKUP/'before.sqlite3.db');src.backup(db);src.close()
  result['database_restored']=True
 result['private_server_restored']=bool(candidate_files)
 result['normal_shutdown']=bool(clients) and all(c.returncode==0 for c,_ in clients) and server is not None and server.returncode==0
 result['normal_runtime_unchanged']=all(digest(Path(p))==h for p,h in normal_hashes.items())
 result['passed']=result['passed'] and result['normal_shutdown'] and result.get('database_restored',False) and result['normal_runtime_unchanged'] and not result['errors'] and all(digest(Path(p))==h for p,h in result['source_inputs'].items())
 (D/'verified.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='source_inputs'}));assert result['passed']
