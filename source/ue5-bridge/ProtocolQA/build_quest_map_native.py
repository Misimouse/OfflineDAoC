"""Build the native quest objective map over the installed NPC indicators."""
import argparse
import json
from pathlib import Path
import shutil

from build_spell_audio_native import build
from prepare_combined_expansion_data import digest


def stage_native(source, staged):
    patched = set()

    def edit(relative, replacements):
        relative = Path("DAoCVisualBridge") / relative
        patched.add(relative)
        text = (source / relative).read_text(encoding="utf-8-sig")
        for before, after in replacements:
            assert text.count(before) == 1, (relative, before)
            text = text.replace(before, after, 1)
        path = staged / relative
        if not path.is_file() or path.read_text(encoding="utf-8-sig") != text:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    edit("Private/DAoCBridgeSubsystem.cpp", [
        ('#include "DAoCBridgeSubsystem.h"', '#include "DAoCBridgeSubsystem.h"\n#include "DAoCBridgeQuestMap.h"'),
        ('#include "DAoCBridgeQuestIndicatorAcceptance.inl"',
         '#include "DAoCBridgeQuestMapAcceptance.inl"\n#include "DAoCBridgeQuestIndicatorAcceptance.inl"'),
    ])
    edit("Private/DAoCBridgeZoneMap.cpp", [
        ('#include "DAoCBridgeQuestIndicator.h"', '#include "DAoCBridgeQuestIndicator.h"\n#include "DAoCBridgeQuestMap.h"'),
        ('   const FLinearColor Tint=BridgeQuestIndicator::Color(Mark.Indicator);', '''   if(Mark.Indicator==0)
   {
       TArray<FVector2D> Circle;
       for(int32 I=0;I<=16;++I)
       {
           const double Angle=UE_TWO_PI*I/16.0;
           Circle.Add(Center+FVector2D(FMath::Cos(Angle),FMath::Sin(Angle))*.5);
       }
       FSlateDrawElement::MakeLines(Out,Layer+1,G.ToPaintGeometry(),Circle,ESlateDrawEffect::None,FLinearColor(.08,.05,0),true,7);
       FSlateDrawElement::MakeLines(Out,Layer+2,G.ToPaintGeometry(),Circle,ESlateDrawEffect::None,FLinearColor(.95,.2,.15),true,5);
       continue;
   }
   const FLinearColor Tint=BridgeQuestIndicator::Color(Mark.Indicator);'''),
        ('  ++Layer;\n }', '  Layer+=2;\n }'),
        ('    return Marks;\n }).Fraction', '''    for(const FVector2D& Point:BridgeQuestMap::StepUnits(ClassicState))
    {
        const FVector2D Fraction=ZoneMapFraction(Point);
        if(Fraction.X>=0&&Fraction.X<=1&&Fraction.Y>=0&&Fraction.Y<=1)Marks.Add({Fraction,0});
    }
    return Marks;
 }).Fraction'''),
    ])
    for path in source.rglob("*"):
        if not path.is_file() or path.relative_to(source) in patched:
            continue
        target = staged / path.relative_to(source)
        if not target.is_file() or digest(path) != digest(target):
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("workspace", "engine"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    staged = workspace / "QuestMapLab/CandidateSource"
    source = Path(__file__).resolve().parents[1] / "UnrealPlugin/DAoCVisualBridge/Source"
    stage_native(source, staged)
    print(json.dumps(build(workspace, args.engine.resolve(), "QuestMapLab", candidate_source=staged)))
