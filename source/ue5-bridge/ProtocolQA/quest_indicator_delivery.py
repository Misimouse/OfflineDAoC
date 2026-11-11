"""Install the verified NPC quest indicators over the quest reward client."""
import argparse
import json
from pathlib import Path
import shutil

from quest_reward_delivery import BINARIES, NATIVE, SOURCE, apply_delivery, current, digest, read, write
from stage_quest_indicators import stage_markers


NATIVE_PATCHED = [
    "Public/DAoCBridgeSubsystem.h",
    "Private/DAoCBridgeSubsystem.cpp",
    "Private/DAoCBridgeZoneMap.cpp",
]
NATIVE_NEW = [
    "Private/DAoCBridgeQuestIndicator.h",
    "Private/DAoCBridgeQuestIndicator.cpp",
    "Private/DAoCBridgeQuestIndicatorAcceptance.inl",
]
GATEWAY = ["live_gateway.gd", "decoded_world_adapter.gd"]


def pairs(workspace, build):
    root = workspace / "QuestIndicatorLab"
    normal = workspace / "Client/Plugins/DAoCVisualBridge"
    compiled = Path(build["project"]).parent / "Plugins/DAoCVisualBridge/Binaries/Win64"
    staged = root / "CandidateSource/DAoCVisualBridge"
    repo = SOURCE / NATIVE / "DAoCVisualBridge"
    result = [(compiled / name, normal / "Binaries/Win64" / name) for name in BINARIES]
    result += [(staged / name, normal / "Source/DAoCVisualBridge" / name) for name in NATIVE_PATCHED + NATIVE_NEW]
    result += [(staged / name, repo / name) for name in NATIVE_PATCHED]
    for directory in [workspace / "Godot", SOURCE / "Godot"]:
        result += [(root / "Delivery/Godot" / name, directory / name) for name in GATEWAY]
    return result


def validate(workspace, plan, after=False, successor_rows=None):
    successor_rows = successor_rows or {}
    root = workspace / "QuestIndicatorLab"
    rewards = workspace / "QuestRewardsLab"
    assert plan["predecessor_sha256"] == digest(rewards / "installed.json")
    proof = {key: Path(path) for key, path in plan["proofs"].items()}
    assert set(proof) == {"build", "native", "protocol"}
    assert proof["build"] == root / "native_build.json"
    assert proof["native"].resolve().is_relative_to(root / "Acceptance")
    assert proof["protocol"].resolve().is_relative_to(rewards / "IndicatorProtocol")
    for key, path in proof.items():
        assert digest(path) == plan["evidence"][key] and read(path)["passed"]
    build, native, protocol = (read(proof[key]) for key in ("build", "native", "protocol"))
    assert native["checks"] == 8 and native["build_sha256"] == digest(proof["build"])
    assert protocol["disposable_only"] and protocol["real_protocol"] and len(protocol["checks"]) == 7
    assert all(protocol["checks"].values())
    assert all(protocol[key] for key in ("database_restored", "private_server_restored", "normal_shutdown", "normal_runtime_unchanged"))
    previous = read(rewards / "Native/native_build.json")
    old_sources = {Path(name).as_posix(): sha for name, sha in previous["source_sha256"].items()}
    new_sources = {Path(name).as_posix(): sha for name, sha in build["source_sha256"].items()}
    assert old_sources.keys() <= new_sources.keys()
    assert {name for name in new_sources if new_sources[name] != old_sources.get(name)} == {
        "DAoCVisualBridge/" + name for name in NATIVE_PATCHED + NATIVE_NEW
    }
    assert build["normal_binary_sha256"] == previous["binaries_sha256"][BINARIES[0]]
    expected = pairs(workspace, build)
    rows = {row["target"]: row for row in plan["files"]}
    assert len(rows) == len(plan["files"]) == len(expected) and set(rows) == {str(dst) for _, dst in expected}
    for src, dst in expected:
        row = rows[str(dst)]
        assert row["source"] == str(src) and digest(src) == row["after_sha256"]
        expected_hash = row["after_sha256" if after else "before_sha256"]
        successor = successor_rows.get(str(dst))
        if successor:
            assert after and successor["before_sha256"] == expected_hash
            expected_hash = successor["after_sha256"]
        assert current(dst) == expected_hash, str(dst)
        if src.name in BINARIES:
            assert row["before_sha256"] == previous["binaries_sha256"][src.name]
            assert row["after_sha256"] == build["binaries_sha256"][src.name]
        elif src.is_relative_to(root / "CandidateSource"):
            relative = src.relative_to(root / "CandidateSource").as_posix()
            assert row["before_sha256"] == old_sources.get(relative)
            assert row["after_sha256"] == new_sources[relative]
        else:
            assert row["before_sha256"] == protocol["source_inputs"][str(workspace / "Godot" / src.name)]
    return rows


def prepare(workspace, native, protocol):
    from central_activation_receipts import verify_files

    assert verify_files(workspace)["quest_rewards_installed"]
    root = workspace / "QuestIndicatorLab"
    proof = {"native": native, "protocol": protocol, "build": root / "native_build.json"}
    delivery = root / "Delivery/Godot"
    delivery.mkdir(parents=True, exist_ok=True)
    for name in GATEWAY:
        shutil.copy2(workspace / "Godot" / name, delivery / name)
    stage_markers(delivery)
    files = [
        dict(source=str(src), target=str(dst), before_sha256=current(dst), after_sha256=digest(src))
        for src, dst in pairs(workspace, read(proof["build"]))
    ]
    plan = dict(
        phase="prepared",
        predecessor_sha256=digest(workspace / "QuestRewardsLab/installed.json"),
        proofs={key: str(path) for key, path in proof.items()},
        evidence={key: digest(path) for key, path in proof.items()},
        files=files,
    )
    validate(workspace, plan)
    path = root / "delivery-plan.json"
    write(path, plan)
    return dict(passed=True, files=len(files), plan=str(path))


def verify_installed(workspace):
    from inventory_quantity_receipts import compose
    from quest_map_delivery import verify_installed as verify_map

    root = workspace / "QuestIndicatorLab"
    receipt = root / "installed.json"
    if not receipt.is_file():
        return {}
    result = read(receipt)
    if not result.get("installed"):
        return {}
    path = root / "delivery-plan.json"
    assert result["phase"] == "complete" and result["plan_sha256"] == digest(path)
    successors = verify_map(workspace)
    return compose(validate(workspace, read(path), after=True, successor_rows=successors), successors)


def install(workspace):
    from central_activation_receipts import verify_files

    root = workspace / "QuestIndicatorLab"
    baseline = verify_files(workspace)
    assert baseline["quest_rewards_installed"] and not baseline["quest_indicators_installed"]
    plan = read(root / "delivery-plan.json")
    validate(workspace, plan)
    return apply_delivery(workspace, root, "QuestIndicators", plan, "quest_indicators_installed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--native", type=Path)
    parser.add_argument("--protocol", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    if args.apply:
        result = install(workspace)
    elif args.native and args.protocol:
        result = prepare(workspace, args.native.resolve(), args.protocol.resolve())
    else:
        parser.error("pass --native and --protocol to prepare delivery")
    print(json.dumps(result))
