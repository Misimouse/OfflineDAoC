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
try:
 wait(lambda:ui().get('skills_ready') and snapshot.get('player_status',{}).get('ready'),'Initial state')
 assert ui()['character']=='Codexdruid'
 before_inventory=snapshot['inventory']['items']
 send('chat',text='/gmstealth off');send('target_self');settle(.6)
 bind('Call Greater Nature Spirit');use()
 wait(lambda:ui().get('pet',{}).get('valid'),'Real pet ownership',25)
 wait(lambda:ui()['pet'].get('name') and ui()['pet'].get('health',-1)>=0,'Actual pet entity')
 result['pet_initial']=ui()['pet'];result['summon_confirmed']=True
 for command,field,expected in [('passive','aggro',3),('stay','walk',2),('follow','walk',1)]:
  bind('petcmd:'+command);use()
  wait(lambda:ui()['pet'][field]==expected,'Server pet '+command)
  result['pet_'+command]=ui()['pet'][field];settle(.3)
 bind('Might of the Redwood');use()
 wait(lambda:len(ui()['concentration']['entries'])>0,'Real maintained concentration',20)
 result['concentration_applied']=ui()['concentration']
 row=ui()['concentration']['entries'][0]
 send('conc_cancel',concentration_index=row['index'],concentration_token=row['token'])
 wait(lambda:not ui()['concentration']['entries'] and not ui()['concentration']['pending'],'Server concentration removal')
 wait(lambda:ui()['concentration']['remaining']==ui()['concentration']['maximum'],'Concentration refund')
 result['concentration_removed']=ui()['concentration']
 send('trainer_refresh');wait(lambda:ui()['trainer']['ready'],'Actual trainer list')
 row=next(x for x in ui()['trainer']['specs'] if x['name']=='Nurture')
 result['training_before']={'level':row['level'],'points':ui()['trainer']['spec_points']}
 send('trainer_train',training_kind='spec',training_index=row['index'],training_token=row['token'])
 wait(lambda:any(x['name']=='Nurture' and x['level']==row['level']+1 for x in ui()['trainer']['specs']) and not ui()['trainer']['pending'],'Real one-level training')
 result['training_after']={'level':next(x['level'] for x in ui()['trainer']['specs'] if x['name']=='Nurture'),'points':ui()['trainer']['spec_points']}
 bind('petcmd:release');use();wait(lambda:not ui()['pet']['valid'],'Server pet release')
 result['pet_released']=True;result['inventory_unchanged']=snapshot['inventory']['items']==before_inventory
 result['passed']=result['inventory_unchanged']
except Exception:result['errors'].append(traceback.format_exc())
finally:
 (RUN/'advanced_trace.json').write_text(json.dumps(trace))
 (ROOT/'Reports/protocol_qa/advanced_result.json').write_text(json.dumps(result,indent=2))
 if session:
  try:send('logout')
  except OSError:pass
 sock.close()
 print(json.dumps(result,ensure_ascii=False),flush=True)
if not result['passed']:raise SystemExit(1)
