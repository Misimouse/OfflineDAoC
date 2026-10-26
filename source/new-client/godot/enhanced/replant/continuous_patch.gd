extends Node3D
var mask:Image
var map_size:=1638.4
var life
func sample_mask(p:Vector2) -> Color:
	if p.x<0 or p.y<0 or p.x>=map_size or p.y>=map_size:return Color(0,0,0,1)
	return mask.get_pixel(clampi(int(p.x/map_size*mask.get_width()),0,mask.get_width()-1),clampi(int(p.y/map_size*mask.get_height()),0,mask.get_height()-1))
