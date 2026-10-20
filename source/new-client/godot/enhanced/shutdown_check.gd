extends SceneTree
## A worker needing a main-loop callback must finish before a manager's blocking _exit_tree runs.
var semaphore := Semaphore.new()
var results := {}

func _initialize() -> void:
	run.call_deferred()

func worker() -> void:
	semaphore.wait()

func run() -> void:
	for kind in ["npc_preload", "region_stream"]:
		var path := "res://game/npcs/npc_manager.gd" if kind == "npc_preload" else "res://game/world/region_world.gd"
		var manager = load(path).new()
		root.add_child(manager)
		var field := "_prep_task" if kind == "npc_preload" else "_task"
		manager.set(field, WorkerThreadPool.add_task(worker))
		# This callback can run only if prepare_shutdown yields instead of blocking on the worker.
		create_timer(0.1).timeout.connect(func():semaphore.post())
		await manager.prepare_shutdown()
		results[kind] = int(manager.get(field)) == -1
		manager.queue_free()
		await process_frame
	print("COOPERATIVE_SHUTDOWN_CHECK ", JSON.stringify(results))
	quit(0 if results.values().all(func(value):return value == true) else 3)
