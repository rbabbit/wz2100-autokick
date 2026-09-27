#!/usr/bin/env python3
from pathlib import Path
import sys, re

root = Path(sys.argv[1]).resolve()

# 1) Engine slots: 12 human positions + 1 scavenger simulation slot.
p = root / "lib/framework/frame.h"
s = p.read_text(encoding="utf-8")
old = "#define MAX_PLAYERS         11"
new = "#define MAX_PLAYERS         13"
if old in s:
    s = s.replace(old, new, 1)
elif new not in s:
    raise SystemExit("MAX_PLAYERS base definition not found")
p.write_text(s, encoding="utf-8")

# 2) Give the fork its own netcode so stock 4.7.0 cannot join.
p = root / "lib/netplay/autorevision_netplay.cmake"
s = p.read_text(encoding="utf-8")
marker = "##################################\n# Debug output"
inject = """##################################
# 12P experimental network fork: deliberately incompatible with stock 4.7.0.
set(NETCODE_VERSION_MAJOR "0x12A0")
set(NETCODE_VERSION_MINOR 1)

##################################
# Debug output"""
if marker in s and 'set(NETCODE_VERSION_MAJOR "0x12A0")' not in s:
    s = s.replace(marker, inject, 1)
elif 'set(NETCODE_VERSION_MAJOR "0x12A0")' not in s:
    raise SystemExit("netcode injection marker not found")
p.write_text(s, encoding="utf-8")

# 3) Convert WaterLoop generator to 12 positions.
p = root / "data/mp/multiplay/maps/10c-WaterLoop/game.js"
s = p.read_text(encoding="utf-8")
if "var players = 10;" in s:
    s = s.replace("var players = 10;", "var players = 12;", 1)
elif "var players = 12;" not in s:
    raise SystemExit("WaterLoop player count not found")

old_trig = """\tvar s = 0.5877852522924731;  // Math.sin(2*Math.PI / players)
\tvar c = 0.8090169943749475;  // Math.cos(2*Math.PI / players)
\tvar xy = [-0.9510565162951535, 0.309016994374947];  // [Math.cos(2*Math.PI / players / 2), Math.sin(2*Math.PI / players / 2)]"""
new_trig = """\tvar s = 0.5;  // Math.sin(2*Math.PI / 12)
\tvar c = 0.8660254037844386;  // Math.cos(2*Math.PI / 12)
\tvar xy = [-0.9659258262890683, 0.25881904510252074];  // 12P half-step start angle"""
if old_trig in s:
    s = s.replace(old_trig, new_trig, 1)
elif new_trig not in s:
    raise SystemExit("WaterLoop trig constants not found")
p.write_text(s, encoding="utf-8")

# 4) Advertise WaterLoop as a 12-player map.
p = root / "data/mp/addon.lev"
s = p.read_text(encoding="utf-8")
pattern = re.compile(r"(level\s+WaterLoop\s*\nplayers\s+)10(\s*\ntype\s+14\s*\ndataset\s+MULTI_CAM_1\s*\ngame\s+\"multiplay/maps/10c-WaterLoop\.gam\")", re.M)
if pattern.search(s):
    s = pattern.sub(r"\g<1>12\g<2>", s, count=1)
elif not re.search(r"level\s+WaterLoop\s*\nplayers\s+12\b", s, re.M):
    raise SystemExit("WaterLoop addon.lev entry not found")
p.write_text(s, encoding="utf-8")

print("12P patch complete")
print((root / "lib/framework/frame.h").read_text(encoding="utf-8").split("#define MAX_PLAYERS",1)[1][:120])
