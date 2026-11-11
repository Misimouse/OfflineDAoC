"""Check that quest objectives follow the logged-in character and original abandonment."""
from pathlib import Path

from prepare_combined_expansion_data import digest
from quest_delivery_case import prepare as prepare_original_quest


ALTERNATE = "Codexmapalt"


def prepare(db, leader, world, result, reference):
    prepare_original_quest(db, leader, world, result, reference)
    occupied = {row[0] for row in db.execute("SELECT AccountSlot FROM DOLCharacters WHERE AccountName=?",
                                             (leader["AccountName"],))}
    slot = next(slot for slot in range(300, 310) if slot not in occupied)
    character = dict(leader, Name=ALTERNATE, AccountSlot=slot, DOLCharacters_ID="codex-private-map-alt", HCFlag=0)
    fields = ",".join(f'"{key}"' for key in character)
    placeholders = ",".join("?" for _ in character)
    db.execute(f"INSERT INTO DOLCharacters ({fields}) VALUES ({placeholders})", list(character.values()))
    result["source_inputs"][str(Path(__file__).resolve())] = digest(Path(__file__).resolve())


def run(a, b, wait, settle, result, checked, output, world, leader):
    checks = result["checks"]
    name = world["quest"]["Name"]

    def ui(peer):
        return peer.snapshot.get("classic_ui", {})

    def marks(peer=a):
        return ui(peer).get("quest_map_marks", [])

    def quest():
        return next((row for row in ui(a).get("journal", {}).get("entries", []) if name in row["name"]), None)

    def items():
        return a.snapshot.get("inventory", {}).get("items", [])

    def npc(npc_name):
        return next((row for row in a.snapshot.get("entities", [])
                     if row.get("kind") == "npc" and row.get("name") == npc_name), None)

    def leave(peer):
        peer.send("chat", text="/quit")
        wait(lambda: not peer.snapshot.get("in_game", True) and
             peer.snapshot.get("character_lobby", {}).get("ready"), "Original saved logout", 90)

    def enter(character):
        lobby = a.snapshot["character_lobby"]
        a.send("character_enter", name=character, lobby_revision=lobby["revision"])
        wait(lambda: a.snapshot.get("in_game") and a.snapshot.get("character") == character and
             ui(a).get("skills_ready") and "quest_map_marks" in ui(a), f"{character} entered the same connection", 45)

    wait(lambda: npc("Evan") and npc("Meara") and "quest_map_marks" in ui(a),
         "Original quest actors and map available")
    a.send("interact", entity_id=npc("Evan")["id"])
    settle(.4)
    a.send("chat", text="/whisper " + world["quest"]["AcceptText"])
    item_name = world["items"][0]["Name"]
    wait(lambda: quest() and any(row.get("name") == item_name for row in items()), "Original quest and letter granted")
    item = next(row for row in items() if row["name"] == item_name)
    target = npc("Meara")
    a.send("inventory_give", slot=item["slot"], item_token=item["token"],
           inventory_revision=a.snapshot["inventory"]["state_revision"], entity_id=target["id"],
           target_name=target["name"], target_model=target["model_id"])
    wait(lambda: quest() and "[Step #2]" in quest()["text"] and len(marks()) == 1,
         "Original second objective and journal available")
    objective = marks()[0]
    original = dict(quest())
    checks["active_objective_belongs_to_only_one_player"] = not marks(b)

    leave(a)
    checks["active_objective_hidden_in_character_menu"] = not marks()
    wait(lambda: any(row["name"] == ALTERNATE for row in a.snapshot["character_lobby"].get("characters", [])),
         "Private alternate character listed")
    enter(ALTERNATE)
    settle(.5)
    checks["alternate_character_has_no_old_quest_or_objective"] = not marks() and not quest()
    a.send("journal_remove", quest_index=original["index"], quest_token=original["token"])
    wait(lambda: "The journal has changed" in ui(a).get("journal", {}).get("feedback", ""),
         "Previous character's journal action refused")
    checks["previous_character_action_refused"] = True
    leave(a)

    enter(leader["Name"])
    wait(lambda: quest() and marks() == [objective], "Original saved objective restored for its owner")
    current = dict(quest())
    checks["saved_objective_restored_from_server"] = current["token"] != original["token"]
    before = dict(a.snapshot["inventory"]["money"])
    a.send("journal_remove", quest_index=current["index"], quest_token=current["token"])
    wait(lambda: not quest() and not marks(), "Original abandonment removes journal and map objective")
    checks["abandonment_clears_journal_and_map"] = True
    checks["abandonment_grants_no_money"] = a.snapshot["inventory"]["money"] == before
    checks["other_player_still_has_no_objective"] = not marks(b)
    leave(a)
    leave(b)
    with checked() as db:
        count = db.execute("SELECT COUNT(*) FROM CharacterXDataQuest WHERE Character_ID=? AND DataQuestID=?",
                           (leader["DOLCharacters_ID"], world["quest"]["ID"])).fetchone()[0]
    checks["abandoned_quest_not_saved_as_completed"] = count == 0
