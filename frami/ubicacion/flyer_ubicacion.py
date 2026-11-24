"""Flyer "Nuestra ubicación" de FRAMI (historia / estado 1080x1920 y feed 1080x1350).

Arriba, un mapa claro de la zona dibujado con datos de OpenStreetMap (bajar_calles.py) y un
marcador grande con la foto de la oficina; abajo, "Nuestra ubicación", la dirección, el
horario, "Envianos mensaje" con el WhatsApp y el logo.

Uso: python3 flyer_ubicacion.py <dir_datos> <foto_oficina.jpg> <logo.png> <dir_fuentes> <dir_salida>
(dir_fuentes: Poppins-*.ttf y DancingScript-Bold.ttf)
"""
import json
import math
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

AZUL = (8, 8, 96)
AZUL_2 = (24, 34, 150)
ROJO = (232, 0, 61)
AMARILLO = (245, 196, 0)
BLANCO = (255, 255, 255)
VERDE_WA = (37, 211, 102)
SS = 2

# mapa (estilo claro)
M_FONDO = (232, 236, 247)
M_CALLE = (255, 255, 255)
M_BORDE = (205, 211, 230)
M_AVENIDA = (255, 226, 140)
M_AV_BORDE = (230, 190, 80)
M_TEXTO = (120, 128, 160)

LAT, LON = -27.4124007, -55.9908180          # Las Rosas 10976 (Nominatim)
DIRECCION = "Las Rosas 10976"
BARRIO = "Itaembé Guazú · Posadas, Misiones"
HORARIO = "De 9 a 12 h y de 17 a 20 h"
WHATSAPP = "3764 886646"
FOTO_CAJA = (130, 280, 1050, 1200)            # recorte cuadrado de la oficina en la foto

R = 6378137.0


def merc(lon, lat):
    return R * math.radians(lon), R * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


class F:
    def __init__(self, d):
        self.d, self.c = d, {}

    def __call__(self, nombre, tam):
        k = (nombre, tam)
        if k not in self.c:
            archivo = "DancingScript-Bold.ttf" if nombre == "Script" else f"Poppins-{nombre}.ttf"
            self.c[k] = ImageFont.truetype(f"{self.d}/{archivo}", tam)
        return self.c[k]


def sombra(capa, radio=14, alfa=150, offset=(0, 10), color=(0, 0, 40)):
    pad = radio * 3
    out = Image.new("RGBA", (capa.width + 2 * pad, capa.height + 2 * pad), (0, 0, 0, 0))
    s = Image.new("RGBA", capa.size, color + (0,))
    s.putalpha(capa.getchannel("A").point(lambda v: v * alfa // 255))
    out.alpha_composite(s, (pad + offset[0], pad + offset[1]))
    out = out.filter(ImageFilter.GaussianBlur(radio))
    out.alpha_composite(capa, (pad, pad))
    return out, pad


def pegar(base, capa, cx, y, **kw):
    """Pega 'capa' centrada horizontalmente en cx, con su borde superior en y."""
    capa, pad = sombra(capa, **kw)
    base.alpha_composite(capa, (int(cx - capa.width / 2), int(y - pad)))


# ----------------------------------------------------------------- mapa
def cargar_calles(d):
    calles = {}
    for archivo in ("n_avenidas.json", "n_grilla.json"):
        try:
            for x in json.load(open(f"{d}/{archivo}")):
                if x.get("class") == "highway" and x.get("geojson", {}).get("type") in (
                        "LineString", "MultiLineString"):
                    calles[x["osm_id"]] = x
        except FileNotFoundError:
            pass
    ox, oy = merc(LON, LAT)
    out = []
    for x in calles.values():
        g = x["geojson"]
        lineas = [g["coordinates"]] if g["type"] == "LineString" else g["coordinates"]
        nombre = x.get("name") or ""
        avenida = nombre.lower().startswith(("avenida", "ruta")) or x.get("type") in (
            "primary", "secondary", "trunk")
        for l in lineas:
            a = np.array([merc(lo, la) for lo, la in l])
            a[:, 0] -= ox
            a[:, 1] -= oy
            out.append((a, nombre, avenida))
    return out


def dibujar_mapa(calles, f, W, Hm, ancho_m, pin_xy):
    """Mapa W x Hm; el local (0, 0) cae en pin_xy (px)."""
    s = W / ancho_m
    img = Image.new("RGB", (W * SS, Hm * SS), M_FONDO)
    d = ImageDraw.Draw(img)

    def tr(a):
        return [((x * s + pin_xy[0]) * SS, (pin_xy[1] - y * s) * SS) for x, y in a]

    for capa in ("borde", "relleno"):
        for a, nombre, av in sorted(calles, key=lambda c: c[2]):
            ancho = (20 if av else 12) * s * SS
            if capa == "borde":
                d.line(tr(a), fill=M_AV_BORDE if av else M_BORDE, width=int(ancho + 5 * SS),
                       joint="curve")
            else:
                d.line(tr(a), fill=M_AVENIDA if av else M_CALLE, width=int(ancho), joint="curve")
    img = img.resize((W, Hm), Image.LANCZOS).convert("RGBA")

    # nombres de calles: un rótulo por nombre, en el tramo visible más largo, sin pisarse
    ocupado = [(pin_xy[0] - 190, pin_xy[1] - 400, pin_xy[0] + 190, pin_xy[1] + 40)]
    tramos = {}
    for a, nombre, av in calles:
        if not nombre:
            continue
        p = np.array([(x * s + pin_xy[0], pin_xy[1] - y * s) for x, y in a])
        for i in range(len(p) - 1):
            (x0, y0), (x1, y1) = p[i], p[i + 1]
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            if not (60 < mx < W - 60 and 60 < my < Hm - 80):
                continue
            largo = math.hypot(x1 - x0, y1 - y0)
            ang = math.degrees(math.atan2(-(y1 - y0), x1 - x0))
            if ang > 90:
                ang -= 180
            if ang < -90:
                ang += 180
            if largo > tramos.get(nombre, (0,))[0]:
                tramos[nombre] = (largo, mx, my, ang, av)
    for nombre, (largo, mx, my, ang, av) in sorted(tramos.items(), key=lambda t: -t[1][0]):
        texto = nombre.upper().replace("AVENIDA", "AV.")
        fn = f("SemiBold", 22)
        tw = fn.getlength(texto)
        if tw > largo * 0.95:
            continue
        lab = Image.new("RGBA", (int(tw) + 20, 40), (0, 0, 0, 0))
        ImageDraw.Draw(lab).text(((tw + 20) / 2, 20), texto, font=fn,
                                 fill=(150, 120, 40) if av else M_TEXTO, anchor="mm",
                                 stroke_width=3, stroke_fill=M_AVENIDA if av else M_CALLE)
        lab = lab.rotate(ang, resample=Image.BICUBIC, expand=True)
        caja = (mx - lab.width / 2, my - lab.height / 2, mx + lab.width / 2, my + lab.height / 2)
        if any(not (caja[2] < o[0] or caja[0] > o[2] or caja[3] < o[1] or caja[1] > o[3])
               for o in ocupado):
            continue
        ocupado.append(caja)
        img.alpha_composite(lab, (int(caja[0]), int(caja[1])))
    return img


def marcador(foto, r=150):
    """Marcador azul con la foto de la oficina en un círculo; la punta es el centro inferior."""
    s = 3
    w, h = 2 * r + 40, int(2 * r + r * 0.75 + 40)
    im = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = w / 2, r + 20
    d.ellipse([(cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s], fill=AZUL)
    d.polygon([((cx - r * 0.62) * s, (cy + r * 0.72) * s), ((cx + r * 0.62) * s,
               (cy + r * 0.72) * s), (cx * s, (h - 8) * s)], fill=AZUL)
    im = im.resize((w, h), Image.LANCZOS)
    ri = int(r * 0.86)
    ft = foto.resize((2 * ri, 2 * ri), Image.LANCZOS).convert("RGBA")
    m = Image.new("L", (2 * ri * s, 2 * ri * s), 0)
    ImageDraw.Draw(m).ellipse([0, 0, 2 * ri * s - 1, 2 * ri * s - 1], fill=255)
    ft.putalpha(m.resize((2 * ri, 2 * ri), Image.LANCZOS))
    im.alpha_composite(ft, (int(cx - ri), int(cy - ri)))
    # filete amarillo fino alrededor de la foto
    a = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    ImageDraw.Draw(a).ellipse([(cx - ri - 4) * s, (cy - ri - 4) * s, (cx + ri + 4) * s,
                               (cy + ri + 4) * s], outline=AMARILLO, width=5 * s)
    im.alpha_composite(a.resize((w, h), Image.LANCZOS))
    return im


# ----------------------------------------------------------------- piezas de abajo
def icono_pin(r, color=AZUL):
    s = 3
    w, h = int(2 * r), int(2.9 * r)
    im = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([0, 0, w * s - 1, w * s - 1], fill=color)
    d.polygon([(r * 0.22 * s, r * 1.45 * s), ((w - r * 0.22) * s, r * 1.45 * s),
               (r * s, (h - 2) * s)], fill=color)
    d.ellipse([r * 0.55 * s, r * 0.55 * s, r * 1.45 * s, r * 1.45 * s], fill=BLANCO)
    return im.resize((w, h), Image.LANCZOS)


def titulo(f, tam):
    f1 = f("ExtraBold", tam)
    f2 = f("Script", int(tam * 1.35))
    w = int(max(f1.getlength("Nuestra"), f2.getlength("ubicación"))) + 60
    h = int(tam * 2.35)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((w / 2, tam * 0.55), "Nuestra", font=f1, fill=AZUL, anchor="mm")
    d.text((w / 2, tam * 1.55), "ubicación", font=f2, fill=ROJO, anchor="mm")
    return im.crop(im.getbbox())


def texto_centrado(f, peso, tam, texto, color):
    fn = f(peso, tam)
    im = Image.new("RGBA", (int(fn.getlength(texto)) + 20, int(tam * 1.5)), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((im.width / 2, im.height / 2), texto, font=fn, fill=color,
                            anchor="mm")
    return im


def linea_horario(f, tam):
    fn = f("Medium", tam)
    r = int(tam * 0.55)
    w = int(fn.getlength(HORARIO)) + 2 * r + 20
    im = Image.new("RGBA", (w, int(tam * 1.6)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cy = im.height / 2
    d.ellipse([0, cy - r, 2 * r, cy + r], outline=AZUL_2, width=3)
    d.line([(r, cy), (r, cy - r * 0.55)], fill=AZUL_2, width=3)
    d.line([(r, cy), (r + r * 0.4, cy + r * 0.2)], fill=AZUL_2, width=3)
    d.text((2 * r + 16, cy), HORARIO, font=fn, fill=(70, 78, 130), anchor="lm")
    return im


def pildora_mensaje(f, tam):
    """Píldora azul: 'Envianos mensaje:' y el WhatsApp (dos líneas)."""
    f1 = f("SemiBold", int(tam * 0.75))
    f2 = f("ExtraBold", tam)
    rw = int(tam * 0.5)
    w = int(max(f1.getlength("Envianos mensaje"), f2.getlength(WHATSAPP) + 2 * rw + 22)) + 110
    h = int(tam * 2.9)
    im = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, w * SS - 1, h * SS - 1], radius=44 * SS,
                                         fill=AZUL)
    im = im.resize((w, h), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    d.text((w / 2, h * 0.3), "Envianos mensaje", font=f1, fill=(200, 210, 255), anchor="mm")
    tw = f2.getlength(WHATSAPP) + 2 * rw + 22
    x0 = w / 2 - tw / 2
    cy = h * 0.66
    d.ellipse([x0, cy - rw, x0 + 2 * rw, cy + rw], fill=VERDE_WA)
    d.arc([x0 + rw * 0.5, cy - rw * 0.5, x0 + rw * 1.5, cy + rw * 0.5], 100, 260, fill=BLANCO,
          width=max(3, int(rw * 0.22)))
    d.text((x0 + 2 * rw + 22, cy), WHATSAPP, font=f2, fill=BLANCO, anchor="lm")
    return im


def decoracion(img, cx, cy, r):
    """Sol amarillo asomando con arco de puntos rojos (detalle de marca)."""
    W, H = img.size
    c = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.ellipse([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS], fill=AMARILLO)
    r2 = r * 1.25
    for a in range(180, 280, 7):
        x, y = cx + r2 * math.cos(math.radians(a)), cy + r2 * math.sin(math.radians(a))
        d.ellipse([(x - 7) * SS, (y - 7) * SS, (x + 7) * SS, (y + 7) * SS], fill=ROJO)
    d.arc([(cx - r * 1.45) * SS, (cy - r * 1.45) * SS, (cx + r * 1.45) * SS,
           (cy + r * 1.45) * SS], 185, 265, fill=AZUL_2 + (90,), width=5 * SS)
    img.alpha_composite(c.resize((W, H), Image.LANCZOS))


# ----------------------------------------------------------------- armado
def armar(calles, foto, logo_p, f, W, H, Hm, ancho_m, pin_xy, r_pin, y_bloque, k, salida):
    y = np.linspace(0, 1, H)[:, None, None]
    fondo = np.broadcast_to(np.array((250, 251, 255), np.float32) * (1 - y) +
                            np.array((222, 228, 250), np.float32) * y, (H, W, 3))
    img = Image.fromarray(fondo.astype(np.uint8)).convert("RGBA")
    mapa = dibujar_mapa(calles, f, W, Hm, ancho_m, pin_xy)
    a = np.ones((Hm, W), np.float32)
    ini = int(Hm * 0.72)
    a[ini:] = np.linspace(1, 0, Hm - ini)[:, None] ** 1.3
    mapa.putalpha(Image.fromarray((a * 255).astype(np.uint8)))
    img.alpha_composite(mapa)
    decoracion(img, W + 40, H + 30, 330 * k)

    pin = marcador(foto, r_pin)
    sp, pad = sombra(pin, 16, 120, (0, 14))
    img.alpha_composite(sp, (int(pin_xy[0] - pin.width / 2 - pad), int(pin_xy[1] - pin.height - pad)))
    # punto en el piso donde apunta el marcador
    ImageDraw.Draw(img).ellipse([pin_xy[0] - 9, pin_xy[1] - 4, pin_xy[0] + 9, pin_xy[1] + 6],
                                fill=(8, 8, 96, 90))

    cx = W / 2
    yb = y_bloque
    ic = icono_pin(int(34 * k))
    pegar(img, ic, cx, yb, radio=8, alfa=60)
    yb += ic.height + int(16 * k)
    t = titulo(f, int(112 * k))
    pegar(img, t, cx, yb, radio=10, alfa=40, offset=(0, 4))
    yb += t.height + int(26 * k)
    dt = texto_centrado(f, "Bold", int(54 * k), DIRECCION, AZUL)
    pegar(img, dt, cx, yb, radio=6, alfa=0)
    yb += dt.height - int(4 * k)
    bt = texto_centrado(f, "Medium", int(31 * k), BARRIO, (90, 98, 150))
    pegar(img, bt, cx, yb, radio=6, alfa=0)
    yb += bt.height + int(6 * k)
    hr = linea_horario(f, int(30 * k))
    pegar(img, hr, cx, yb, radio=6, alfa=0)
    yb += hr.height + int(30 * k)
    pl = pildora_mensaje(f, int(46 * k))
    pegar(img, pl, cx, yb, radio=14, alfa=110)

    # sin el logo de FRAMI (pedido de la clienta)
    # atribución de los datos del mapa (licencia ODbL)
    ImageDraw.Draw(img).text((W - 24, Hm - 40), "Mapa: © colaboradores de OpenStreetMap",
                             font=f("Medium", 16), fill=(140, 146, 175), anchor="rm")
    img.convert("RGB").save(salida)
    return yb + pl.height


def main():
    datos, foto_p, logo_p, fuentes, salida = sys.argv[1:6]
    f = F(fuentes)
    calles = cargar_calles(datos)
    foto = Image.open(foto_p).convert("RGB").crop(FOTO_CAJA)
    fin_h = armar(calles, foto, logo_p, f, 1080, 1920, 1120, 640, (540, 740), 160, 965, 0.96,
                  f"{salida}/frami_ubicacion_historia.png")
    fin_f = armar(calles, foto, logo_p, f, 1080, 1350, 700, 820, (540, 520), 125, 600, 0.82,
                  f"{salida}/frami_ubicacion_feed.png")
    print("fin del contenido: historia", fin_h, "/1920 · feed", fin_f, "/1350")


if __name__ == "__main__":
    main()
