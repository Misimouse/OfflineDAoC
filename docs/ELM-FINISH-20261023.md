# Elm finishing pass after owner feedback, 2026-10-23

The owner accepted the first elm's geometry and foliage, and Elm2's foliage and
texture. Scope is limited to the first elm's pale repeated bark band and Elm2's
oversized child branches growing from thinner parent branches.

The first elm uses the exact same source GLB and placement. Its bark shader now
normalizes broad luminance variations baked into the source photograph before
mixing the offset samples. Fine grain, original image pixels, normal and roughness
maps, foliage materials and AA settings are retained. The earlier offset-only
blend reduced repetition but left the original photograph's pale band visible.

Elm2's 583 surviving original wood tubes are reconstructed from their actual
indexed ring order. Parent attachments are inferred from the nearest earlier
centreline. The parent radius is increased, only where necessary upstream of a
child attachment, to at least 1.15 times the child radius plus its axis offset.
Additional rings stop reinforcement at the actual attachment, avoiding thick
unused spurs beyond it. Source ring order and triangle winding are verified before
rebuilding. There are 235 reinforced parents and zero support-ratio violations.
The largest source radius changes from 0.85 to 0.92404 source metres. The original
centrelines and the existing UV mapping along each tube remain in place.

Elm2's accepted foliage and short curved shoots retain byte-identical positions,
UVs, indices, materials and embedded images. No additional shoots or removed
leaves are introduced. Both prepared scenes keep their previous uniform scales.

Geometry/material/root-contact checks and close A/B renders passed separately
from the owner's running game. The two-tree stand also checks collision and AA
preservation, restoration and reload. These checks do not replace the owner's
final visual review of bark and branch proportions.

Private scene bundles: `even_bark_20261023` and `elm2_supported_20261023`, under
`.enhanced-session/elm_trial/bundles`. Same Inspector identities and LAB positions.
`review_stand_before_finish_20261023.json` restores the previous pair. Shared
661-tree activation, stock art, databases, client/server processes and gameplay
are untouched. Private binaries, pipeline and reports are archived in Remasters
under `graphics/zone207/elm-finish-20261023`.
