# Welded first-elm review and Elm2 upper-shoot pruning

The previous ring-thickness correction did not weld intersecting tubes. The owner
still saw hard joints, while other nearby elms retained their earlier geometry.

The new **single first-elm review specimen** uses a smooth signed-distance union of
the trunk and larger branch segments, sampled at 0.045 source metres. Its major
surface has 453,894 triangles and every edge is shared by exactly two faces. A trial
reduction introduced non-manifold edges, so it was rejected. 11,164 original fine-shoot
triangles are retained; these fine shoots are not claimed to be a welded manifold.
The resulting model has **481,902 triangles including foliage**. It is a deliberately
heavy geometry review, not a replacement approved for the 661 zone placements.

All original leaf geometry and embedded texture bytes are retained. The original
first-elm uniform scale (1.41930538923305) is kept explicitly: the rounded underground
base must not shrink the crown during height normalization. Ground seating is checked.
The accepted photographic bark images remain unchanged; world triplanar projection
avoids the UV transfer seams exposed by the union mesh. Bark mapping/orientation is
therefore different and still subject to the owner's visual approval.

Elm2 receives a limited upper-crown prune: 34 thin high twig components (872 wood
triangles) and 280 isolated upper leaf cards (5% of 5,600 cards). Retained vertex/UV
arrays and embedded images are unchanged. Its prepared scene has 39,366 triangles.
Its leaf material now has the same alpha-to-coverage and low-specularity settings as
the first review model.

The LAB review stand temporarily hides five older private elm visuals (ten mesh parts)
near the pair so they cannot be mistaken for the updated specimens. Their Inspector
rows are omitted while hidden, then return with the originals. No fixture/database or
collision changes are made. Only `review_stand.json` changes; the shared 661-tree
activation remains unchanged, with the prior stand configuration saved for rollback.

Temporal anti-aliasing is enabled only while the review stand is attached. The owner
can toggle it with **Ctrl+Shift+F7** (the HUD says “Suavizar hojas”). Plain Ctrl+F7 keeps
its existing time-of-day action. The previous viewport setting is restored when the
stand is removed. This trades some sharpness for stability; motion shimmer is awaiting
owner review, not declared eliminated by still captures.

Checks: closed major union, source/scene geometry and texture transfer, preserved crown
scale, grounded base, two models, five hidden/restored trees, collision count, reload,
AA toggle/restoration, and actual renderer captures. These are offline checks without
a server/account. No live player session was restarted or modified.

Private archive: `DAoC-Godot-Remasters/graphics/zone207/elm-fused-review-20261022`.
The local geometry pipeline uses scikit-image 0.26, scipy 1.18 and fast-simplification
0.2; only the closed full-resolution union is accepted for this visual trial.
