"""Assemble the quest candidate over the exact installed trade gateway sources."""
from pathlib import Path
import shutil


def stage_gateway(godot: Path, state: Path) -> None:
    def replace(text, old, new):
        if text.count(old) != 1:
            raise ValueError("Quest gateway predecessor has changed: " + old)
        return text.replace(old, new, 1)

    gateway = godot / "live_gateway.gd"
    transport = godot / "visual_bridge.gd"
    live = gateway.read_text(encoding="utf-8-sig")
    wire = transport.read_text(encoding="utf-8-sig")
    live = replace(live, "var player_trade:RefCounted", """var player_trade:RefCounted
var quest_rewards:RefCounted
var quest_conversation_epoch:=0""")
    live = replace(live, '    player_trade=load(folder.path_join("player_trade_controller.gd")).new()', '''    player_trade=load(folder.path_join("player_trade_controller.gd")).new()
    quest_rewards=load(folder.path_join("quest_reward_state.gd")).new()''')
    live = replace(live, "func world_event(kind:String,data:Dictionary)->void:", '''func quest_context()->Dictionary:
    var id:String=interaction.conversation_id
    var row:Dictionary=adapter.entities.get(id,{})
    return {"alive":server.playing and not leaving and player_state.alive(),"selected":interaction.selected_id,
        "conversation":id,"conversation_epoch":quest_conversation_epoch,"npc":row,"distance_m":interaction._distance(row,position),
        "exchange_busy":player_trade.blocks_inventory() or exchange.inventory_locked() or not inventory.pending.is_empty()}

func world_event(kind:String,data:Dictionary)->void:
    if kind=="quest_dialog":
        for items in [data.get("fixed_items",[]),data.get("optional_items",[])]:
            for item in items:
                item["icon"]=server.item_icon(int(item.get("model",0)))
        quest_rewards.receive(data,quest_context())
        return
    if kind!="death" or int(data.get("oid",0))==int(server.me_oid):
        quest_rewards.observe(kind,data)''')
    live = replace(live, '    if action in ["target_object","target_loot","get_object"]:', '''    if action=="quest_reward_response":
        var now:=Time.get_ticks_msec()
        journal.sync(server,now)
        var reply:=value.duplicate()
        reply["action"]=value.get("action_name","")
        quest_rewards.request(reply,server.client,quest_context(),journal.entries,now)
        return
    if action=="journal_remove" and quest_rewards.finishing():return
    if quest_rewards.finishing() and action in ["player_trade_begin","player_trade_update","player_trade_accept","inventory_move","inventory_equip","inventory_unequip","inventory_give","merchant_buy","merchant_sell","exchange_buy","exchange_list","exchange_take","exchange_claim"]:return
    if action in ["target_object","target_loot","get_object"]:''')
    live = replace(live, "        interaction.execute(value,server.client,adapter.entities,position)", '''        if interaction.execute(value,server.client,adapter.entities,position) and action=="interact":
            quest_conversation_epoch+=1
        quest_rewards.maintain(quest_context(),journal.entries,Time.get_ticks_msec())''')
    live = replace(live, "        journal.sync(server,now);classic_ui.journal=journal.snapshot()", '''        journal.sync(server,now);classic_ui.journal=journal.snapshot()
        quest_rewards.maintain(quest_context(),journal.entries,now)''')
    live = replace(live, '        transport.snapshot_metadata["classic_ui"]=classic_ui.snapshot()', '''        if not server.playing or leaving:
            quest_rewards.reset()
        else:
            quest_rewards.maintain(quest_context(),journal.entries,now)
        transport.snapshot_metadata["quest_rewards"]=quest_rewards.snapshot()
        transport.snapshot_metadata["classic_ui"]=classic_ui.snapshot()''')
    wire = replace(wire, '"character_lobby","player_trade","exchange"', '"character_lobby","player_trade","quest_rewards","exchange"')
    wire = replace(wire, '"journal_remove","journal_guide"', '"quest_reward_response","journal_remove","journal_guide"')
    shutil.copy2(state, godot / state.name)
    gateway.write_text(live, encoding="utf-8")
    transport.write_text(wire, encoding="utf-8")
