# Original merchant roundtrip from an empty inventory

The installed inventory fix passes15 ordinary-server merchant checks. A marked,
disposable Magician starts with no inventory rows and a funded account/realm
balance. The original Evan catalogue is copied from its pinned read-only source
only into the private QA database. Names, icons and prices remain original.

The empty character receives exactly one purchased nadurtha vest and pays its
catalogue price. The original server refuses reinforced armor for Magician;
the bridge ends the denied request while retaining the actual backpack item
and money. Selling removes the item and pays the original item_sell_ratio.
Insufficient funds, stale catalogue/item handles, duplicate sale and purchasing
from a dismissed catalogue are refused. Normal logout saves the balance.

Both clients/server exit normally. Private data and libraries are restored;
normal native/server hashes are unchanged. No runtime change beyond the prior
empty-inventory delivery is needed. These are server/state checks, not rendered
merchant or all-class armor acceptance. Private proof: EmptyInventoryTradeLab.

Reproduce with DAOC_MERCHANT_QA_LAB=EmptyInventoryTradeLab and
verify_merchant_lifecycle_real.py in the marked private QA runtime.
