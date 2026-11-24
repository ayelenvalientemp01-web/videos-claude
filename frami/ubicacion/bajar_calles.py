"""Baja de Nominatim (OpenStreetMap) las calles alrededor de la oficina de FRAMI.

Uso: python3 bajar_calles.py <dir_datos>
Genera n_grilla.json (búsqueda inversa en una grilla de ~85 m) y n_avenidas.json.
Una consulta por segundo como máximo (política de uso de Nominatim). © OpenStreetMap.
"""
import json
import math
import sys
import time
import urllib.parse
import urllib.request

UA = {"User-Agent": "video-map-render/1.0"}
LAT0, LON0 = -27.4124007, -55.9908180      # Las Rosas 10976, Posadas
VIEWBOX = "-56.006,-27.400,-55.976,-27.424"


def nominatim(ruta, **p):
    p.update(format="json", polygon_geojson=1)
    u = f"https://nominatim.openstreetmap.org/{ruta}?" + urllib.parse.urlencode(p)
    for intento in range(3):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60))
            time.sleep(1.05)
            return r
        except Exception as e:
            print("reintento", e, flush=True)
            time.sleep(5)
    return []


def main():
    d = sys.argv[1]
    avenidas = {}
    for n in ("Avenida El Puma", "Avenida Los Horneros", "Avenida Ñandú", "Las Rosas"):
        for x in nominatim("search", q=f"{n}, Posadas", viewbox=VIEWBOX, bounded=1, limit=50,
                           dedupe=0, polygon_threshold=0.00001):
            if x.get("class") == "highway":
                avenidas[x["osm_id"]] = x
    json.dump(list(avenidas.values()), open(f"{d}/n_avenidas.json", "w"))
    print("avenidas", len(avenidas), flush=True)
    paso = 85
    dlat = paso / 111320
    dlon = paso / (111320 * math.cos(math.radians(LAT0)))
    puntos = sorted(((i, j) for j in range(-7, 8) for i in range(-5, 6)),
                    key=lambda ij: (ij[0] * 1.3) ** 2 + ij[1] ** 2)
    vistos = {}
    for n, (i, j) in enumerate(puntos):
        r = nominatim("reverse", lat=LAT0 + j * dlat, lon=LON0 + i * dlon, zoom=17)
        if isinstance(r, dict) and r.get("class") == "highway":
            vistos[r["osm_id"]] = r
        if n % 15 == 14:
            json.dump(list(vistos.values()), open(f"{d}/n_grilla.json", "w"))
            print(n + 1, "de", len(puntos), "calles", len(vistos), flush=True)
    json.dump(list(vistos.values()), open(f"{d}/n_grilla.json", "w"))
    print("listo", len(vistos))


if __name__ == "__main__":
    main()
