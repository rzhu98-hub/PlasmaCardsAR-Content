#!/usr/bin/env python3
"""Normalise the web .glb materials so the deck reads as one family of machines.

Three different situations existed, which is why the viewer looked inconsistent:
  * ITER / HBT-EP  - metallic 0.55, rough 0.45          -> a bit plasticky
  * NSTX-U / FRC   - NO materials at all                -> glTF default (metal 1.0, rough 1.0): dull grey
  * DFD Rocket     - metallicFactor absent (= 1.0), rough 0.90, baseColorFactor 0.4 over a painted
                     texture. baseColorFactor MULTIPLIES the texture, so 0.4 was crushing the artwork
                     to 40% brightness. That is the "rocket is too dark" bug.

Rewrites only the JSON chunk; the binary mesh chunk is untouched. Files are in git, so reversible.

    python tools/fix-web-materials.py
"""
import json, struct, glob, os

# Bright brushed aluminium: high metallic so it genuinely reflects the studio HDR, roughness in the
# brushed (not mirror) range, near-white base with a whisper of cool.
ALU = {
    "pbrMetallicRoughness": {
        "baseColorFactor": [0.902, 0.918, 0.945, 1.0],
        "metallicFactor": 0.90,
        "roughnessFactor": 0.32,
    },
    "doubleSided": True,
    "name": "BrushedAluminium",
}

# The rocket keeps its painted illustration (stars, plasma plume): barely metallic so the texture
# reads, and baseColorFactor lifted to 1.0 so it stops being multiplied down.
ROCKET = {"metallicFactor": 0.10, "roughnessFactor": 0.55, "baseColorFactor": [1.0, 1.0, 1.0, 1.0]}

TEXTURED_KEEP = "DFD-Rocket"


def load(path):
    d = open(path, "rb").read()
    jl = struct.unpack("<I", d[12:16])[0]
    return d, jl, json.loads(d[20:20 + jl].decode("utf-8"))


def save(path, d, jl, g):
    js = json.dumps(g, separators=(",", ":")).encode("utf-8")
    js += b" " * ((4 - len(js) % 4) % 4)
    body = struct.pack("<I4s", len(js), b"JSON") + js + d[20 + jl:]
    out = struct.pack("<4sII", b"glTF", struct.unpack("<I", d[4:8])[0], 12 + len(body)) + body
    v = struct.unpack("<I", out[12:16])[0]
    json.loads(out[20:20 + v].decode("utf-8"))          # re-parse before committing to disk
    open(path, "wb").write(out)


def main():
    for path in sorted(glob.glob("models/*.glb")):
        name = os.path.basename(path).replace(".glb", "")
        d, jl, g = load(path)
        mats = g.get("materials", [])

        if name == TEXTURED_KEEP:
            for m in mats:
                pbr = m.setdefault("pbrMetallicRoughness", {})
                pbr.update(ROCKET)                       # keeps baseColorTexture untouched
                m["doubleSided"] = True
            note = "texture kept, darkness fixed"
        elif mats:
            for m in mats:
                m["pbrMetallicRoughness"] = dict(ALU["pbrMetallicRoughness"])
                m["doubleSided"] = True
            note = f"{len(mats)} material(s) -> aluminium"
        else:
            # No materials at all: add one and point every primitive at it.
            g["materials"] = [json.loads(json.dumps(ALU))]
            prims = 0
            for mesh in g.get("meshes", []):
                for p in mesh.get("primitives", []):
                    p["material"] = 0
                    prims += 1
            note = f"material ADDED, {prims} primitive(s) assigned"

        save(path, d, jl, g)
        print(f"{name:18} {note}")


if __name__ == "__main__":
    main()
