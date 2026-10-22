# First elm: root contact and bark repair

The supplied prototype GLB had both color textures, but neither mesh carried normals.
Its lowest vertex had been aligned to the fixture origin; the outer root tips still
floated 0.52–0.74 m above the actual terrain beside the Ardee well (fixture 207:1109).

`prepare_elm.gd --repair=true` generates missing normals and tangents, preserves the
triangle positions and UVs, and seats the outer root tips instead of the mesh minimum.
The small 0.06 m model-space embed is applied inside the model, leaving fixture placement
and physics untouched. The final well sample has 56 root tips at -0.222 to -0.004 m
relative to terrain. This sampling verifies the well tree, not every slope in the zone.

An optional `--bark=<directory>` replaces the placeholder noise bark with the 2k
Diffuse, OpenGL Normal and Roughness maps from
[Poly Haven bark_brown_02](https://polyhaven.com/a/bark_brown_02), Rob Tuytel, CC0.
Expected names: `bark_colour.jpg`, `bark_normal.png`, `bark_roughness.jpg`, plus
`source.json` recording attribution, URLs and checksums. The supplied foliage stays intact.
Maps and the new scene are privately archived rather than committed to public source.

Checks run against the actual Godot renderer, without a server or account:

- `check_elm_repair.gd`: identical triangle positions/UVs, complete unit normals,
  correct texture pixels and root contact at the well.
- `preview_elm.gd --check --manifest=...`: exact original restoration, unchanged
  collision shapes, reload handling and rejected scene hash mismatch.
- `check_all_elms.gd --manifest=...`: all 661 existing placements, visibility range
  synchronization, original restoration, region reload and safe partial-match failure.
- Five rendered A/B views include roots and bark close-ups. These are offline scene
  checks, not a live gameplay or forest LOD performance certification.

The owner requested the shared model update for all 661 Connacht elms. A versioned
manifest and guarded activation preserve the previous model for rollback. Visual approval
remains pending; this repair does not mark the prototype's foliage or LOD work complete.
Private archive: `DAoC-Godot-Remasters/graphics/zone207/elm-repair-20261022`.
