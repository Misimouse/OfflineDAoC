#pragma once
#include "CoreMinimal.h"
#include "Dom/JsonObject.h"
#include "Misc/FileHelper.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

// Gameplay surface only. Never modifies the approved river actors or materials.
struct FBridgeWaterSample {
    bool Present=false,Swimming=false,Wading=false;
    float Height=0,TargetFeet=0;
    int32 Body=-1;
};
class FBridgeWaterData {
public:
    TArray<uint8> Mask;
    TMap<int32,float> Heights;
    float SizeMetres=0;
    bool Ready=false;
    bool Load(const FString& Path){
        Ready=false;Mask.Empty();Heights.Empty();FString Text;TSharedPtr<FJsonObject> Root;
        if(!FFileHelper::LoadFileToString(Text,*Path)||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root)||!Root)return false;
        auto Number=[](const TSharedPtr<FJsonObject>& O,const TCHAR* Key,double Fallback){double V=Fallback;if(O)O->TryGetNumberField(Key,V);return FMath::IsFinite(V)?V:Fallback;};
        if(Number(Root,TEXT("version"),0)!=1||Number(Root,TEXT("zone"),0)!=207||Number(Root,TEXT("width"),0)!=256||Number(Root,TEXT("height"),0)!=256||Number(Root,TEXT("dry_id"),0)!=255)return false;
        SizeMetres=Number(Root,TEXT("size_m"),0);if(FMath::Abs(SizeMetres-1638.4f)>.01)return false;
        const TSharedPtr<FJsonObject>* Bodies=nullptr;const TArray<TSharedPtr<FJsonValue>>* Runs=nullptr;
        if(!Root->TryGetObjectField(TEXT("bodies"),Bodies)||!Root->TryGetArrayField(TEXT("mask_runs"),Runs)||Runs->Num()>65536)return false;
        for(const auto& Pair:(*Bodies)->Values){
            const FString Key(*Pair.Key);if(!Key.IsNumeric()||Pair.Value->Type!=EJson::Object)return false;
            const int32 Id=FCString::Atoi(*Key);const double H=Number(Pair.Value->AsObject(),TEXT("height_m"),-10000);
            if(Id<0||Id>=255||H< -100||H>2000)return false;Heights.Add(Id,float(H*100-13000));
        }
        for(const auto& Value:*Runs){
            if(Value->Type!=EJson::Array)return false;const auto& Run=Value->AsArray();
            if(Run.Num()!=2||Run[0]->Type!=EJson::Number||Run[1]->Type!=EJson::Number)return false;
            const double Id=Run[0]->AsNumber(),Count=Run[1]->AsNumber();
            if(!FMath::IsFinite(Id)||!FMath::IsFinite(Count)||Id<0||Id>255||Id!=FMath::FloorToDouble(Id)||Count<1||Count>65536-Mask.Num()||Count!=FMath::FloorToDouble(Count)||((int32)Id!=255&&!Heights.Contains((int32)Id)))return false;
            for(int32 I=0;I<int32(Count);++I)Mask.Add(uint8(Id));
        }
        Ready=Mask.Num()==65536;return Ready;
    }
    FBridgeWaterSample Sample(const FVector& Feet,float Bed)const{
        FBridgeWaterSample Result;if(!Ready||Feet.ContainsNaN()||!FMath::IsFinite(Bed))return Result;
        const double X=Feet.X/100+1364,Y=Feet.Y/100+1263;
        if(X<0||Y<0||X>=SizeMetres||Y>=SizeMetres)return Result;
        const int32 IX=FMath::Clamp(FMath::FloorToInt(X/SizeMetres*256),0,255),IY=FMath::Clamp(FMath::FloorToInt(Y/SizeMetres*256),0,255);
        const int32 Id=Mask[IY*256+IX];const auto* H=Heights.Find(Id);if(!H)return Result;
        Result.Present=true;Result.Body=Id;Result.Height=*H;Result.TargetFeet=*H-30;
        // Original Player.SWIM_DEPTH, SWIM_FLOAT and entry threshold. A bridge,
        // pier or a character jumping above the surface stays out of swim mode.
        Result.Swimming=*H-Bed>125&&Feet.Z<*H+5;
        Result.Wading=!Result.Swimming&&*H-Feet.Z>10;return Result;
    }
};
