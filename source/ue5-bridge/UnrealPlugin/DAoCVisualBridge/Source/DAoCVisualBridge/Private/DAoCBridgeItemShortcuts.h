#pragma once
#include "CoreMinimal.h"
#include "Dom/JsonObject.h"
namespace FBridgeItemShortcuts {
enum class EUse {None,Equip,Use};
inline FString Text(const TSharedPtr<FJsonObject>& Row,const TCHAR* Key){FString Value;if(Row)Row->TryGetStringField(Key,Value);return Value;}
inline bool Carried(int32 Slot){return (Slot>=40&&Slot<80)||TArray<int32>{10,11,12,13,21,22,23,24,25,26,27,28,29,32,33,34,35,36,37}.Contains(Slot);}
inline EUse Use(int32 Slot,const TSharedPtr<FJsonObject>& Item,const TSharedPtr<FJsonObject>& Entry){
    if(!Carried(Slot)||!Item.IsValid()||Text(Item,TEXT("token")).IsEmpty())return EUse::None;
    const TArray<TSharedPtr<FJsonValue>>* Slots=nullptr;
    if(Slot>=40&&Item->TryGetArrayField(TEXT("equip_slots"),Slots)&&!Slots->IsEmpty())return EUse::Equip;
    return Text(Entry,TEXT("id"))==FString::Printf(TEXT("srv:%d"),Slot)&&Text(Entry,TEXT("kind"))==TEXT("item")&&!Text(Entry,TEXT("token")).IsEmpty()?EUse::Use:EUse::None;
}
inline bool Sale(int32 Slot,const TSharedPtr<FJsonObject>& Item,const FString& Token){return Slot>=40&&Slot<80&&Item.IsValid()&&!Token.IsEmpty()&&Text(Item,TEXT("token"))==Token;}
}
