# Vault regression after player-trade integration

The installed network binary and installed Godot gateway pass19 ordinary-server
vault checks in the marked disposable database. Personal deposits, stack counts,
last-slot reordering and withdrawals work. Account storage pages stay separate,
old keeper/page tokens are refused, closing hides cached storage, and deposits
do not charge money. Saved rows retain character ownership for the personal
vault and account/realm ownership for account storage, with no duplicate items.

The existing original vault UI separately passes25 state and87 installed native
checks. No runtime fix or server-rule change was required. The wrapper restores
its temporary network binaries; the underlying verifier restores private server
libraries and database and closes client/server normally. The full installed
receipt chain passes again after restoration. Owner bank-window review is still
pending; this is not a Housing or guild-vault implementation.

Next: ordinary player-trade cancellation when the partner moves away or logs
out, and competing inventory requests during an open trade. This checks the new
transaction lifecycle without changing unrelated world or appearance work.
