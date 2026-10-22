# User Elm2 candidate: isolated comparison

The supplied `Olmo_usuario_3D.zip` contains a 41,358-triangle GLB with a photographed
bark color map and a four-cluster alpha leaf atlas. Both surfaces omit normals.
The trial generates normals/tangents and mipmaps, preserving the supplied triangle
positions, UVs and texture pixels. Its flat trunk base is seated slightly into the
terrain. This is a different model from the first 30,162-triangle elm.

The private candidate is compared with the corrected first elm at the existing
Ardee well fixture 207:1109, with the same target height and light. This staging
location is an Elm fixture: it is not deployment to the 335 Elm2 placements.
`active.json` and the currently enabled 661-tree model remain unchanged.

`preview_elm_candidate.gd` adds an A/B comparison between two hash-verified private
models without changing activation. Five camera views cover silhouette, crown,
base and bark. `check_elm_candidate.gd` compares the repaired scene with its own
source GLB for geometry, UVs, texture pixels and complete normals/tangents, then
checks base contact at this fixture. Offline renderer checks also verify original
fixture restoration and unchanged collision shapes; no server or account is used.

Visual review: the proposed crown is open, with conspicuous branching, rather than
the dense rounded silhouette in the reference photograph. It remains an unapproved
candidate. No forest performance or distance LOD validation is claimed.

Private backup: `DAoC-Godot-Remasters/graphics/zone207/elm2-candidate-20261022`.
Original source files, repaired scene and local preview support are retained there.
