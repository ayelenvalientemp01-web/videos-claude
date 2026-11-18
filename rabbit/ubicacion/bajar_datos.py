"""Descarga los datos del mapa de Posadas desde Nominatim (OpenStreetMap).

Uso: python3 bajar_datos.py <dir_datos>

Genera en <dir_datos>:
  n_ciudad.json   límite del Municipio de Posadas
  n_parana.json   eje del río Paraná (relación 421678)
  n_calles.json   tramos de las avenidas principales (búsqueda por nombre)
  n_grilla.json   calles alrededor del local (búsqueda inversa en una grilla de ~150 m)

Respeta la política de uso de Nominatim: una consulta por segundo como máximo.
Los datos son © colaboradores de OpenStreetMap (licencia ODbL).
"""
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request

UA = {"User-Agent": "video-map-render/1.0"}
VIEWBOX = "-56.03,-27.32,-55.84,-27.48"
LAT0, LON0 = -27.3794728, -55.9069448   # Av. Lavalle 3288

AVENIDAS = [
    "Avenida Lavalle", "Avenida Uruguay", "Avenida Quaranta", "Avenida López Torres",
    "Avenida Corrientes", "Avenida Mitre", "Avenida Roque Sáenz Peña", "Avenida Cabred",
    "Avenida Tambor de Tacuarí", "Avenida Francisco de Haro", "Avenida Santa Catalina",
    "Avenida Jauretche", "Avenida Urquiza", "Avenida Bustamante", "Avenida Andrés Guacurarí",
    "Avenida Chacabuco", "Avenida San Martín", "Avenida Roca", "Avenida Rademacher",
    "Avenida Centenario", "Avenida Blas Parera", "Avenida Aguado", "Avenida Zapiola",
    "Avenida Polonia", "Avenida Trincheras de San José", "Avenida Fangio", "Avenida Costanera",
    "Avenida Monseñor Kemerer", "Avenida Comandante Andresito", "Avenida Las Heras",
    "Avenida Cocomarola", "Avenida Leandro N. Alem", "Avenida Tomás Guido", "Avenida Maipú",
    "Moraez Dutrá", "Almirante Brown", "Tamareu", "Ruta Nacional 12", "Ruta Nacional 105",
]


def nominatim(ruta, **p):
    p.update(format="json", polygon_geojson=1)
    u = f"https://nominatim.openstreetmap.org/{ruta}?" + urllib.parse.urlencode(p)
    for intento in range(3):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA),
                                                 timeout=60))
            time.sleep(1.05)
            return r
        except Exception as e:  # el servicio a veces responde 503: reintentar
            print("reintento", intento + 1, e, flush=True)
            time.sleep(5)
    return []


def main():
    d = sys.argv[1]
    os.makedirs(d, exist_ok=True)
    json.dump(nominatim("search", q="Posadas, Misiones, Argentina", limit=1,
                        polygon_threshold=0.0002), open(f"{d}/n_ciudad.json", "w"))
    json.dump(nominatim("lookup", osm_ids="R421678", polygon_threshold=0.0005),
              open(f"{d}/n_parana.json", "w"))

    calles = {}
    for n in AVENIDAS:
        excl = []
        for _ in range(4):
            p = dict(q=f"{n}, Posadas", viewbox=VIEWBOX, bounded=1, limit=50, dedupe=0,
                     polygon_threshold=0.00002)
            if excl:
                p["exclude_place_ids"] = ",".join(map(str, excl))
            r = [x for x in nominatim("search", **p) if x.get("class") == "highway"]
            for x in r:
                excl.append(x["place_id"])
                calles[x["place_id"]] = x
            if len(r) < 50:
                break
        print(n, len(excl), flush=True)
    json.dump(list(calles.values()), open(f"{d}/n_calles.json", "w"))

    paso = 150
    dlat = paso / 111320
    dlon = paso / (111320 * math.cos(math.radians(LAT0)))
    puntos = sorted(((i, j) for j in range(-8, 9) for i in range(-6, 7)),
                    key=lambda ij: (abs(ij[0]) * 1.4) ** 2 + ij[1] ** 2)
    vistos = {}
    for i, j in puntos:
        r = nominatim("reverse", lat=LAT0 + j * dlat, lon=LON0 + i * dlon, zoom=17)
        if isinstance(r, dict) and r.get("class") == "highway":
            vistos[r["osm_id"]] = r
    json.dump(list(vistos.values()), open(f"{d}/n_grilla.json", "w"))
    print("listo:", len(calles), "tramos de avenidas,", len(vistos), "calles cercanas")


if __name__ == "__main__":
    main()
