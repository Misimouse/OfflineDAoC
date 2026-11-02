from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
from pathlib import Path
import shutil
R=Path(str(ROOT));B=R/'Backups/ReleaseCamera_20261101';B.mkdir(exist_ok=True);(R/'Reports/release_camera').mkdir(exist_ok=True)
for name in ['Source','Binaries']:shutil.copytree(R/'Client/Plugins/DAoCVisualBridge'/name,B/name,dirs_exist_ok=True)
shutil.copy2(R/'Godot/live_gateway.gd',B/'live_gateway.gd')
p=R/'Godot/live_gateway.gd';s=p.read_text(encoding='utf-8').replace('var home_jump_requested:=false','var home_jump_requested:=false\nvar test_return_attempts:=0\nvar test_return_at:=-10000')
s=s.replace('if not home_jump_requested and (door_trial or int(server.entry.get("zone",-1))!=207 or Vector2(position.x-initial_spawn.x,position.z-initial_spawn.z).length()>20):','if int(server.entry.get("zone",-1))==207 and not home_jump_requested and (door_trial or Vector2(position.x-initial_spawn.x,position.z-initial_spawn.z).length()>20):')
anchor='func _process(_delta:float)->void:'
new='''func recover_test_region(now:int)->void:
    if not server.playing or leaving:return
    if int(server.entry.get("zone",-1))==207:
        test_return_attempts=0
        return
    # This client only renders Connacht. Preserve the actual bind point and ask
    # the server for the same GM transfer used on entry, after real revival.
    if not player_state.ready or int(player_state.vitals.get("health_pct",0))<=0:
        status="Fuera de Connacht: esperando recuperación del servidor"
        return
    if not gm_mode.ready or gm_mode.uncertain or not gm_mode.pending.is_empty() or gm_mode.combat_test:
        status="Fuera de Connacht: esperando confirmación de GM protegido"
        return
    if test_return_attempts>=3:
        status="No se confirmó el regreso GM a Ardee. La región de destino no está implementada."
        return
    if now-test_return_at<5000:return
    test_return_at=now;test_return_attempts+=1;home_jump_requested=true
    server.command("/jump to %d %d %d 200" % [roundi(initial_spawn.x*40)+35*8192,roundi(initial_spawn.z*40)+51*8192,roundi(initial_spawn.y*40)])
    status="Vínculo fuera del mapa de prueba: solicitando regreso GM a Ardee"

'''
assert anchor in s;s=s.replace(anchor,new+anchor).replace('    player_state.advance(now)','    recover_test_region(now)\n    player_state.advance(now)');p.write_text(s,encoding='utf-8')
for base in ['UnrealPlugin/DAoCVisualBridge','GMCombatTest/NativeHost/Plugins/DAoCVisualBridge']:
 p=R/base/'Source/DAoCVisualBridge/Private/DAoCBridgeCharacter.cpp';s=p.read_text(encoding='utf-8');a='SetActorLocation(Feet+FVector(0,0,GetCapsuleComponent()->GetScaledCapsuleHalfHeight()),false,nullptr,ETeleportType::TeleportPhysics);';b=a+'''if(CameraArm){const bool Lag=CameraArm->bEnableCameraLag;CameraArm->bEnableCameraLag=false;CameraArm->TickComponent(0.f,LEVELTICK_All,nullptr);CameraArm->bEnableCameraLag=Lag;}''';assert a in s;s=s.replace(a,b);p.write_text(s,encoding='utf-8')
 p=R/base/'Source/DAoCVisualBridge/Private/DAoCBridgeSubsystem.cpp';s=p.read_text(encoding='utf-8');a='if(IsValid(PlayerPawn))PlayerPawn->TeleportFeet(Position);';b='''if(IsValid(PlayerPawn)){PlayerPawn->TeleportFeet(Position);PreviousFeet=Position;if(IsValid(Camera)){Camera->AttachToComponent(PlayerPawn->CameraArm,FAttachmentTransformRules::SnapToTargetNotIncludingScale,USpringArmComponent::SocketName);if(auto* PC=GetWorld()->GetFirstPlayerController())PC->SetViewTarget(Camera);}}''';assert a in s;s=s.replace(a,b);p.write_text(s,encoding='utf-8')
 p=R/base/'Source/DAoCVisualBridge/Private/DAoCBridgePlayerStatusAcceptance.cpp';s=p.read_text(encoding='utf-8').replace('#include "Engine/StaticMeshActor.h"','#include "Engine/StaticMeshActor.h"\n#include "Camera/CameraActor.h"\n#include "GameFramework/SpringArmComponent.h"');a='bControls=true;Outgoing.Empty();';b='''const FVector BeforeTeleportCamera=Camera->GetActorLocation();const FVector RespawnFeet=PlayerPawn->FeetPosition()+FVector(12000,18000,0);PlayerPawn->TeleportFeet(RespawnFeet);Check(PlayerPawn->FeetPosition().Equals(RespawnFeet,.01f),TEXT("server respawn transfer moves pawn to exact destination"));Check(FVector::Dist(Camera->GetActorLocation(),RespawnFeet)<600,TEXT("camera immediately follows respawn instead of retaining corpse position"));Check(FVector::Dist(Camera->GetActorLocation(),BeforeTeleportCamera)>10000,TEXT("camera leaves original death area in same update"));Check(PlayerPawn->CameraArm->bEnableCameraLag,TEXT("normal camera lag restored after teleport reset"));bControls=true;Outgoing.Empty();''';assert a in s;s=s.replace(a,b);p.write_text(s,encoding='utf-8')
print('Recuperación de región de prueba y cámara preparadas')
