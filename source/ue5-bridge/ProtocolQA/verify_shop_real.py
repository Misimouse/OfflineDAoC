from qa_runtime import *
import sqlite3, subprocess, socket, time, hashlib, shutil, traceback

D=ROOT/'Reports/inventory';D.mkdir(exist_ok=True)
result={'passed':False,'real_protocol':True,'disposable_only':True,'checks':{},'errors':[]}
server=client=sock=None;logs=[];saved={};serial=0;session='';snapshot={};buffer=b''
def checked():
 db=sqlite3.connect(DB);db.row_factory=sqlite3.Row
 assert db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0]==RUN.name
 return db
def update(db,table,keyfield,key,values):
 db.execute('UPDATE '+table+' SET '+','.join('"'+k+'"=?' for k in values)+' WHERE "'+keyfield+'"=?',list(values.values())+[key])
def send(action,**values):
 global serial
 serial+=1;sock.sendall((json.dumps(dict(type='command',session=session,id='shop:'+str(serial),action=action,**values))+'\n').encode())
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
def wait(test,label,seconds=25):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  pump()
  if test():return
 raise RuntimeError(label+'; inventory feedback='+str(snapshot.get('inventory',{}).get('feedback',''))+'; interaction='+str(snapshot.get('interaction',{}).get('feedback','')))
def inventory():return snapshot.get('inventory',{})
def item(slot):return next((i for i in inventory().get('items',[]) if i['slot']==slot),None)
def total():
 m=inventory().get('money',{});return sum(int(m.get(k,0))*n for k,n in [('copper',1),('silver',100),('gold',10000),('platinum',10000000),('mithril',10000000000)])
try:
 with checked() as db:
  char=db.execute("SELECT DOLCharacters_ID,AccountName,Xpos,Ypos,Zpos,Region,Copper,Silver,Gold,Platinum FROM DOLCharacters WHERE Name='Codexdruid'").fetchone();assert char
  saved['char']=dict(char)
  saved['account']=dict(db.execute('SELECT Name,PrivLevel,Realm FROM Account WHERE Name=?',(char['AccountName'],)).fetchone())
  wallet=db.execute('SELECT * FROM AccountXMoney WHERE AccountId=? AND Realm=3',(char['AccountName'],)).fetchone();assert wallet
  saved['wallet']=dict(wallet);update(db,'AccountXMoney','AccountxMoney_ID',wallet['AccountxMoney_ID'],{'Platinum':1})
  update(db,'Account','Name',char['AccountName'],{'PrivLevel':1,'Realm':3})
  update(db,'DOLCharacters','DOLCharacters_ID',char['DOLCharacters_ID'],{'Gold':0,'Silver':0,'Copper':0,'Platinum':10})
  mob=db.execute("SELECT * FROM Mob WHERE Name='Codex Pet Training Dummy'").fetchone();assert mob;saved['mob']=dict(mob)
  update(db,'Mob','Mob_ID',mob['Mob_ID'],{'Name':'Codex QA Merchant','ClassType':'DOL.GS.GameMerchant','Brain':'','Realm':3,'Speed':0,'AggroLevel':0,'X':char['Xpos']+80,'Y':char['Ypos'],'Z':char['Zpos'],'Region':char['Region'],'ItemsListTemplateID':'codex-qa-shop-only'})
  db.execute("DELETE FROM MerchantItem WHERE ItemListID='codex-qa-shop-only'")
  db.execute("INSERT INTO MerchantItem(ItemListID,ItemTemplateID,PageNumber,SlotPosition,MerchantItem_ID) VALUES ('codex-qa-shop-only','Ailbes_Claw',0,0,'codex-qa-shop-only-0')")
  ticket=db.execute('SELECT Id_nb FROM ItemTemplate WHERE Model=499 LIMIT 1').fetchone();assert ticket
  db.execute("INSERT INTO MerchantItem(ItemListID,ItemTemplateID,PageNumber,SlotPosition,MerchantItem_ID) VALUES ('codex-qa-shop-only',?,0,1,'codex-qa-shop-only-1')",(ticket[0],))
 for p in (ROOT/'Godot').glob('*.gd'):shutil.copy2(p,RUN/'Godot'/p.name)
 p=RUN/'Godot/visual_bridge.gd';p.write_text(p.read_text(encoding='utf-8-sig').replace('port: int = 19727','port: int = 19737'),encoding='utf-8')
 (RUN/'Reports/live/logout.request').unlink(missing_ok=True)
 log=(D/'shop_real_server.log').open('w',encoding='utf-8');logs.append(log)
 server=subprocess.Popen([str(dotnet),str(SERVER/'CoreServer.dll'),'--start'],cwd=SERVER,env=env,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
 end=time.monotonic()+35
 while time.monotonic()<end:
  try:
   with socket.create_connection(('127.0.0.1',10351),timeout=.2):break
  except OSError:time.sleep(.2)
 else:raise RuntimeError('QA server unavailable')
 game=INSTALL/'new-client';sdk=ENGINE/'Binaries/ThirdParty/DotNet/10.0/win-x64'
 account='codexqa'+hashlib.sha256(RUN.name.encode()).hexdigest()[:10];password=hashlib.sha256(('disposable-local-protocol-qa:'+RUN.name).encode()).hexdigest()[:24]
 ce=dict(env,DOTNET_ROOT=str(sdk),DOTNET_ROOT_X64=str(sdk),PATH=str(sdk)+os.pathsep+env['PATH'],APPDATA=str(RUN/'appdata'))
 log=(D/'shop_real_client.log').open('w',encoding='utf-8');logs.append(log)
 client=subprocess.Popen([str(game/'tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),'--headless','--path',str(game/'godot'),'--script',str(RUN/'Godot/gateway_main.gd'),'--','--server=127.0.0.1','--server-port=10351','--account='+account,'--password='+password,'--no-world','--bridge-character=Codexdruid'],cwd=RUN,env=ce,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 end=time.monotonic()+45
 while time.monotonic()<end:
  try:sock=socket.create_connection(('127.0.0.1',19737),timeout=.3);sock.settimeout(.1);break
  except OSError:time.sleep(.2)
 else:raise RuntimeError('QA bridge unavailable')
 wait(lambda:inventory().get('ready') and any(e.get('name')=='Codex QA Merchant' for e in snapshot.get('entities',[])),'Inventory and merchant ready')
 assert snapshot['classic_ui']['character']=='Codexdruid'
 end=time.monotonic()+2
 while time.monotonic()<end:pump()
 original=item(10);assert original
 free=next(i for i in range(40,80) if item(i) is None)
 send('inventory_unequip',slot=10,item_token=original['token'],inventory_revision=inventory()['state_revision'])
 wait(lambda:item(10) is None and item(free) and not inventory()['pending'],'Unequip acknowledged');result['checks']['unequip']=True
 send('inventory_equip',slot=free,item_token=item(free)['token'],inventory_revision=inventory()['state_revision'])
 wait(lambda:item(10) and item(free) is None and not inventory()['pending'],'Equip acknowledged');result['checks']['equip']=True
 merchant=next(e for e in snapshot['entities'] if e.get('name')=='Codex QA Merchant')
 send('interact',entity_id=merchant['id'])
 wait(lambda:bool(snapshot.get('interaction',{}).get('merchant',{}).get('pages')),'Merchant catalogue')
 shop=snapshot['interaction']['merchant'];expected_icons=json.loads((game/'godot/content/items/model_icons.json').read_text(encoding='utf-8-sig'))
 assert all(i.get('icon')==int(expected_icons.get(str(i.get('model')),0)) for page in shop['pages'].values() for i in page)
 result['checks']['original_item_icons']=True
 assert any(i.get('model')==499 and i.get('icon')==1273 for page in shop['pages'].values() for i in page);result['checks']['horse_ticket_icon']=True
 (D/'merchant_real_snapshot.json').write_text(json.dumps(snapshot),encoding='utf-8')
 shop=snapshot['interaction']['merchant'];before=total();baseline={i['slot'] for i in inventory()['items']}
 offered=next(iter(shop['pages'].values()))[0]
 result['catalogue_price']=offered.get('price');result['initial_copper']=before
 send('merchant_buy',page=0,index=offered['index'],count=1,merchant_id=merchant['id'],merchant_revision=shop['catalog_revision'],inventory_revision=inventory()['state_revision'])
 wait(lambda:any(i['slot'] not in baseline for i in inventory()['items']) and not inventory()['pending'],'Purchase confirmed by original server')
 bought=next(i for i in inventory()['items'] if i['slot'] not in baseline)
 assert total()<before;result['checks']['purchase_item_and_coins']=True
 shop=snapshot['interaction']['merchant'];before=total()
 send('merchant_sell',slot=bought['slot'],item_token=bought['token'],merchant_id=merchant['id'],merchant_revision=shop['catalog_revision'],inventory_revision=inventory()['state_revision'])
 wait(lambda:item(bought['slot']) is None and not inventory()['pending'],'Sale confirmed')
 assert total()>before;result['checks']['sale_item_and_coins']=True
 result['passed']=True
except Exception:result['errors'].append(traceback.format_exc())
finally:
 if sock and session:
  try:send('logout')
  except OSError:pass
 if client and client.poll() is None:
  (RUN/'Reports/live/logout.request').write_text('logout',encoding='utf-8')
  try:client.wait(timeout=90)
  except subprocess.TimeoutExpired:client.kill();client.wait();result['errors'].append('QA client forced stop')
 if sock:sock.close()
 if server and server.poll() is None:
  server.stdin.write('exit\n');server.stdin.flush()
  try:server.wait(timeout=45)
  except subprocess.TimeoutExpired:server.kill();server.wait();result['errors'].append('QA server forced stop')
 for log in logs:log.close()
 if saved:
  with checked() as db:
   if 'mob' in saved:
    mob=saved['mob'];update(db,'Mob','Mob_ID',mob['Mob_ID'],{k:v for k,v in mob.items() if k!='Mob_ID'})
   if 'char' in saved:
    c=saved['char'];update(db,'DOLCharacters','DOLCharacters_ID',c['DOLCharacters_ID'],{k:c[k] for k in ['Copper','Silver','Gold','Platinum']})
   if 'wallet' in saved:
    w=saved['wallet'];update(db,'AccountXMoney','AccountxMoney_ID',w['AccountxMoney_ID'],{k:v for k,v in w.items() if k!='AccountxMoney_ID'})
   if 'account' in saved:
    a=saved['account'];update(db,'Account','Name',a['Name'],{'PrivLevel':a['PrivLevel'],'Realm':a['Realm']})
   db.execute("DELETE FROM MerchantItem WHERE ItemListID='codex-qa-shop-only'")
 result['passed']=result['passed'] and not result['errors']
 (D/'shop_real.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 print(json.dumps(result));assert result['passed']
