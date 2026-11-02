from qa_runtime import *
import socket,time
s=socket.create_connection(('127.0.0.1',19737),timeout=2);s.settimeout(.2);buffer=b'';last={};deadline=time.monotonic()+15
try:
 while time.monotonic()<deadline:
  try:chunk=s.recv(1048576)
  except socket.timeout:continue
  if not chunk:break
  buffer+=chunk
  while b'\n' in buffer:
   line,buffer=buffer.split(b'\n',1);value=json.loads(line)
   if value.get('type')=='snapshot':last=value
  if last.get('classic_ui',{}).get('skills_ready'):break
 assert last.get('classic_ui',{}).get('skills_ready')
 (RUN/'advanced_snapshot.json').write_text(json.dumps(last))
 ui=last['classic_ui']
 print(json.dumps({'character':ui.get('character'),'points':ui.get('points'),'entries':[{k:e.get(k) for k in ['id','kind','name','line','level']} for e in ui.get('entries',[])],'concentration':ui.get('concentration'),'pet':ui.get('pet')},ensure_ascii=False))
finally:s.close()
