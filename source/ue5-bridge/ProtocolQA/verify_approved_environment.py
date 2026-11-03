"""Compare native environment diagnostics with the approved scene's independent audit.

This checks loaded content, not pixel visibility or a live server session.
"""
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("report", type=Path)
parser.add_argument("approved_audit", type=Path)
args = parser.parse_args()
raw = args.report.read_bytes()
state = json.loads(raw.decode("utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig"))
audit = json.loads(args.approved_audit.read_text(encoding="utf-8-sig"))
components = [part for actor in audit["actors"] for part in actor["components"]]
expected = {
    "actors": len(audit["actors"]),
    "components": len(components),
    "instances": sum(len(c["instances"]) for c in components if c.get("instances") is not None),
    "logs": sum(any(word in c["mesh"].lower() for word in ("fallenlog", "driftwood_log")) for c in components),
    "algae_films": sum("algae_film" in c["mesh"].lower() for c in components),
    "aquatic_components": sum("river_aquatic_communities" in c["mesh"].lower() for c in components),
    "visible_components": len(components),
}
bindings = state.get("approved_environment", {}).get("bindings", [])
assert len(bindings) == 1, "Expected one approved environment binding"
binding = bindings[0]
assert binding["references"] == 1 and binding["loaded"], binding
assert binding["terrain_matches"] and binding["old_water_hidden"], binding
for key, value in expected.items():
    assert binding[key] == value, (key, binding[key], value)
assert state["connected"] and state["navigation_ready"], "Expected native replay connection and initialized navigation"
print(json.dumps({"passed": True, "scope": "native loaded content; inspect captures separately", **expected}))
