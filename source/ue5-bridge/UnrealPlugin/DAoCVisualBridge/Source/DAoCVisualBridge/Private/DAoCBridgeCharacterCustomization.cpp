#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeAppearance.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Widgets/SCanvas.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SSlider.h"
#include "Widgets/Text/STextBlock.h"
#include "Styling/CoreStyle.h"
#include "Engine/World.h"
#include "Components/SceneCaptureComponent2D.h"
namespace {
TSharedPtr<FJsonObject> Object(TSharedPtr<FJsonObject> O,const FString& K){const TSharedPtr<FJsonObject>* V=nullptr;return O&&O->TryGetObjectField(K,V)?*V:nullptr;}
TArray<TSharedPtr<FJsonValue>> Array(TSharedPtr<FJsonObject> O,const TCHAR* K){const TArray<TSharedPtr<FJsonValue>>* V=nullptr;return O&&O->TryGetArrayField(K,V)?*V:TArray<TSharedPtr<FJsonValue>>{};}
FString String(TSharedPtr<FJsonObject> O,const TCHAR* K){FString V;if(O)O->TryGetStringField(K,V);return V;}
int32 Number(TSharedPtr<FJsonObject> O,const FString& K,int32 D=0){double V=D;if(O)O->TryGetNumberField(K,V);return int32(V);}
}
TSharedRef<SWidget> UDAoCBridgeSubsystem::BuildCharacterCustomization(double Width){
    auto Canvas=SNew(SCanvas).Visibility(EVisibility::SelfHitTestInvisible);const FString Path=DAoCAppearancePath();FString Text;TSharedPtr<FJsonObject> Catalog;
    if(Path.IsEmpty()||!FFileHelper::LoadFileToString(Text,*Path)||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Catalog))return Canvas;
    auto Figure=Object(Object(Catalog,TEXT("figures")),FString::FromInt(CharacterLobbyPreviewModel)),Meta=Object(Figure,TEXT("meta")),Swatches=Object(Figure,TEXT("swatches"));
    if(!Meta||!Swatches)return Canvas;if(!CharacterLobbyLook)CharacterLobbyLook=MakeShared<FJsonObject>();
    const double Shift=Width-1024;const FLinearColor Gold(1,.84,.45),Cream(.93,.89,.78);
    auto At=[Canvas](double X,double Y,double W,double H,TSharedRef<SWidget> Widget){Canvas->AddSlot().Position(FVector2D(X,Y)).Size(FVector2D(W,H))[Widget];};
    auto Label=[&](const FString& Value,double X,double Y,double W,int32 Size=15,bool Center=false){At(X,Y,W,26,SNew(STextBlock).Text(FText::FromString(Value.ToUpper())).Font(FSlateFontInfo(FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/InterfaceFonts/minionpro-bold.ttf"),FMath::RoundToInt(Size*.75))).ColorAndOpacity(Cream).Visibility(EVisibility::HitTestInvisible).Justification(Center?ETextJustify::Center:ETextJustify::Left));};
    auto ImageButton=[&](double X,double Y,double W,double H,FVector2D Min,FVector2D Max,TFunction<void()> Action){TSharedPtr<FButtonStyle> Style=MakeShared<FButtonStyle>(FCoreStyle::Get().GetWidgetStyle<FButtonStyle>("NoBorder"));CharacterLobbyButtonStyles.Add(Style);auto Brush=*ClassicArt(TEXT("Pregame/misc_pieces_new"),Min/256.,Max/256.);Style->SetNormal(Brush);Style->SetHovered(Brush);Style->SetPressed(Brush);At(X,Y,W,H,SNew(SButton).IsFocusable(false).ButtonStyle(Style.Get()).ContentPadding(0).OnClicked_Lambda([Action,Style](){Action();return FReply::Handled();}));};
    auto Commit=[this](){UpdateCharacterLobbyAppearance(CharacterLobbyLook);RefreshCharacterLobby();};
    auto Lock=[&](const FString& Key,double Y){const bool Locked=CharacterLobbyLookLocks.Contains(Key);ImageButton(990+Shift,Y+5,12,14,Locked?FVector2D(244,210):FVector2D(226,209),Locked?FVector2D(251,220):FVector2D(236,220),[this,Key](){if(CharacterLobbyLookLocks.Contains(Key))CharacterLobbyLookLocks.Remove(Key);else CharacterLobbyLookLocks.Add(Key);RefreshCharacterLobby();});};
    auto Stepper=[&](const FString& Title,const FString& Key,const TArray<FString>& Values,double& Y){if(Values.IsEmpty())return;const int32 Current=FMath::Clamp(Number(CharacterLobbyLook,Key,Key==TEXT("size")?1:0),0,Values.Num()-1);Label(Title,770+Shift,Y,96);Label(Values[Current],882+Shift,Y,88,15,true);Lock(Key,Y);
        for(int32 Side=0;Side<2;++Side)ImageButton(866+Shift+Side*104,Y+4,16,16,FVector2D(3+Side*23,200),FVector2D(19+Side*23,213),[this,Key,Current,Side,Count=Values.Num(),Meta,Commit](){const int32 Value=(Current+(Side?1:-1)+Count)%Count;CharacterLobbyLook->SetNumberField(Key,Value);if(Key==TEXT("hair")){auto Styles=Array(Meta,TEXT("hair_styles"));const int32 N=Array(Styles[Value]->AsObject(),TEXT("colours")).Num();CharacterLobbyLook->SetNumberField(TEXT("hair_color"),FMath::Clamp(Number(CharacterLobbyLook,TEXT("hair_color")),0,FMath::Max(N-1,0)));}Commit();});Y+=27;};
    auto SwatchRow=[&](const FString& Title,const FString& Key,const TArray<TSharedPtr<FJsonValue>>& Colors,double& Y){if(Colors.IsEmpty())return;Label(Title,770+Shift,Y,140);Lock(Key,Y);Y+=22;const int32 Current=Number(CharacterLobbyLook,Key);
        for(int32 I=0;I<Colors.Num();++I){const auto RGB=Colors[I]->AsArray();if(RGB.Num()!=3)continue;const FLinearColor Color=FLinearColor::FromSRGBColor(FColor(FMath::RoundToInt(RGB[0]->AsNumber()*255),FMath::RoundToInt(RGB[1]->AsNumber()*255),FMath::RoundToInt(RGB[2]->AsNumber()*255)));
            At(772+Shift+(I%8)*27,Y+(I/8)*24,24,21,SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush(TEXT("WhiteBrush"))).BorderBackgroundColor(I==Current?Gold:FLinearColor(.01,.01,.01)).Padding(I==Current?2:1)[SNew(SButton).IsFocusable(false).ButtonStyle(&FCoreStyle::Get().GetWidgetStyle<FButtonStyle>("NoBorder")).ContentPadding(0).OnClicked_Lambda([this,Key,I,Commit](){CharacterLobbyLook->SetNumberField(Key,I);Commit();return FReply::Handled();})[SNew(SBorder).Padding(0).BorderImage(FCoreStyle::Get().GetBrush(TEXT("WhiteBrush"))).BorderBackgroundColor(Color).Visibility(EVisibility::HitTestInvisible)]]);
        }Y+=FMath::CeilToInt(Colors.Num()/8.)*24+4;};
    auto Labels=[](const TArray<TSharedPtr<FJsonValue>>& A){TArray<FString> R;for(auto V:A)R.Add(String(V->AsObject(),TEXT("label")));return R;};
    Label(TEXT("FACIAL FEATURES"),760+Shift,64,248,22,true);double Y=100;
    Stepper(TEXT("FACE"),TEXT("face"),Labels(Array(Meta,TEXT("faces"))),Y);
    const auto Sliders=Array(Meta,TEXT("sliders")),Values=Array(CharacterLobbyLook,TEXT("sliders"));
    for(int32 I=0;I<Sliders.Num();++I){Label(String(Sliders[I]->AsObject(),TEXT("label")),770+Shift,Y,96);At(868+Shift,Y+2,118,20,SNew(SSlider).MinValue(0).MaxValue(8).StepSize(1).Value(I<Values.Num()?Values[I]->AsNumber():4).OnValueChanged_Lambda([this,I,N=Sliders.Num()](float V){auto A=Array(CharacterLobbyLook,TEXT("sliders"));while(A.Num()<N)A.Add(MakeShared<FJsonValueNumber>(4));A[I]=MakeShared<FJsonValueNumber>(FMath::Clamp(FMath::RoundToInt(V),0,8));CharacterLobbyLook->SetArrayField(TEXT("sliders"),A);UpdateCharacterLobbyAppearance(CharacterLobbyLook);}));Y+=27;}
    Y+=4;SwatchRow(TEXT("EYE COLOR"),TEXT("eyes"),Array(Swatches,TEXT("eyes")),Y);SwatchRow(TEXT("SKIN TONE"),TEXT("skin"),Array(Swatches,TEXT("skin")),Y);
    auto Styles=Array(Meta,TEXT("hair_styles"));Stepper(TEXT("HAIR STYLE"),TEXT("hair"),Labels(Styles),Y);const int32 Hair=FMath::Clamp(Number(CharacterLobbyLook,TEXT("hair")),0,FMath::Max(Styles.Num()-1,0));
    if(!Styles.IsEmpty()&&!String(Styles[Hair]->AsObject(),TEXT("node")).IsEmpty())SwatchRow(TEXT("HAIR COLOR"),TEXT("hair_color"),Array(Object(Swatches,TEXT("hair")),*FString::FromInt(Hair)),Y);
    Stepper(TEXT("SIZE"),TEXT("size"),{TEXT("SHORT"),TEXT("AVERAGE"),TEXT("TALL")},Y);Stepper(TEXT("TATTOO"),TEXT("tattoo"),Labels(Array(Meta,TEXT("tattoos"))),Y);
    auto TextButton=[&](const FString& Caption,double X,double RowY,TFunction<void()> Action){ImageButton(X,RowY,108,28,FVector2D(0,105),FVector2D(102,127),Action);Label(Caption,X,RowY+4,108,15,true);};
    TextButton(TEXT("RANDOM"),776+Shift,606,[this,Meta,Commit](){const TMap<FString,FString> Fields={{TEXT("face"),TEXT("faces")},{TEXT("eyes"),TEXT("eyes")},{TEXT("skin"),TEXT("skin_tones")},{TEXT("hair"),TEXT("hair_styles")},{TEXT("tattoo"),TEXT("tattoos")}};for(const auto& Field:Fields)if(!CharacterLobbyLookLocks.Contains(Field.Key))CharacterLobbyLook->SetNumberField(Field.Key,FMath::RandRange(0,FMath::Max(Array(Meta,*Field.Value).Num()-1,0)));if(!CharacterLobbyLookLocks.Contains(TEXT("size")))CharacterLobbyLook->SetNumberField(TEXT("size"),FMath::RandRange(0,2));auto Styles=Array(Meta,TEXT("hair_styles"));if(!Styles.IsEmpty()){const int32 N=Array(Styles[FMath::Clamp(Number(CharacterLobbyLook,TEXT("hair")),0,Styles.Num()-1)]->AsObject(),TEXT("colours")).Num();CharacterLobbyLook->SetNumberField(TEXT("hair_color"),CharacterLobbyLookLocks.Contains(TEXT("hair_color"))?FMath::Clamp(Number(CharacterLobbyLook,TEXT("hair_color")),0,FMath::Max(N-1,0)):FMath::RandRange(0,FMath::Max(N-1,0)));}TArray<TSharedPtr<FJsonValue>> Values;for(int32 I=0;I<Array(Meta,TEXT("sliders")).Num();++I)Values.Add(MakeShared<FJsonValueNumber>(FMath::RandRange(0,8)));CharacterLobbyLook->SetArrayField(TEXT("sliders"),Values);Commit();});
    TextButton(TEXT("DEFAULT"),892+Shift,606,[this,Commit](){CharacterLobbyLook=MakeShared<FJsonObject>();Commit();});
    const TArray<FVector2D> CameraMin={FVector2D(110,177),FVector2D(173,178),FVector2D(138,138),FVector2D(106,138)};const TArray<FVector2D> CameraSize={FVector2D(26,29),FVector2D(26,29),FVector2D(32,31),FVector2D(32,31)};
    for(int32 I=0;I<4;++I)ImageButton(30+I*36,600,30,30,CameraMin[I],CameraMin[I]+CameraSize[I],[this,I](){if(I<2){LobbyFigureYaw+=I==0?-20:20;if(CharacterLobbyPreviewActor)CharacterLobbyPreviewActor->SetActorRotation(FRotator(0,225+LobbyFigureYaw,0));}else LobbyZoom=FMath::Clamp(LobbyZoom+(I==2?-.15f:.15f),.25f,5.f);UpdateLobbyCamera();});
    Label(TEXT("LEFT DRAG: TURN CHARACTER   RIGHT DRAG: ORBIT   WHEEL: ZOOM"),30,574,550,11);
    return Canvas;
}
