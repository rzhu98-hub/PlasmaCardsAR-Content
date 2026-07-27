#!/usr/bin/env python3
"""
Rebuild the website's 3D models (models/*.glb) from the app's full-resolution
source meshes (../PlasmaCardsAR/Assets/Models/<name>/*.obj).

Why this exists: ITER and HBT-EP once shipped DECIMATED, which shredded their thin
edge geometry (ports, plates). This regenerates them at full resolution with:
  - angle-based normals (35 deg): crisp hard edges, smooth curves
  - the original metal PBR material (metallic 0.55 / rough 0.45, cool blue-white)
  - double-sided (thin single-sided plates never vanish)

Requires: pip install trimesh scipy numpy
Run:      python tools/rebuild-web-models.py
After:    bump the ?v=N cache tag in showcase.html + viewer.html, then commit + push.

Portable: assumes the app repo (PlasmaCardsAR) and this content repo
(PlasmaCardsAR-Content) sit side by side, as CLAUDE.md requires.
"""
import json, struct, os
import numpy as np, trimesh
from trimesh.visual.material import PBRMaterial

HERE = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.dirname(HERE)                       # PlasmaCardsAR-Content/
APP = os.path.join(os.path.dirname(CONTENT), "PlasmaCardsAR")   # sibling app repo

# (source .obj under APP/Assets/Models, output .glb under CONTENT/models)
JOBS = [
    ("ITER/iter.obj",   "ITER-Card.glb"),
    ("HBTEP/hbt-ep.obj", "HBTEP-Card.glb"),
    # add new cards here, e.g. ("W7X/w7x.obj", "W7X-Card.glb"),
]
ANGLE_DEG = 30   # smoothing threshold; lower = crisper/more faceted, higher = smoother
MAT = PBRMaterial(name="reactor", baseColorFactor=[209, 217, 230, 255],
                  metallicFactor=0.55, roughnessFactor=0.45, doubleSided=True)


def angle_smooth(obj_path, angle_deg=ANGLE_DEG):
    m = trimesh.load(obj_path, force='mesh')
    m.merge_vertices()                                # 3x-unshared corners -> welded positions
    V, F = np.asarray(m.vertices), np.asarray(m.faces)
    fn, area = np.asarray(m.face_normals), np.asarray(m.area_faces)
    vn = np.zeros((len(V), 3))
    for i in range(3):
        np.add.at(vn, F[:, i], fn * area[:, None])
    vn /= np.clip(np.linalg.norm(vn, axis=1), 1e-9, None)[:, None]
    cos_t = np.cos(np.radians(angle_deg))
    P = V[F].reshape(-1, 3)
    N = np.empty((len(F), 3, 3))
    for i in range(3):
        sm = vn[F[:, i]]
        use = np.einsum('ij,ij->i', sm, fn) > cos_t   # keep flat across sharp edges
        N[:, i, :] = np.where(use[:, None], sm, fn)
    N = N.reshape(-1, 3)
    N /= np.clip(np.linalg.norm(N, axis=1), 1e-9, None)[:, None]
    comb = np.round(np.hstack([P, N]).astype(np.float32), 4)
    _, idx, inv = np.unique(comb, axis=0, return_index=True, return_inverse=True)
    out = trimesh.Trimesh(vertices=P[idx], faces=inv.reshape(len(F), 3).astype(np.uint32), process=False)
    out.vertex_normals = N[idx]
    out.visual = trimesh.visual.TextureVisuals(material=MAT)
    return out


def write_glb(mesh, path):
    glb = trimesh.exchange.gltf.export_glb(mesh, include_normals=True)
    n = struct.unpack('<I', glb[12:16])[0]; j = json.loads(glb[20:20 + n])
    for mm in j.get('materials', []):
        mm['doubleSided'] = True                      # belt-and-suspenders
    nj = json.dumps(j, separators=(',', ':')).encode(); nj += b' ' * ((4 - len(nj) % 4) % 4)
    binc = glb[20 + ((n + 3) & ~3):]
    o = struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(nj) + len(binc)) + \
        struct.pack('<II', len(nj), 0x4E4F534A) + nj + binc
    open(path, 'wb').write(o)
    return len(o)


if __name__ == "__main__":
    for obj_rel, glb_name in JOBS:
        src = os.path.join(APP, "Assets", "Models", obj_rel)
        dst = os.path.join(CONTENT, "models", glb_name)
        sz = write_glb(angle_smooth(src), dst)
        print(f"{glb_name:20s} {sz / 1048576:5.2f} MB")
    print("Done. Now bump ?v=N in showcase.html + viewer.html, then commit + push.")
