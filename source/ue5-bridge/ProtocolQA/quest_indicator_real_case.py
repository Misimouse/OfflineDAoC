"""Observe real NPC create and quest effect packets with two ordinary sessions."""
from pathlib import Path

from prepare_combined_expansion_data import digest
from quest_reward_gateway_case import prepare as prepare_reward
from quest_reward_wire_case import QUEST


def prepare(db, leader, world, result):
    prepare_reward(db, leader, world, result)
    for path in (Path(__file__), Path(__file__).with_name("stage_quest_indicators.py")):
        result["source_inputs"][str(path.resolve())] = digest(path)


def run(a, b, wait, settle, result, checked, output, world, leader):
    checks = result["checks"]

    def keeper(peer=a):
        return next((row for row in peer.snapshot.get("entities", []) if row.get("name") == "Codex Reward Keeper"), {})

    def marker(peer=a):
        return keeper(peer).get("quest_indicator")

    def effect(value, peer=a):
        npc = keeper(peer).get("id", "")
        return npc.startswith("npc:") and any(
            row["oid"] == int(npc.split(":")[1]) and row["value"] == value
            for row in peer.snapshot.get("qa_marker_updates", []))

    def dialog():
        return a.snapshot.get("quest_rewards", {})

    def open_window(code):
        a.send("interact", entity_id=keeper()["id"])
        wait(lambda: dialog().get("dialog", {}).get("code") == code, "Original reward test dialog")
        return dialog()["token"]

    wait(lambda: marker(a) == marker(b) == 1, "Server NPC-create available markers on two clients")
    checks["npc_create_carries_authoritative_available_marker"] = True
    a.send("quest_reward_response", action_name="accept", token=open_window(0x22))
    wait(lambda: marker() == 2 and effect(2) and not dialog().get("pending"), "Accept changes current NPC to turn-in via subtype 7")
    checks["effect_7_updates_existing_npc_without_reentering"] = True
    checks["quest_mark_is_specific_to_the_viewing_player"] = marker(b) == 1 and not effect(2,b)
    settle(1)
    a.send("quest_reward_response", action_name="finish", token=open_window(0x21), choices=[1])
    wait(lambda: marker() == 0 and effect(0) and not dialog().get("pending"), "Completing clears original marker")
    checks["completion_clears_marker_without_reentering"] = marker(b) == 1
    for peer in (a, b):
        peer.send("chat", text="/quit")
        wait(lambda: not peer.snapshot.get("in_game",True) and peer.snapshot.get("character_lobby",{}).get("ready"), "Save and quit",90)
    checks["logout_removes_quest_marker_rows"] = not keeper(a) and not keeper(b)
    with checked() as db:
        row = db.execute("SELECT Step,Count FROM CharacterXDataQuest WHERE Character_ID=? AND DataQuestID=?", (leader["DOLCharacters_ID"], QUEST)).fetchone()
        checks["marker_changes_match_saved_completion"] = row is not None and row["Step"] <= 0 and row["Count"] == 1
