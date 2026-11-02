from qa_runtime import *
import socket,time,traceback
deadline=time.monotonic()+35
while time.monotonic()<deadline:
 try:sock=socket.create_connection(('127.0.0.1',19737),timeout=.3);break
 except OSError:time.sleep(.2)
else:raise RuntimeError('Disposable bridge did not start')
sock.settimeout(.1)
buffer=b'';snapshot={};session='';serial=0;answered=set();trace=[]
result={'passed':False,'real_protocol':True,'disposable_character':'Codexdruid','normal_characters_modified':False,'scope':'client macros and original read-only server commands','errors':[]}
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
def macro(name,command):
 send('chat',text='/macro '+name+' '+command)
 wait(lambda:any(e['kind']=='macro' and e['name']==name for e in ui().get('entries',[])),'Create '+name)
 return next(e for e in ui()['entries'] if e['kind']=='macro' and e['name']==name)
def use_macro(entry):
 for bar in range(3):
  bank=ui()['banks'][bar]
  for slot,item in enumerate(ui()['bars'][bar][bank]):
   if item.get('id')==entry['id']:send('ui_use_slot',bar=bar,slot=slot);return
 raise RuntimeError('Macro was not placed in any free shown slot')
try:
 wait(lambda:ui().get('skills_ready') and snapshot.get('inventory',{}).get('ready'),'Ready')
 assert ui()['character']=='Codexdruid'
 baseline_inventory=snapshot['inventory']['items'];baseline_points=ui()['points']
 local=macro('QA_LOC','/loc');global_loc=macro('QA_GLOC','/gloc');training=macro('QA_TRAIN','/train')
 assert not any('loc=' in m or 'You are at X:' in m for m in snapshot.get('messages',[])),'Creation unexpectedly executed command'
 result['creation_did_not_execute']=True
 use_macro(local);wait(lambda:any(': loc=' in m for m in snapshot.get('messages',[])),'Original client location macro')
 result['client_loc_line']=next(m for m in snapshot['messages'] if ': loc=' in m)
 use_macro(global_loc);wait(lambda:any('You are at X:' in m for m in snapshot.get('messages',[])),'Actual server global-coordinate command')
 result['server_gloc_line']=next(m for m in snapshot['messages'] if 'You are at X:' in m)
 use_macro(training);wait(lambda:ui()['trainer']['ready'],'Original trainer refresh from macro')
 result['trainer_opened_without_training']=True
 send('chat',text='/qbar 2 3');wait(lambda:ui()['banks'][2]==1,'Original client quickbar page command')
 result['qbar_client_command']=True
 send('ui_detail',entry_id=global_loc['id'],entry_token=global_loc['token']);wait(lambda:ui().get('detail',{}).get('lines')==['/gloc'],'Literal macro command inspection')
 (ROOT/'Reports/macros/real_snapshot.json').write_text(json.dumps(snapshot))
 result['inventory_unchanged']=snapshot['inventory']['items']==baseline_inventory;result['points_unchanged']=ui()['points']==baseline_points
 result['passed']=result['inventory_unchanged'] and result['points_unchanged']

except Exception:result['errors'].append(traceback.format_exc())
finally:
 (RUN/'macro_trace.json').write_text(json.dumps(trace))
 (ROOT/'Reports/macros/real_result.json').write_text(json.dumps(result,indent=2))
 if session:
  try:send('logout')
  except OSError:pass
 sock.close()
 print(json.dumps(result,ensure_ascii=False),flush=True)
if not result['passed']:raise SystemExit(1)
