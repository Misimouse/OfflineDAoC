# First elm junction draft and two-tree LAB review

This work targets the **first** 30,162-triangle elm. Elm2 remains the separate
41,358-triangle candidate. The owner's close-ups show oversized branch starts,
blunt/open ends, repeated bark UV starts and shimmering leaf/shadow edges.

The original generator's pure geometry was reconstructed and checked against the
supplied GLB: all trunk positions match exactly and UVs match within float tolerance.
Its 431 independent tubes have no branch centres outside their inferred parent;
286 initial radii exceed 95% of the original supporting radius. Thick child starts
expose tube rims despite their centres being connected.

The draft narrows inner branch rings according to the supporting parent's adjusted
radius and centre offset, returning gradually to the original outer shape. There are
373 adjusted starts after propagation through the hierarchy. End rings taper to
3 mm. Every branch centre-line, the trunk/root base, all leaf vertices/UVs and embedded
texture bytes stay intact. Bark UV phase continues from each parent instead of
restarting identically on every child. This is a visual junction repair: independent
tubes still intersect; it does **not** claim a welded sculpted fork topology.

The prepared scene keeps the existing photographic bark maps, generates normals and
tangents, and tries alpha-to-coverage with reduced leaf specularity. Leaf shimmer
requires owner review in motion; it is not certified fixed from still captures.

An offline shadow-only probe moved the camera in 2.5 cm steps and paired shadow/no-shadow
renders. Connacht's 4096 atlas and splits 0.06/0.15/0.4 produced 203 large ratio jumps
instead of 268 in 97,920 sample pairs. Mean variation was similar (0.0193 vs 0.0186).
The improvement reduces large jumps rather than eliminating temporal variation.
Other zones keep their existing shadow settings.

`elm_review_stand.gd` is attached **only by Ardee LAB**. Its private hash-verified config
places the first draft at the well (1395.2,1302.4) and one Elm2 at (1440,1325), both
sampled onto the terrain, with different labels. The previous first-elm parts at the
well are hidden reversibly; no extra physics or fixture/database edits are made.
Inspector receives two distinct destinations for GO TO. The existing 661-tree
activation remains unchanged, and Ctrl+F9 hides the review stand when originals are shown.

Offline checks cover geometry/material transfer, base contact, two prepared models,
unchanged collision count, hiding/restoration/reload and script loading. The owner
must reopen the LAB client to load these edits; the running session/server is preserved.
Visual status: **review pending**, with welded fork topology and residual shimmer open.

Private archive: `DAoC-Godot-Remasters/graphics/zone207/elm-junction-review-20261022`.
