"""Reel de ubicación de Rabbit Food & Drinks (Posadas, Misiones).

Arranca con el mapa de Posadas, hace zoom hasta Av. Lavalle, cae el marcador con el
emblema del conejo y una tarjeta con la dirección; después las fotos del frente y un cierre
con el mapa y la dirección.

El mapa se dibuja en vectores con datos de OpenStreetMap (© colaboradores de OpenStreetMap)
descargados con Nominatim (ver bajar_datos.py): límite de Posadas, río Paraná, avenidas y
calles cercanas al local.

Uso: python3 video_ubicacion.py <dir_datos> <dir_fuentes> <dir_audio> <emblema.png>
                                <foto1> <foto2> <foto3> <salida.mp4>
<dir_audio> debe tener musica.wav, whoosh.wav, pop.wav y click.wav (musica_sfx.py de FRAMI).
"""
import json
import math
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union

W, H, FPS = 1080, 1920, 30
SS = 2  # supermuestreo del mapa

# Paleta (la del cartel: fondo oscuro, rojo, crema, verde)
FONDO = (17, 17, 19)
CIUDAD = (30, 30, 34)
AGUA = (20, 36, 58)
CALLE = (66, 66, 74)
AVENIDA = (104, 104, 116)
ROJO = (255, 18, 18)
VERDE = (0, 200, 70)
CREMA = (242, 232, 212)
BLANCO = (255, 255, 255)
GRIS = (170, 170, 180)

# Ubicación del local (Av. Lavalle 3288, lado oeste de la avenida, entre Moraez Dutrá y
# Almirante Brown). Se ajusta en main() con las calles reales.
LAT, LON = -27.3794728, -55.9069448
DIRECCION = "Av. Lavalle 3288"
ENTRE = "entre Moráez Dutrá y Almirante Brown"

# Línea de tiempo (s)
T_ZOOM0, T_ZOOM1 = 1.3, 5.4
T_PIN = 5.4
T_WIPE = 7.4
FOTO_DUR = 2.8
T_FOTOS = [T_WIPE, T_WIPE + FOTO_DUR, T_WIPE + 2 * FOTO_DUR]
T_CIERRE = T_WIPE + 3 * FOTO_DUR
DUR = T_CIERRE + 4.2

ANCHO_INI = 15000.0   # metros visibles a lo ancho al inicio (toda la ciudad)
ANCHO_FIN = 520.0     # metros visibles a lo ancho al final del zoom
CENTRO_INI = (-55.915, -27.385)   # centro de Posadas (lon, lat)


# ----------------------------------------------------------------- utilidades
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = clamp(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_back(x, s=1.7):
    x = clamp(x)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def mezcla(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


R = 6378137.0


def merc(lon, lat):
    return R * math.radians(lon), R * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


class Fuentes:
    def __init__(self, d):
        self.d, self.cache = d, {}

    def __call__(self, nombre, tam):
        k = (nombre, tam)
        if k not in self.cache:
            archivo = "Anton-Regular.ttf" if nombre == "Anton" else f"Poppins-{nombre}.ttf"
            self.cache[k] = ImageFont.truetype(f"{self.d}/{archivo}", tam)
        return self.cache[k]


def sombra(capa, radio=14, alfa=150, offset=(0, 10)):
    s = Image.new("RGBA", capa.size, (0, 0, 0, 0))
    s.putalpha(capa.getchannel("A").point(lambda v: v * alfa // 255)
               .filter(ImageFilter.GaussianBlur(radio)))
    out = Image.new("RGBA", capa.size, (0, 0, 0, 0))
    out.alpha_composite(s, offset)
    out.alpha_composite(capa)
    return out


def pegar(base, im, cx, cy, esc=1.0, alfa=1.0):
    if esc <= 0.01 or alfa <= 0.01:
        return
    if abs(esc - 1) > 1e-3:
        im = im.resize((max(1, int(im.width * esc)), max(1, int(im.height * esc))),
                       Image.BILINEAR)
    if alfa < 0.999:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alfa)))
    base.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


# ----------------------------------------------------------------- datos del mapa
def lineas(g):
    if g["type"] == "LineString":
        return [g["coordinates"]]
    if g["type"] == "MultiLineString":
        return g["coordinates"]
    return []


class Mapa:
    def __init__(self, d):
        self.ox, self.oy = merc(LON, LAT)
        calles = {}
        for archivo in ("n_calles.json", "n_grilla.json"):
            try:
                for x in json.load(open(f"{d}/{archivo}")):
                    if x.get("class") == "highway" and x.get("geojson"):
                        calles[x["osm_id"]] = x
            except FileNotFoundError:
                pass
        principales = {"primary", "secondary", "trunk", "motorway", "tertiary",
                       "primary_link", "secondary_link", "trunk_link"}
        self.av, self.calles, self.lavalle = [], [], []
        for x in calles.values():
            nombre = x.get("name") or ""
            for l in lineas(x["geojson"]):
                a = self.proy(l)
                if len(a) < 2:
                    continue
                if "lavalle" in nombre.lower():
                    self.lavalle.append(a)
                elif x.get("type") in principales or nombre.lower().startswith(("avenida", "ruta")):
                    self.av.append(a)
                else:
                    self.calles.append(a)
        ciudad = json.load(open(f"{d}/n_ciudad.json"))[0]["geojson"]
        polys = [ciudad["coordinates"]] if ciudad["type"] == "Polygon" else ciudad["coordinates"]
        self.ciudad = [self.proy(p[0]) for p in polys]
        # Río Paraná: eje del río (recortado a la zona) con un ancho de ~2,6 km
        par = json.load(open(f"{d}/n_parana.json"))[0]["geojson"]
        ejes = [LineString(self.proy(l)) for l in lineas(par) if len(l) > 1]
        zona = box(-40000, -40000, 40000, 40000)
        rio = unary_union([e.intersection(zona) for e in ejes]).buffer(1300, resolution=12)
        rio = rio.simplify(20)
        self.rio = [np.array(p.exterior.coords) for p in getattr(rio, "geoms", [rio])]
        self.etiquetas_calles = self._etiquetas(calles)
        for lista in (self.av, self.calles, self.lavalle):
            lista[:] = [(a, a.min(0), a.max(0)) for a in lista]

    def proy(self, coords):
        a = np.array([merc(lon, lat) for lon, lat in coords], np.float64)
        a[:, 0] -= self.ox
        a[:, 1] -= self.oy
        return a

    def _etiquetas(self, calles):
        """Posición y ángulo de los nombres de las calles cercanas (punto más cercano al
        local, desplazado para no tapar el marcador)."""
        quiero = {"lavalle": ("Av. Lavalle", (0, 230)), "brown": ("Almirante Brown", (-150, 0)),
                  "dutr": ("Moráez Dutrá", (-150, 0)), "tamareu": ("Tamareu", (-150, 0))}
        out = []
        for clave, (texto, (dx, dy)) in quiero.items():
            mejor = None
            for x in calles.values():
                if clave not in (x.get("name") or "").lower():
                    continue
                for l in lineas(x["geojson"]):
                    a = self.proy(l)
                    if len(a) < 2:
                        continue
                    ls = LineString(a)
                    # punto de la calle más cercano al local, desplazado (dx, dy)
                    cerca = ls.interpolate(ls.project(Point(0, 0)))
                    objetivo = Point(cerca.x + dx, cerca.y + dy)
                    p = ls.interpolate(ls.project(objetivo))
                    dist = math.hypot(cerca.x, cerca.y)
                    if mejor is None or dist < mejor[0]:
                        # dirección local de la calle para rotar el texto
                        pr = ls.project(p)
                        p0 = ls.interpolate(max(0, pr - 8))
                        q = ls.interpolate(min(ls.length, pr + 8))
                        ang = math.degrees(math.atan2(q.y - p0.y, q.x - p0.x))
                        if ang > 90:
                            ang -= 180
                        if ang < -90:
                            ang += 180
                        mejor = (dist, p.x, p.y, ang)
            if mejor and mejor[0] < 400:
                out.append((texto, mejor[1], mejor[2], mejor[3]))
        return out

    def dibujar(self, cx, cy, ancho_m, k_lavalle=1.0):
        """Cuadro del mapa centrado en (cx, cy) metros, con ancho_m metros a lo ancho."""
        s = W * SS / ancho_m          # px (supermuestreados) por metro
        img = Image.new("RGB", (W * SS, H * SS), FONDO)
        d = ImageDraw.Draw(img)
        mx, my = ancho_m / 2, ancho_m * H / W / 2

        def tr(a):
            return [((x - cx) * s + W * SS / 2, (cy - y) * s + H * SS / 2) for x, y in a]

        def visible(mn, mx_):
            return not (mx_[0] < cx - mx or mn[0] > cx + mx or mx_[1] < cy - my or mn[1] > cy + my)

        for p in self.ciudad:
            d.polygon(tr(p), fill=CIUDAD)
        for p in self.rio:
            d.polygon(tr(p), fill=AGUA)
        # calles: aparecen a medida que se acerca la cámara
        k_calles = clamp((4500 - ancho_m) / 3000)
        if k_calles > 0:
            col = mezcla(CIUDAD, CALLE, k_calles)
            ancho = max(1, int(max(1.2, 7 * s / SS) * SS))
            for a, mn, mx_ in self.calles:
                if visible(mn, mx_):
                    d.line(tr(a), fill=col, width=ancho, joint="curve")
        ancho = max(2, int(max(1.6, 10 * s / SS) * SS))
        for a, mn, mx_ in self.av:
            if visible(mn, mx_):
                d.line(tr(a), fill=AVENIDA, width=ancho, joint="curve")
        col = mezcla(AVENIDA, ROJO, k_lavalle)
        ancho = max(3, int(max(3.0 + 3 * k_lavalle, 12 * s / SS) * SS))
        for a, mn, mx_ in self.lavalle:
            if visible(mn, mx_):
                d.line(tr(a), fill=col, width=ancho, joint="curve")
        return img.resize((W, H), Image.LANCZOS).convert("RGBA"), s / SS

    def a_pantalla(self, x, y, cx, cy, s):
        return (x - cx) * s + W / 2, (cy - y) * s + H / 2


# ----------------------------------------------------------------- piezas gráficas
def insignia(emblema, d=170):
    """Emblema del conejo en un círculo oscuro con borde crema."""
    s = 3
    im = Image.new("RGBA", (d * s, d * s), (0, 0, 0, 0))
    m = Image.new("L", (d * s, d * s), 0)
    ImageDraw.Draw(m).ellipse([0, 0, d * s - 1, d * s - 1], fill=255)
    e = emblema.convert("RGB")
    lado = min(e.size)
    e = e.crop(((e.width - lado) // 2, e.height - lado, (e.width + lado) // 2, e.height))
    e = e.resize((int(d * s * 0.96), int(d * s * 0.96)), Image.LANCZOS)
    fondo = Image.new("RGB", (d * s, d * s), (44, 40, 40))
    fondo.paste(e, ((d * s - e.width) // 2, (d * s - e.height) // 2))
    im.paste(fondo, (0, 0), m)
    ImageDraw.Draw(im).ellipse([0, 0, d * s - 1, d * s - 1], outline=CREMA, width=7 * s)
    return im.resize((d, d), Image.LANCZOS)


def marcador(ins):
    """Pin rojo con la insignia adentro (la punta queda en el centro inferior)."""
    s = 3
    w, h = 210, 270
    im = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = 100
    cx, cy = w / 2, 105
    d.ellipse([(cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s], fill=ROJO)
    d.polygon([((cx - 62) * s, (cy + 78) * s), ((cx + 62) * s, (cy + 78) * s),
               (cx * s, (h - 4) * s)], fill=ROJO)
    im = im.resize((w, h), Image.LANCZOS)
    ins = ins.resize((172, 172), Image.LANCZOS)
    im.alpha_composite(ins, (int(cx - 86), int(cy - 86)))
    return sombra(im, 10, 140, (0, 8)), (w / 2, h)


def titulo_cartel(f, lineas_txt, tam=120, rot=-3):
    """Cartel rojo con texto Anton blanco (mismo estilo que 'CONVOCATORIA CERRADA')."""
    font = f("Anton", tam)
    anchos = [font.getlength(t) for t in lineas_txt]
    lh = int(tam * 1.08)
    w, h = int(max(anchos)) + 110, lh * len(lineas_txt) + 70
    s = 2
    im = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w * s - 1, h * s - 1], radius=22 * s, fill=ROJO)
    d.rounded_rectangle([12 * s, 12 * s, (w - 12) * s, (h - 12) * s], radius=14 * s,
                        outline=BLANCO, width=5 * s)
    im = im.resize((w, h), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    y = 35 + lh / 2
    for t in lineas_txt:
        d.text((w / 2, y - 6), t, font=font, fill=BLANCO, anchor="mm")
        y += lh
    im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    return sombra(im, 16, 170, (0, 12))


def tarjeta_info(f, ins):
    w, h = 940, 330
    s = 2
    im = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w * s - 1, h * s - 1], radius=40 * s, fill=(26, 26, 29, 240),
                        outline=(255, 255, 255, 40), width=2 * s)
    im = im.resize((w, h), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    im.alpha_composite(ins.resize((190, 190), Image.LANCZOS), (40, 40))
    x = 262
    d.text((x, 92), "Rabbit", font=f("SemiBold", 104), fill=ROJO, anchor="lm")
    fs = f("Bold", 27)
    t = "FOOD & DRINKS - EVENTOS"
    d.rounded_rectangle([x, 160, x + 40, 166], radius=3, fill=VERDE)
    d.text((x + 54, 163), t, font=fs, fill=BLANCO, anchor="lm")
    xe = x + 54 + fs.getlength(t) + 14
    d.rounded_rectangle([xe, 160, xe + 40, 166], radius=3, fill=ROJO)
    # línea de dirección con ícono de pin
    y = 262
    d.ellipse([40, y - 26, 80, y + 14], fill=ROJO)
    d.polygon([(46, y + 2), (74, y + 2), (60, y + 30)], fill=ROJO)
    d.ellipse([52, y - 14, 68, y + 2], fill=(26, 26, 29))
    d.text((100, y - 14), DIRECCION + " · Posadas", font=f("Bold", 40), fill=BLANCO,
           anchor="lm")
    d.text((100, y + 30), ENTRE, font=f("Medium", 28), fill=GRIS, anchor="lm")
    return sombra(im, 18, 170, (0, 14))


def chip(f, texto, icono=True):
    fn = f("SemiBold", 34)
    w, h = int(fn.getlength(texto)) + (100 if icono else 60), 76
    s = 2
    im = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, w * s - 1, h * s - 1], radius=38 * s,
                                         fill=(20, 20, 22, 215))
    im = im.resize((w, h), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    x = 30
    if icono:
        d.ellipse([x, 16, x + 30, 46], fill=ROJO)
        d.polygon([(x + 4, 38), (x + 26, 38), (x + 15, 60)], fill=ROJO)
        d.ellipse([x + 9, 25, x + 21, 37], fill=(20, 20, 22))
        x += 46
    d.text((x, h / 2), texto, font=fn, fill=BLANCO, anchor="lm")
    return sombra(im, 10, 140, (0, 6))


def etiqueta_mapa(f, texto, tam, color=GRIS, ang=0.0, peso="SemiBold", espaciado=0):
    fn = f(peso, tam)
    if espaciado:
        texto = (" " * espaciado).join(texto)
    w = int(fn.getlength(texto)) + 40
    h = int(tam * 1.6)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((w / 2, h / 2), texto, font=fn, fill=color + (255,), anchor="mm",
                            stroke_width=max(2, tam // 10), stroke_fill=FONDO + (255,))
    return im.rotate(ang, resample=Image.BICUBIC, expand=True) if ang else im


# ----------------------------------------------------------------- fotos
class Foto:
    """Foto con movimiento tipo Ken Burns: ventana 9:16 que se desplaza y acerca."""

    def __init__(self, path, ini, fin):
        self.im = Image.open(path).convert("RGB")
        self.ini, self.fin = ini, fin   # (cx, cy, alto) relativos: centro y alto de ventana

    def cuadro(self, k):
        w, h = self.im.size
        cx = (self.ini[0] + (self.fin[0] - self.ini[0]) * k) * w
        cy = (self.ini[1] + (self.fin[1] - self.ini[1]) * k) * h
        alto = (self.ini[2] + (self.fin[2] - self.ini[2]) * k) * h
        ancho = alto * W / H
        x0 = clamp(cx - ancho / 2, 0, w - ancho)
        y0 = clamp(cy - alto / 2, 0, h - alto)
        return self.im.transform((W, H), Image.EXTENT, (x0, y0, x0 + ancho, y0 + alto),
                                 Image.BICUBIC).convert("RGBA")


# ----------------------------------------------------------------- audio
def leer_wav(path):
    with wave.open(path) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        return x.reshape(-1, w.getnchannels()), w.getframerate()


def mezclar_audio(dir_audio, eventos, out):
    sr = 48000
    n = int(DUR * sr)
    mus, _ = leer_wav(f"{dir_audio}/musica.wav")
    mus = mus if mus.shape[1] == 2 else np.repeat(mus, 2, axis=1)
    mus = np.pad(mus, ((0, max(0, n - len(mus))), (0, 0)))[:n] * 0.55
    t = np.arange(n) / sr
    env = np.clip(t / 0.4, 0, 1) * np.clip((DUR - t) / 1.2, 0, 1)
    mix = mus * env[:, None]
    muestras = {k: leer_wav(f"{dir_audio}/{k}.wav")[0].mean(axis=1) for k in
                ("whoosh", "pop", "click")}
    gan = {"whoosh": 0.35, "pop": 0.4, "click": 0.3}
    for tt, k in eventos:
        x = muestras[k] * gan[k]
        i = int(tt * sr)
        if i < n:
            mix[i:i + len(x)] += x[:n - i, None]
    previa = out + ".previa.wav"
    with wave.open(previa, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", previa, "-af",
                    "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", out], check=True)


# ----------------------------------------------------------------- principal
def main():
    datos, fuentes, dir_audio, emblema_p, f1, f2, f3, salida = sys.argv[1:9]
    f = Fuentes(fuentes)
    global FUENTE_ATRIB
    FUENTE_ATRIB = f("Medium", 20)
    mapa = Mapa(datos)
    ins = insignia(Image.open(emblema_p))
    pin, (pin_ax, pin_ay) = marcador(ins)
    titulo = titulo_cartel(f, ["¿DÓNDE", "ESTAMOS?"], 118)
    titulo_cierre = titulo_cartel(f, ["ACÁ", "ESTAMOS"], 118, rot=3)
    tarjeta = tarjeta_info(f, ins)
    chip_dir = chip(f, DIRECCION + " · Posadas")
    fotos = [
        Foto(f1, (0.33, 0.45, 0.98), (0.62, 0.45, 0.86)),   # fachada completa: paneo
        Foto(f2, (0.45, 0.55, 1.0), (0.42, 0.52, 0.82)),    # cartel en ángulo: acercamiento
        Foto(f3, (0.5, 0.55, 0.80), (0.5, 0.52, 1.0)),      # frente: se aleja
    ]
    textos_fotos = [["FOOD &", "DRINKS"], ["EVENTOS"], ["¡TE", "ESPERAMOS!"]]
    carteles_fotos = [titulo_cartel(f, t, 96, rot=(-3 if i % 2 == 0 else 3))
                      for i, t in enumerate(textos_fotos)]
    rotulo_posadas = etiqueta_mapa(f, "POSADAS", 64, CREMA, peso="Bold", espaciado=1)
    rotulo_misiones = etiqueta_mapa(f, "Misiones · Argentina", 32, GRIS, peso="Medium")
    rotulo_rio = etiqueta_mapa(f, "Río Paraná", 40, (110, 150, 200), ang=8, peso="Medium")
    rotulos_calles = [(etiqueta_mapa(f, t, 38, (205, 205, 215), ang=a, peso="SemiBold"), x, y)
                      for t, x, y, a in mapa.etiquetas_calles]

    c0 = merc(*CENTRO_INI)
    c0 = (c0[0] - mapa.ox, c0[1] - mapa.oy)
    # el local queda un poco arriba del centro para dejar lugar a la tarjeta
    c1 = (0.0, -ANCHO_FIN * H / W * 0.12)

    def camara(t):
        k = ease_in_out((t - T_ZOOM0) / (T_ZOOM1 - T_ZOOM0))
        ancho = math.exp(math.log(ANCHO_INI) + (math.log(ANCHO_FIN) - math.log(ANCHO_INI)) * k)
        # el centro sigue al zoom en escala logarítmica para que no "derrape"
        kc = (math.log(ANCHO_INI) - math.log(ancho)) / (math.log(ANCHO_INI) - math.log(ANCHO_FIN))
        cx = c0[0] + (c1[0] - c0[0]) * kc
        cy = c0[1] + (c1[1] - c0[1]) * kc
        return cx, cy, ancho * (1 + 0.012 * max(0, t - T_ZOOM1)) if t < T_WIPE else ancho

    # cuadro fijo del mapa cercano (para el final del zoom y el cierre)
    cache = {}

    def mapa_en(t, cierre=False):
        if cierre:
            ancho = ANCHO_FIN * 1.1
            cx, cy, ancho = 0.0, (1010 - H / 2) / (W / ancho), ancho   # punta del pin en y=1010
        else:
            cx, cy, ancho = camara(min(t, T_WIPE))
        clave = (round(cx, 1), round(cy, 1), round(ancho, 2))
        if clave not in cache:
            k_lav = clamp((t - (T_ZOOM1 - 1.6)) / 1.2)
            cache.clear()
            cache[clave] = mapa.dibujar(cx, cy, ancho, k_lav) + ((cx, cy),)
        return cache[clave]

    def capa_mapa(t, cierre=False):
        img, s, (cx, cy) = mapa_en(t, cierre)
        img = img.copy()
        cx_, cy_, ancho = cx, cy, W / s
        # rótulos de ciudad y río (se van con el zoom)
        k = clamp((6000 - ancho) / 4000)
        if k < 1:
            ox, oy = mapa.a_pantalla(c0[0], c0[1] + 900, cx_, cy_, s)
            pegar(img, rotulo_posadas, ox, oy, 1, 1 - k)
            pegar(img, rotulo_misiones, ox, oy + 62, 1, 1 - k)
            rx, ry = mapa.a_pantalla(c0[0] + 2500, c0[1] + 6200, cx_, cy_, s)
            pegar(img, rotulo_rio, rx, ry, 1, 1 - k)
        # nombres de calles al final del zoom
        kc = clamp((1500 - ancho) / 700)
        if kc > 0:
            for im, x, y in rotulos_calles:
                px, py = mapa.a_pantalla(x, y, cx_, cy_, s)
                pegar(img, im, px, py, 1, kc)
        # atribución de los datos del mapa (licencia ODbL)
        ImageDraw.Draw(img).text((W - 40, 1700), "Mapa: © colaboradores de OpenStreetMap",
                                 font=FUENTE_ATRIB, fill=(120, 120, 130), anchor="rm")
        # marcador
        px, py = mapa.a_pantalla(0, 0, cx_, cy_, s)
        if t >= T_PIN or cierre:
            u = 1.0 if cierre else (t - T_PIN)
            caida = 1 - ease_out(u / 0.35)
            rebote = 0 if u < 0.35 else 18 * math.sin(math.pi * clamp((u - 0.35) / 0.25)) \
                * (1 - clamp((u - 0.35) / 0.25))
            # sombra en el piso y ondas
            capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            dc = ImageDraw.Draw(capa)
            k_s = clamp(u / 0.35)
            dc.ellipse([px - 40 * k_s, py - 12 * k_s, px + 40 * k_s, py + 12 * k_s],
                       fill=(0, 0, 0, int(120 * k_s)))
            for o in range(2):
                uu = (u - 0.35 - o * 0.45) % 1.8 if u > 0.35 else -1
                if 0 <= uu < 1.2:
                    rr = 30 + 170 * ease_out(uu / 1.2)
                    dc.ellipse([px - rr, py - rr * 0.38, px + rr, py + rr * 0.38],
                               outline=ROJO + (int(200 * (1 - uu / 1.2)),), width=5)
            img.alpha_composite(capa)
            pegar(img, pin, px, py - pin_ay / 2 - 700 * caida - rebote + 6, 1.0,
                  clamp(u / 0.1))
        return img

    eventos = [(T_ZOOM0 - 0.1, "whoosh"), (T_PIN + 0.3, "pop"), (T_PIN + 0.75, "pop"),
               (T_WIPE - 0.15, "whoosh"), (T_FOTOS[1] - 0.2, "whoosh"),
               (T_FOTOS[2] - 0.2, "whoosh"), (T_CIERRE - 0.2, "whoosh"),
               (T_CIERRE + 0.45, "pop"), (T_CIERRE + 0.9, "click"), (0.15, "pop")]
    eventos += [(t0 + 0.25, "click") for t0 in T_FOTOS]

    tmp = salida + ".video.mp4"
    enc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
         "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709",
         "-color_trc", "bt709", tmp], stdin=subprocess.PIPE)
    n_total = int(round(DUR * FPS))
    portada = None
    for i in range(n_total):
        t = i / FPS
        if t < T_WIPE:
            img = capa_mapa(t)
            # título "¿DÓNDE ESTAMOS?" al principio
            k_in = ease_back(t / 0.45)
            k_out = ease_in_out((t - (T_ZOOM0 + 0.6)) / 0.4)
            if k_out < 1:
                pegar(img, titulo, W / 2, 420 - 500 * k_out, 0.6 + 0.4 * k_in,
                      clamp(t / 0.15) * (1 - k_out))
            # tarjeta con la dirección
            u = t - (T_PIN + 0.45)
            if u > 0:
                pegar(img, tarjeta, W / 2, 1490 + 220 * (1 - ease_out(u / 0.45)),
                      0.9 + 0.1 * ease_back(u / 0.45), clamp(u / 0.2))
            if abs(t - (T_WIPE - 0.5)) < 0.5 / FPS:
                portada = img.copy()
        if T_WIPE - 0.35 <= t < T_CIERRE + 0.35:
            # fotos con cortina circular desde el pin y deslizamiento entre fotos
            j = min(2, max(0, int((t - T_WIPE) // FOTO_DUR))) if t >= T_WIPE else 0
            k = clamp((t - T_FOTOS[j] + 0.35) / (FOTO_DUR + 0.7))
            foto = fotos[j].cuadro(ease_in_out(k) * 0.6 + k * 0.4)
            u = t - T_FOTOS[j]
            pegar(foto, carteles_fotos[j], W / 2, 400 + 30 * (1 - ease_out(u / 0.4)),
                  0.7 + 0.3 * ease_back(u / 0.4), clamp(u / 0.15))
            pegar(foto, chip_dir, W / 2, 1560, 1, 1)
            if t < T_WIPE:
                # cortina circular desde el pin hacia afuera
                r = 1400 * ease_in_out((t - (T_WIPE - 0.35)) / 0.35)
                m = Image.new("L", (W, H), 0)
                px, py = W / 2, H / 2 - 0.12 * H - 150   # cabeza del marcador
                ImageDraw.Draw(m).ellipse([px - r, py - r, px + r, py + r], fill=255)
                img.paste(foto, (0, 0), m)
            elif j > 0 and u < 0.3:
                # la foto nueva entra desde abajo empujando a la anterior
                prev = fotos[j - 1].cuadro(1.0)
                pegar(prev, carteles_fotos[j - 1], W / 2, 400, 1, 1)
                pegar(prev, chip_dir, W / 2, 1560, 1, 1)
                e = ease_in_out(u / 0.3)
                img = Image.new("RGBA", (W, H))
                img.alpha_composite(prev, (0, int(-H * e)))
                img.alpha_composite(foto, (0, int(H * (1 - e))))
            else:
                img = foto
        if t >= T_CIERRE:
            # cierre: el mapa cercano con el marcador, oscurecido, y la tarjeta al centro
            u = t - T_CIERRE
            fondo = capa_mapa(T_WIPE - 0.01, cierre=True)
            k = ease_in_out(u / 0.4)
            if u < 0.4:
                ultima = fotos[2].cuadro(1.0)
                pegar(ultima, carteles_fotos[2], W / 2, 400, 1, 1)
                img = Image.blend(ultima, fondo, k)
            else:
                img = fondo
            capa = Image.new("RGBA", (W, H), (0, 0, 0, int(80 * k)))
            img.alpha_composite(capa)
            uu = u - 0.35
            if uu > 0:
                pegar(img, titulo_cierre, W / 2, 400 + 40 * (1 - ease_out(uu / 0.4)),
                      0.7 + 0.3 * ease_back(uu / 0.4), clamp(uu / 0.15))
            uu = u - 0.6
            if uu > 0:
                pegar(img, tarjeta, W / 2, 1490 + 160 * (1 - ease_out(uu / 0.45)),
                      0.9 + 0.1 * ease_back(uu / 0.45), clamp(uu / 0.2))
        enc.stdin.write(img.convert("RGB").tobytes())
        if i % 60 == 0:
            print(f"cuadro {i}/{n_total}", flush=True)
    enc.stdin.close()
    enc.wait()

    audio = salida + ".audio.wav"
    mezclar_audio(dir_audio, eventos, audio)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-i", audio, "-map", "0:v:0",
                    "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", "-shortest", salida], check=True)
    if portada is not None:
        portada.convert("RGB").save(salida.rsplit(".", 1)[0] + "_portada.png")
    print(f"Listo: {DUR:.1f} s")


if __name__ == "__main__":
    main()
