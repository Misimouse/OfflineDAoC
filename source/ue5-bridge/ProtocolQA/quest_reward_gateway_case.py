"""Run the ordinary-server reward fixture through the candidate gateway action."""
from pathlib import Path
from quest_reward_wire_case import prepare as prepare_wire, QUEST
from prepare_combined_expansion_data import digest


def prepare(db, leader, world, result):
    prepare_wire(db, leader, world, result)
    for path in [Path(__file__), Path(__file__).with_name("stage_quest_reward_gateway.py"),
                 Path(__file__).parents[1] / "Godot/quest_reward_state.gd"]:
        result["source_inputs"][str(path.resolve())] = digest(path)


def run(a, b, wait, settle, result, checked, output, world, leader):
    checks = result["checks"]

    def state(peer=a):
        return peer.snapshot.get("quest_rewards", {})

    def dialog(peer=a):
        return state(peer).get("dialog", {})

    def active():
        return any(q["name"].startswith("Codex Reward Protocol") for q in
                   a.snapshot.get("classic_ui", {}).get("journal", {}).get("entries", []))

    def inventory(peer):
        return peer.snapshot.get("inventory", {})

    def count(name, peer=a):
        return sum(i.get("count", 1) for i in inventory(peer).get("items", []) if i.get("name", "").lower() == name)

    def copper(peer=a):
        coins = inventory(peer).get("money", {})
        return sum(coins.get(k, 0)*v for k, v in [("copper",1),("silver",100),("gold",10000),("platinum",10000000),("mithril",10000000000)])

    def respond(peer, action, token, **payload):
        peer.send("quest_reward_response", action_name=action, token=token, **payload)

    wait(lambda: all(inventory(p).get("ready") for p in [a,b]) and
         any(r.get("name")=="Codex Reward Keeper" for r in a.snapshot["entities"]), "Isolated NPC and inventories ready")
    npc = next(r for r in a.snapshot["entities"] if r.get("name")=="Codex Reward Keeper")
    base_money, other_money = copper(), copper(b)
    cloak, poison, other_cloak = count("cloak"), count("minor lethal poison"), count("cloak", b)

    def open_window(code):
        old = state().get("token", "")
        a.send("interact", entity_id=npc["id"])
        wait(lambda: dialog().get("code")==code and state().get("token")!=old, "Bound original quest dialog")
        return state()["token"]

    first = open_window(0x22)
    checks["gateway_shows_only_bound_original_offer"] = dialog()["quest_id"]==QUEST+32767 and not dialog(b)
    respond(a, "decline", first)
    wait(lambda: not dialog(), "Decline closes the dialog")
    checks["decline_does_not_create_journal"] = not active() and copper()==base_money
    settle(1)
    second = open_window(0x22)
    respond(a, "accept", first)
    settle(.3)
    checks["stale_token_refuses_accept"] = state()["token"]==second and not active()
    respond(a, "accept", second)
    wait(lambda: active() and not state().get("pending") and not dialog(), "Journal acknowledges original accept")
    checks["offer_accept_confirmed_by_journal"] = True
    settle(1)
    token = open_window(0x21)
    reward = dict(dialog())
    respond(b, "finish", token, choices=[1])
    respond(a, "finish", token, choices=[-1])
    settle(.4)
    checks["invalid_choice_and_cross_session_token_refused"] = state()["token"]==token and active() and copper(b)==other_money and count("cloak",b)==other_cloak
    respond(a, "close", token)
    wait(lambda: not dialog(), "Not Yet closes without a grant")
    checks["not_yet_preserves_original_quest"] = active() and copper()==base_money
    settle(1)
    token2 = open_window(0x21)
    respond(a, "finish", token2, choices=[1], giver_id=0, quest_id=0)
    respond(a, "finish", token2, choices=[1])
    wait(lambda: not active() and not state().get("pending") and copper()==base_money+321 and count("cloak")==cloak+1 and count("minor lethal poison")==poison+int(reward["fixed_items"][0]["value1"]), "Authoritative journal and inventory")
    settle(.5)
    checks["single_gateway_grant_after_double_click"] = copper()==base_money+321 and count("cloak")==cloak+1
    for peer in [a,b]:
        peer.send("chat", text="/quit")
        wait(lambda: not peer.snapshot.get("in_game",True) and peer.snapshot.get("character_lobby",{}).get("ready"), "Original logout saves",90)
    with checked() as db:
        row=db.execute("SELECT Step,Count FROM CharacterXDataQuest WHERE Character_ID=? AND DataQuestID=?", (leader["DOLCharacters_ID"], QUEST)).fetchone()
        checks["gateway_completion_persisted_once"] = row is not None and row["Step"]<=0 and row["Count"]==1
