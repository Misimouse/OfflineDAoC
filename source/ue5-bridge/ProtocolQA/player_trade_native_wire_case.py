"""Actual native viewport/UI commands relayed byte-for-byte to an ordinary QA session."""
import json,socket,subprocess,time
from pathlib import Path
from prepare_combined_expansion_data import digest

class NativeRelay:
    def __init__(self,peer):
        self.peer=peer;self.listener=socket.socket();self.listener.bind(('127.0.0.1',0));self.listener.listen(1);self.listener.setblocking(False)
        self.port=self.listener.getsockname()[1];self.view=None;self.buffer=b'';self.pending=b'';self.last_sequence=-1;self.commands=[];self.closed=False
    def pump(self):
        if self.closed:return
        if self.view is None:
            try:self.view,_=self.listener.accept()
            except BlockingIOError:return
            self.view.setblocking(False)
            self.pending=(json.dumps(dict(type='hello',protocol='daoc-visual-bridge',version=1,session=self.peer.session))+'\n').encode()
        try:chunk=self.view.recv(1048576)
        except BlockingIOError:chunk=None
        except (ConnectionResetError,ConnectionAbortedError):self.closed=True;return
        if chunk==b'':self.closed=True;return
        if chunk:
            self.buffer+=chunk
            while b'\n' in self.buffer:
                raw,self.buffer=self.buffer.split(b'\n',1);command=json.loads(raw)
                assert command.get('type')=='command' and command.get('session')==self.peer.session
                self.commands.append(command)
                # Never replace the native identity, token, item, amount or action.
                self.peer.sock.sendall(raw+b'\n')
        if not self.pending and self.peer.snapshot and self.peer.snapshot.get('seq')!=self.last_sequence:
            self.last_sequence=self.peer.snapshot['seq'];self.pending=(json.dumps(self.peer.snapshot)+'\n').encode()
        if self.pending:
            try:sent=self.view.send(self.pending);self.pending=self.pending[sent:]
            except BlockingIOError:pass
            except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):self.closed=True
    def close(self):
        if self.view:self.view.close()
        self.listener.close()

def read(path):
    raw=path.read_bytes();return json.loads(raw.decode('utf-16' if raw[:2] in [b'\xff\xfe',b'\xfe\xff'] else 'utf-8-sig'))

def run(a,b,wait,settle,result,checked,output,workspace,engine):
    root=workspace/'PlayerTradeGatewayLab';bp=root/'native_build.json';build=read(bp);assert build['passed']
    binary=Path(build['project']).parent/'Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'
    assert digest(binary)==build['binaries_sha256'][binary.name]
    result['source_inputs'].update({str(p):digest(p) for p in [Path(__file__).resolve(),bp,binary,workspace/'models.json',workspace/'equipment_catalog_v01.json']})
    def inventory(peer):return peer.snapshot.get('inventory',{})
    def rows(peer,name):return [i for i in inventory(peer).get('items',[]) if i.get('name')==name]
    def state(peer):return peer.snapshot.get('player_trade',{})
    def money(peer):return sum(inventory(peer).get('money',{}).get(k,0)*v for k,v in [('copper',1),('silver',100),('gold',10000),('platinum',10000000),('mithril',10000000000)])
    wait(lambda:all(inventory(p).get('ready') for p in [a,b]),'Original inventories for native trade')
    assert rows(a,'Codex Trade A') and rows(b,'Codex Trade B') and money(a)==money(b)==10000
    for peer in [a,b]:
        local=next(r for r in peer.snapshot['entities'] if r['id']=='player:local')
        peer.send('move',position_m=local['position_m'],forward_xz=[0,1],speed_mps=0.0,swimming=False,on_ground=True,vertical_speed_mps=0)
    wait(lambda:any(r.get('name')=='Codexfriend' and r.get('kind')=='player' for r in a.snapshot['entities']),'Actual native trade recipient')
    relay=NativeRelay(a);original_pump=a.pump;native_closing=False
    def pump():
        try:original_pump()
        except RuntimeError as error:
            if not native_closing or str(error)!='QA bridge closed':raise
        relay.pump()
    a.pump=pump;instruction=output/'native_trade_instruction.json';step_number=0;commands=[];process=None;normal_exit=False
    def step(action,timeout=30,**values):
        nonlocal step_number
        step_number+=1;identity=str(step_number);instruction.write_text(json.dumps(dict(id=identity,action=action,**values)))
        response=Path(str(instruction)+'.result.json')
        def ready():
            assert process.poll() is None,'Native client exited before '+action
            try:return read(response).get('id')==identity
            except (OSError,ValueError):return False
        wait(ready,'Native '+action,timeout)
        value=read(response);assert value['ok'],value;commands.append(value)
        if value.get('command'):
            wait(lambda:any(c.get('id')==value['command']['id'] and c==value['command'] for c in relay.commands),'Unmodified native command reaches original transport',15)
        return value
    args=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),build['project'],'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeReadOnly','-DaocBridgePort='+str(relay.port),'-DaocBridgeCatalog='+str(workspace/'models.json'),'-DaocBridgeEquipmentCatalog='+str(workspace/'equipment_catalog_v01.json'),'-DaocBridgePlayerTradeLive='+str(instruction),'-DaocBridgeQuality=accessible','-RenderOffscreen','-d3d11','-windowed','-ResX=1280','-ResY=720','-unattended','-nosound','-nosplash','-abslog='+str(output/'native_engine.log')]
    for key,file in [('DisplaySettings','display.ini'),('InterfaceSettings','interface.ini'),('KeyConfiguration','keys.ini'),('ControlsSettings','camera.json'),('AudioSettings','audio.ini')]:args.append('-DaocBridge'+key+'='+str(output/file))
    try:
        with (output/'native_stdout.log').open('w',encoding='utf-8') as log:
            process=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            step('ready',120)
            result['checks']['actual_native_session_and_inventory']=True
            begin=step('begin',slot=40,target_name='Codexfriend')
            result['checks']['actual_native_body_drop']=begin['command']['action']=='player_trade_begin' and begin['picked']==begin['command']['entity_id'] and begin['command']['target_name']=='Codexfriend'
            wait(lambda:state(a).get('visible') and state(b).get('visible'),'Native drop opens original server trade')
            step('cancel');wait(lambda:not state(a).get('visible') and not state(b).get('visible'),'Native cancel closes server trade');step('closed')
            result['checks']['actual_native_cancel_preserves_goods']=bool(rows(a,'Codex Trade A') and rows(b,'Codex Trade B') and money(a)==money(b)==10000)
            step('begin',slot=40,target_name='Codexfriend');wait(lambda:state(a).get('visible') and state(b).get('visible'),'Native repeat opening')
            step('offer',money=[0,0,0,1,0]);wait(lambda:state(a).get('offer',{}).get('own_money')==[0,0,0,1,0],'Actual native money update')
            item=rows(b,'Codex Trade B')[0]
            b.send('player_trade_update',trade_token=state(b)['token'],inventory_revision=inventory(b)['state_revision'],slots=[item['slot']],item_tokens={str(item['slot']):item['token']},money=[0,0,0,0,50])
            wait(lambda:bool(state(a).get('offer',{}).get('partner_items')),'Original partner offer for native window');settle(.6)
            step('offer_visible',name='Codex Trade B')
            result['checks']['actual_native_partner_item_label']=True
            accept=step('accept')
            result['checks']['actual_native_accept_button']=accept['command']['action']=='player_trade_accept' and bool(accept['command']['trade_token'])
            wait(lambda:state(a).get('pending'),'Native acceptance waits for original server partner')
            result['checks']['native_accept_does_not_predict_ownership']=bool(rows(a,'Codex Trade A') and rows(b,'Codex Trade B') and money(a)==money(b)==10000)
            b.send('player_trade_accept',trade_token=state(b)['token'])
            wait(lambda:not state(a).get('visible') and not state(b).get('visible'),'Original two-party completion closes native trade')
            wait(lambda:rows(a,'Codex Trade B') and rows(b,'Codex Trade A') and money(a)==9950 and money(b)==10050,'Actual native/server item and money outcomes',20)
            step('closed');result['checks']['actual_native_trade_transfers_goods_and_money']=True
            result['checks']['native_commands_forwarded_without_rewrite']=all(not v.get('command') or any(c==v['command'] for c in relay.commands) for v in commands)
            # QuitGame sends the real client's final saved logout and closes
            # its gateway. Only that expected closure is allowed at this point.
            native_closing=True
            step('finish');wait(lambda:process.poll() is not None,'Native test client closes normally',45);assert process.returncode==0;normal_exit=True
    finally:
        a.pump=(lambda:None) if normal_exit else original_pump;relay.close()
        if process and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=20)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        result['checks']['native_client_normal_shutdown']=normal_exit
        (output/'native_command_trace.json').write_text(json.dumps(dict(steps=commands,forwarded_commands=relay.commands),indent=2))
    b.send('chat',text='/quit');wait(lambda:not b.snapshot.get('in_game',True) and b.snapshot.get('character_lobby',{}).get('ready'),'Original saved return after native trade',90)
    with checked() as db:
        characters={r['Name']:dict(r) for r in db.execute("SELECT * FROM DOLCharacters WHERE Name IN ('Codexdruid','Codexfriend')")}
        owners={r['ITemplate_Id']:r['OwnerID'] for r in db.execute("SELECT OwnerID,ITemplate_Id FROM Inventory WHERE ITemplate_Id LIKE 'codex-private-player-trade-%'")}
        result['checks']['native_trade_saved_item_ownership']=owners['codex-private-player-trade-b']==characters['Codexdruid']['DOLCharacters_ID'] and owners['codex-private-player-trade-a']==characters['Codexfriend']['DOLCharacters_ID']
        balances=[]
        for name in ['Codexdruid','Codexfriend']:
            coins=db.execute('SELECT Copper,Silver,Gold,Platinum,Mithril FROM AccountXMoney WHERE Realm=3 AND AccountId=?',(characters[name]['AccountName'],)).fetchone();balances.append(sum(v*m for v,m in zip(coins,[1,100,10000,10000000,10000000000])))
        result['checks']['native_trade_saved_account_realm_balances']=balances==[9950,10050]
