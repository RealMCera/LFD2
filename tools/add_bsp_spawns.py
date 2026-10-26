#!/usr/bin/env python3
"""Add first-person camera locations to an EXISTING locally converted BSP mesh.

Reads an extracted Source BSP entity lump (including Valve's LZMA compression),
selects only survivor/player spawn coordinates and orientations, and writes an
enriched mesh under gitignored research/local/. No game entity scripts,
names/asset contents, or proprietary game data go to GitHub.
"""
from __future__ import annotations
import argparse
import json
import math
import re
import sys
from pathlib import Path

try:
    from .bsp_to_browser_mesh import MAP, ROOT, BspError, read_directory, read_lump
except ImportError:
    from bsp_to_browser_mesh import MAP, ROOT, BspError, read_directory, read_lump

DEFAULT_MESH = ROOT / "research" / "local" / "c1m1_hotel.mesh.json"
DEFAULT_OUTPUT = ROOT / "research" / "local" / "c1m1_hotel_spawns.mesh.json"
SPAWN_TYPES = ("info_player_start", "info_survivor_position")
FALLBACK_TYPES = ("info_landmark",)
ENTITY_PATTERN = re.compile(rb"\{([^{}]{0,50000})\}")
PAIR_PATTERN = re.compile(rb'"([^"\\]*(?:\\.[^"\\]*)*)"\s+"([^"\\]*(?:\\.[^"\\]*)*)"')


def parse_spawns(entity_data: bytes, limit: int = 32) -> list[dict]:
    """Extract only selected named point locations; never return full entity KV data."""
    if len(entity_data) > 16_000_000:
        raise BspError("Entity text exceeded safety limit")
    results = []
    for match in ENTITY_PATTERN.finditer(entity_data):
        fields = {}
        for key, value in PAIR_PATTERN.findall(match.group(1)):
            k = key.decode("utf-8", errors="replace").lower()
            if k in ("classname", "origin", "angles", "angle", "targetname"):
                fields[k] = value.decode("utf-8", errors="replace")
        cls = fields.get("classname", "").lower()
        if cls not in SPAWN_TYPES + FALLBACK_TYPES or "origin" not in fields:
            continue
        try:
            xyz = [float(p) for p in fields["origin"].split()]
            if len(xyz) != 3 or not all(math.isfinite(x) and abs(x) < 1000000 for x in xyz):
                continue
            yaw_deg = 0.0
            pitch_deg = 0.0
            if "angles" in fields:
                angles = [float(p) for p in fields["angles"].split()]
                if len(angles) == 3 and all(math.isfinite(a) for a in angles):
                    pitch_deg, yaw_deg, _roll_deg = angles
            elif "angle" in fields:
                yaw_deg = float(fields["angle"])
            if not math.isfinite(yaw_deg):
                yaw_deg = 0.0
            # Source engine: positive pitch looks down, so invert for viewer.
            # Player/ survivor positions mark character origin, not eye origin.
            is_spawn = cls in SPAWN_TYPES
            results.append({
                "name": f"{cls} {len(results) + 1}",
                "kind": cls,
                "position": [round(xyz[0], 3), round(xyz[1], 3),
                             round(xyz[2] + (64 if is_spawn else 48), 3)],
                "yaw": round(math.radians(yaw_deg), 6),
                "pitch": round(max(-1.2, min(1.2, math.radians(-pitch_deg))), 6),
                "is_spawn": is_spawn,
            })
            if len(results) >= limit:
                break
        except ValueError:
            continue
    # Use real player starts first, then survivor positions, then landmarks.
    order = {name: index for index, name in enumerate(SPAWN_TYPES + FALLBACK_TYPES)}
    results.sort(key=lambda e: order.get(e["kind"], 99))
    return results


def extract_spawns(bsp: bytes) -> list[dict]:
    endian, directory, _layout = read_directory(bsp)
    entities = read_lump(bsp, directory[0], endian)
    return parse_spawns(entities)


def enrich_mesh(mesh: dict, spawn_points: list[dict]) -> dict:
    if mesh.get("format") != "source-brush-mesh-0.1":
        raise BspError("Expected mesh from bsp_to_browser_mesh.py")
    if not isinstance(mesh.get("vertices"), list) or not isinstance(mesh.get("indices"), list):
        raise BspError("Mesh file lacks vertex/index arrays")
    out = dict(mesh)
    out["camera_spawns"] = spawn_points
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bsp", type=Path, default=MAP)
    parser.add_argument("--mesh", type=Path, default=DEFAULT_MESH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    if not output.is_relative_to(ROOT / "research" / "local"):
        parser.error("Output must stay in gitignored research/local")
    if output.exists():
        parser.error(f"Refusing to overwrite existing private output: {output}")
    try:
        mesh_path = args.mesh.expanduser().resolve()
        bsp_path = args.bsp.expanduser().resolve()
        with mesh_path.open(encoding="utf-8") as handle:
            mesh = json.load(handle)
        spawns = extract_spawns(bsp_path.read_bytes())
        enriched = enrich_mesh(mesh, spawns)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as handle:
            json.dump(enriched, handle, separators=(",", ":"))
        counts = {name: sum(p["kind"] == name for p in spawns)
                  for name in SPAWN_TYPES + FALLBACK_TYPES}
        print(f"Local map: {bsp_path.name}")
        print(f"Camera location candidates: {len(spawns)} ({counts})")
        if not any(p["is_spawn"] for p in spawns):
            print("Note: no player/survivor spawn found; only landmarks or overview available.")
        print(f"Private enriched map: {output} ({output.stat().st_size:,} bytes)")
        print("In Chrome reload docs/map-viewer.html and choose this NEW .mesh.json file.")
        print("No game assets, scripts, or code were uploaded.")
        return 0
    except (OSError, UnicodeError, ValueError, BspError, json.JSONDecodeError) as exc:
        print(f"Could not add spawn locations: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
