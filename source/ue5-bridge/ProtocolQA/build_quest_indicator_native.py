"""Build the original NPC quest indicators in a private Unreal candidate."""
import argparse
import json
from pathlib import Path
import shutil

from build_spell_audio_native import build
from prepare_combined_expansion_data import digest


def stage_native(source, staged):
    patched = set()

    def edit(relative, pairs):
        relative = Path("DAoCVisualBridge") / relative
        patched.add(relative)
        code = (source / relative).read_text(encoding="utf-8-sig")
        for before, after in pairs:
            assert code.count(before) == 1, (str(relative), before)
            code = code.replace(before, after, 1)
        path = staged / relative
        if not path.is_file() or path.read_text(encoding="utf-8-sig") != code:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(code, encoding="utf-8")

    edit("Public/DAoCBridgeSubsystem.h", [
        ("    void ApplyQuestRewards(TSharedPtr<FJsonObject> State);", '''    void ApplyQuestRewards(TSharedPtr<FJsonObject> State);
    void UpdateNpcQuestIndicator(const FString& Id,AActor& Actor,const FJsonObject& Row);
    TMap<FString,TWeakObjectPtr<class UProceduralMeshComponent>> NpcQuestRings;'''),
    ])
    edit("Private/DAoCBridgeSubsystem.cpp", [
        ('#include "UnrealClient.h"', '#include "UnrealClient.h"\n#include "ProceduralMeshComponent.h"'),
        ("void UDAoCBridgeSubsystem::Tick(float Dt){", 'void UDAoCBridgeSubsystem::Tick(float Dt){\n#include "DAoCBridgeQuestIndicatorAcceptance.inl"'),
        ('            if(!Smoothed&&Id!=TEXT("player:local"))SetEntityAnimation(Id,State);',
         '''            if(Kind==TEXT("npc")&&(Row->HasField(TEXT("quest_indicator"))||NpcQuestRings.Contains(Id)))UpdateNpcQuestIndicator(Id,*A,*Row);
            if(!Smoothed&&Id!=TEXT("player:local"))SetEntityAnimation(Id,State);'''),
        ("    for(auto& Id:Gone){", "    for(const auto& Id:Gone)NpcQuestRings.Remove(Id);\n    for(auto& Id:Gone){"),
        ("Entities.Empty();AnimationStates.Empty();", "Entities.Empty();NpcQuestRings.Empty();AnimationStates.Empty();"),
    ])
    edit("Private/DAoCBridgeZoneMap.cpp", [
        ('#include "DAoCBridgeSubsystem.h"', '#include "DAoCBridgeSubsystem.h"\n#include "DAoCBridgeQuestIndicator.h"'),
        ("class SZoneMapPicture", '''struct FZoneQuestMark
{
    FVector2D Fraction;
    int32 Indicator;
};
class SZoneMapPicture'''),
        ("SLATE_ARGUMENT(TFunction<FVector2D()>,Forward)", "SLATE_ARGUMENT(TFunction<FVector2D()>,Forward)SLATE_ARGUMENT(TFunction<TArray<FZoneQuestMark>()>,QuestMarks)"),
        ("Forward=Args._Forward;Click=Args._Click;", "Forward=Args._Forward;QuestMarks=Args._QuestMarks;Click=Args._Click;"),
        ("if(!Fraction)return Layer;auto F=Fraction();", '''if(!Fraction)return Layer;
 if(QuestMarks)
 {
  for(const auto& Mark:QuestMarks())
  {
   const FVector2D Center=Mark.Fraction*G.GetLocalSize();
   const FLinearColor Tint=BridgeQuestIndicator::Color(Mark.Indicator);
   TArray<FVector2D> Stem;
   if(Mark.Indicator==2) Stem={Center+FVector2D(-2,-3),Center+FVector2D(0,-5),Center+FVector2D(2,-3),Center+FVector2D(0,-1)};
   else if(Mark.Indicator==16) Stem={Center+FVector2D(-3,0),Center+FVector2D(0,-3),Center+FVector2D(3,0),Center+FVector2D(0,3),Center+FVector2D(-3,0)};
   else Stem={Center+FVector2D(0,-5),Center+FVector2D(0,-1)};
   FSlateDrawElement::MakeLines(Out,Layer+1,G.ToPaintGeometry(),Stem,ESlateDrawEffect::None,Tint,true,2);
   if(Mark.Indicator!=16)
   {
       const TArray<FVector2D> Dot={Center+FVector2D(0,2),Center+FVector2D(0,3)};
       FSlateDrawElement::MakeLines(Out,Layer+1,G.ToPaintGeometry(),Dot,ESlateDrawEffect::None,Tint,true,2);
   }
  }
  ++Layer;
 }
 auto F=Fraction();'''),
        ("private:TFunction<FVector2D()> Fraction,Forward;", "private:TFunction<FVector2D()> Fraction,Forward;TFunction<TArray<FZoneQuestMark>()> QuestMarks;"),
        (".Image(Art).Fraction([this]()", '''.Image(Art).QuestMarks([this](){
    TArray<FZoneQuestMark> Marks;
    for(const auto& Pair:EntityRows)
    {
        const auto& Row=Pair.Value;
        const int32 Indicator=Row?BridgeQuestIndicator::FromRow(*Row):0;
        if(!Indicator)continue;
        const auto Position=A(Row,TEXT("position_m"));
        if(Position.Num()!=3)continue;
        const FVector2D Fraction=ZoneMapFraction({Position[0]->AsNumber()*40,Position[2]->AsNumber()*40});
        if(Fraction.X>=0&&Fraction.X<=1&&Fraction.Y>=0&&Fraction.Y<=1)Marks.Add({Fraction,Indicator});
    }
    return Marks;
 }).Fraction([this]()'''),
    ])
    for path in source.rglob("*"):
        if not path.is_file() or path.relative_to(source) in patched:
            continue
        target = staged / path.relative_to(source)
        if not target.is_file() or digest(path) != digest(target):
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def main(workspace, engine):
    lab = "QuestIndicatorLab"
    staged = workspace / lab / "CandidateSource"
    source = Path(__file__).resolve().parents[1] / "UnrealPlugin/DAoCVisualBridge/Source"
    stage_native(source, staged)
    return build(workspace, engine, lab, candidate_source=staged)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("workspace","engine"):
        parser.add_argument("--"+name, required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(main(args.workspace.resolve(), args.engine.resolve())))
