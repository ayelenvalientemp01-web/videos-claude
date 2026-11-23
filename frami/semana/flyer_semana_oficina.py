"""Flyer de comienzo de semana de FRAMI con la foto de la oficina (versión rediseñada).

La foto ocupa toda la pieza; el cielo (extendido hacia arriba y teñido con el azul de
marca) es el fondo del título: "¡Arrancamos" en Poppins + "la semana!" en cursiva amarilla.
Debajo, los días de la semana con el lunes destacado. Abajo, una tarjeta de vidrio
esmerilado con "Ya estamos atendiendo" y el WhatsApp. Detalles de marca en el cielo.

Retoques de la foto: se borra el cartel "Cerrado" de la puerta y queda afuera del encuadre
la bandera de Rapipago.

Uso: python3 flyer_semana_oficina.py <foto_oficina.jpg> <logo.png> <dir_fuentes> <dir_salida>
(dir_fuentes debe tener Poppins-*.ttf y DancingScript-Bold.ttf)
"""
import math
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

AZUL = (8, 8, 96)
ROJO = (232, 0, 61)
AMARILLO = (245, 196, 0)
BLANCO = (255, 255, 255)
VERDE_WA = (37, 211, 102)
SS = 2

CARTEL_CERRADO = (724, 772, 782, 816)   # caja del cartel "Cerrado" en la foto original
ANCHO_UTIL = 1125                        # a la derecha está la bandera de Rapipago
DIAS = ["LUN", "MAR", "MIÉ", "JUE", "VIE"]
WHATSAPP = "3764 886646"
DIRECCION = "Las Rosas 10976"
HORARIO = "De 9 a 12 h y de 17 a 20 h"
USUARIO = "@frami.productoresasesores"


class F:
    def __init__(self, d):
        self.d, self.c = d, {}

    def __call__(self, nombre, tam):
        k = (nombre, tam)
        if k not in self.c:
            archivo = f"{nombre}.ttf" if "-" in nombre and not nombre.startswith(
                ("Bold", "Medium")) else f"Poppins-{nombre}.ttf"
            self.c[k] = ImageFont.truetype(f"{self.d}/{archivo}", tam)
        return self.c[k]


def sombra(capa, radio=14, alfa=150, offset=(0, 10)):
    pad = radio * 3
    out = Image.new("RGBA", (capa.width + 2 * pad, capa.height + 2 * pad), (0, 0, 0, 0))
    s = Image.new("RGBA", capa.size, (0, 0, 0, 0))
    s.putalpha(capa.getchannel("A").point(lambda v: v * alfa // 255))
    out.alpha_composite(s, (pad + offset[0], pad + offset[1]))
    out = out.filter(ImageFilter.GaussianBlur(radio))
    out.alpha_composite(capa, (pad, pad))
    return out, pad


def pegar(base, capa, x, y, con_sombra=True, **kw):
    if con_sombra:
        capa, pad = sombra(capa, **kw)
        x, y = x - pad, y - pad
    base.alpha_composite(capa, (int(x), int(y)))


# ----------------------------------------------------------------- foto
def retocar(foto):
    """Borra el cartel 'Cerrado' (relleno fila por fila: el reflejo son franjas
    horizontales) y da un poco más de contraste y color."""
    a = np.asarray(foto, np.float32).copy()
    x0, y0, x1, y1 = CARTEL_CERRADO
    izq = a[y0:y1, x0 - 3:x0].mean(axis=1)
    der = a[y0:y1, x1:x1 + 3].mean(axis=1)
    k = np.linspace(0, 1, x1 - x0)[None, :, None]
    ruido = np.random.default_rng(3).normal(0, 2.0, (y1 - y0, x1 - x0, 3))
    a[y0:y1, x0:x1] = izq[:, None] * (1 - k) + der[:, None] * k + ruido
    foto = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    foto = ImageEnhance.Contrast(foto).enhance(1.06)
    return ImageEnhance.Color(foto).enhance(1.08)


def fondo(foto, W, H, cielo):
    """Foto a todo el ancho (sin la bandera), con 'cielo' píxeles de cielo agregados arriba
    (continuación del degradado real) y un tinte azul de marca en la parte alta."""
    esc = W / ANCHO_UTIL
    f = foto.crop((0, 0, ANCHO_UTIL, foto.height))
    f = f.resize((W, round(f.height * esc)), Image.LANCZOS)
    f = f.crop((0, 0, W, min(f.height, H - cielo)))
    a = np.asarray(f, np.float32)
    fila = a[:8].mean(axis=0)                                 # color del cielo arriba
    fila = np.asarray(Image.fromarray(fila[None].astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(40)), np.float32)[0]
    oscuro = fila * 0.72                                      # el cielo se oscurece hacia arriba
    t = (np.arange(cielo, dtype=np.float32) / max(1, cielo))[:, None, None]
    arriba = oscuro[None] * (1 - t) + fila[None] * t
    img = np.zeros((H, W, 3), np.float32)
    img[:cielo] = arriba
    img[cielo:cielo + a.shape[0]] = a
    if cielo + a.shape[0] < H:
        img[cielo + a.shape[0]:] = a[-1]
    img = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    costura = img.crop((0, cielo - 24, W, cielo + 24)).filter(ImageFilter.GaussianBlur(10))
    img.paste(costura, (0, cielo - 24))
    img = img.convert("RGBA")
    # tinte azul FRAMI arriba (para el título) y abajo (para la tarjeta)
    g = np.zeros((H, W, 4), np.uint8)
    g[..., :3] = AZUL
    y = np.arange(H, dtype=np.float32)
    arriba_a = np.clip(1 - y / (cielo + 260), 0, 1) ** 1.3 * 175
    abajo_a = np.clip((y - (H - 520)) / 520, 0, 1) ** 1.5 * 200
    g[..., 3] = np.maximum(arriba_a, abajo_a).astype(np.uint8)[:, None]
    img.alpha_composite(Image.fromarray(g, "RGBA"))
    return img


def detalles_cielo(img, cx, cy, r):
    """Destello de sol + arco amarillo fino + arco de puntos rojos (detalles de marca)."""
    W, H = img.size
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    g = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (r * 1.1) ** 2)) * 0.55
    luz = np.zeros((H, W, 4), np.uint8)
    luz[..., :3] = (255, 236, 170)
    luz[..., 3] = (g * 255).astype(np.uint8)
    img.alpha_composite(Image.fromarray(luz, "RGBA"))
    c = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.arc([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS], 110, 250,
          fill=AMARILLO + (230,), width=5 * SS)
    r2 = r * 1.22
    for a in range(120, 245, 7):
        x, y = cx + r2 * math.cos(math.radians(a)), cy + r2 * math.sin(math.radians(a))
        d.ellipse([(x - 5) * SS, (y - 5) * SS, (x + 5) * SS, (y + 5) * SS], fill=ROJO + (230,))
    img.alpha_composite(c.resize((W, H), Image.LANCZOS))


# ----------------------------------------------------------------- tipografía
def titulo(f, tam):
    """'¡Arrancamos' (Poppins) y debajo 'la semana!' en cursiva amarilla, más grande."""
    f1 = f("ExtraBold", tam)
    f2 = f("DancingScript-Bold", int(tam * 1.5))
    w = int(max(f1.getlength("¡Arrancamos"), f2.getlength("la semana!") + tam * 0.6)) + 40
    h = int(tam * 2.45)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((0, tam * 0.6), "¡Arrancamos", font=f1, fill=BLANCO, anchor="lm")
    d.text((tam * 0.55, tam * 1.52), "la semana!", font=f2, fill=AMARILLO, anchor="lm")
    return im.crop(im.getbbox())


def dias(f, tam=24):
    fn = f("SemiBold", tam)
    w, h, sep = int(tam * 3.3), int(tam * 2.0), 12
    im = Image.new("RGBA", (len(DIAS) * (w + sep) - sep, h), (0, 0, 0, 0))
    for i, dia in enumerate(DIAS):
        p = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
        dp = ImageDraw.Draw(p)
        if i == 0:
            dp.rounded_rectangle([0, 0, w * SS - 1, h * SS - 1], radius=h * SS // 2,
                                 fill=AMARILLO)
        else:
            dp.rounded_rectangle([0, 0, w * SS - 1, h * SS - 1], radius=h * SS // 2,
                                 outline=(255, 255, 255, 170), width=2 * SS)
        p = p.resize((w, h), Image.LANCZOS)
        ImageDraw.Draw(p).text((w / 2, h / 2), dia, font=fn,
                               fill=AZUL if i == 0 else BLANCO, anchor="mm")
        im.alpha_composite(p, (i * (w + sep), 0))
    return im


def icono_pin(d, cx, cy, r):
    d.ellipse([cx - r, cy - r * 1.15, cx + r, cy + r * 0.85], fill=AMARILLO)
    d.polygon([(cx - r * 0.72, cy + r * 0.35), (cx + r * 0.72, cy + r * 0.35),
               (cx, cy + r * 1.45)], fill=AMARILLO)
    d.ellipse([cx - r * 0.38, cy - r * 0.53, cx + r * 0.38, cy + r * 0.23], fill=AZUL)


def icono_reloj(d, cx, cy, r):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=AMARILLO)
    d.ellipse([cx - r * 0.66, cy - r * 0.66, cx + r * 0.66, cy + r * 0.66], outline=AZUL,
              width=max(3, int(r * 0.12)))
    d.line([(cx, cy), (cx, cy - r * 0.42)], fill=AZUL, width=max(3, int(r * 0.12)))
    d.line([(cx, cy), (cx + r * 0.3, cy + r * 0.18)], fill=AZUL, width=max(3, int(r * 0.12)))


def tarjeta_vidrio(base, f, x, y, w, k=1.0):
    """Tarjeta de vidrio esmerilado con 'Ya estamos atendiendo' y el contacto."""
    h = int(300 * k)
    caja = (int(x), int(y), int(x + w), int(y + h))
    fondo_ = base.crop(caja).filter(ImageFilter.GaussianBlur(24))
    m = Image.new("L", (w * SS, h * SS), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w * SS - 1, h * SS - 1], radius=40 * SS,
                                        fill=255)
    m = m.resize((w, h), Image.LANCZOS)
    sombra_ = Image.new("RGBA", (w + 120, h + 120), (0, 0, 0, 0))
    sm = Image.new("L", (w + 120, h + 120), 0)
    sm.paste(m.point(lambda v: v * 110 // 255), (60, 76))
    sombra_.putalpha(sm.filter(ImageFilter.GaussianBlur(22)))
    base.alpha_composite(sombra_, (caja[0] - 60, caja[1] - 60))
    base.paste(fondo_, caja[:2], m)
    capa = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    dc = ImageDraw.Draw(capa)
    dc.rounded_rectangle([0, 0, w * SS - 1, h * SS - 1], radius=40 * SS,
                         fill=(14, 18, 90, 150), outline=(255, 255, 255, 120), width=2 * SS)
    capa = capa.resize((w, h), Image.LANCZOS)
    d = ImageDraw.Draw(capa)
    x0 = int(40 * k)
    d.text((x0, int(52 * k)), "Visitanos en la oficina", font=f("Bold", int(44 * k)),
           fill=BLANCO, anchor="lm")
    fl = f("Medium", int(30 * k))
    for n, (icono, texto) in enumerate((("pin", DIRECCION), ("reloj", HORARIO))):
        cy = int((118 + n * 58) * k)
        r = int(19 * k)
        if icono == "pin":
            icono_pin(d, x0 + r, cy, r)
        else:
            icono_reloj(d, x0 + r, cy, r)
        d.text((x0 + 2 * r + int(18 * k), cy), texto, font=fl, fill=(225, 230, 255),
               anchor="lm")
    yl = int(214 * k)
    d.line([(x0, yl), (w - x0, yl)], fill=(255, 255, 255, 60), width=2)
    yc = int(256 * k)
    rw = int(19 * k)
    cx = x0 + rw
    d.ellipse([cx - rw, yc - rw, cx + rw, yc + rw], fill=VERDE_WA)
    d.arc([cx - rw * 0.5, yc - rw * 0.5, cx + rw * 0.5, yc + rw * 0.5], 100, 260, fill=BLANCO,
          width=max(3, int(rw * 0.22)))
    d.text((cx + rw + int(16 * k), yc), WHATSAPP, font=f("Bold", int(32 * k)), fill=BLANCO,
           anchor="lm")
    d.text((w - x0, yc), USUARIO, font=f("Medium", int(24 * k)), fill=(190, 200, 255),
           anchor="rm")
    base.alpha_composite(capa, caja[:2])


def nube(base, y_top, k=1.0):
    """Nube azul que sube desde abajo: borde superior hecho de 'bollos' redondeados, con
    una segunda nube más clara detrás para dar profundidad."""
    W, H = base.size
    capas = [((40, 60, 175), y_top - int(26 * k), 11), (AZUL, y_top, 7)]
    for color, y0, semilla in capas:
        rng = np.random.default_rng(semilla)
        c = Image.new("L", (W * SS, H * SS), 0)
        d = ImageDraw.Draw(c)
        d.rectangle([0, (y0 + 48 * k) * SS, W * SS, H * SS], fill=255)
        x = -40
        while x < W + 60:
            r = rng.uniform(48, 82) * k
            cy = y0 + 48 * k + rng.uniform(-12, 14) * k
            d.ellipse([(x - r) * SS, (cy - r) * SS, (x + r) * SS, (cy + r) * SS], fill=255)
            x += r * rng.uniform(1.15, 1.45)
        m = c.resize((W, H), Image.LANCZOS)
        sombra_ = Image.new("RGBA", (W, H), (0, 0, 30, 0))
        sombra_.putalpha(m.filter(ImageFilter.GaussianBlur(26)).point(lambda v: v * 90 // 255))
        base.alpha_composite(sombra_, (0, -10))
        capa = Image.new("RGBA", (W, H), color + (255,))
        capa.putalpha(m)
        base.alpha_composite(capa)


def info_nube(base, f, x, y, k=1.0):
    """'Visitanos en la oficina', dirección, horario y WhatsApp, en blanco sobre la nube."""
    W, _ = base.size
    capa = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    d.text((x, y), "Visitanos en la oficina", font=f("Bold", int(42 * k)), fill=BLANCO,
           anchor="lm")
    fl = f("Medium", int(29 * k))
    for n, (icono, texto) in enumerate((("pin", DIRECCION), ("reloj", HORARIO))):
        cy = y + int((60 + n * 48) * k)
        r = int(19 * k)
        (icono_pin if icono == "pin" else icono_reloj)(d, x + r, cy, r)
        d.text((x + 2 * r + int(18 * k), cy), texto, font=fl, fill=(225, 230, 255), anchor="lm")
    yc = y + int(166 * k)
    rw = int(19 * k)
    cx = x + rw
    d.ellipse([cx - rw, yc - rw, cx + rw, yc + rw], fill=VERDE_WA)
    d.arc([cx - rw * 0.5, yc - rw * 0.5, cx + rw * 0.5, yc + rw * 0.5], 100, 260, fill=BLANCO,
          width=max(3, int(rw * 0.22)))
    d.text((cx + rw + int(16 * k), yc), WHATSAPP, font=f("Bold", int(32 * k)), fill=BLANCO,
           anchor="lm")
    d.text((W - x, yc), USUARIO, font=f("Medium", int(24 * k)), fill=(190, 200, 255),
           anchor="rm")
    base.alpha_composite(capa)


# ----------------------------------------------------------------- armado
def armar(foto, f, logo_p, W, H, cielo, y_titulo, y_tarjeta, salida, k=1.0, y_logo=56):
    img = fondo(foto, W, H, cielo)
    m = 70
    t = titulo(f, int(96 * k))
    r = 165 * k
    # el arco (que se abre hacia la izquierda) queda siempre a la derecha del título
    cx = max(W - 95 * k, m + t.width + 24 + r * 1.22)
    detalles_cielo(img, cx, y_titulo + 120 * k, r)
    # sin el logo de FRAMI (pedido de la clienta)
    pegar(img, t, m, y_titulo, radio=18, alfa=190)
    nube(img, y_tarjeta, k)
    info_nube(img, f, m, y_tarjeta + int(92 * k), k)
    img.convert("RGB").save(salida)


def main():
    foto_p, logo_p, fuentes, salida = sys.argv[1:5]
    f = F(fuentes)
    foto = retocar(Image.open(foto_p).convert("RGB"))
    armar(foto, f, logo_p, 1080, 1350, 170, 70, 1052,
          f"{salida}/frami_semana_oficina_feed.png")
    armar(foto, f, logo_p, 1080, 1920, 400, 265, 1392,
          f"{salida}/frami_semana_oficina_historia.png", k=1.08, y_logo=250)


if __name__ == "__main__":
    main()
