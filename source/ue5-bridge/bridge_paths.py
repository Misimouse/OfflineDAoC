"""Portable paths for source tools; runtime state remains local and ignored."""
from pathlib import Path
import os
ROOT=Path(__file__).resolve().parent
INSTALL=Path(os.environ.get('DAOC_INSTALL',str(ROOT/'local/playable')))
ENGINE=Path(os.environ.get('DAOC_UE_ENGINE',r'C:/Program Files/Epic Games/UE_5.8/Engine'))
ART_PROJECT=Path(os.environ.get('DAOC_ART_PROJECT',str(ROOT.parent/'DAoC-Enhanced-Unreal')))
