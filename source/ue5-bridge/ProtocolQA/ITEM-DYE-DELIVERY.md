# Original backpack dye combinations

The installed inventory move path already reaches DOL's original CombineItems/DyeItem logic. No additional runtime, palette, native binary or server change was needed.

Nineteen checks against the installed backend and a marked disposable DOL database verify cloth dye on a cloak and cloth armor, leather dye, shield enamel and weapon luster. Each accepted combination consumes one vial, applies the original color and clears the item's emblem according to the existing server rule. Stale repeats consume nothing. An unsuitable combination keeps the vial count and target color unchanged; original inventory rules may swap the two backpack slots, which is not treated as a new refusal rule. Dyed cloak and cloth armor retain their color when equipped, and all five colors persist after normal shutdown. Wallets are unchanged. All private fixtures and copied server libraries are restored.

The fixture uses ordinary privileges and an original Hibernian cloth vest for the equipped check. An initial other-realm vest was correctly refused by the server; that exposed a separate delayed rejection-feedback issue, recorded for the next package. No realm or class restriction was weakened to make this test pass.

Owner review: place an eligible item and its matching original dye in the backpack, drag the dye onto the item, then equip it and re-enter. Confirm one vial is consumed and the color remains. Applying a dye removes an existing emblem under the original rules, so use an item you intend to recolor. Palette/material appearance still requires visual owner review; these checks certify the transaction and saved data, not a graphical remaster or every armor material.
