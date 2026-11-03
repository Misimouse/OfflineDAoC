extends SceneTree
class GatewayProbe extends "res://live_gateway.gd":
    var entries:Array=[]
    func enter_character(chosen:Dictionary)->void:entries.append(chosen.name)
class FakeServer extends Node:
    var pending:=true
    func character_list_pending()->bool:return pending
    func characters_in(_realm:String)->Array:return [{"name":"Existinghero"}]
class FakeLobby extends RefCounted:
    var enabled:=false
    var refreshes:=0
    func refresh(_server:Node)->void:refreshes+=1
func _initialize()->void:run.call_deferred()
func run()->void:
    var gateway:=GatewayProbe.new();var server:=FakeServer.new();var lobby:=FakeLobby.new();gateway.server=server;gateway.character_lobby=lobby
    gateway.characters_ready("hib")
    assert(gateway.entries.is_empty(),"direct entry must wait while older realm requests are outstanding")
    server.pending=false;gateway.characters_ready("hib")
    assert(gateway.entries==["Existinghero"],"direct entry follows the final authoritative roster")
    gateway.entries.clear();gateway.characters_ready("alb")
    assert(gateway.entries.is_empty(),"other realm replies never start Hibernia entry")
    lobby.enabled=true;gateway.characters_ready("hib")
    assert(gateway.entries.is_empty(),"menu mode keeps manual character selection")
    gateway.free();server.free();print(JSON.stringify({"passed":true,"checks":4}));quit()
