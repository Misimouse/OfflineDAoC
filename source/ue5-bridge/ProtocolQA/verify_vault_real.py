from qa_runtime import *
import socket,time,traceback
deadline=time.monotonic()+35
while time.monotonic()<deadline:
 try:sock=socket.create_connection(('127.0.0.1',19737),timeout=.3);break
 except OSError:time.sleep(.2)
else:raise RuntimeError('Disposable bridge did not start')
sock.settimeout(.1)
buffer=b'';snapshot={};session='';serial=0;answered=set();trace=[]
result={'passed':False,'real_protocol':True,'disposable_character':'Codexdruid','normal_characters_modified':False,'geometry_scope':'Self-only LOS replies; non-self queries fail closed','errors':[]}
def send(action,**values):
 global serial
 serial+=1;sock.sendall((json.dumps(dict(type='command',session=session,id='qa:'+str(serial),action=action,**values))+'\n').encode())
def pump():
 global buffer,snapshot,session
 try:chunk=sock.recv(1048576)
 except socket.timeout:return
 if not chunk:raise RuntimeError('Disposable bridge closed')
 buffer+=chunk
 while b'\n' in buffer:
  line,buffer=buffer.split(b'\n',1);value=json.loads(line)
  if value.get('type')=='hello':session=value['session']
  if value.get('type')=='snapshot':
   snapshot=value
   for q in value.get('los_queries',[]):
    key=(q['id'],q['token'])
    if key not in answered:
     answered.add(key);send('los_reply',query_id=q['id'],query_token=q['token'],visible=q['source_id']==q['target_id'])
   trace.append({'at':time.monotonic(),'snapshot':value})
def ui():return snapshot.get('classic_ui',{})
def wait(test,label,timeout=18):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  pump()
  if test():return
 raise RuntimeError(label+'; messages='+repr(snapshot.get('messages',[]))+'; feedback='+repr(ui().get('feedback')))
def settle(seconds):
 end=time.monotonic()+seconds
 while time.monotonic()<end:pump()
def bind(name):
 e=next(e for e in ui()['entries'] if e['name']==name or e['id']==name)
 send('ui_assign',bar=2,bank=ui()['banks'][2],slot=9,entry_id=e['id'],entry_token=e['token'])
 wait(lambda:ui()['bars'][2][ui()['banks'][2]][9].get('id')==e['id'],'Bind '+name)
 return e
def use():send('ui_use_slot',bar=2,slot=9)
def find_inventory(slot):return next((x for x in snapshot.get('inventory',{}).get('items',[]) if x['slot']==slot),None)
def move(source,destination):
 item=find_inventory(source);state=snapshot['inventory'];vault=state.get('vault',{})
 assert item is not None and not state.get('pending')
 values=dict(slot=source,to_slot=destination,item_token=item['token'],inventory_revision=state['state_revision'])
 if source>=110 or destination>=110:values['vault_token']=vault['token']
 send('inventory_move',**values)
 wait(lambda:find_inventory(source) is None and find_inventory(destination) is not None and not snapshot['inventory']['pending'],'Original item move '+str(source)+' -> '+str(destination))
def open_keeper(kind):
 before={x['id'] for x in snapshot.get('entities',[])}
 send('chat',text='/mob create '+kind+' 3')
 wait(lambda:any(e['id'] not in before and e.get('name')=='New Mob' for e in snapshot.get('entities',[])),'Create disposable '+kind)
 keeper=next(e for e in snapshot['entities'] if e['id'] not in before and e.get('name')=='New Mob')
 send('target',entity_id=keeper['id']);wait(lambda:snapshot.get('interaction',{}).get('target',{}).get('id')==keeper['id'],'Select QA keeper')
 send('interact',entity_id=keeper['id'])
 wait(lambda:snapshot.get('inventory',{}).get('vault',{}).get('valid') and snapshot['inventory']['vault'].get('keeper_id')==keeper['id'],'Original storage window packet for current keeper')
 return keeper
try:
 wait(lambda:ui().get('skills_ready') and snapshot.get('inventory',{}).get('ready'),'Ready')
 assert ui()['character']=='Codexdruid'
 if find_inventory(10) is None:
  old_club=next(x for x in snapshot['inventory']['items'] if x['name']=='training club' and 40<=x['slot']<80)
  send('inventory_equip',slot=old_club['slot'],item_token=old_club['token'],inventory_revision=snapshot['inventory']['state_revision'])
  wait(lambda:find_inventory(10) is not None and not snapshot['inventory']['pending'],'Restore previous QA club')
 baseline={x['slot']:(x['name'],x['count'],x.get('model')) for x in snapshot['inventory']['items']}
 bag_slot=next(slot for slot in range(40,80) if find_inventory(slot) is None)
 club=find_inventory(10);assert club is not None
 send('inventory_unequip',slot=10,item_token=club['token'],inventory_revision=snapshot['inventory']['state_revision'])
 wait(lambda:find_inventory(bag_slot) is not None and find_inventory(10) is None and not snapshot['inventory']['pending'],'Real unequip to backpack')
 keeper=open_keeper('DOL.GS.GameVaultKeeper')
 assert snapshot['inventory']['vault']['first']==110
 result['personal_opened']=True
 move(bag_slot,110);result['personal_deposit']=find_inventory(110)
 (ROOT/'Reports/vault/real_personal_snapshot.json').write_text(json.dumps(snapshot))
 move(110,bag_slot);result['personal_withdrawn']=True
 # Open another original service; the prior personal token must no longer authorize moves.
 old_token=snapshot['inventory']['vault']['token']
 account_keeper=open_keeper('DOL.GS.AccountVaultKeeper')
 assert snapshot['inventory']['vault']['first']==150 and snapshot['inventory']['vault']['count']==100
 result['account_opened']=True
 move(bag_slot,150);result['account_deposit']=find_inventory(150)
 # The account keeper exposes a second original server page through its own dialogue keywords.
 (ROOT/'Reports/vault/real_account_snapshot.json').write_text(json.dumps(snapshot))
 for word in ['second','first']:
  previous=snapshot['inventory']['vault']['token']
  talk=snapshot.get('interaction',{}).get('talk',{})
  assert word in talk.get('keywords',[]),talk
  send('keyword',word=word,reply_id=talk['id'])
  wait(lambda:snapshot['inventory']['vault'].get('valid') and snapshot['inventory']['vault']['token']!=previous,'Original account page '+word)
  assert snapshot['inventory']['vault']['first']==150
  result['account_server_page_'+word]=True
  assert (find_inventory(150) is None) if word=='second' else (find_inventory(150) is not None and find_inventory(150)['name']=='training club')
 move(150,bag_slot);result['account_withdrawn']=True
 result['account_page_contents_isolated']=True
 current=snapshot['inventory']['vault'];send('vault_close',vault_token=current['token'])
 wait(lambda:not snapshot.get('inventory',{}).get('vault',{}).get('valid'),'Explicit storage close')
 result['closed']=True
 item=find_inventory(bag_slot);send('inventory_equip',slot=bag_slot,item_token=item['token'],inventory_revision=snapshot['inventory']['state_revision'])
 wait(lambda:find_inventory(10) is not None and find_inventory(bag_slot) is None and not snapshot['inventory']['pending'],'Restore equipment')
 result['inventory_restored']={x['slot']:(x['name'],x['count'],x.get('model')) for x in snapshot['inventory']['items']}==baseline
 result['passed']=result['inventory_restored'];result['created_only_disposable_keepers']=[keeper['id'],account_keeper['id']]

except Exception:result['errors'].append(traceback.format_exc())
finally:
 if session:
  try:
   club=next((x for x in snapshot.get('inventory',{}).get('items',[]) if x['name']=='training club'),None)
   if club is None and snapshot.get('inventory',{}).get('vault',{}).get('first')==150:
    talk=snapshot.get('interaction',{}).get('talk',{});previous=snapshot['inventory']['vault']['token'];send('keyword',word='first',reply_id=talk['id']);wait(lambda:snapshot['inventory']['vault']['token']!=previous,'Recover first QA account page');club=find_inventory(150)
   if club is not None and club['slot']>=110:
    free=next(slot for slot in range(40,80) if find_inventory(slot) is None);move(club['slot'],free);club=find_inventory(free)
   if club is not None and 40<=club['slot']<80:
    send('inventory_equip',slot=club['slot'],item_token=club['token'],inventory_revision=snapshot['inventory']['state_revision'])
    wait(lambda:find_inventory(10) is not None and not snapshot['inventory']['pending'],'Finally restore QA equipment')
   result['cleanup_equipment_restored']=find_inventory(10) is not None
  except Exception:result['errors'].append('Disposable cleanup: '+traceback.format_exc())
 (RUN/'vault_trace.json').write_text(json.dumps(trace))
 (ROOT/'Reports/vault/real_result.json').write_text(json.dumps(result,indent=2))
 if session:
  try:send('logout')
  except OSError:pass
 sock.close()
 print(json.dumps(result,ensure_ascii=False),flush=True)
if not result['passed']:raise SystemExit(1)
