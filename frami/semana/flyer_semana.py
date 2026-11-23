"""Flyer de comienzo de semana de FRAMI: "¡Arrancamos la semana!" + "Ya estamos atendiendo".

Fondo azul de marca con un sol amarillo saliendo detrás de la asesora (foto recortada),
logo, píldora roja, título, bajada y contacto. Genera feed (1080x1350) e historia /
estado de WhatsApp (1080x1920).

Uso: python3 flyer_semana.py <asesora_recortada.png> <logo.png> <dir_fuentes> <dir_salida>
"""
import math
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

AZUL = (8, 8, 96)
AZUL_2 = (24, 34, 150)
ROJO = (232, 0, 61)
AMARILLO = (245, 196, 0)
BLANCO = (255, 255, 255)
CELESTE = (170, 190, 255)

PILDORA = "YA ESTAMOS ATENDIENDO"
TITULO = [("¡Arrancamos", BLANCO), ("la semana!", AMARILLO)]
BAJADA = ["Comenzá la semana", "asegurando lo que", "más te importa."]
WHATSAPP = "3764 886646"
USUARIO = "@frami.productoresasesores"
SS = 2


class F:
    def __init__(self, d):
        self.d, self.c = d, {}

    def __call__(self, peso, tam):
        k = (peso, tam)
        if k not in self.c:
            self.c[k] = ImageFont.truetype(f"{self.d}/Poppins-{peso}.ttf", tam)
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


def fondo(W, H, sol):
    """Degradado azul, brillo rojo suave, grilla de puntos y sol amarillo con halo."""
    y = np.linspace(0, 1, H)[:, None, None]
    base = np.broadcast_to(np.array(AZUL, np.float32) * (1 - y) +
                           np.array(AZUL_2, np.float32) * y, (H, W, 3)).copy()
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    for cx, cy, r, col, a in [(W * 0.1, H * 0.12, 520, (60, 90, 255), 0.35),
                              (W * 0.95, H * 0.55, 480, ROJO, 0.22)]:
        g = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / r ** 2))[..., None] * a
        base = base * (1 - g) + np.array(col, np.float32) * g
    scx, scy, sr = sol
    # halo cálido alrededor del sol
    g = np.exp(-(((xx - scx) ** 2 + (yy - scy) ** 2) / (sr * 1.7) ** 2))[..., None] * 0.45
    base = base * (1 - g) + np.array((255, 170, 40), np.float32) * g
    img = Image.fromarray(base.clip(0, 255).astype(np.uint8)).convert("RGBA")

    c = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    for gy in range(int(H * 0.06), int(H * 0.06) + 7 * 42, 42):      # puntos arriba a la der.
        for gx in range(W - 330, W - 40, 42):
            d.ellipse([(gx - 4) * SS, (gy - 4) * SS, (gx + 4) * SS, (gy + 4) * SS],
                      fill=(255, 255, 255, 45))
    # rayos del sol
    for i in range(9):                     # rayos solo hacia arriba a la derecha
        a = math.radians(250 + i * (110 / 8))
        r0, r1 = sr * 1.12, sr * 1.42
        d.line([((scx + r0 * math.cos(a)) * SS, (scy + r0 * math.sin(a)) * SS),
                ((scx + r1 * math.cos(a)) * SS, (scy + r1 * math.sin(a)) * SS)],
               fill=AMARILLO + (150,), width=10 * SS)
    d.ellipse([(scx - sr) * SS, (scy - sr) * SS, (scx + sr) * SS, (scy + sr) * SS],
              fill=AMARILLO + (255,))
    # anillo fino rojo punteado
    r3 = sr * 1.6
    for i in range(0, 104, 6):             # arco punteado solo a la derecha
        a = math.radians(258 + i)
        x, y_ = scx + r3 * math.cos(a), scy + r3 * math.sin(a)
        d.ellipse([(x - 6) * SS, (y_ - 6) * SS, (x + 6) * SS, (y_ + 6) * SS], fill=ROJO)
    img.alpha_composite(c.resize((W, H), Image.LANCZOS))
    return img


def pildora(f, tam=28):
    fn = f("Bold", tam)
    w, h = int(fn.getlength(PILDORA)) + 96, int(tam * 2.2)
    im = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w * SS - 1, h * SS - 1], radius=h * SS // 2, fill=ROJO)
    r = h * 0.17
    d.ellipse([(30 - r * 1.8) * SS, (h / 2 - r * 1.8) * SS, (30 + r * 1.8) * SS,
               (h / 2 + r * 1.8) * SS], fill=(255, 255, 255, 70))      # punto "en vivo"
    d.ellipse([(30 - r) * SS, (h / 2 - r) * SS, (30 + r) * SS, (h / 2 + r) * SS], fill=BLANCO)
    im = im.resize((w, h), Image.LANCZOS)
    ImageDraw.Draw(im).text((58, h / 2), PILDORA, font=fn, fill=BLANCO, anchor="lm")
    return im


def titulo(f, tam):
    fn = f("ExtraBold", tam)
    lh = int(tam * 1.08)
    w = int(max(fn.getlength(t) for t, _ in TITULO)) + 20
    im = Image.new("RGBA", (w, lh * len(TITULO) + 30), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, (t, c) in enumerate(TITULO):
        d.text((0, 10 + lh * i + lh / 2), t, font=fn, fill=c, anchor="lm")
    return im.crop(im.getbbox())


def bajada(f, tam):
    fn = f("Medium", tam)
    lh = int(tam * 1.4)
    w = int(max(fn.getlength(t) for t in BAJADA)) + 10
    im = Image.new("RGBA", (w, lh * len(BAJADA)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, t in enumerate(BAJADA):
        d.text((0, lh * i + lh / 2), t, font=fn, fill=(225, 230, 255), anchor="lm")
    return im


def contacto(f, tam=36):
    fn = f("Bold", tam)
    fu = f("Medium", int(tam * 0.7))
    w = int(max(fn.getlength(WHATSAPP) + 70, fu.getlength(USUARIO))) + 10
    h = int(tam * 2.5)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r, cx, cy = 21, 22, tam * 0.62
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(37, 211, 102))
    d.polygon([(cx - r * 0.85, cy + r * 1.05), (cx - r * 0.5, cy + r * 0.4),
               (cx - r * 0.1, cy + r * 0.8)], fill=(37, 211, 102))
    d.arc([cx - r * 0.5, cy - r * 0.5, cx + r * 0.5, cy + r * 0.5], 100, 260, fill=BLANCO,
          width=5)
    d.text((62, cy), WHATSAPP, font=fn, fill=BLANCO, anchor="lm")
    d.text((0, tam * 1.8), USUARIO, font=fu, fill=CELESTE, anchor="lm")
    return im


def persona(path, alto):
    p = Image.open(path).convert("RGBA")
    p = p.crop(p.getbbox())
    return p.resize((round(p.width * alto / p.height), alto), Image.LANCZOS)


def armar(f, foto_p, logo_p, W, H, salida, k=1.0, y0=0):
    """y0: desplazamiento vertical para la historia (zona segura de Instagram)."""
    alto_p = int(H * (0.56 if H < 1600 else 0.52))
    p = persona(foto_p, alto_p)
    px = W - p.width + int(p.width * 0.14)
    py = H - p.height
    sol = (px + p.width * 0.47, py + p.height * 0.33, p.width * 0.43)
    img = fondo(W, H, sol)
    # sombra suave detrás de la persona y la persona
    halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    m = p.getchannel("A").filter(ImageFilter.GaussianBlur(24)).point(lambda v: v * 120 // 255)
    halo.paste(Image.new("RGBA", p.size, (0, 0, 40, 255)), (px + 14, py + 18), m)
    img.alpha_composite(halo)
    img.alpha_composite(p, (px, py))

    m = 70
    lg = Image.open(logo_p).convert("RGBA")
    lw = int(118 * k)
    lg = lg.resize((lw, round(lg.height * lw / lg.width)), Image.LANCZOS)
    pegar(img, lg, m, 56 + y0, radio=10, alfa=110)
    y = 56 + y0 + lg.height + int(54 * k)
    pl = pildora(f, int(28 * k))
    pegar(img, pl, m, y, radio=10, alfa=120)
    y += pl.height + int(34 * k)
    t = titulo(f, int(104 * k))
    pegar(img, t, m, y, radio=18, alfa=170)
    y += t.height + int(34 * k)
    # línea amarilla corta
    ImageDraw.Draw(img).rounded_rectangle([m, y, m + 110, y + 8], radius=4, fill=AMARILLO)
    y += int(34 * k)
    b = bajada(f, int(38 * k))
    pegar(img, b, m, y, radio=10, alfa=140)
    c = contacto(f, int(36 * k))
    pegar(img, c, m, H - (y0 // 2 if y0 else 0) - int(170 * k), radio=10, alfa=140)
    img.convert("RGB").save(salida)


def main():
    foto_p, logo_p, fuentes, salida = sys.argv[1:5]
    f = F(fuentes)
    armar(f, foto_p, logo_p, 1080, 1350, f"{salida}/frami_semana_feed.png")
    armar(f, foto_p, logo_p, 1080, 1920, f"{salida}/frami_semana_historia.png", k=1.12, y0=200)


if __name__ == "__main__":
    main()
