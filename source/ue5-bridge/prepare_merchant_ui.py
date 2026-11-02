"""Add the original merchant artwork to the existing private classic UI library."""
import hashlib,shutil
from bridge_paths import ROOT, INSTALL

source=INSTALL/'new-client/godot/content/ui/classic/x4plus/merchant.png'
if not source.exists():source=INSTALL/'new-client/godot/content/ui/classic/original/merchant.png'
assert source.is_file(),'Original merchant artwork is missing'
target=ROOT/'UnrealPlugin/DAoCVisualBridge/Content/ClassicUI/merchant.png'
target.parent.mkdir(parents=True,exist_ok=True)
if target.exists() and target.read_bytes()!=source.read_bytes():
    backup=ROOT/'Backups/MerchantArtwork/merchant.png';backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(target,backup)
shutil.copy2(source,target)
assert hashlib.sha256(target.read_bytes()).digest()==hashlib.sha256(source.read_bytes()).digest()
print('Original merchant artwork prepared; uses the existing item icon sheets and icon_sheets.json.')
