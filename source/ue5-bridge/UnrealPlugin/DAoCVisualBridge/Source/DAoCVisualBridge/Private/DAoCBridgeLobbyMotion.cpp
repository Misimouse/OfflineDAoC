#include "DAoCBridgeLobbyMotion.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Engine/StaticMeshActor.h"
#include "Components/StaticMeshComponent.h"
#include "Materials/MaterialInterface.h"
#include "Engine/Texture2D.h"

namespace {
TArray<TSharedPtr<FJsonValue>> Values(TSharedPtr<FJsonObject> O,const TCHAR* Key){const TArray<TSharedPtr<FJsonValue>>* A=nullptr;return O&&O->TryGetArrayField(Key,A)?*A:TArray<TSharedPtr<FJsonValue>>{};}
TArray<FVector> Vectors(const TArray<TSharedPtr<FJsonValue>>& A){TArray<FVector> V;for(int32 I=0;I+2<A.Num();I+=3)V.Add(FVector(A[I]->AsNumber(),A[I+1]->AsNumber(),A[I+2]->AsNumber()));return V;}
TArray<double> Numbers(const TArray<TSharedPtr<FJsonValue>>& A){TArray<double> V;for(auto X:A)V.Add(X->AsNumber());return V;}
}
TSharedPtr<FDAoCLobbyMotion> FDAoCLobbyMotion::Load(AStaticMeshActor* Actor,const FString& Path){
    FString Text;TSharedPtr<FJsonObject> Data;
    if(!Actor||!FFileHelper::LoadFileToString(Text,*Path)||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Data)||!Data||Data->GetIntegerField(TEXT("version"))!=1||Data->GetIntegerField(TEXT("triangles"))!=62798)return nullptr;
    auto Motion=MakeShared<FDAoCLobbyMotion>();TMap<FString,int32> Slots;int32 Triangles=0;
    for(auto Value:Values(Data,TEXT("surfaces"))){
        auto Row=Value->AsObject();const FString Material=Row->GetStringField(TEXT("material"));
        int32 Index;if(auto* Found=Slots.Find(Material))Index=*Found;else{Index=Motion->Sections.AddDefaulted();Slots.Add(Material,Index);Motion->Sections[Index].Material=Material;}
        auto& Section=Motion->Sections[Index];const int32 Offset=Section.Vertices.Num();auto Vertices=Vectors(Values(Row,TEXT("vertices")));const int32 Count=Vertices.Num();
        if(Count==0)return nullptr;Section.Vertices.Append(Vertices);Section.Normals.Append(Vectors(Values(Row,TEXT("normals"))));
        const auto Indices=Values(Row,TEXT("indices"));if(Indices.Num()%3)return nullptr;Triangles+=Indices.Num()/3;
        for(int32 I=0;I<Indices.Num();I+=3){Section.Indices.Add(Offset+int32(Indices[I]->AsNumber()));Section.Indices.Add(Offset+int32(Indices[I+2]->AsNumber()));Section.Indices.Add(Offset+int32(Indices[I+1]->AsNumber()));}
        const auto UVs=Values(Row,TEXT("uvs"));if(UVs.Num()!=4)return nullptr;
        for(int32 C=0;C<4;++C){auto A=UVs[C]->AsArray();if(A.Num()!=Count*2)return nullptr;for(int32 I=0;I<A.Num();I+=2)Section.UV[C].Add(FVector2D(A[I]->AsNumber(),A[I+1]->AsNumber()));}
        const auto Colors=Values(Row,TEXT("colours"));if(Colors.Num()!=Count*4)return nullptr;for(int32 I=0;I<Colors.Num();I+=4)Section.Colors.Add(FLinearColor(Colors[I]->AsNumber(),Colors[I+1]->AsNumber(),Colors[I+2]->AsNumber(),Colors[I+3]->AsNumber()));
        if(Row->HasField(TEXT("billboard_origin"))){auto O=Vectors(Values(Row,TEXT("billboard_origin"))),T=Vectors(Values(Row,TEXT("billboard_toward")));if(O.Num()!=1||T.Num()!=1)return nullptr;FBillboard B;B.Section=Index;B.Offset=Offset;B.Origin=O[0];B.Toward=T[0];B.Base=Vertices;B.Animated=Row->HasField(TEXT("controller"));Motion->Billboards.Add(MoveTemp(B));Section.Moving=true;}
        const TSharedPtr<FJsonObject>* Controller=nullptr;
        if(Row->TryGetObjectField(TEXT("controller"),Controller)){
            FController M;M.Section=Index;M.Offset=Offset;M.Base=MoveTemp(Vertices);auto C=*Controller;M.Start=C->GetNumberField(TEXT("start"));M.Stop=C->GetNumberField(TEXT("stop"));M.Frequency=C->GetNumberField(TEXT("frequency"));M.Phase=C->GetNumberField(TEXT("phase"));M.Cycle=C->GetStringField(TEXT("cycle"));M.Times=Numbers(Values(C,TEXT("times")));
            for(auto W:Values(C,TEXT("weights")))M.Weights.Add(Numbers(W->AsArray()));
            for(auto Shape:Values(Row,TEXT("shapes"))){auto P=Vectors(Shape->AsArray());if(P.Num()!=Count)return nullptr;M.Shapes.Add(MoveTemp(P));}
            if(M.Times.IsEmpty()||M.Times.Num()!=M.Weights.Num()||M.Stop<=M.Start)return nullptr;
            for(const auto& W:M.Weights)if(W.Num()!=M.Shapes.Num())return nullptr;
            Motion->Controllers.Add(MoveTemp(M));Section.Moving=true;
        }
    }
    if(Triangles!=62798||Motion->Controllers.Num()!=325)return nullptr;
    auto* Component=NewObject<UProceduralMeshComponent>(Actor,NAME_None,RF_Transient);Actor->AddInstanceComponent(Component);Component->SetupAttachment(Actor->GetRootComponent());Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);Component->SetCastShadow(false);Component->SetVisibleInSceneCaptureOnly(true);Component->SetCanEverAffectNavigation(false);Component->RegisterComponent();
    Motion->Mesh=Component;
    FString MaterialRoot=TEXT("/DAoCVisualBridge/Pregame_v03");Data->TryGetStringField(TEXT("material_root"),MaterialRoot);
    for(int32 I=0;I<Motion->Sections.Num();++I){auto& S=Motion->Sections[I];Component->CreateMeshSection_LinearColor(I,S.Vertices,S.Indices,S.Normals,S.UV[0],S.UV[1],S.UV[2],S.UV[3],S.Colors,S.Tangents,false,false);const FString Material=MaterialRoot+TEXT("/M_Layered_")+S.Material;Component->SetMaterial(I,LoadObject<UMaterialInterface>(nullptr,*Material));}
    Component->SetTextureForceResidentFlag(true);Component->PrestreamTextures(30,true);
    // Procedural sections do not supply the static mesh's texture-streaming
    // UV-density data. Explicit residency is bounded to this small menu scene.
    for(int32 I=0;I<Component->GetNumMaterials();++I)if(auto* Material=Component->GetMaterial(I)){
        TArray<UTexture*> Textures;Material->GetUsedTextures(Textures,EMaterialQualityLevel::High,false,ERHIFeatureLevel::SM5,false);
        for(auto* Texture:Textures)if(auto* Image=Cast<UTexture2D>(Texture)){Image->SetForceMipLevelsToBeResident(60);Motion->ResidentTextures.AddUnique(Image);}
    }
    Motion->LoadAmbient(Actor,FPaths::GetPath(Path)/TEXT("lobby_particles.json"));
    Actor->GetStaticMeshComponent()->SetVisibility(false);Motion->Began=FPlatformTime::Seconds();Motion->Tick();return Motion;
}
void FDAoCLobbyMotion::Tick(){
    if(!IsValid(Mesh))return;const double Now=FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeLobbyMotionStill"))?0:FPlatformTime::Seconds()-Began;if(Now-Last<1./30)return;Last=Now;
    if(Now-LastResidency>10){for(auto Texture:ResidentTextures)if(Texture.IsValid())Texture->SetForceMipLevelsToBeResident(60);LastResidency=Now;}
    TickAmbient(Now);
    for(const auto& M:Controllers){
        const double Span=FMath::Max(M.Stop-M.Start,.0001);double Time=Now*M.Frequency+M.Phase;
        if(M.Cycle==TEXT("clamp"))Time=FMath::Clamp(Time,M.Start,M.Stop);
        else if(M.Cycle==TEXT("reverse")){double U=FMath::Fmod(Time-M.Start,Span*2);if(U<0)U+=Span*2;Time=M.Start+(U<=Span?U:Span*2-U);}
        else{double U=FMath::Fmod(Time-M.Start,Span);if(U<0)U+=Span;Time=M.Start+U;}
        int32 A=0;while(A+1<M.Times.Num()&&M.Times[A+1]<Time)++A;const int32 B=FMath::Min(A+1,M.Times.Num()-1);const double T=A==B?0:FMath::Clamp((Time-M.Times[A])/FMath::Max(M.Times[B]-M.Times[A],.0001),0.,1.);
        TArray<double> Weights;double Sum=0;for(int32 I=0;I<M.Shapes.Num();++I){const double W=FMath::Lerp(M.Weights[A][I],M.Weights[B][I],T);Weights.Add(W);Sum+=W;}
        auto& Out=Sections[M.Section].Vertices;for(int32 V=0;V<M.Base.Num();++V){FVector P=M.Base[V]*(1-Sum);for(int32 I=0;I<M.Shapes.Num();++I)P+=M.Shapes[I][V]*Weights[I];Out[M.Offset+V]=P;}
    }
    for(const auto& B:Billboards){auto& Out=Sections[B.Section].Vertices;const FQuat Rotation=FQuat::FindBetweenNormals(B.Toward,(Camera-B.Origin).GetSafeNormal());for(int32 V=0;V<B.Base.Num();++V){const FVector P=B.Animated?Out[B.Offset+V]:B.Base[V];Out[B.Offset+V]=B.Origin+Rotation.RotateVector(P-B.Origin);}}
    for(int32 I=0;I<Sections.Num();++I){auto& S=Sections[I];if(S.Moving)Mesh->UpdateMeshSection_LinearColor(I,S.Vertices,S.Normals,S.UV[0],S.UV[1],S.UV[2],S.UV[3],S.Colors,S.Tangents,false);}
}

void FDAoCLobbyMotion::LoadAmbient(AStaticMeshActor* Actor,const FString& Path){
    FString Text;TSharedPtr<FJsonObject> Data;
    if(!FFileHelper::LoadFileToString(Text,*Path)||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Data)||!Data||Data->GetIntegerField(TEXT("version"))!=1)return;
    for(auto V:Values(Data,TEXT("emitters"))){
        auto Spec=V->AsObject();if(!Spec||Spec->GetStringField(TEXT("blend"))!=TEXT("add")||Spec->GetStringField(TEXT("texture"))!=TEXT("grnglow"))continue;
        auto* Material=LoadObject<UMaterialInterface>(nullptr,*Spec->GetStringField(TEXT("material")));if(!Material)continue;
        FAmbientEmitter E;E.Spec=Spec;E.Slots=FMath::Clamp(FMath::CeilToInt(Spec->GetNumberField(TEXT("emit_rate"))*Spec->GetNumberField(TEXT("lifetime"))),1,512);
        for(int32 I=0;I<E.Slots;++I){E.Indices.Append({I*4,I*4+1,I*4+2,I*4,I*4+2,I*4+3});E.UV.Append({{0,0},{1,0},{1,1},{0,1}});}
        E.Vertices.SetNumZeroed(E.Slots*4);E.Normals.Init(FVector::UpVector,E.Slots*4);E.Colors.Init(FLinearColor::Transparent,E.Slots*4);
        auto* C=NewObject<UProceduralMeshComponent>(Actor,NAME_None,RF_Transient);Actor->AddInstanceComponent(C);C->SetupAttachment(Actor->GetRootComponent());C->SetCollisionEnabled(ECollisionEnabled::NoCollision);C->SetCanEverAffectNavigation(false);C->SetCastShadow(false);C->SetVisibleInSceneCaptureOnly(true);C->SetReceivesDecals(false);C->RegisterComponent();C->SetMaterial(0,Material);C->SetTextureForceResidentFlag(true);
        TArray<FProcMeshTangent> Tangents;C->CreateMeshSection_LinearColor(0,E.Vertices,E.Indices,E.Normals,E.UV,E.Colors,Tangents,false,false);E.Mesh=C;Ambient.Add(MoveTemp(E));
        TArray<UTexture*> Textures;Material->GetUsedTextures(Textures,EMaterialQualityLevel::High,false,ERHIFeatureLevel::SM5,false);for(auto* Texture:Textures)if(auto* Image=Cast<UTexture2D>(Texture)){Image->SetForceMipLevelsToBeResident(60);ResidentTextures.AddUnique(Image);}
    }
}
void FDAoCLobbyMotion::TickAmbient(double Time){
    for(auto& E:Ambient){
        if(!IsValid(E.Mesh))continue;const auto Spec=E.Spec;const double Life=Spec->GetNumberField(TEXT("lifetime")),Rate=Spec->GetNumberField(TEXT("emit_rate"));if(Life<=0||Rate<=0)continue;
        const auto Emitter=Spec->GetObjectField(TEXT("emitter"));const auto Origin=Emitter->GetArrayField(TEXT("origin")),Basis=Emitter->GetArrayField(TEXT("basis")),Box=Spec->GetArrayField(TEXT("box"));
        // Original coordinates are metres, Y up. Transform there before changing
        // to Unreal centimetres; this preserves the complete rotated source box.
        auto ToUnreal=[&](FVector P){FVector O;for(int32 A=0;A<3;++A){auto Row=Basis[A]->AsArray();O[A]=Origin[A]->AsNumber()+Row[0]->AsNumber()*P.X+Row[1]->AsNumber()*P.Y+Row[2]->AsNumber()*P.Z;}return FVector(O.X,O.Z,O.Y)*100;};
        const double Clock=Time+Life;const int32 LastBorn=FMath::FloorToInt(Clock*Rate);
        for(int32 I=0;I<E.Slots;++I){const int32 Seed=LastBorn-I;FRandomStream Random(Seed*196613+1777);const double Age=Clock-Seed/Rate;
            FVector P((Random.FRand()-.5)*Box[0]->AsNumber(),(Random.FRand()-.5)*Box[1]->AsNumber(),(Random.FRand()-.5)*Box[2]->AsNumber());
            const double Decl=Spec->GetNumberField(TEXT("declination"))+(Random.FRand()*2-1)*Spec->GetNumberField(TEXT("declination_variation")),Plan=Spec->GetNumberField(TEXT("planar_angle"))+(Random.FRand()*2-1)*Spec->GetNumberField(TEXT("planar_angle_variation"));
            const double Speed=FMath::Max(0.,Spec->GetNumberField(TEXT("speed"))+(Random.FRand()*2-1)*Spec->GetNumberField(TEXT("speed_random")));
            P+=FVector(FMath::Sin(Decl)*FMath::Sin(Plan),FMath::Cos(Decl),FMath::Sin(Decl)*FMath::Cos(Plan))*Speed*Age;P=ToUnreal(P);
            double Radius=Spec->GetNumberField(TEXT("size"))*100;for(auto V:Values(Spec,TEXT("modifiers"))){auto M=V->AsObject();if(M->GetStringField(TEXT("type"))==TEXT("growfade")){const double Grow=M->GetNumberField(TEXT("grow")),Fade=M->GetNumberField(TEXT("fade"));if(Grow>0)Radius*=FMath::Clamp(Age/Grow,0.,1.);if(Fade>0)Radius*=FMath::Clamp((Life-Age)/Fade,0.,1.);}}
            const FVector Toward=(Camera-P).GetSafeNormal(),Right=FVector::CrossProduct(FVector::UpVector,Toward).GetSafeNormal()*Radius,Up=FVector::CrossProduct(Toward,Right.GetSafeNormal())*Radius;
            E.Vertices[I*4]=P-Right-Up;E.Vertices[I*4+1]=P+Right-Up;E.Vertices[I*4+2]=P+Right+Up;E.Vertices[I*4+3]=P-Right+Up;for(int32 J=0;J<4;++J)E.Colors[I*4+J]=Age<Life?FLinearColor::White:FLinearColor::Transparent;
        }
        E.Mesh->UpdateMeshSection_LinearColor(0,E.Vertices,E.Normals,E.UV,E.Colors,TArray<FProcMeshTangent>(),false);
    }
}
bool FDAoCLobbyMotion::CheckAmbientMotion(){
    if(Ambient.Num()!=1||Ambient[0].Slots!=180)return false;
    TickAmbient(0);const auto Before=Ambient[0].Vertices;TickAmbient(.5);const auto After=Ambient[0].Vertices;
    bool Valid=Before.Num()==720&&After.Num()==720;
    for(const auto& P:After)Valid=Valid&&!P.ContainsNaN();
    // A full-grown original sprite is 12.5 cm wide. Checking actual submitted
    // geometry catches radius/diameter and metre/centimetre conversion mistakes.
    Valid=Valid&&FMath::IsNearlyEqual(FVector::Distance(After[40],After[41]),12.5,.001)&&!Before[40].Equals(After[40],.01);
    const FVector Saved=Camera;Camera+=FVector(700,300,200);TickAmbient(.5);
    Valid=Valid&&!Ambient[0].Vertices[40].Equals(After[40],.001);Camera=Saved;TickAmbient(FPlatformTime::Seconds()-Began);return Valid;
}
