#!/bin/bash
# 015 setup + render, VM-replacement-proof:
# - own apt lists dir (no fight with the boot replay's apt lock)
# - mesa Vulkan/EGL .debs extracted into ~/workspace/mesa/ (persistent)
# - renders 4 views with the extracted lavapipe driver
# - all output logged to scenes/tmp_views/setup-render015.log
LOG=~/workspace/blender-portfolio/scenes/tmp_views/setup-render015.log
mkdir -p ~/workspace/blender-portfolio/scenes/tmp_views ~/workspace/mesa-debs ~/workspace/mesa ~/workspace/apt-lists/partial
exec > >(tee -a "$LOG") 2>&1
set -x

BLENDER=~/workspace/blender/blender-5.3.0-linux-x64/blender
MESA=~/workspace/mesa
APT="apt-get -o Dir::State::Lists=$HOME/workspace/apt-lists"

if [ ! -f "$MESA/usr/lib/x86_64-linux-gnu/libvulkan_lvp.so" ]; then
  if ! ls $HOME/workspace/apt-lists/*_Packages >/dev/null 2>&1; then
    sudo -n $APT update
  else
    echo "APT_LISTS_PRESENT: skipping update"
  fi
  cd ~/workspace/mesa-debs
  $APT download mesa-vulkan-drivers libegl-mesa0 libegl1 libgl1-mesa-dri
  for deb in mesa-vulkan-drivers_*.deb libegl-mesa0_*.deb libegl1_*.deb libgl1-mesa-dri_*.deb; do
    [ -f "$deb" ] && dpkg-deb -x "$deb" "$MESA"
  done
  ICD="$MESA/usr/share/vulkan/icd.d/lvp_icd.json"
  python3 - "$ICD" "$MESA/usr/lib/x86_64-linux-gnu/libvulkan_lvp.so" <<'PYEOF'
import json, sys
p, lib = sys.argv[1], sys.argv[2]
d = json.load(open(p))
d["ICD"]["library_path"] = lib
json.dump(d, open(p, "w"), indent=2)
print("ICD_PATCHED:", p)
PYEOF
fi

ls -la "$MESA/usr/lib/x86_64-linux-gnu/libEGL.so.1" "$MESA/usr/lib/x86_64-linux-gnu/libvulkan_lvp.so"
export LD_LIBRARY_PATH="$MESA/usr/lib/x86_64-linux-gnu:$MESA/usr/lib/x86_64-linux-gnu/dri${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export VK_ICD_FILENAMES="$MESA/usr/share/vulkan/icd.d/lvp_icd.json"
export VK_DRIVER_FILES="$VK_ICD_FILENAMES"

cd ~/workspace/blender-portfolio
"$BLENDER" --background --python scenes/015-render-views.py 2>&1 | grep -E "GROUP|VIEW_|ANNOTATIONS|BLEND_SAVED|GROUP_POLY|Error|Traceback|Saved"
echo "RENDER_EXIT=$?"
ls -la scenes/tmp_views/
