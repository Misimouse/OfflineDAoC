extends SceneTree
class Client extends Node:
    var calls:Array=[]
    func LosReply(source:int,target:int,visible:bool)->void:calls.append([source,target,visible])
var n:=0
var failures:Array=[]
func check(ok:bool,label:String)->void:n+=1;if not ok:failures.append(label)
func _initialize()->void:
    var sight=load("res://line_of_sight.gd").new();var client:=Client.new();var p:={1:{"id":"player:local","pos":Vector3.ZERO},2:{"id":"npc:2","pos":Vector3(3,0,0)}}
    sight.request({"source":1,"target":2},client,p,0);check(client.calls.is_empty() and sight.pending.size()==1,"close targets also require native geometry")
    var close:Dictionary=sight.snapshot()[0];check(sight.reply({"query_id":close.id,"query_token":close.token,"visible":true},client,50) and client.calls==[[1,2,true]],"positive geometry reply preserves close target identity")
    sight.request({"source":1,"target":99},client,p,0);check(client.calls.back()==[1,99,false],"missing endpoints do not fabricate visibility")
    p[2].pos=Vector3(10,0,0);sight.request({"source":1,"target":2},client,p,100);check(sight.pending.size()==1 and client.calls.size()==2,"further visibility waits for native geometry")
    var q:Dictionary=sight.snapshot()[0];check(q.source_id=="player:local" and q.target_id=="npc:2","native question carries original endpoints")
    check(not sight.reply({"query_id":q.id,"query_token":"wrong","visible":true},client,150) and sight.pending.size()==1,"forged token cannot answer server request")
    check(not sight.reply({"query_id":q.id,"query_token":q.token,"visible":1},client,150),"visibility must be a real boolean")
    check(sight.reply({"query_id":q.id,"query_token":q.token,"visible":false},client,200) and client.calls.back()==[1,2,false],"blocked native ray returns original negative LOS reply")
    check(not sight.reply({"query_id":q.id,"query_token":q.token,"visible":true},client,201),"duplicate answer cannot change server result")
    sight.request({"source":1,"target":2},client,p,300);q=sight.snapshot()[0];check(not sight.reply({"query_id":q.id,"query_token":q.token,"visible":true},client,2000) and client.calls.back()==[1,2,false],"late geometry response cannot grant visibility")
    sight.request({"source":1,"target":2},client,p,3000);sight.maintain(client,4600);check(sight.pending.is_empty() and sight.timeouts==2,"missing native response times out cleanly")
    sight.request({"source":1,"target":2},client,p,5000);sight.reset();check(sight.pending.is_empty(),"session lifecycle drops old questions")
    var report:={"passed":failures.is_empty(),"checks":n,"failures":failures,"real_server":false};var f:=FileAccess.open(get_script().resource_path.get_base_dir().path_join("../Reports/spell_casting/sight_tests.json"),FileAccess.WRITE);f.store_string(JSON.stringify(report));f.close();print(JSON.stringify(report));client.free();quit(0 if failures.is_empty() else 1)
