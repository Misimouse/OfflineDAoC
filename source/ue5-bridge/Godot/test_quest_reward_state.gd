extends SceneTree

const RewardState = preload("res://quest_reward_state.gd")

class Wire:
    var calls: Array = []
    var available := true

    func QuestOffer(quest: int, giver: int, accept: bool) -> bool:
        if available:
            calls.append([quest, giver, accept])
        return available

    func QuestReward(quest: int, giver: int, count: int, options: int, choices: PackedInt32Array) -> bool:
        if available:
            calls.append([quest, giver, count, options, Array(choices)])
        return available

var checks := 0
var failures: Array = []

func check(ok: bool, label: String) -> void:
    checks += 1
    if not ok:
        failures.append(label)

func _initialize() -> void:
    var state = RewardState.new()
    var wire := Wire.new()
    var context := {"alive": true, "selected": "npc:12", "conversation": "npc:12", "distance_m": 2, "conversation_epoch": 1,
        "npc": {"id": "npc:12", "kind": "npc", "name": "Keeper", "model_id": 110, "health": 1}}
    var offer := {"code": 0x22, "type": 2, "quest_id": 31, "giver_id": 12, "title": "Reward Test",
        "required_choices": 2, "fixed_items": [{"name": "Coin Purse"}], "optional_items": [{"name": "Club"}, {"name": "Cloak"}, {"name": "Ring"}]}
    var reward := offer.duplicate(true)
    reward.code = 0x21
    reward.type = 1
    var journal := [{"index": 7, "name": "Reward Test (Level 1)"}]
    check(not state.receive(offer, {}), "requires current living NPC")
    var remote := context.duplicate(true)
    remote.distance_m = 6.01
    check(not state.receive(offer, remote), "refuses outside interaction distance")
    remote.distance_m = NAN
    check(not state.receive(offer, remote), "refuses non-finite distance")
    remote.distance_m = 2
    remote.npc.kind = "player"
    check(not state.receive(offer, remote), "refuses player identity")
    check(state.receive(offer, context), "accepts original offer")
    var token: String = state.snapshot().token
    var other = RewardState.new()
    check(other.receive(offer, context) and not other.request({"token": token, "action": "accept"}, wire, context, [], 0), "same dialog in another session refuses its token")
    check(state.receive(offer, context) and state.snapshot().token == token, "identical network repeat retains token")
    check(not state.request({"token": token, "action": "finish", "choices": [0, 1]}, wire, context, [], 10), "offer cannot award")
    check(not state.request({"token": token, "action": "accept"}, wire, context, journal, 11), "known active quest cannot accept again")
    wire.available = false
    check(not state.request({"token": token, "action": "accept"}, wire, context, [], 12) and not state.snapshot().pending, "send refusal does not close or wait")
    wire.available = true
    check(state.request({"token": token, "action": "accept", "quest_id": 999, "giver_id": 999}, wire, context, [], 20), "accept original offer")
    check(wire.calls == [[31, 12, true]], "uses packet identities")
    check(state.snapshot().pending and not state.receive(reward, context), "waits for authoritative update")
    state.maintain(context, [{"index": 8, "name": "Reward Test (Level Other)"}], 50)
    check(state.snapshot().pending, "similar title does not confirm")
    state.maintain(context, journal, 60)
    check(not state.snapshot().pending and not state.receive(offer, context), "real journal confirms and old offer cannot replay")
    context.conversation_epoch += 1
    check(state.receive(reward, context), "new reward conversation")
    token = state.snapshot().token
    var finish := {"token": token, "action": "finish", "choices": [2.0, 0], "required_choices": 0}
    check(not state.request({"token": token, "action": "decline"}, wire, context, journal, 70), "reward cannot use offer response")
    for invalid in [[], [0], [0, 0], [0, 3], [0, 1.5], [0, true], [0, NAN], [0, "1"], [0, 1, 2]]:
        var bad := finish.duplicate()
        bad.choices = invalid
        check(not state.request(bad, wire, context, journal, 75), "invalid choices %s" % [invalid])
    check(not state.request(finish, wire, context, [], 80), "requires active journal match")
    check(not state.request(finish, wire, context, journal + [{"index": 8, "name": "Reward Test"}], 80), "ambiguous journal match refused")
    context.exchange_busy = true
    check(not state.request(finish, wire, context, journal, 80), "blocks concurrent exchange")
    context.exchange_busy = false
    check(state.request(finish, wire, context, journal, 80), "accepts distinct in-range UI choices")
    check(wire.calls.back() == [31, 12, 2, 3, [2, 0]], "encodes original metadata and indices")
    check(not state.request(finish, wire, context, journal, 90) and wire.calls.size() == 2, "double click emits one request")
    state.maintain(context, journal, 100)
    check(state.snapshot().pending, "no client grant")
    state.maintain(context, [], 120)
    check(not state.snapshot().pending and not state.receive(reward, context), "journal update closes request without replay")
    context.conversation_epoch += 1
    check(state.receive(reward, context), "opens new context")
    token = state.snapshot().token
    check(state.request({"token": token, "action": "close"}, wire, context, journal, 130) and wire.calls.size() == 2, "Not Yet stays local")
    check(state.receive(reward, context) and state.snapshot().token != token, "new token after closing")
    state.observe("remove", {"oid": 12})
    check(state.snapshot().dialog.is_empty(), "removal invalidates even if same OID reappears")
    context.conversation_epoch += 1
    check(state.receive(offer, context), "new offer after NPC replacement")
    token = state.snapshot().token
    context.npc.model_id = 999
    check(not state.request({"token": token, "action": "accept"}, wire, context, [], 140), "identity change invalidates action")
    check(state.receive(offer, context), "fresh original packet for new model")
    token = state.snapshot().token
    check(state.request({"token": token, "action": "accept"}, wire, context, [], 150), "fresh acceptance waits")
    state.maintain(context, [], 5150)
    check(not state.snapshot().pending and wire.calls.size() == 3 and not state.receive(offer, context), "timeout never retries or reopens replay")
    context.conversation_epoch += 1
    check(state.receive(offer, context), "fresh interaction after timeout")
    token = state.snapshot().token
    check(state.request({"token": token, "action": "decline"}, wire, context, [], 5200) and wire.calls.back() == [31, 12, false], "decline encodes original response")
    check(not state.snapshot().pending, "decline does not wait for a journal entry")
    context.conversation_epoch += 1
    reward.required_choices = 0
    check(state.receive(reward, context), "opens fixed-only reward")
    token = state.snapshot().token
    check(state.request({"token": token, "action": "finish", "choices": []}, wire, context, journal, 5300), "fixed reward sends zero choices")
    state.observe("region_changed", {})
    check(not state.snapshot().pending and state.snapshot().token.is_empty(), "session transition clears pending state")
    print(JSON.stringify({"passed": failures.is_empty(), "checks": checks, "failures": failures}))
    quit(0 if failures.is_empty() else 1)
