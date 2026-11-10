# Original item shortcuts: bounded delivery

Original game_ui.gd Use Item equips a selected backpack item with valid equipment slots; otherwise it uses the server item. It does not unequip worn charges. Sell supports the selected backpack slot or a dragged inventory item while the original merchant window is open.

The native candidate routes U through existing inventory_equip or canonical ui_use. It reuses current item tokens, inventory revision and canonical entry tokens. Sale reuses merchant_sell and current merchant identity/revision. A dragged item must still match its original item token; cancellation marks the drag handled before discarding it so unrelated world-drop/give callbacks cannot run. No item, money, armor proficiency, charge, reuse or success state is fabricated locally.

Use Item defaults to U. Sell appears in Controls but starts unbound: original Shift+S overlaps the accepted S/Shift+S backward movement, and this delivery preserves those controls. A free chord can be assigned. Second Use Item, destruction, salvage/crafting and full original presets are separate work. Pending inventory, death, chat/options and character exit keep their gates. Worn and vault items cannot be sold; vault use requires withdrawal.

Candidate evidence:507 native checks exercise actual key dispatch and previous controls;113 existing inventory, armor-denial, canonical UI and consumable-detail checks pass. Thirteen ordinary disposable merchant checks verify catalogue/price/icons, exact buy/sell changes, stale items/catalogues and saved balances. Eleven original consumable-server checks verify refusals, healing, shared reuse, current remaining charges, money preservation and saved consumption. These server checks exercise the existing canonical commands; native keyboard and drag-token resolution are verified separately. Normal shutdown and private data/library restoration pass. This does not claim a rendered end-to-end keyboard sale against a live account.

The seven-file successor uses exact predecessor hashes, simulated damaged-plan rejection, backup and guarded rollback. Installed verification and owner gameplay review must be recorded separately. No player data, server rules, DOL population, WORK maps or art assets change.

All507 native checks repeat successfully against the installed client. The seven-file delivery passes31 simulated chain checks, installed predecessor verification and rollback preview. Owner gameplay review remains pending.
