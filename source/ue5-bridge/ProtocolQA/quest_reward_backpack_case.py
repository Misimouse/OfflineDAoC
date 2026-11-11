"""Verify the installed reward client recovers from the original full-backpack refusal."""
from pathlib import Path
from uuid import uuid4

from prepare_combined_expansion_data import digest
from quest_reward_gateway_case import prepare as prepare_reward
from quest_reward_wire_case import QUEST


def prepare(db, leader, world, result):
    prepare_reward(db, leader, world, result)
    owner = leader["DOLCharacters_ID"]
    source = dict(db.execute("SELECT * FROM Inventory WHERE OwnerID=? AND SlotPosition=40", (owner,)).fetchone())
    cloak = db.execute("SELECT Item_Type FROM ItemTemplate WHERE Id_nb='cloak'").fetchone()
    cloak_slot = int(cloak[0])
    assert 21 <= cloak_slot <= 29
    db.execute("DELETE FROM Inventory WHERE OwnerID=? AND SlotPosition IN (?,78,79)", (owner, cloak_slot))
    used = {row[0] for row in db.execute("SELECT SlotPosition FROM Inventory WHERE OwnerID=?", (owner,))}
    fields = list(source)
    sql = "INSERT INTO Inventory (" + ",".join('"' + field + '"' for field in fields) + ") VALUES (" + ",".join("?" for _ in fields) + ")"
    for slot in range(40, 79):
        if slot in used:
            continue
        item = dict(source, Inventory_ID=str(uuid4()), ITemplate_Id="cloak" if slot == 78 else "club",
                    UTemplate_Id=None, SlotPosition=slot, Count=1)
        db.execute(sql, [item[key] for key in fields])
    result["source_inputs"][str(Path(__file__).resolve())] = digest(Path(__file__).resolve())
    result["equipped_test_slot"] = cloak_slot


def run(a, b, wait, settle, result, checked, output, world, leader):
    checks = result["checks"]

    def inventory():
        return a.snapshot.get("inventory", {})

    def entries():
        return inventory().get("items", [])

    def count(name):
        return sum(row.get("count", 1) for row in entries() if row.get("name", "").lower() == name)

    def state():
        return a.snapshot.get("quest_rewards", {})

    def active():
        rows = a.snapshot.get("classic_ui", {}).get("journal", {}).get("entries", [])
        return any(row["name"].startswith("Codex Reward Protocol") for row in rows)

    def bag():
        return {row["slot"]: row for row in entries() if 40 <= row["slot"] <= 79}

    def copper(coins):
        return sum(coins.get(key, 0)*value for key, value in
                   (("copper", 1), ("silver", 100), ("gold", 10000), ("platinum", 10000000), ("mithril", 10000000000)))

    def respond(action, token, **values):
        a.send("quest_reward_response", action_name=action, token=token, **values)

    wait(lambda: inventory().get("ready") and len(bag()) == 39 and
         any(row.get("name") == "Codex Reward Keeper" for row in a.snapshot["entities"]), "Backpack and test NPC")
    npc = next(row for row in a.snapshot["entities"] if row.get("name") == "Codex Reward Keeper")
    baseline_money = dict(inventory()["money"])
    baseline_poison = count("minor lethal poison")
    baseline_cloak = count("cloak")
    checks["one_slot_free_for_two_rewards"] = 79 not in bag() and bag()[78]["name"].lower() == "cloak"

    def open_dialog(code):
        a.send("interact", entity_id=npc["id"])
        wait(lambda: state().get("dialog", {}).get("code") == code, "Original quest dialog")
        return state()["token"]

    respond("accept", open_dialog(0x22))
    wait(lambda: active() and not state().get("pending"), "Quest accepted by server")
    settle(1)
    denied_token = open_dialog(0x21)
    respond("finish", denied_token, choices=[1])
    wait(lambda: state().get("pending"), "Reward request sent")
    wait(lambda: "inventory does not have enough space" in str(a.snapshot.get("chat", {})).lower(), "Original insufficient-space response")
    checks["original_server_refusal_reaches_client"] = True
    checks["refusal_preserves_quest_items_and_money"] = (active() and dict(inventory()["money"]) == baseline_money
         and count("minor lethal poison") == baseline_poison and count("cloak") == baseline_cloak and len(bag()) == 39)
    wait(lambda: not state().get("pending"), "Refused request expires without retry")
    checks["no_predicted_completion_or_automatic_retry"] = active() and not state().get("dialog") and state().get("feedback", "").startswith("The server has not confirmed")
    cloak = bag()[78]
    a.send("inventory_equip", slot=78, item_token=cloak["token"], inventory_revision=inventory()["state_revision"])
    wait(lambda: len(bag()) == 38 and not inventory().get("pending") and any(
        row["slot"] == result["equipped_test_slot"] and row["name"].lower() == "cloak" for row in entries()), "Equip original cloak to make room")
    checks["ordinary_equipment_frees_required_backpack_slot"] = True
    retry_token = open_dialog(0x21)
    expected_coins = copper(baseline_money) + state()["dialog"]["money"]
    expected_poison = baseline_poison + state()["dialog"]["fixed_items"][0]["value1"]
    checks["retry_uses_fresh_dialog_identity"] = retry_token != denied_token
    respond("finish", denied_token, choices=[1])
    settle(.25)
    checks["refused_dialog_cannot_be_reused"] = state().get("token") == retry_token and active()
    respond("finish", retry_token, choices=[1])
    wait(lambda: not active() and not state().get("pending") and count("cloak") == baseline_cloak + 1 and
         count("minor lethal poison") == expected_poison and copper(inventory()["money"]) == expected_coins,
         "Original journal, items and coins all update after making room")
    checks["successful_retry_receives_both_rewards"] = True
    for peer in (a, b):
        peer.send("chat", text="/quit")
        wait(lambda: not peer.snapshot.get("in_game", True) and peer.snapshot.get("character_lobby", {}).get("ready"), "Save and leave the original server", 90)
    with checked() as db:
        row = db.execute("SELECT Step,Count FROM CharacterXDataQuest WHERE Character_ID=? AND DataQuestID=?", (leader["DOLCharacters_ID"], QUEST)).fetchone()
        checks["one_completion_saved_after_refusal"] = row is not None and row["Step"] <= 0 and row["Count"] == 1
        saved = {row["ITemplate_Id"]:row["count"] for row in db.execute(
            "SELECT ITemplate_Id, SUM(Count) AS count FROM Inventory WHERE OwnerID=? AND ITemplate_Id IN ('cloak','minor_lethal_poison') GROUP BY ITemplate_Id",
            (leader["DOLCharacters_ID"],))}
        checks["both_reward_items_saved"] = saved.get("cloak") == baseline_cloak + 1 and saved.get("minor_lethal_poison") == expected_poison
