"""Verify and install the tested quest client over the player trade delivery."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from player_trade_delivery_plan import read
from prepare_combined_expansion_data import digest
from stage_quest_reward_gateway import stage_gateway


SOURCE = Path(__file__).resolve().parents[1]
NATIVE = "UnrealPlugin/DAoCVisualBridge/Source"
NATIVE_PATCHED = [
    "Private/DAoCBridgeClassicUI.cpp",
    "Private/DAoCBridgeSubsystem.cpp",
    "Private/DAoCBridgeViewport.cpp",
    "Private/DAoCBridgeWorldPointer.cpp",
    "Public/DAoCBridgeSubsystem.h",
]
NATIVE_NEW = ["Private/DAoCBridgeQuestRewards.inl", "Private/DAoCBridgeQuestRewardAcceptance.inl"]
GATEWAY = ["live_gateway.gd", "visual_bridge.gd"]
BINARIES = ["UnrealEditor-DAoCVisualBridge.dll", "UnrealEditor.modules"]


def write(path, value):
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def current(path):
    return digest(path) if path.is_file() else None


def pairs(workspace, install, codec):
    root = workspace / "QuestRewardsLab"
    native = workspace / "Client/Plugins/DAoCVisualBridge"
    staged = root / "Native/CandidateSource/DAoCVisualBridge"
    candidate_plugin = Path(read(root / "Native/native_build.json")["project"]).parent / "Plugins/DAoCVisualBridge"
    backend = Path(codec["candidate_backend"]).parent
    game = install / "new-client/godot"
    net = game / "game/net"
    repo_net = SOURCE.parent / "new-client/godot/game/net"
    result = [(candidate_plugin / "Binaries/Win64" / name, native / "Binaries/Win64" / name) for name in BINARIES]
    result += [(staged / name, native / "Source/DAoCVisualBridge" / name) for name in NATIVE_PATCHED + NATIVE_NEW]
    result += [(staged / name, SOURCE / NATIVE / "DAoCVisualBridge" / name) for name in NATIVE_PATCHED]
    result += [(root / "Delivery/Godot" / name, workspace / "Godot" / name) for name in GATEWAY + ["quest_reward_state.gd"]]
    result += [(root / "Delivery/Godot" / name, SOURCE / "Godot" / name) for name in GATEWAY]
    result += [(backend / name, game / ".godot/mono/temp/bin/Debug" / name) for name in ["MMOEngine.dll", "MMOEngine.pdb"]]
    core = backend.parent / "BackendSource/game/net/DaocClient.cs"
    result += [(core, net / core.name), (core, repo_net / core.name), (repo_net / "DaocQuestRewardCodec.cs", net / "DaocQuestRewardCodec.cs")]
    return result


def validate(workspace, install, plan, after=False):
    root = workspace / "QuestRewardsLab"
    assert plan["predecessor_sha256"] == digest(workspace / "PlayerTradeGatewayLab/installed.json")
    proof = {key: Path(path) for key, path in plan["proofs"].items()}
    assert set(proof) == {"codec", "wire", "gateway", "native", "build"}
    for key, path in proof.items():
        assert path.resolve().is_relative_to(root.resolve())
        assert digest(path) == plan["evidence"][key] and read(path)["passed"]
    codec, wire, gateway, native, build = (read(proof[key]) for key in ("codec", "wire", "gateway", "native", "build"))
    assert codec["checks"] >= 265 and codec["candidate_dispatch_enabled"]
    assert digest(Path(codec["candidate_backend"])) == codec["candidate_backend_sha256"]
    assert native["checks"] >= 14 and native["build_receipt_sha256"] == digest(proof["build"])
    assert native["wire_proof_sha256"] == digest(proof["wire"])
    for evidence in [wire, gateway]:
        assert evidence["disposable_only"] and evidence["real_protocol"] and all(evidence["checks"].values())
        assert all(evidence[key] for key in ("database_restored", "private_server_restored", "normal_shutdown", "normal_runtime_unchanged"))
        assert evidence["source_inputs"][str(proof["codec"])] == digest(proof["codec"])
    assert gateway["checks"]["gateway_completion_persisted_once"] and gateway["checks"]["single_gateway_grant_after_double_click"]
    previous = read(workspace / "PlayerTradeGatewayLab/native_build.json")
    old_sources = {Path(p).as_posix(): h for p, h in previous["source_sha256"].items()}
    new_sources = {Path(p).as_posix(): h for p, h in build["source_sha256"].items()}
    assert old_sources.keys() <= new_sources.keys()
    assert {name for name in new_sources if new_sources[name] != old_sources.get(name)} == {
        "DAoCVisualBridge/" + name for name in NATIVE_PATCHED + NATIVE_NEW
    }
    assert build["normal_binary_sha256"] == previous["binaries_sha256"][BINARIES[0]]
    assert plan["native_after_sha256"] == build["binaries_sha256"][BINARIES[0]]
    expected = pairs(workspace, install, codec)
    rows = {row["target"]: row for row in plan["files"]}
    assert len(rows) == len(plan["files"]) == len(expected) and set(rows) == {str(dst) for _, dst in expected}
    for src, dst in expected:
        row = rows[str(dst)]
        assert row["source"] == str(src) and digest(src) == row["after_sha256"]
        native_source = root / "Native/CandidateSource"
        if src.is_relative_to(native_source):
            assert row["after_sha256"] == new_sources[src.relative_to(native_source).as_posix()]
        if src.name in BINARIES:
            assert row["after_sha256"] == build["binaries_sha256"][src.name]
        assert current(dst) == row["after_sha256" if after else "before_sha256"]
    for evidence in (codec, gateway):
        for name, sha in evidence["source_inputs"].items():
            row = rows.get(name)
            assert (row["before_sha256"] if row and after else digest(Path(name))) == sha
    return rows


def prepare(workspace, install, proofs):
    from central_activation_receipts import verify_files
    assert verify_files(workspace)["player_trade_installed"]
    root = workspace / "QuestRewardsLab"
    proofs["build"] = root / "Native/native_build.json"
    delivery = root / "Delivery/Godot"
    delivery.mkdir(parents=True, exist_ok=True)
    for name in GATEWAY:
        shutil.copy2(workspace / "Godot" / name, delivery / name)
    stage_gateway(delivery, SOURCE / "Godot/quest_reward_state.gd")
    files = [
        dict(source=str(src), target=str(dst), before_sha256=current(dst), after_sha256=digest(src))
        for src, dst in pairs(workspace, install, read(proofs["codec"]))
    ]
    plan = dict(phase="prepared", install_root=str(install),
                predecessor_sha256=digest(workspace / "PlayerTradeGatewayLab/installed.json"),
                native_after_sha256=read(proofs["build"])["binaries_sha256"][BINARIES[0]],
                proofs={k:str(p) for k,p in proofs.items()}, evidence={k:digest(p) for k,p in proofs.items()}, files=files)
    validate(workspace, install, plan)
    path = root / "delivery-plan.json"
    write(path, plan)
    return dict(passed=True, files=len(files), plan=str(path))


def verify_installed(workspace):
    root = workspace / "QuestRewardsLab"
    receipt = root / "installed.json"
    if not receipt.is_file():
        return None, {}
    result = read(receipt)
    if not result.get("installed"):
        return None, {}
    path = root / "delivery-plan.json"
    assert result["phase"] == "complete" and result["plan_sha256"] == digest(path)
    plan = read(path)
    return result, validate(workspace, Path(plan["install_root"]), plan, after=True)


def replace(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".quest-delivery-", dir=target.parent)
    os.close(fd)
    try:
        shutil.copyfile(source, temp)
        os.replace(temp, target)
    finally:
        Path(temp).unlink(missing_ok=True)


def install_client(workspace, install):
    from central_activation_receipts import verify_files
    root = workspace / "QuestRewardsLab"
    path = root / "delivery-plan.json"
    receipt = root / "installed.json"
    assert not receipt.exists() or not read(receipt).get("installed")
    assert verify_files(workspace)["player_trade_installed"]
    plan = read(path)
    assert Path(plan["install_root"]) == install
    validate(workspace, install, plan)
    connections = subprocess.check_output(["netstat", "-ano", "-p", "tcp"], text=True, errors="replace", timeout=15)
    for line in connections.splitlines():
        columns = line.split()
        if len(columns) == 5 and columns[0] == "TCP":
            assert not columns[1].endswith(":19727") or columns[4] == "0", "Normal bridge must be stopped"
    backup = workspace / "Backups" / ("QuestRewards_" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    backup.mkdir(parents=True)
    backups = {}
    for index, row in enumerate(plan["files"]):
        target = Path(row["target"])
        assert current(target) == row["before_sha256"]
        if target.is_file():
            saved = backup / str(index)
            shutil.copy2(target, saved)
            assert digest(saved) == row["before_sha256"]
            backups[str(target)] = str(saved)
        else:
            backups[str(target)] = None
    write(backup / "recovery.json", dict(phase="ready", backups=backups, plan=plan))
    changed = []
    try:
        for row in plan["files"]:
            source, target = Path(row["source"]), Path(row["target"])
            assert current(target) == row["before_sha256"]
            replace(source, target)
            changed.append(row)
            assert digest(target) == row["after_sha256"]
        result = dict(installed=True, phase="complete", files=len(changed), plan_sha256=digest(path), backup=str(backup))
        write(receipt, result)
        assert verify_installed(workspace)[0]["installed"]
        checks = verify_files(workspace)
        assert checks["player_trade_installed"] and checks["quest_rewards_installed"]
        write(root / "installed_verification.json", checks)
        return result
    except BaseException:
        for row in reversed(changed):
            target = Path(row["target"])
            saved = backups[str(target)]
            if saved:
                replace(Path(saved), target)
            else:
                target.unlink()
            assert current(target) == row["before_sha256"]
        write(receipt, dict(installed=False, phase="rolled_back", backup=str(backup)))
        verify_files(workspace)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for key in ("workspace", "install"):
        parser.add_argument("--" + key, required=True, type=Path)
    for key in ("codec", "wire", "gateway", "native"):
        parser.add_argument("--" + key, type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    workspace, install = args.workspace.resolve(), args.install.resolve()
    if args.apply:
        result = install_client(workspace, install)
    else:
        result = prepare(workspace, install, {key:getattr(args, key).resolve() for key in ("codec", "wire", "gateway", "native")})
    print(json.dumps(result))
