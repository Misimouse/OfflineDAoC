# Inactive original reward codec

264 compiled checks pass for the original1.127 quest dialog and its two request
paths. The bounded parser retains original title/summary/story, goals, unsigned
money, experience byte and modern fixed/optional item records. It rejects every
truncated prefix of the test packet, trailing bytes, invalid header/identities,
inconsistent repeated quest ID and unencodable choice counts. Reward records
reuse the already tested modern item boundary reader, including optional spell
fields; all may legitimately have the same item slot.

Accept/decline uses original DialogResponse QuestSubscribe0x64 and the actual
quest/giver identities. Echoing the incoming0x22 window code has no matching DOL
handler. Finishing uses the distinct20-byte QuestRewardChosen0xE8 body, with
exact required choices, unique in-range indices and at most eight selections.
Zero-choice rewards remain supported. Neither builder awards or completes a
quest locally.

This is an inactive source candidate compiled in a private copy. No normal
decoder dispatch, network binary, UI, server rule or database was changed.
Next gate: actual original-server offer/accept/reward/choice and saved inventory
outcomes, followed by token-bound state and original UI before installation.
Future quest-interface modernization remains outside this package.
