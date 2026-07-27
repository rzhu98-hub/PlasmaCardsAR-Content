#!/usr/bin/env python3
"""Generate the studio environment the web 3D viewer reflects.

Metal only looks like metal when it has something to reflect. The app gets that free from
AREnvironmentProbeManager (the real room); on the web we have to supply it. This writes a small
equirectangular Radiance .hdr: a bright soft ceiling, three overhead softboxes that draw the long
specular streaks that read as brushed aluminium, a horizon band, and a dark floor for contrast.

Generated rather than downloaded: no licence questions, ~200 KB, and every highlight is tunable here.

    python tools/make-studio-hdr.py        ->  env/studio-silver.hdr
"""
import math, os, struct

W, H = 1024, 512
OUT = "env/studio-silver.hdr"

# --- softboxes: (centre azimuth 0..1, centre elevation 0..1 top->bottom, half-width, half-height, intensity)
SOFTBOXES = [
    (0.18, 0.16, 0.11, 0.075, 14.0),   # key light, upper left
    (0.62, 0.13, 0.14, 0.060, 10.0),   # fill, upper right — wider, softer
    (0.88, 0.30, 0.055, 0.10, 6.0),    # rim, side — narrow vertical streak
]


def smoothstep(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0))) if e1 != e0 else 0.0
    return t * t * (3 - 2 * t)


def sample(u, v):
    """u = azimuth 0..1, v = 0 at zenith, 1 at nadir. Returns linear RGB."""
    # Vertical gradient: cool bright ceiling -> neutral horizon -> dark floor.
    if v < 0.5:
        t = v / 0.5
        base = 1.35 - 0.85 * t                      # 1.35 at top -> 0.5 at horizon
        r, g, b = base * 0.97, base * 0.99, base * 1.05   # faintly cool
    else:
        t = (v - 0.5) / 0.5
        base = 0.5 - 0.42 * smoothstep(0.0, 1.0, t)       # falls to a dark floor
        r, g, b = base * 1.02, base * 1.0, base * 0.98    # faintly warm underside

    # A soft horizon lift keeps the silhouette from going muddy.
    horizon = math.exp(-((v - 0.5) ** 2) / 0.0022) * 0.30
    r += horizon; g += horizon; b += horizon

    # Softboxes — these are what actually show up as reflections on the metal.
    for cu, cv, hw, hh, power in SOFTBOXES:
        du = abs(u - cu)
        du = min(du, 1.0 - du)                      # wrap around the sphere
        dv = abs(v - cv)
        fall = (1.0 - smoothstep(hw * 0.45, hw, du)) * (1.0 - smoothstep(hh * 0.45, hh, dv))
        if fall > 0.0:
            e = power * fall
            r += e * 1.00; g += e * 1.00; b += e * 1.02
    return r, g, b


def to_rgbe(r, g, b):
    m = max(r, g, b)
    if m < 1e-8:
        return (0, 0, 0, 0)
    mant, exp = math.frexp(m)
    scale = mant * 256.0 / m
    return (min(255, int(r * scale)), min(255, int(g * scale)),
            min(255, int(b * scale)), min(255, exp + 128))


def rle_component(vals):
    """Radiance adaptive RLE for one component of one scanline."""
    out, i, n = bytearray(), 0, len(vals)
    while i < n:
        run = 1
        while i + run < n and run < 127 and vals[i + run] == vals[i]:
            run += 1
        if run >= 4:
            out += bytes((128 + run, vals[i]))
            i += run
        else:
            j = i + 1
            while j < n and (j - i) < 128:
                if j + 3 < n and vals[j] == vals[j + 1] == vals[j + 2] == vals[j + 3]:
                    break
                j += 1
            out.append(j - i)
            out += bytes(vals[i:j])
            i = j
    return bytes(out)


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "wb") as f:
        f.write(b"#?RADIANCE\n")
        f.write(b"# Plasma Physics Trading Cards - generated studio environment\n")
        f.write(b"FORMAT=32-bit_rle_rgbe\n\n")
        f.write(f"-Y {H} +X {W}\n".encode())
        for y in range(H):
            v = (y + 0.5) / H
            chans = ([], [], [], [])
            for x in range(W):
                u = (x + 0.5) / W
                for c, val in enumerate(to_rgbe(*sample(u, v))):
                    chans[c].append(val)
            f.write(bytes((2, 2, (W >> 8) & 0xFF, W & 0xFF)))
            for c in range(4):
                f.write(rle_component(chans[c]))
    print(f"wrote {OUT}  ({os.path.getsize(OUT)/1024:.0f} KB, {W}x{H})")


if __name__ == "__main__":
    main()
