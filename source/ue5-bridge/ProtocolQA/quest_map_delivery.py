"""Exact, reversible delivery of original quest objective map points."""
import argparse
import json
from pathlib import Path
import shutil

from quest_reward_delivery import BINARIES, SOURCE, NATIVE, apply_delivery, current, digest, read, write
from stage_quest_map import stage_gateway


PATCHED = ["Private/DAoCBridgeSubsystem.cpp", "Private/DAoCBridgeZoneMap.cpp"]
ADDED = ["Private/DAoCBridgeQuestMap.h", "Private/DAoCBridgeQuestMapAcceptance.inl"]


def pairs(workspace, build):
    root = workspace / "QuestMapLab"
    normal = workspace / "Client/Plugins/DAoCVisualBridge"
    compiled = Path(build["project"]).parent / "Plugins/DAoCVisualBridge"
    candidate = root / "CandidateSource/DAoCVisualBridge"
    result = [(compiled / "Binaries/Win64" / name, normal / "Binaries/Win64" / name) for name in BINARIES]
    result += [(candidate / name, normal / "Source/DAoCVisualBridge" / name) for name in PATCHED + ADDED]
    result += [(candidate / name, SOURCE / NATIVE / "DAoCVisualBridge" / name) for name in PATCHED]
    result += [(root / "Delivery/Godot/live_gateway.gd", folder / "live_gateway.gd")
               for folder in [workspace / "Godot", SOURCE / "Godot"]]
    result.append((SOURCE / "Godot/quest_map_state.gd", workspace / "Godot/quest_map_state.gd"))
    return result


def validate(workspace, plan, after=False):
    root = workspace / "QuestMapLab"
    assert plan["predecessor_sha256"] == digest(workspace / "QuestIndicatorLab/installed.json")
    proofs = {key: Path(path) for key, path in plan["proofs"].items()}
    assert set(proofs) == {"build", "native", "protocol", "state"}
    assert all(path.resolve().is_relative_to(root.resolve()) for path in proofs.values())
    assert all(digest(path) == plan["evidence"][key] and read(path)["passed"] for key, path in proofs.items())
    build, native, protocol, state = (read(proofs[key]) for key in ("build", "native", "protocol", "state"))
    assert native["checks"] == 6 and native["build_sha256"] == digest(proofs["build"])
    assert state["checks"] == 15 and not state["failures"]
    assert protocol["real_protocol"] and protocol["disposable_only"]
    assert len(protocol["checks"]) == 16 and all(protocol["checks"].values())
    assert all(protocol[key] for key in ("database_restored", "private_server_restored", "normal_shutdown", "normal_runtime_unchanged"))
    assert not protocol["original_world_travel_verified"] and protocol["private_npc_proximity_staging"]
    previous = read(workspace / "QuestIndicatorLab/native_build.json")
    old = {Path(key).as_posix(): value for key, value in previous["source_sha256"].items()}
    new = {Path(key).as_posix(): value for key, value in build["source_sha256"].items()}
    assert old.keys() <= new.keys()
    assert {key for key in new if new[key] != old.get(key)} == {
        "DAoCVisualBridge/" + name for name in PATCHED + ADDED
    }
    assert build["normal_binary_sha256"] == previous["binaries_sha256"][BINARIES[0]]
    expected = pairs(workspace, build)
    rows = {row["target"]: row for row in plan["files"]}
    assert len(rows) == len(plan["files"]) == len(expected) and set(rows) == {str(dst) for _, dst in expected}
    for src, dst in expected:
        row = rows[str(dst)]
        assert row["source"] == str(src) and digest(src) == row["after_sha256"]
        assert current(dst) == row["after_sha256" if after else "before_sha256"], str(dst)
        if src.name in BINARIES:
            assert row["before_sha256"] == previous["binaries_sha256"][src.name]
            assert row["after_sha256"] == build["binaries_sha256"][src.name]
        elif src.is_relative_to(root / "CandidateSource"):
            relative = src.relative_to(root / "CandidateSource").as_posix()
            assert row["before_sha256"] == old.get(relative) and row["after_sha256"] == new[relative]
        elif src.name == "live_gateway.gd":
            assert row["before_sha256"] == protocol["source_inputs"][str(workspace / "Godot/live_gateway.gd")]
        else:
            assert digest(src) == state["source_inputs"][str(src)]
    return rows


def prepare(workspace, proofs):
    from central_activation_receipts import verify_files

    assert verify_files(workspace)["quest_indicators_installed"]
    root = workspace / "QuestMapLab"
    delivery = root / "Delivery/Godot"
    delivery.mkdir(parents=True, exist_ok=True)
    for name in ("live_gateway.gd", "visual_bridge.gd"):
        shutil.copy2(workspace / "Godot" / name, delivery / name)
    stage_gateway(delivery)
    proofs["build"] = root / "native_build.json"
    plan = dict(
        phase="prepared",
        predecessor_sha256=digest(workspace / "QuestIndicatorLab/installed.json"),
        proofs={key: str(path) for key, path in proofs.items()},
        evidence={key: digest(path) for key, path in proofs.items()},
        files=[dict(source=str(src), target=str(dst), before_sha256=current(dst), after_sha256=digest(src))
               for src, dst in pairs(workspace, read(proofs["build"]))],
    )
    validate(workspace, plan)
    path = root / "delivery-plan.json"
    write(path, plan)
    return dict(passed=True, files=len(plan["files"]), plan=str(path))


def verify_installed(workspace):
    root = workspace / "QuestMapLab"
    receipt = root / "installed.json"
    if not receipt.is_file() or not read(receipt).get("installed"):
        return {}
    result = read(receipt)
    path = root / "delivery-plan.json"
    assert result["phase"] == "complete" and result["plan_sha256"] == digest(path)
    return validate(workspace, read(path), after=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    for name in ("native", "protocol", "state"):
        parser.add_argument("--" + name, type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    if args.apply:
        from central_activation_receipts import verify_files
        assert verify_files(workspace)["quest_indicators_installed"]
        root = workspace / "QuestMapLab"
        plan = read(root / "delivery-plan.json")
        validate(workspace, plan)
        result = apply_delivery(workspace, root, "QuestMap", plan, "quest_map_installed")
    else:
        result = prepare(workspace, {key: getattr(args, key).resolve() for key in ("native", "protocol", "state")})
    print(json.dumps(result))
