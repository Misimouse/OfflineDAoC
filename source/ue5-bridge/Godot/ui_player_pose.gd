extends Node3D
var velocity:=Vector3.ZERO
var heading:=0
func facing()->float:return -float(heading)*TAU/4096.0-PI
