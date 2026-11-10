"""Check native-viewer startup failures without starting UE or a server."""
import argparse,importlib.util,json,sys,time
from pathlib import Path
from unittest.mock import patch
from prepare_combined_expansion_data import digest

def verify(workspace):
    helper=Path(__file__).resolve().parents[1]/'magic_sight_relay.py'
    sys.path.insert(0,str(helper.parent));spec=importlib.util.spec_from_file_location('isolated_native_sight',helper);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    root=workspace/'NativeSightHarnessLab/State'/time.strftime('%Y%m%d-%H%M%S');root.mkdir(parents=True)
    checks={}
    class Socket:
        def __init__(self):self.closed=False
        def bind(self,*a):pass
        def listen(self,*a):pass
        def settimeout(self,*a):pass
        def getsockname(self):return ('127.0.0.1',19739)
        def close(self):self.closed=True
    class Process:
        def __init__(self,code):self.code=code;self.stopped=False
        def poll(self):return self.code
        def terminate(self):self.stopped=True;self.code=0
        def wait(self,**k):return self.code
    project=workspace.parent/'DAoC-Enhanced-Unreal/DAoCEnhanced.uproject'
    for label,code,clock in [('exited',1,[0,1]),('timeout',None,[0,301])]:
        sock=Socket();proc=Process(code)
        with patch.object(m.socket,'socket',return_value=sock),patch.object(m.subprocess,'Popen',return_value=proc) as launch,patch.object(m.time,'monotonic',side_effect=clock):
            try:m.NativeSightRelay(None,workspace,'private-test',{},project=project,report_dir=root/label,offscreen=True,enabled_plugins=['DAoCVisualBridge'],navigation_probe=True,headless_geometry=label=='timeout')
            except (RuntimeError,TimeoutError):pass
            else:raise AssertionError('Startup failure was accepted')
        checks[label+'_listener_closed']=sock.closed
        checks[label+'_process_cleanup']=proc.stopped if code is None else not proc.stopped
        args=launch.call_args.args[0]
        checks[label+'_read_only_offscreen']='-DaocBridgeReadOnly' in args and '-RenderOffscreen' in args
        checks[label+'_project_working_directory']=launch.call_args.kwargs['cwd']==project.parent
        checks[label+'_navigation_probe']='-DaocBridgeNavigationProbe' in args
        checks[label+'_rendering_mode']=('-nullrhi' in args and '-d3d11' not in args and '-DaocBridgeSpellVisualTest' not in args) if label=='timeout' else ('-nullrhi' not in args and '-d3d11' in args and '-DaocBridgeSpellVisualTest' in args)
        checks[label+'_private_log']=any(a.startswith('-abslog='+str(root/label)) for a in args)
        for name,flag in [('environment_catalog.json','-DaocBridgeEnvironmentCatalog='),('foliage_lods.json','-DaocBridgeFoliageCatalog=')]:
            checks[label+'_'+name]=((flag+str(workspace/name)) in args)==(workspace/name).is_file()
    value=dict(passed=all(checks.values()),checks=checks,source_inputs={str(helper):digest(helper)},server_started=False,unreal_started=False,normal_installation_modified=False)
    (root/'verified.json').write_text(json.dumps(value,indent=2));assert value['passed'];return dict(passed=True,checks=len(checks),proof=str(root/'verified.json'))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.workspace.resolve())))
