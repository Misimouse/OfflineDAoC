# Installed player-trade cancellation

The installed gateway and installed network binary pass14 ordinary two-player
checks covering open-trade inventory move/equip/sell refusal, cancellation after
accepting, partner movement beyond range, stale acceptance after cancellation,
fresh offer identity on reopening, partner logout, recovered inventory movement
and saved item ownership without transfer or duplication. The original server
remains authoritative; no new runtime fix was required.

The first private run tried opening while only one client had discovered its
partner. The remote identity guard correctly cancelled that window. The final
test waits for both original player identities and then exercises the intended
transaction lifecycle. This preparation failure remains recorded separately
from the passing test.

The wrapper derives an explicit private runner from the existing two-player
harness, pins installed inputs and preserves the original source/candidate
evidence. It does not rewrite normal gateway code or bypass its session/token
checks. Data, server libraries, navigation and temporary network binaries are
restored; both clients and the private server close normally. The installed
receipt chain passes after the run. Owner gameplay acceptance remains pending.
