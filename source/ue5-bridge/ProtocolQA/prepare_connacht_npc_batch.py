"""Export the most common missing creature bodies into a private Connacht candidate."""
import argparse
import json
import os
from pathlib import Path
import struct
import subprocess

from prepare_combined_expansion_data import digest


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def glb_json(path):
    with path.open("rb") as stream:
        magic, version, size, length, kind = struct.unpack("<4sIIII", stream.read(20))
        assert magic == b"glTF" and version == 2 and size == path.stat().st_size and kind == 0x4E4F534A
        return json.loads(stream.read(length))


def export(workspace, install, engine, batch=1, count=3):
    lab = workspace / "ConnachtNpcCoverageLab"
    audit_path = lab / (f"audit_after_batch{batch-1}.json" if batch > 1 else "audit.json")
    audit = read(audit_path)
    assert audit["passed"] and audit["zone"] == 207 and not audit["database_modified"]
    assert all(digest(Path(path)) == value for path, value in audit["sources"].items())
    game = install / "new-client/godot"
    metadata = game / "content/monsters/monsters.json"
    original = read(metadata)
    catalog_path = workspace / "models.json"
    catalog = read(catalog_path)
    top = [row for row in audit["models"] if row["active_spawns"] > 0 and row["status"] == "original_mesh_available"][:count]
    assert top and count > 0 and batch > 0
    root = lab / f"Batch{batch}"
    receipt = root / "installed.json"
    assert not receipt.is_file() or not read(receipt).get("installed"), "Installed batches retain their verified assets"
    output = root / "SourceModels"
    output.mkdir(parents=True, exist_ok=True)
    original_script = Path(__file__).resolve().parents[1] / "Godot/export_connacht_models.gd"
    script = root / "export_connacht_models.gd"
    exporter = original_script.read_text(encoding="utf-8-sig")
    anchor = '\texport_folder=base'
    assert exporter.count(anchor) == 1
    script.write_text(exporter.replace(anchor, '''\tfor arg in OS.get_cmdline_user_args():
\t\tif arg.begins_with("--output-folder="):
\t\t\tbase=arg.trim_prefix("--output-folder=")
\texport_folder=base''', 1), encoding="utf-8")
    inputs = {str(path): digest(path) for path in (original_script, script, metadata, catalog_path, audit_path)}
    tasks = []
    for row in top:
        ident = str(row["model_id"])
        assert ident not in catalog and ident in original
        info = original[ident]
        model = Path(row["original_source"]).resolve()
        assert model.is_relative_to(game / "content/monsters") and model.is_file()
        inputs[str(model)] = digest(model)
        source = read(model)
        for dep in source.get("buffers", []) + source.get("images", []):
            uri = dep.get("uri", "")
            if uri and not uri.startswith("data:"):
                path = (model.parent / uri).resolve()
                assert path.is_relative_to(game / "content") and path.is_file()
                inputs[str(path)] = digest(path)
        tasks.append(dict(id=ident, info=info, equipment=[]))
    (output / "tasks.json").write_text(json.dumps(tasks, indent=2), encoding="utf-8")
    prepared = read(workspace / "Reports/protocol_qa/prepared.json")
    project = (Path(prepared["root"]) / "LobbyProject").resolve()
    assert project.is_relative_to(workspace / "ProtocolQA") and project.is_dir()
    sdk = engine / "Binaries/ThirdParty/DotNet/10.0/win-x64"
    env = dict(os.environ, DOTNET_ROOT=str(sdk), DOTNET_ROOT_X64=str(sdk), APPDATA=str(root / "AppData"),
               LOCALAPPDATA=str(root / "LocalAppData"))
    executable = install / "new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe"
    args = [str(executable), "--headless", "--path", str(project), "--script", str(script), "--",
            "--output-folder=" + str(output)]
    log = root / "export.log"
    with log.open("w", encoding="utf-8") as stream:
        result = subprocess.run(args, env=env, stdout=stream, stderr=subprocess.STDOUT,
                                timeout=180, creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode == 0 and f"BRIDGE_MODEL_EXPORT_PASS count={len(top)}" in log.read_text(encoding="utf-8"), str(log)
    rows_path = output / "exported.json"
    rows = read(rows_path)
    assert [row["id"] for row in rows] == [row["id"] for row in tasks]
    evidence = {}
    for row in rows:
        ident = row["id"]
        path = Path(row["file"]).resolve()
        assert path.parent == output.resolve()
        model = glb_json(path)
        clips = {clip["name"] for clip in model.get("animations", [])}
        assert {"idle", "walk"}.issubset(clips), (ident, clips)
        assert all(model.get(field) for field in ("meshes", "skins", "images", "materials")), ident
        evidence[ident] = dict(file=str(path), sha256=digest(path), clips=sorted(clips), meshes=len(model["meshes"]),
                               textures=len(model["images"]), materials=len(model["materials"]))
    assert all(digest(Path(path)) == sha for path, sha in inputs.items())
    proof = dict(passed=True, models=evidence, inputs=inputs, exported_sha256=digest(rows_path),
                 active_spawns=sum(row["active_spawns"] for row in top), normal_catalogue_modified=False)
    target = root / "export_verified.json"
    target.write_text(json.dumps(proof, indent=2), encoding="utf-8")
    return dict(passed=True, model_ids=list(evidence), active_spawns=proof["active_spawns"], proof=str(target))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for key in ("workspace", "install", "engine"):
        parser.add_argument("--" + key, type=Path, required=True)
    parser.add_argument("--batch", type=int, default=1)
    parser.add_argument("--count", type=int, default=3)
    args = parser.parse_args()
    print(json.dumps(export(args.workspace.resolve(), args.install.resolve(), args.engine.resolve(), args.batch, args.count)))
