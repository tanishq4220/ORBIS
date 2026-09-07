"""Prepare credited static cartography/imagery, never orbital or confidence data."""
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
import json
import requests
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend/public/assets"
DATA = ROOT / "backend/data"
ASSETS.mkdir(parents=True, exist_ok=True)
DATA.mkdir(parents=True, exist_ok=True)

TEXTURES = {
    "earth-day.jpg": ("https://eoimages.gsfc.nasa.gov/images/imagerecords/57000/57730/land_ocean_ice_8192.png", 4096),
    "earth-night.jpg": ("https://raw.githubusercontent.com/vasturiano/three-globe/master/example/img/earth-night.jpg", 4096),
    "earth-clouds.jpg": ("https://threejs.org/examples/textures/planets/earth_clouds_1024.png", 1024),
    "hubble.jpg": ("https://cdn.esahubble.org/archives/images/screen/heic0908c.jpg", 1200),
}


def texture(item):
    name, (url, width) = item
    response = requests.get(url, timeout=90)
    response.raise_for_status()
    image = Image.open(BytesIO(response.content))
    if image.mode == "P" and "transparency" in image.info:
        image = image.convert("RGBA")
    if image.mode == "RGBA":
        # NASA cloud product's alpha carries cloud coverage.
        image = image.getchannel("A").convert("RGB")
    else:
        image = image.convert("RGB")
    image.thumbnail((width, width))
    image.save(ASSETS / name, quality=90, optimize=True)
    print("Prepared", name, image.size, flush=True)


def geography(level, filename):
    source = f"https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/{filename}.geojson"
    response = requests.get(source, timeout=90)
    response.raise_for_status()
    features = response.json()["features"]
    lines, labels = [], []
    for feature in features:
        p, g = feature["properties"], feature["geometry"]
        if not g:
            continue
        name = p.get("NAME") or p.get("name") or p.get("ADMIN")
        if level == "cities":
            x, y = g["coordinates"]
            labels.append({"name": name, "latitude": y, "longitude": x, "capital": bool(p.get("ADM0CAP", 0))})
            continue
        polygons = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for poly in polygons:
            for ring in poly:
                if len(ring) > 1:
                    lines.append([[round(x, 4), round(y, 4)] for x, y, *extra in ring])
        x = p.get("LABEL_X", p.get("longitude"))
        y = p.get("LABEL_Y", p.get("latitude"))
        if name and x is not None and y is not None:
            labels.append({"name": name, "latitude": float(y), "longitude": float(x), "capital": False})
    out = {"source": f"Natural Earth · public domain · {filename}", "lines": lines, "labels": labels}
    (DATA / f"geography-{level}.json").write_text(json.dumps(out, separators=(",", ":")))
    print("Prepared", level, len(lines), "rings", len(labels), "labels", flush=True)


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(texture, TEXTURES.items()))
        list(pool.map(lambda pair: geography(*pair), [
            ("countries", "ne_110m_admin_0_countries"),
            ("regions", "ne_50m_admin_1_states_provinces"),
            ("cities", "ne_110m_populated_places"),
        ]))