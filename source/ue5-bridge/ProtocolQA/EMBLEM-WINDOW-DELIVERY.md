# Original guild emblem editor

The current private candidate reuses the original 219 x 288 picker frame, original palette (16 field colors, eight charge colors and four patterns), all 255 logo masks and the existing native shield material/UVs. A capture-only, non-colliding shield turns about a centered pivot; its geometry, surface and emblem textures are the already-imported original resources. It creates no replacement art or world lights.

The window opens only after the original server emblem-dialog packet. Preview edits remain local to the current authorized draft. SET EMBLEM sends the original four-byte EmblemChoice packet, retaining all eight logo bits; CANCEL and Escape never submit a choice. Character/guild changes, logout, stale tokens and repeat submissions cannot reuse the old editor. The interface remains in English.

The actual DOL server retains guild-leader permission checks, duplicate-emblem rules, the free first choice and the original 200-gold change confirmation/payment. The bridge never deducts coins or claims acceptance from the act of sending a request. The native preview is a draft, not a changed equipped item. Applying an emblem to an item through an EmblemNPC is a separate item handover transaction; this editor does not claim that additional path is migrated.

## Evidence and boundaries

Private evidence is under EmblemWindowLab. The state tests cover field bounds, high-bit logos, immutable snapshots, exact packet arguments, connection loss, character changes and cancellation. Gateway tests cover original event/command wiring. The final 29 native checks exercise the actual window, all logo textures, real captured geometry, centered rotation, retained logo-scroll position, pointer blocking and destruction of preview resources. Real DOL tests use a marked disposable database, ordinary account permissions and disposable guild/NPC/wallet fixtures. They verify free choice, original paid change, cancellation, repeat-submission protection, restricted-rank rejection and persistence after normal server shutdown. All fixtures and private server libraries are restored afterwards; played accounts and databases are not modified.

The installer requires exact source/build evidence and the installed guild predecessor. It replaces a bounded set of client files and adds two resources under a separate content namespace. No server binary, rules, world map or database is changed. It backs up existing files and supports bounded rollback. Owner gameplay acceptance remains separate from automated proof.

## Owner review after installation

Use the normal server launcher followed by INICIAR-ARDEE-GM.cmd. A guild leader can target an original emblemeer and use /gc emblem. Check the four selectors, scroll through logos, preview, Cancel and Escape. Confirm only if you intend the original server action: changing an existing emblem costs 200 gold. A character without the required guild rank must be rejected by the server. No membership or money is granted to the played character by the test tooling.

## Installed evidence, 7 November

Installed 15 bounded client files after 33 state, 12 gateway, 29 final native, nine real leader/payment/save and three restricted-member checks. The final native build passed 33 guild, 47 display, 257 controls, 53 movement, nine jump, 35 tracking, 65,559 water-data and the established 265 audio/UI checks. All 29 installed-window checks then passed using the installed resource path. The receipt-chain test passes 115 synthetic checks. The played database, server libraries and WORK map were unchanged; WORK remained open. Owner gameplay review remains pending.

An initial regression runner used the predecessor summary path. Its output was retained separately and the historical guild summary was reconstructed solely from the original proofs; the restored bytes match the original sealed SHA-256 exactly. Every guild evidence hash was verified afterwards. The corrected runner writes only to the new lab and refuses a sealed installed lab.
