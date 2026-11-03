using System.Diagnostics;
using System.Net.Sockets;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Text.Json;

string root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"../../../../"));
string install=Environment.GetEnvironmentVariable("DAOC_INSTALL") ?? throw new InvalidOperationException("Set DAOC_INSTALL to your playable OfflineDAoC folder.");
string reports=Path.Combine(root,"Reports/live");Directory.CreateDirectory(reports);
string logout=Path.Combine(reports,"logout.request");if(File.Exists(logout))File.Delete(logout);
using(var reservation=new System.Net.Sockets.TcpListener(System.Net.IPAddress.Loopback,19727)){
    try{reservation.Start();reservation.Stop();}
    catch(SocketException){Console.WriteLine("A bridge session is already active. Close it normally before starting another.");return;}
}
string sessionReport=Path.Combine(reports,"godot_session.json");
if(File.Exists(sessionReport))File.Delete(sessionReport);
bool probe=args.Contains("--probe"), sessionOnly=args.Contains("--session-only");
bool doorTesting=args.Contains("--door-test")||args.Contains("--shack-door-test")||args.Contains("--interaction-test");
bool poseTesting=args.Contains("--pose-test");
bool equipmentTesting=args.Contains("--equipment-test");
bool classicTesting=args.Contains("--ui-test");
string catalogFile=Path.Combine(root,poseTesting?"models_combat_samples.json":"models.json");
string? character=args.FirstOrDefault(a=>a.StartsWith("--character="))?.Split('=',2)[1];
bool menuTesting=args.Contains("--menu-test");
bool characterMenu=menuTesting||args.Contains("--character-menu")||(character==null&&!probe&&!sessionOnly&&!args.Any(a=>a.EndsWith("-test")));
// Do not read, print, copy or rewrite the credential file. Invoke the normal launcher's provider.
string runtime=Path.Combine(install,"runtime");
if(!File.Exists(Path.Combine(runtime,"account.txt")))throw new InvalidOperationException("Use the normal launcher to create the local account first.");
using(var port=new TcpClient()){
    try{await port.ConnectAsync("127.0.0.1",10300);}
    catch{Console.WriteLine("Start the normal OfflineDAoC server before launching the bridge.");return;}
}
Assembly normalLauncher=Assembly.LoadFrom(Path.Combine(install,"new-client/runtime/OfflineDAoC.dll"));
Type provider=normalLauncher.GetType("OfflineDaoc.Launcher.PortableCredentials",throwOnError:true)!;
var credentials=(ITuple)provider.GetMethod("ReadOrCreate",BindingFlags.Static|BindingFlags.Public)!.Invoke(null,[runtime])!;
string account=(string)credentials[0]!, password=(string)credentials[1]!;
var godotStart=new ProcessStartInfo(Path.Combine(install,"new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64.exe")){
    WorkingDirectory=Path.Combine(install,"new-client/godot"),UseShellExecute=false,CreateNoWindow=true,
    RedirectStandardOutput=true,RedirectStandardError=true
};
// Use the known working host that is already running this launcher. Godot also
// probes dotnet --list-sdks; include this host directory in its private PATH.
string godotDotnet=Path.GetDirectoryName(Environment.ProcessPath!)!;
if(!File.Exists(Path.Combine(godotDotnet,"dotnet.exe")))godotDotnet=Path.Combine(install,"tools/dotnet");
godotStart.Environment["DOTNET_ROOT"]=godotDotnet;
godotStart.Environment["DOTNET_ROOT_X64"]=godotDotnet;
godotStart.Environment["PATH"]=godotDotnet+Path.PathSeparator+Environment.GetEnvironmentVariable("PATH");
godotStart.Environment["APPDATA"]=Path.Combine(reports,"isolated-save");
foreach(var value in new[]{"--headless","--path",Path.Combine(install,"new-client/godot"),"--script",Path.Combine(root,"Godot/gateway_main.gd"),"--","--server=127.0.0.1","--no-world","--account="+account,"--password="+password})godotStart.ArgumentList.Add(value);
if(args.Contains("--record-motion"))godotStart.ArgumentList.Add("--bridge-motion-record");
if(character!=null)godotStart.ArgumentList.Add("--bridge-character="+character);
if(characterMenu)godotStart.ArgumentList.Add("--bridge-character-menu");
if(args.Contains("--door-test"))godotStart.ArgumentList.Add("--bridge-door-test");
if(args.Contains("--shack-door-test")||args.Contains("--interaction-test"))godotStart.ArgumentList.Add("--bridge-shack-door-test");
using var godot=new Process{StartInfo=godotStart};
// Engine output is deliberately not echoed; it can contain account/session information.
godot.OutputDataReceived+=(_,_)=>{};godot.ErrorDataReceived+=(_,_)=>{};
godot.Start();godot.BeginOutputReadLine();godot.BeginErrorReadLine();
account="";password="";
Console.WriteLine(characterMenu?"Connecting to character selection...":"Godot session started. Waiting for the Hibernia character...");
Process? unreal=null;
try{
    var deadline=DateTime.UtcNow.AddSeconds(80);bool ready=false;
    while(DateTime.UtcNow<deadline&&!godot.HasExited){
        try{
            using var report=JsonDocument.Parse(await File.ReadAllTextAsync(Path.Combine(reports,"godot_session.json")));
            if(characterMenu&&report.RootElement.TryGetProperty("character_lobby",out var lobby)&&lobby.TryGetProperty("ready",out var menuReady)&&menuReady.GetBoolean()){ready=true;break;}
            if(!characterMenu&&report.RootElement.GetProperty("playing").GetBoolean()&&report.RootElement.GetProperty("zone").GetInt32()==207){ready=true;break;}
        }catch(IOException){}catch(JsonException){}
        await Task.Delay(500);
    }
    if(!ready){Console.WriteLine("The character session did not become ready. See the sanitized session status.");return;}
    Console.WriteLine(characterMenu?"Character selection ready.":"Connected to Connacht.");
    // Pick the available base race matching the real selected character.
    // Equipment and face customization remain a separate visual integration step.
    if(!characterMenu)using(var state=JsonDocument.Parse(await File.ReadAllTextAsync(Path.Combine(reports,"godot_session.json")))){
        string prefix=state.RootElement.GetProperty("player_prefix").GetString()??"";
        using var tasks=JsonDocument.Parse(await File.ReadAllTextAsync(Path.Combine(root,"SourceModels/tasks.json")));
        var catalog=System.Text.Json.Nodes.JsonNode.Parse(await File.ReadAllTextAsync(catalogFile))!.AsObject();
        foreach(var task in tasks.RootElement.EnumerateArray()){
            if(task.GetProperty("info").TryGetProperty("race",out var race)&&race.GetString()==prefix){
                string id=task.GetProperty("id").GetString()!;
                if(catalog[id]!=null)catalog["0"]=catalog[id]!.DeepClone();
                break;
            }
        }
        await File.WriteAllTextAsync(catalogFile,catalog.ToJsonString(new JsonSerializerOptions{WriteIndented=true}));
    }
    if(probe){await Task.Delay(12000);return;}
    if(sessionOnly){Console.WriteLine("Session-only mode. Close this window to request normal logout.");await godot.WaitForExitAsync();return;}
    string project=Path.Combine(root,"Client/DAoCBridgeClient.uproject");
    var start=new ProcessStartInfo(Path.Combine(Environment.GetEnvironmentVariable("DAOC_UE_ENGINE") ?? @"C:\Program Files\Epic Games\UE_5.8\Engine","Binaries/Win64/UnrealEditor.exe")){
        WorkingDirectory=Path.GetDirectoryName(project)!,UseShellExecute=false
    };
    foreach(var value in new[]{project,menuTesting?"/Engine/Maps/Entry":"/Game/DAoC/Connacht_v01/Ardee_Nwiro_Prueba","-game","-DaocBridge","-windowed","-ResX=1920","-ResY=1080","-d3d11","-nosplash",
        "-DaocBridgeHeights="+Path.Combine(install,"new-client/godot/content/zones/zone207/heights.f32"),
        "-DaocBridgeCatalog="+catalogFile,"-DaocBridgeReport="+Path.Combine(reports,"unreal_session.json")})start.ArgumentList.Add(value);
    if(menuTesting)start.ArgumentList.Add("-DaocBridgeCharacterLobbyLiveProbe="+Path.Combine(root,"Reports/character_lobby/live_menu.json"));
    start.ArgumentList.Add("-DaocBridgeCollisionCatalog="+Path.Combine(root,"collision_catalog.json"));
    var environmentCatalog=Path.Combine(root,"environment_catalog.json");
    if(File.Exists(environmentCatalog))start.ArgumentList.Add("-DaocBridgeEnvironmentCatalog="+environmentCatalog);
    if(args.Contains("--motion-test"))start.ArgumentList.Add("-DaocBridgeRemoteMotionProbe="+Path.Combine(root,"Reports/movement/live_visual_samples.json"));
    if(args.Contains("--interaction-test"))start.ArgumentList.Add("-DaocBridgeAutoInteractionTest");
    if(args.Contains("--inventory-test"))start.ArgumentList.Add("-DaocBridgeOpenInventory");
    if(poseTesting)start.ArgumentList.Add("-DaocBridgePoseVisualTest");
    start.ArgumentList.Add("-DaocBridgeEquipmentCatalog="+Path.Combine(root,"equipment_catalog_v01.json"));
    if(equipmentTesting)start.ArgumentList.Add("-DaocBridgeEquipmentVisualTest");
    if(classicTesting)start.ArgumentList.Add("-DaocBridgeClassicVisualTest");
    if(doorTesting){start.ArgumentList.Add("-DaocBridgeAutoDoorTest");start.ArgumentList.Add((args.Contains("--shack-door-test")||args.Contains("--interaction-test"))?"-DaocBridgeYaw=-90":"-DaocBridgeYaw=90");}
    using(var config=JsonDocument.Parse(await File.ReadAllTextAsync(Path.Combine(root,"bridge_config.json")))){
        if(!doorTesting&&config.RootElement.TryGetProperty("initial_camera_yaw_deg",out var yaw))
            start.ArgumentList.Add("-DaocBridgeYaw="+yaw.GetDouble().ToString(System.Globalization.CultureInfo.InvariantCulture));
        string quality=args.FirstOrDefault(a=>a.StartsWith("--quality="))?.Split('=',2)[1]
            ??(config.RootElement.TryGetProperty("client_quality",out var profile)?profile.GetString():"balanced")??"balanced";
        quality=quality.ToLowerInvariant();if(quality is not ("balanced" or "high" or "superior" or "accessible" or "original"))quality="balanced";
        start.ArgumentList.Add("-DaocBridgeQuality="+quality);
        start.ArgumentList.Add("-DaocBridgeFoliageCatalog="+Path.Combine(root,"foliage_lods.json"));
    }
    if(args.Contains("--auto-test")||args.Contains("--motion-test")||doorTesting||args.Contains("--inventory-test")||poseTesting||equipmentTesting||classicTesting){
        start.ArgumentList.Add("-DaocBridgeNavigationProbe");
        start.ArgumentList.Add("-DaocBridgeAutoTest");start.ArgumentList.Add("-DaocBridgeCapture="+Path.Combine(reports,"Ardee_GM_Client.png"));
        if(args.Contains("--walk-test"))start.ArgumentList.Add("-DaocBridgeAutoWalk");
    }
    unreal=Process.Start(start)!;await unreal.WaitForExitAsync();
}finally{
    await File.WriteAllTextAsync(logout,"logout");
    if(!godot.HasExited){
        Console.WriteLine("Waiting for normal server logout and character saving...");
        using var timeout=new CancellationTokenSource(TimeSpan.FromSeconds(100));
        try{await godot.WaitForExitAsync(timeout.Token);}
        catch(OperationCanceledException){Console.WriteLine("Logout still pending. Godot remains running to preserve the server save.");}
    }
}
