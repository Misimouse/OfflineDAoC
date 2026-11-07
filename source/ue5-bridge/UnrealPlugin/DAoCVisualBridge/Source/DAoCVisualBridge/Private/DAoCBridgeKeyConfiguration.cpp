#include "DAoCBridgeKeyConfiguration.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/Paths.h"

FBridgeKeyConfiguration::FBridgeKeyConfiguration(){
    auto Add=[&](const TCHAR* Id,const TCHAR* Label,const TCHAR* Key,bool Held=false){Actions.Add({Id,Label,{Key},{Key},Held});};
    Add(TEXT("move_forward"),TEXT("Move Forward"),TEXT("W"),true);
    Add(TEXT("move_back"),TEXT("Move Backward"),TEXT("S"),true);
    Add(TEXT("strafe_left"),TEXT("Strafe Left"),TEXT("A"),true);
    Add(TEXT("strafe_right"),TEXT("Strafe Right"),TEXT("D"),true);
    Add(TEXT("jump"),TEXT("Jump / Dismount"),TEXT("SpaceBar"));
    Add(TEXT("walk"),TEXT("Walk"),TEXT("ScrollLock"));
    Add(TEXT("run_lock"),TEXT("Run Lock"),TEXT("NumLock"));
    Add(TEXT("face"),TEXT("Face"),TEXT("F"));
    Add(TEXT("follow"),TEXT("Follow"),TEXT("Shift+F"));
    Add(TEXT("stick"),TEXT("Stick"),TEXT("Shift+V"));
    auto UI=[&](const TCHAR* Id,const TCHAR* Label,const TCHAR* Key,const TCHAR* Category=TEXT("Show")){Add(Id,Label,Key);Actions.Last().Category=Category;};
    UI(TEXT("show_stats"),TEXT("Show Stats"),TEXT("P"));
    UI(TEXT("show_inventory"),TEXT("Show Inventory"),TEXT("I"));
    UI(TEXT("show_skills"),TEXT("Show Skills"),TEXT("H"));
    UI(TEXT("show_spells"),TEXT("Show Spells"),TEXT(""));
    UI(TEXT("show_combat"),TEXT("Show Combat"),TEXT("J"));
    UI(TEXT("show_group"),TEXT("Show Group"),TEXT("G"));
    UI(TEXT("show_map"),TEXT("Map Window"),TEXT("M"));
    UI(TEXT("show_journal"),TEXT("Quest Journal"),TEXT("L"));
    UI(TEXT("show_trainer"),TEXT("Training Window"),TEXT("T"));
    UI(TEXT("target_self"),TEXT("Target Self"),TEXT("F7"),TEXT("Targeting"));
    UI(TEXT("target_enemy"),TEXT("Nearest Enemy"),TEXT("Tab"),TEXT("Targeting"));
    UI(TEXT("interact"),TEXT("Interact"),TEXT("E"),TEXT("Targeting"));
    UI(TEXT("inspect_item"),TEXT("Inspect Item"),TEXT("Shift+I"),TEXT("Targeting"));
    UI(TEXT("attack_mode"),TEXT("Attack Mode"),TEXT("C"),TEXT("Combat"));
    UI(TEXT("sit"),TEXT("Sit/Stand"),TEXT("N"),TEXT("Combat"));
    for(int32 Bar=1;Bar<=3;++Bar)for(int32 Slot=1;Slot<=10;++Slot){
        const FString Id=FString::Printf(TEXT("qb%d_%d"),Bar,Slot),Label=FString::Printf(TEXT("Quickbar %d Slot %d"),Bar,Slot);
        const FString Key=FString(Bar==3?TEXT("Ctrl+"):Bar==2?TEXT("Alt+"):TEXT(""))+FString(Slot==10?TEXT("Zero"):Slot==1?TEXT("One"):Slot==2?TEXT("Two"):Slot==3?TEXT("Three"):Slot==4?TEXT("Four"):Slot==5?TEXT("Five"):Slot==6?TEXT("Six"):Slot==7?TEXT("Seven"):Slot==8?TEXT("Eight"):TEXT("Nine"));
        UI(*Id,*Label,*Key,TEXT("Quickbars"));
    }
    for(int32 Bank=1;Bank<=10;++Bank){
        const FString Id=FString::Printf(TEXT("qbank_%d"),Bank),Label=FString::Printf(TEXT("Quickbar Bank %d"),Bank);
        const FString Key=TEXT("Shift+")+Find(FString::Printf(TEXT("qb1_%d"),Bank))->Defaults[0];UI(*Id,*Label,*Key,TEXT("Quickbar Banks"));
    }
}
FBridgeKeyConfiguration::FAction* FBridgeKeyConfiguration::Find(const FString& Id){return Actions.FindByPredicate([&](const FAction& A){return A.Id==Id;});}
const FBridgeKeyConfiguration::FAction* FBridgeKeyConfiguration::Find(const FString& Id)const{return Actions.FindByPredicate([&](const FAction& A){return A.Id==Id;});}
bool FBridgeKeyConfiguration::Reserved(const FKey& Key){
    // Menu, chat, camera/GM keys and pointer gestures remain outside this editable surface.
    for(const FKey K:{EKeys::Escape,EKeys::Enter,EKeys::LeftMouseButton,EKeys::RightMouseButton,EKeys::MiddleMouseButton,
        EKeys::MouseScrollUp,EKeys::MouseScrollDown,EKeys::LeftShift,EKeys::RightShift,EKeys::LeftControl,EKeys::RightControl,EKeys::LeftAlt,EKeys::RightAlt,
        EKeys::LeftCommand,EKeys::RightCommand,EKeys::F1,EKeys::F2,EKeys::F3,EKeys::F4,EKeys::F5,EKeys::F6,EKeys::F8,EKeys::F9,EKeys::F10,EKeys::F11,EKeys::F12,
        EKeys::PageUp,EKeys::PageDown})if(Key==K)return true;
    return false;
}
bool FBridgeKeyConfiguration::Parse(const FString& Text,FChord& Out){
    Out={};if(Text.IsEmpty()||Text.Len()>80)return false;TArray<FString> Parts;Text.ParseIntoArray(Parts,TEXT("+"),false);
    for(int32 I=0;I<Parts.Num()-1;++I){if(Parts[I]==TEXT("Shift")&&!Out.Shift)Out.Shift=true;else if(Parts[I]==TEXT("Ctrl")&&!Out.Ctrl)Out.Ctrl=true;else if(Parts[I]==TEXT("Alt")&&!Out.Alt)Out.Alt=true;else return false;}
    if(Parts.IsEmpty())return false;Out.Key=FKey(*Parts.Last());return Out.Key.IsValid()&&!Out.Key.IsAxis1D()&&!Out.Key.IsAxis2D()&&!Out.Key.IsAxis3D()&&!Out.Key.IsGamepadKey()&&!Reserved(Out.Key);
}
FString FBridgeKeyConfiguration::Describe(FKey Key,bool Shift,bool Ctrl,bool Alt){return (Ctrl?FString(TEXT("Ctrl+")):FString())+(Alt?TEXT("Alt+"):TEXT(""))+(Shift?TEXT("Shift+"):TEXT(""))+Key.GetFName().ToString();}
bool FBridgeKeyConfiguration::Matches(const FChord& C,FKey Key,bool Shift,bool Ctrl,bool Alt,bool Held){return C.Key==Key&&C.Ctrl==Ctrl&&C.Alt==Alt&&(C.Shift==Shift||(Held&&!C.Shift));}
FString FBridgeKeyConfiguration::Text(const FString& Id,int32 Slot)const{const auto* A=Find(Id);return A&&A->Bindings.IsValidIndex(Slot)&&!A->Bindings[Slot].IsEmpty()?A->Bindings[Slot]:TEXT("-");}
bool FBridgeKeyConfiguration::Bind(const FString& Id,int32 Slot,const FString& Value,FString& Message){
    auto* A=Find(Id);if(!A||Slot<0||Slot>1){Message=TEXT("Invalid binding.");return false;}
    FChord C;if(!Value.IsEmpty()&&!Parse(Value,C)){Message=TEXT("That key is reserved for another control.");return false;}
    // Held movement permits extra Shift for walking; avoid ambiguous cross-action chords on that key.
    if(!Value.IsEmpty())for(const auto& Other:Actions)for(const auto& B:Other.Bindings){FChord D;if(Other.Id!=Id&&Parse(B,D)&&C.Key==D.Key&&(A->Held||Other.Held)){Message=TEXT("Clear the other action using this movement key first.");return false;}}
    Message=TEXT("Changes are saved automatically.");
    if(!Value.IsEmpty())for(auto& Other:Actions)for(int32 I=0;I<Other.Bindings.Num();++I){FChord D;if(Parse(Other.Bindings[I],D)&&D.Key==C.Key&&D.Shift==C.Shift&&D.Ctrl==C.Ctrl&&D.Alt==C.Alt&&!(Other.Id==Id&&I==Slot)){Other.Bindings[I].Empty();Message=TEXT("Moved from ")+Other.Label+TEXT(".");}}
    while(A->Bindings.Num()<2)A->Bindings.Add(TEXT(""));A->Bindings[Slot]=Value;return true;
}
bool FBridgeKeyConfiguration::Pressed(APlayerController* PC,const FString& Id)const{
    const auto* A=Find(Id);if(!PC||!A)return false;bool S=PC->IsInputKeyDown(EKeys::LeftShift)||PC->IsInputKeyDown(EKeys::RightShift),C=PC->IsInputKeyDown(EKeys::LeftControl)||PC->IsInputKeyDown(EKeys::RightControl),T=PC->IsInputKeyDown(EKeys::LeftAlt)||PC->IsInputKeyDown(EKeys::RightAlt);
    for(const auto& B:A->Bindings){FChord D;if(Parse(B,D)&&PC->WasInputKeyJustPressed(D.Key)&&Matches(D,D.Key,S,C,T,false))return true;}return false;
}
bool FBridgeKeyConfiguration::Held(APlayerController* PC,const FString& Id)const{
    const auto* A=Find(Id);if(!PC||!A)return false;bool S=PC->IsInputKeyDown(EKeys::LeftShift)||PC->IsInputKeyDown(EKeys::RightShift),C=PC->IsInputKeyDown(EKeys::LeftControl)||PC->IsInputKeyDown(EKeys::RightControl),T=PC->IsInputKeyDown(EKeys::LeftAlt)||PC->IsInputKeyDown(EKeys::RightAlt);
    for(const auto& B:A->Bindings){FChord D;if(Parse(B,D)&&PC->IsInputKeyDown(D.Key)&&Matches(D,D.Key,S,C,T,true))return true;}return false;
}
void FBridgeKeyConfiguration::Reset(){for(auto& A:Actions)A.Bindings=A.Defaults;}
void FBridgeKeyConfiguration::Load(const FString& File){
    Path=File;Reset();FConfigFile Config;Config.Read(File);
    // Stage the entire saved map first so swaps do not conflict with defaults. Invalid files keep defaults.
    auto Saved=Actions;for(auto& A:Actions)for(int32 I=0;I<2;++I){FString V;if(Config.GetString(TEXT("Bindings"),*(A.Id+FString::FromInt(I)),V)){FChord D;if(!V.IsEmpty()&&!Parse(V,D)){Actions=Saved;return;}while(A.Bindings.Num()<2)A.Bindings.Add(TEXT(""));A.Bindings[I]=V;}}
    for(int32 I=0;I<Actions.Num();++I)for(int32 J=I;J<Actions.Num();++J)for(int32 X=0;X<Actions[I].Bindings.Num();++X)for(int32 Y=0;Y<Actions[J].Bindings.Num();++Y){if(I==J&&X>=Y)continue;FChord C,D;if(Parse(Actions[I].Bindings[X],C)&&Parse(Actions[J].Bindings[Y],D)&&C.Key==D.Key&&((I!=J&&(Actions[I].Held||Actions[J].Held))||(C.Shift==D.Shift&&C.Ctrl==D.Ctrl&&C.Alt==D.Alt))){Actions=Saved;return;}}
}
bool FBridgeKeyConfiguration::Save()const{if(Path.IsEmpty())return false;IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path),true);FConfigFile Config;Config.SetString(TEXT("KeyConfiguration"),TEXT("Version"),TEXT("1"));for(const auto& A:Actions)for(int32 I=0;I<2;++I)Config.SetString(TEXT("Bindings"),*(A.Id+FString::FromInt(I)),A.Bindings.IsValidIndex(I)?*A.Bindings[I]:TEXT(""));return Config.Write(Path);}
