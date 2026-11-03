from qa_runtime import *
import sqlite3, subprocess, socket, time, hashlib, shutil, traceback

D=ROOT/'Reports/exchange';D.mkdir(exist_ok=True)
SOURCE=ROOT/'Godot'
result={'passed':False,'real_protocol':True,'disposable_only':True,'checks':{},'errors':[]}
server=client=sock=None;logs=[];serial=0;session='';snapshot={};buffer=b''
backup=ROOT/'Backups'/('ExchangeProtocolQA_'+time.strftime('%Y%m%d-%H%M%S'));backup.mkdir()
config=RUN/'bridge_config.json';config_bytes=config.read_bytes();backed=False

def checked():
 db=sqlite3.connect(DB);db.row_factory=sqlite3.Row
 assert db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0]==RUN.name
 return db
def update(db,table,keyfield,key,values):
 db.execute('UPDATE '+table+' SET '+','.join('"'+k+'"=?' for k in values)+' WHERE "'+keyfield+'"=?',list(values.values())+[key])
def send(action,**values):
 global serial
 serial+=1;sock.sendall((json.dumps(dict(type='command',session=session,id='exchange:'+str(serial),action=action,**values))+'\n').encode())
def pump():
 global session,snapshot,buffer
 try:data=sock.recv(1048576)
 except socket.timeout:return
 if not data:raise RuntimeError('Disposable bridge closed')
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
 raise RuntimeError(label+'; exchange='+str(ex())+'; interaction='+str(snapshot.get('interaction',{}).get('feedback','')))
def inv():return snapshot.get('inventory',{})
def ex():return snapshot.get('exchange',{})
def item(slot):return next((i for i in inv().get('items',[]) if i['slot']==slot),None)
def total():return sum(int(inv().get('money',{}).get(k,0))*n for k,n in [('copper',1),('silver',100),('gold',10000),('platinum',10000000),('mithril',10000000000)])
def command(action,**values):
 send(action,exchange_token=ex()['token'],catalog_revision=ex()['catalog_revision'],**values)
def stop_client():
 global client,sock,session,snapshot,buffer
 if sock and session:
  try:send('logout')
  except OSError:pass
 if client and client.poll() is None:
  (RUN/'Reports/live/logout.request').write_text('logout',encoding='utf-8')
  try:client.wait(timeout=90)
  except subprocess.TimeoutExpired:client.kill();client.wait();result['errors'].append('QA client forced stop')
 if sock:sock.close()
 client=None;sock=None;session='';snapshot={};buffer=b''
def start_client(character):
 global client,sock
 (RUN/'Reports/live/logout.request').unlink(missing_ok=True)
 game=INSTALL/'new-client';sdk=ENGINE/'Binaries/ThirdParty/DotNet/10.0/win-x64'
 account='codexqa'+hashlib.sha256(RUN.name.encode()).hexdigest()[:10];password=hashlib.sha256(('disposable-local-protocol-qa:'+RUN.name).encode()).hexdigest()[:24]
 ce=dict(env,DOTNET_ROOT=str(sdk),DOTNET_ROOT_X64=str(sdk),PATH=str(sdk)+os.pathsep+env['PATH'])
 log=(D/('real_client_'+character+'.log')).open('w',encoding='utf-8');logs.append(log)
 client=subprocess.Popen([str(game/'tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),'--headless','--path',str(RUN/'LobbyProject'),'--script',str(RUN/'Godot/gateway_main.gd'),'--','--server=127.0.0.1','--server-port=10351','--account='+account,'--password='+password,'--no-world','--bridge-character='+character],cwd=RUN,env=ce,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 end=time.monotonic()+55
 while time.monotonic()<end:
  try:sock=socket.create_connection(('127.0.0.1',19737),timeout=.3);sock.settimeout(.1);break
  except OSError:time.sleep(.2)
 else:raise RuntimeError('QA bridge unavailable')
 wait(lambda:inv().get('ready') and snapshot.get('classic_ui',{}).get('character')==character and any(e.get('name')=='Codex QA Exchange' for e in snapshot.get('entities',[])),'Inventory and broker ready')
def open_exchange(tab):
 broker=next(e for e in snapshot['entities'] if e.get('name')=='Codex QA Exchange')
 send('interact',entity_id=broker['id'])
 wait(lambda:bool(snapshot.get('interaction',{}).get('talk',{}).get('keywords')),'Broker dialogue')
 talk=snapshot['interaction']['talk'];word='Browse the exchange' if tab=='browse' else 'Manage my listings'
 assert word in talk['keywords']
 send('keyword',word=word,reply_id=talk['id'])
 wait(lambda:ex().get('visible') and ex().get('tab')==tab and not ex().get('pending'),'Exchange '+tab)

try:
 for port in [10351,19737]:
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=.2):raise RuntimeError('Private QA port already in use')
  except ConnectionRefusedError:pass
  except socket.timeout:pass
 with checked() as db:
  dest=sqlite3.connect(backup/'before.sqlite3.db');db.backup(dest);dest.close();backed=True
  buyer=db.execute("SELECT * FROM DOLCharacters WHERE Name='Codexdruid'").fetchone();assert buyer
  seller=db.execute("SELECT * FROM DOLCharacters WHERE Name LIKE 'Codexnew%' AND AccountName=? ORDER BY Name LIMIT 1",(buyer['AccountName'],)).fetchone();assert seller
  seller_name=seller['Name'];buyer_name=buyer['Name']
  update(db,'Account','Name',buyer['AccountName'],{'PrivLevel':3,'Realm':3})
  update(db,'AccountXMoney','AccountId',buyer['AccountName'],{'Platinum':1,'Gold':0,'Silver':0,'Copper':0})
  for character in [buyer,seller]:
   update(db,'DOLCharacters','DOLCharacters_ID',character['DOLCharacters_ID'],{k:buyer[k] for k in ['Xpos','Ypos','Zpos','Region']})
  mob=db.execute("SELECT Mob_ID FROM Mob WHERE Name='Codex Pet Training Dummy'").fetchone();assert mob
  update(db,'Mob','Mob_ID',mob[0],{'Name':'Codex QA Exchange','Guild':'Realm Exchange','ClassType':'DOL.GS.RealmExchangeBroker','Brain':'','Realm':3,'Speed':0,'AggroLevel':0,'X':buyer['Xpos']+80,'Y':buyer['Ypos'],'Z':buyer['Zpos'],'Region':buyer['Region']})
 cfg=json.loads(config_bytes);cfg['initial_spawn_m']=[(buyer['Xpos']-35*8192)*.025,buyer['Zpos']*.025,(buyer['Ypos']-51*8192)*.025];config.write_text(json.dumps(cfg),encoding='utf-8')
 for p in SOURCE.glob('*.gd'):shutil.copy2(p,RUN/'Godot'/p.name)
 p=RUN/'Godot/visual_bridge.gd';p.write_text(p.read_text(encoding='utf-8-sig').replace('port: int = 19727','port: int = 19737'),encoding='utf-8')
 log=(D/'real_server.log').open('w',encoding='utf-8');logs.append(log)
 server=subprocess.Popen([str(dotnet),str(SERVER/'CoreServer.dll'),'--start'],cwd=SERVER,env=env,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
 end=time.monotonic()+40
 while time.monotonic()<end:
  try:
   with socket.create_connection(('127.0.0.1',10351),timeout=.2):break
  except OSError:time.sleep(.2)
 else:raise RuntimeError('QA server unavailable')
 start_client(seller_name)
 baseline={i['slot'] for i in inv()['items']}
 send('chat',text='/item create club')
 wait(lambda:any(i['slot'] not in baseline and i.get('model')==449 for i in inv()['items']),'Create private tradable club')
 created=next(i for i in inv()['items'] if i['slot'] not in baseline and i.get('model')==449)
 open_exchange('listings');result['checks']['original_broker_open']=True
 created=item(created['slot'])
 (D/'before_list.json').write_text(json.dumps(snapshot),encoding='utf-8')
 command('exchange_list',slot=created['slot'],item_token=created['token'],inventory_revision=inv()['state_revision'])
 wait(lambda:ex().get('listing_rows') and item(created['slot']) is None and not ex()['pending'],'Listing transfer confirmed')
 listing=next(i for i in ex()['listing_rows'] if i['model']==449);result['checks']['list_server_inventory']=True
 price=1234
 command('exchange_price',index=listing['index'],exchange_item_token=listing['token'],copper=price)
 wait(lambda:not ex()['pending'] and any(i['index']==listing['index'] and i['price']==price for i in ex()['listing_rows']),'Price acknowledged')
 result['checks']['price_ack']=True
 (D/'real_seller_snapshot.json').write_text(json.dumps(snapshot),encoding='utf-8')
 stop_client();start_client(buyer_name);open_exchange('browse')
 prior_requests=ex()['requests'];command('exchange_search',filters={'name':'club','price_max':price})
 wait(lambda:ex()['requests']>prior_requests and not ex()['pending'] and any(i['model']==449 and i['price']==price for i in ex()['market_rows']),'Find other character listing')
 offered=next(i for i in ex()['market_rows'] if i['model']==449 and i['price']==price)
 result['checks']['search_real_listing_and_icon']=offered['icon']>0
 before=total();baseline={i['slot'] for i in inv()['items']}
 command('exchange_buy',index=offered['index'],exchange_item_token=offered['token'])
 wait(lambda:not ex()['pending'] and any(i['slot'] not in baseline and i.get('model')==449 for i in inv()['items']),'Buy receipt and refresh')
 assert total()==before-price;result['checks']['purchase_exact_coins_and_item']=True
 assert not any(i['model']==449 and i['price']==price for i in ex()['market_rows']);result['checks']['sold_listing_removed']=True
 (D/'real_buyer_snapshot.json').write_text(json.dumps(snapshot),encoding='utf-8')
 stop_client();start_client(seller_name);open_exchange('listings')
 assert ex()['proceeds']>=price;before=total();claim=ex()['proceeds']
 command('exchange_claim')
 wait(lambda:not ex()['pending'] and ex()['proceeds']==0 and total()==before+claim,'Proceeds credited by server')
 result['checks']['claim_exact_proceeds']=True
 baseline={i['slot'] for i in inv()['items']};send('chat',text='/item create club')
 wait(lambda:any(i['slot'] not in baseline and i.get('model')==449 for i in inv()['items']),'Second private item')
 # GM creation sends item, encumbrance and wallet updates as separate packets.
 end=time.monotonic()+.8
 while time.monotonic()<end:pump()
 created=next(i for i in inv()['items'] if i['slot'] not in baseline and i.get('model')==449)
 command('exchange_list',slot=created['slot'],item_token=created['token'],inventory_revision=inv()['state_revision'])
 wait(lambda:ex()['listing_rows'] and item(created['slot']) is None and not ex()['pending'],'Second listing')
 listing=next(i for i in ex()['listing_rows'] if i['model']==449)
 command('exchange_take',index=listing['index'],exchange_item_token=listing['token'])
 wait(lambda:not ex()['pending'] and not any(i['index']==listing['index'] for i in ex()['listing_rows']) and any(i.get('model')==449 for i in inv()['items'] if i['slot']>=40),'Take back receipt')
 result['checks']['take_back_server_inventory']=True;result['passed']=all(result['checks'].values())
except Exception:
 result['errors'].append(traceback.format_exc())
 (D/'failed_snapshot.json').write_text(json.dumps(snapshot),encoding='utf-8')
finally:
 stop_client()
 if server and server.poll() is None:
  server.stdin.write('exit\n');server.stdin.flush()
  try:server.wait(timeout=45)
  except subprocess.TimeoutExpired:server.kill();server.wait();result['errors'].append('QA server forced stop')
 for log in logs:log.close()
 if backed:
  assert DB.is_relative_to(RUN) and RUN.is_relative_to(ROOT/'ProtocolQA')
  with checked() as dst:
   src=sqlite3.connect(backup/'before.sqlite3.db');src.backup(dst);src.close()
  config.write_bytes(config_bytes)
  result['database_restored']=True
 result['passed']=result['passed'] and not result['errors']
 (D/'real_protocol.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 print(json.dumps(result));assert result['passed']
