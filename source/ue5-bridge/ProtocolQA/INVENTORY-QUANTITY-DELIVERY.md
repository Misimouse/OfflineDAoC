# Original inventory quantity chooser

Shift-drag a carried stack onto an empty backpack or currently open vault slot
to open **Choose Quantity**. Normal dragging still moves the whole stack.
The chooser reuses the original `value_chooser.xml` dimensions, English labels,
frame, arrows, and Accept/Cancel artwork. Arrows change the amount by one;
holding Shift while clicking an arrow changes it by ten.

Accept sends the original `MoveItem(fromSlot, toSlot, count)` request. No item,
coin, stack count or destination is changed locally. DOL performs splitting,
merging and persistence. Cancel/Escape sends no move. Changed inventory,
container identity, character session or death invalidates the choice.

The bounded partial-stack operation requires an empty backpack/vault slot.
It cannot become equipment, poison application, NPC handover or a merchant
purchase. Existing whole-stack operations retain their original behavior.

Validation before delivery:

- 24 state checks, including malformed/excess quantities and stale commands.
- 25 ordinary-player server checks covering partial moves, original merges,
  personal/account vault isolation, persistence and duplicate prevention.
- 19 actual native widget/command checks and a rendered original panel.
- Existing vault regression: 25 state checks and 87 native checks.
- Full predecessor receipt simulation with damaged-receipt rejection before
  any installed file is replaced.

Protocol tests use a marked disposable database, restore its contents and
configuration, and stop both private processes normally. Installation requires
closed normal game/server ports, exact predecessor hashes and a backup, with
automatic rollback on failure. Original server rules and player databases are
not changed by this delivery. Owner gameplay review is tracked separately.
