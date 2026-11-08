extends SceneTree
class Client extends Node:
    var calls:Array=[]
    func MoveItem(a:int,b:int,n:int)->void:calls.append([a,b,n])
class Server extends Node:
    var playing:=true
    var client:Node=Client.new()
class Adapter extends Node:
    var entities:Dictionary={}
class Player extends "res://player_combat_state.gd":
    func _init()->void:
        ready=true;vitals={"health_pct":100}
class Exchange extends RefCounted:
    const ACTIONS=[]
    var locked:=false
    func inventory_locked()->bool:return locked
class Gateway extends "res://live_gateway.gd":
    func sync_inventory(_now:int)->void:pass
var checks:=0
var failures:Array=[]
func check(value:bool,label:String)->void:
    checks+=1
    if not value:failures.append(label)
func _initialize()->void:
    var gateway:=Gateway.new();var server:=Server.new();var adapter:=Adapter.new()
    gateway.server=server;gateway.adapter=adapter;gateway.player_state=Player.new();gateway.exchange=Exchange.new()
    gateway.inventory=load("res://inventory_state.gd").new();gateway.interaction=load("res://interaction_state.gd").new()
    var rows:Array=[{"slot":40,"count":1,"name":"QA Shield","model":60,"object_type":42,"item_type":11}]
    gateway.inventory.sync(rows,{"gold":10},{},"standard",0,100,0);gateway.inventory.observe("inventory")
    adapter.entities={"npc:7":{"id":"npc:7","kind":"npc","name":"Emblemer","model_id":1984,"health":1,"position_m":[1,0,0]}}
    var command:Dictionary={"action":"inventory_give","slot":40,"item_token":gateway.inventory.items[40].token,"inventory_revision":gateway.inventory.state_revision,"entity_id":"npc:7","target_name":"Emblemer","target_model":1984}
    server.playing=false;gateway.command(command);check(server.client.calls.is_empty(),"logged-out gateway cannot hand over items");server.playing=true
    gateway.leaving=true;gateway.command(command);check(server.client.calls.is_empty(),"saving session cannot hand over items");gateway.leaving=false
    gateway.player_state.ready=false;gateway.command(command);check(server.client.calls.is_empty(),"loading player cannot hand over items");gateway.player_state.ready=true
    gateway.player_state.vitals.health_pct=0;gateway.command(command);check(server.client.calls.is_empty(),"dead player cannot hand over items");gateway.player_state.vitals.health_pct=100
    gateway.exchange.locked=true;gateway.command(command);check(server.client.calls.is_empty() and gateway.inventory.feedback.contains("Realm Exchange"),"marketplace inventory lock is retained");gateway.exchange.locked=false
    gateway.command(command);check(server.client.calls==[[40,1007,1]],"actual gateway routes handover through original MoveItem API")
    gateway.command(command);check(server.client.calls.size()==1,"actual gateway blocks duplicate pending transaction")
    gateway.inventory.observe("inventory");gateway.inventory.sync(rows,{"gold":10},{},"standard",0,100,1)
    adapter.entities.clear();gateway.command(command);check(server.client.calls.size()==1,"despawn between display and drop sends no item packet")
    check(gateway.inventory.items.has(40) and gateway.inventory.money.gold==10,"all gateway refusals preserve authoritative inventory and gold")
    server.client.free();gateway.free();server.free();adapter.free()
    print(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures}));quit(0 if failures.is_empty() else 1)
