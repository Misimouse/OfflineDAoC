"""Real GM inventory round trip via the normal launcher and game protocol.
Never edits the database, gives money, or destroys/drops items.
"""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,socket,subprocess,time,math,traceback
from pathlib import Path
R=Path(__file__).resolve().parent;O=R/'Reports/inventory';O.mkdir(exist_ok=True);LIVE=R/'Reports/live'
DOTNET=str(ENGINE / 'Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe')
snapshot={};buffer=b'';session='';serial=0;sock=None;process=None
result={'real_server':True,'character':'BridgeFighter','steps':[],'errors':[],'normal_logout':False,'transactions_started':False}
class CommerceUnavailable(Exception):pass
baseline={};purchased=None;source_slot=-1;equip_slot=-1
def write():(O/'server_verification.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
def pump(duration=.15):
 global buffer,session,snapshot
 end=time.monotonic()+duration
 while time.monotonic()<end:
  try:data=sock.recv(1048576)
  except socket.timeout:continue
  if not data:raise RuntimeError('Bridge closed')
  buffer+=data
  while b'\n' in buffer:
   line,buffer=buffer.split(b'\n',1);value=json.loads(line)
   if value.get('type')=='hello':session=value['session']
   if value.get('type')=='snapshot':snapshot=value
def wait(predicate,label,timeout=18):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  pump()
  if predicate():return
 raise RuntimeError('Timeout: '+label+'; '+snapshot.get('inventory',{}).get('feedback',''))
def send(action,**values):
 global serial
 serial+=1;sock.sendall((json.dumps(dict(values,type='command',session=session,id='inventory-probe:'+str(serial),action=action))+'\n').encode())
def inventory():return snapshot.get('inventory',{})
def items():return {int(it['slot']):it for it in inventory().get('items',[])}
def coins():
 m=inventory().get('money',{});return sum(int(m.get(k,0))*scale for k,scale in [('copper',1),('silver',100),('gold',10000),('platinum',10000000),('mithril',10000000000)])
def body(it):return {k:v for k,v in it.items() if k not in ['slot','token']}
def personal():return {s:body(it) for s,it in items().items()}
def free():return next((s for s in range(40,80) if s not in items()),-1)
def mark(label):
 result['steps'].append({'step':label,'inventory_revision':inventory().get('state_revision'),'coins_copper':coins(),'slots':len(items())});write();print(label,flush=True)
def command(action,slot=None,**values):
 wait(lambda:not inventory().get('pending',True),'previous server operation')
 values['inventory_revision']=inventory()['state_revision']
 if slot is not None:values.update(slot=slot,item_token=items()[slot]['token'])
 if action.startswith('merchant_'):
  m=snapshot['interaction']['merchant'];values.update(merchant_id=m['entity_id'],merchant_revision=m['catalog_revision'])
 send(action,**values)
def move(a,b):
 expected=body(items()[a]);old=body(items()[b]) if b in items() else None
 command('inventory_move',a,to_slot=b)
 wait(lambda: b in items() and body(items()[b])==expected and ((a not in items()) if old is None else a in items() and body(items()[a])==old),'move '+str(a)+' -> '+str(b))
 wait(lambda:not inventory().get('pending',True),'move server update')
def is_purchased(it):return purchased is not None and body(it)==body(purchased)
try:
 with (O/'server_probe_stdout.log').open('w')as log:
  process=subprocess.Popen([DOTNET,str(R/'Launcher/bin/Release/net10.0/BridgeLauncher.dll'),'--character=BridgeFighter','--session-only','--interaction-test'],cwd=R,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  end=time.monotonic()+80
  while time.monotonic()<end:
   if process.poll()is not None:raise RuntimeError('Normal launcher exited before bridge became ready')
   try:sock=socket.create_connection(('127.0.0.1',19727),timeout=.2);break
   except OSError:time.sleep(.2)
  if sock is None:raise RuntimeError('No bridge listener')
  sock.settimeout(.12)
  wait(lambda:bool(session) and snapshot.get('in_game') and inventory().get('ready',False),'real inventory',80)
  pump(1.2);baseline=personal();baseline_coins=coins();baseline_money=inventory()['money'];(O/'server_baseline.json').write_text(json.dumps({'items':items(),'money':baseline_money},indent=2,ensure_ascii=False),encoding='utf-8');mark('Real inventory received')
  local=next(e for e in snapshot['entities'] if e['id']=='player:local');original_pos=local['position_m']
  # Reversible real-item tests do not depend on buying power.
  backpack=next((s for s in items() if 40<=s<=79),-1);empty=free()
  if backpack<0 or empty<0:raise RuntimeError('No reversible backpack move available')
  move(backpack,empty);mark('Existing backpack item moved');move(empty,backpack);mark('Existing backpack item restored')
  worn=next((s for s in [10,11,21,22,23,25,26,27,28,29,32] if s in items()),-1);empty=free()
  if worn<0 or empty<0:raise RuntimeError('No reversible equipment operation available')
  original_worn=body(items()[worn]);command('inventory_unequip',worn)
  wait(lambda:worn not in items() and empty in items() and body(items()[empty])==original_worn,'real unequip');wait(lambda:not inventory().get('pending',True),'unequip settled');mark('Existing equipment removed into backpack')
  command('inventory_equip',empty)
  wait(lambda:worn in items() and body(items()[worn])==original_worn and empty not in items(),'real equip');wait(lambda:not inventory().get('pending',True),'equip settled');mark('Original equipment re-equipped')
  if personal()!=baseline or coins()!=baseline_coins:raise RuntimeError('Original state not restored after core round trip')
  result['core_inventory_verified']=True
  wait(lambda:any(e.get('name')=='Mahon' for e in snapshot.get('entities',[])),'Mahon visible in server data')
  merchant=next(e for e in snapshot['entities'] if e.get('name')=='Mahon');point=list(merchant['position_m']);point[0]+=1.5
  (O/'view_point.json').write_text(json.dumps({'position_m':point,'camera_yaw_deg':180,'source':'actual Mahon server position; GM visual test only'}))
  send('chat',text='/jump to %d %d %d 200'%(round(point[0]*40)+35*8192,round(point[2]*40)+51*8192,round(point[1]*40)))
  wait(lambda:any(e['id']=='player:local' and math.dist(e['position_m'],point)<1 for e in snapshot.get('entities',[])),'GM transfer near merchant')
  send('interact',entity_id=merchant['id']);wait(lambda:bool(snapshot.get('interaction',{}).get('merchant',{}).get('pages')),'real merchant catalog')
  mark('Mahon catalog received')
  m=snapshot['interaction']['merchant'];offers=[(int(page),it) for page,its in m['pages'].items() for it in its if it.get('can_use') and 0<int(it.get('price',0))<=1000 and int(it['price'])<=coins() and int(it.get('model',0)) not in {i.get('model') for i in items().values()}]
  if not offers:raise CommerceUnavailable('Only '+str(coins())+' copper available; no affordable usable test item. No resources granted.')
  if len([s for s in range(40,80) if s not in items()])<2:raise RuntimeError('Need two free backpack slots; no items removed')
  page,offer=min(offers,key=lambda p:p[1]['price']);source_slot=free();result['offer']=offer;result['transactions_started']=True;write()
  command('merchant_buy',page=page,index=offer['index'],count=1)
  wait(lambda:source_slot in items() and items()[source_slot]['model']==offer['model'],'purchase appears in actual inventory')
  wait(lambda:not inventory().get('pending',True),'purchase settled');purchased=dict(items()[source_slot]);result['purchase_cost_copper']=baseline_coins-coins();mark('Purchase confirmed by real inventory')
  other=free();move(source_slot,other);mark('Backpack move confirmed');move(other,source_slot);mark('Backpack return confirmed')
  fits=items()[source_slot].get('equip_slots',[])
  if not fits:raise RuntimeError('Bought item has no equipment destination')
  equip_slot=next((s for s in fits if s not in items()),fits[0]);before_target=body(items()[equip_slot]) if equip_slot in items() else None
  command('inventory_equip',source_slot)
  wait(lambda:equip_slot in items() and is_purchased(items()[equip_slot]),'equipment accepted by real server')
  wait(lambda:not inventory().get('pending',True),'equipment settled');mark('Equip confirmed by real server')
  if before_target is None:move(equip_slot,source_slot)
  else:move(source_slot,equip_slot)
  equip_slot=-1;mark('Original equipment restored')
  before_sale=coins();command('merchant_sell',source_slot)
  wait(lambda:source_slot not in items(),'sale removes actual purchased item');wait(lambda:not inventory().get('pending',True),'sale settled');pump(.8)
  result['sale_received_copper']=coins()-before_sale;result['net_cost_copper']=baseline_coins-coins();result['original_inventory_restored']=personal()==baseline;mark('Sale confirmed; original inventory compared')
  result['passed']=result['original_inventory_restored'] and result['purchase_cost_copper']==offer['price'] and result['sale_received_copper']>=0
  result['commerce_live_verified']=result['passed']
except CommerceUnavailable as why:
 result['commerce_live_verified']=False;result['commerce_unavailable']=str(why);result['passed']=result.get('core_inventory_verified',False)
except Exception:
 result['errors'].append(traceback.format_exc());result['passed']=False;write()
finally:
 if sock is not None and session:
  try:
   if baseline:
    pump(.3)
    for target,expected in baseline.items():
     if target in items() and body(items()[target])==expected:continue
     candidates=[s for s,it in items().items() if body(it)==expected]
     occupant=body(items()[target]) if target in items() else None
     known=occupant is None or occupant in baseline.values() or purchased is not None and occupant==body(purchased)
     if len(candidates)!=1 or not known:raise RuntimeError('Cannot unambiguously restore original slot '+str(target))
     move(candidates[0],target)
    result['original_inventory_restored']=all(target in items() and body(items()[target])==expected for target,expected in baseline.items())
   if purchased is not None:
    # Recover a still-worn test item before leaving. Never touch an unrelated item.
    pump(.3);locations=[s for s,it in items().items() if is_purchased(it)]
    if len(locations)==1 and locations[0]<40:
     current=locations[0]
     if source_slot in items() and body(items()[source_slot])==baseline.get(current):move(source_slot,current)
     elif source_slot not in items():move(current,source_slot)
     else:result['errors'].append('Manual equipment recovery needed; test item retained, no unrelated move attempted')
    result['final_personal_inventory']=personal();result['original_inventory_restored']=personal()==baseline
   if 'original_pos' in globals():
    send('chat',text='/jump to %d %d %d 200'%(round(original_pos[0]*40)+35*8192,round(original_pos[2]*40)+51*8192,round(original_pos[1]*40)));pump(.4)
   send('logout')
  except Exception:result['errors'].append('Cleanup: '+traceback.format_exc())
 (LIVE/'logout.request').write_text('logout')
 if process is not None:
  try:process.wait(timeout=100)
  except subprocess.TimeoutExpired:result['errors'].append('Normal logout still pending; process kept alive')
 if sock is not None:sock.close()
 try:
  final=json.loads((LIVE/'godot_session.json').read_text(encoding='utf-8-sig'));result['normal_logout']=not final.get('playing',True) and 'protocolo normal' in final.get('status','');result['gateway_inventory']=final.get('inventory',{});result['bridge_rejected']=final.get('bridge_rejected');result['helper_exit_code']=process.returncode if process else None
 except Exception:result['errors'].append('Missing final sanitized session report')
 result['passed']=bool(result.get('passed') and result['normal_logout'] and not result['errors']);write();print(json.dumps({k:v for k,v in result.items() if k not in ['final_personal_inventory','offer']},ensure_ascii=False),flush=True)
 if not result['passed']:raise SystemExit(1)
