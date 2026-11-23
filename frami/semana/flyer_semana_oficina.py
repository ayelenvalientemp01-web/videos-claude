"""Variante del flyer de comienzo de semana con la foto de la oficina de FRAMI.

Arriba, sobre el azul de marca: píldora "Ya estamos atendiendo", título y bajada.
Abajo: la foto de la oficina con corte diagonal y filete amarillo, y el contacto.
La foto se retoca: se borra el cartel "Cerrado" de la puerta y se deja afuera del encuadre
la bandera de Rapipago.

Uso: python3 flyer_semana_oficina.py <foto_oficina.jpg> <logo.png> <dir_fuentes> <dir_salida>
"""
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance

from flyer_semana import (AMARILLO, AZUL, AZUL_2, SS, F, bajada, contacto, pegar, pildora,
                          titulo)

CARTEL_CERRADO = (724, 772, 782, 816)   # caja del cartel "Cerrado" en la foto original
ANCHO_UTIL = 1125                        # a la derecha de esto está la bandera de Rapipago


def retocar(foto):
    """Borra el cartel 'Cerrado': cada fila se rellena interpolando entre los píxeles de
    los costados (el reflejo del vidrio son franjas horizontales)."""
    a = np.asarray(foto, np.float32).copy()
    x0, y0, x1, y1 = CARTEL_CERRADO
    izq = a[y0:y1, x0 - 3:x0].mean(axis=1)
    der = a[y0:y1, x1:x1 + 3].mean(axis=1)
    k = np.linspace(0, 1, x1 - x0)[None, :, None]
    relleno = izq[:, None] * (1 - k) + der[:, None] * k
    ruido = np.random.default_rng(3).normal(0, 2.0, relleno.shape)   # grano para que no quede liso
    a[y0:y1, x0:x1] = relleno + ruido
    foto = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    foto = ImageEnhance.Contrast(foto).enhance(1.05)
    return ImageEnhance.Color(foto).enhance(1.06)


def recorte(foto, w, h, y_centro):
    """Recorte w:h dentro del ancho útil (sin la bandera), centrado en y_centro."""
    esc = w / ANCHO_UTIL
    alto = h / esc
    y0 = int(min(max(y_centro - alto / 2, 0), foto.height - alto))
    c = foto.crop((0, y0, ANCHO_UTIL, int(y0 + alto)))
    return c.resize((w, h), Image.LANCZOS)


def armar(foto, f, logo_p, W, H, y_foto, alto_foto, y_centro, salida, k=1.0, y0=0):
    y = np.linspace(0, 1, H)[:, None, None]
    base = np.broadcast_to(np.array(AZUL, np.float32) * (1 - y) +
                           np.array(AZUL_2, np.float32) * y, (H, W, 3))
    img = Image.fromarray(base.astype(np.uint8)).convert("RGBA")

    # puntos sutiles arriba a la derecha
    c = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    for gy in range(y0 + 70, y0 + 70 + 6 * 42, 42):
        for gx in range(W - 300, W - 40, 42):
            d.ellipse([(gx - 4) * SS, (gy - 4) * SS, (gx + 4) * SS, (gy + 4) * SS],
                      fill=(255, 255, 255, 45))
    img.alpha_composite(c.resize((W, H), Image.LANCZOS))

    # foto con borde superior en diagonal + filete amarillo
    ft = recorte(foto, W, alto_foto, y_centro).convert("RGBA")
    caida = 120
    m = Image.new("L", (W * SS, alto_foto * SS), 0)
    ImageDraw.Draw(m).polygon([(0, caida * SS), (W * SS, 0), (W * SS, alto_foto * SS),
                               (0, alto_foto * SS)], fill=255)
    ft.putalpha(m.resize((W, alto_foto), Image.LANCZOS))
    img.alpha_composite(ft, (0, y_foto))
    c = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    ImageDraw.Draw(c).line([(0, (y_foto + caida - 22) * SS), (W * SS, (y_foto - 22) * SS)],
                           fill=AMARILLO + (255,), width=12 * SS)
    img.alpha_composite(c.resize((W, H), Image.LANCZOS))
    # degradado azul abajo para el contacto
    g = np.zeros((H, W, 4), np.uint8)
    g[..., :3] = AZUL
    yy = np.arange(H, dtype=np.float32)
    ini = H - (y0 // 2) - int(420 * k)
    g[..., 3] = (np.clip((yy - ini) / (330 * k), 0, 1) ** 1.2 * 225).astype(np.uint8)[:, None]
    img.alpha_composite(Image.fromarray(g, "RGBA"))

    m_ = 70
    lg = Image.open(logo_p).convert("RGBA")
    lw = int(118 * k)
    lg = lg.resize((lw, round(lg.height * lw / lg.width)), Image.LANCZOS)
    pegar(img, lg, W - m_ - lw, 56 + y0, radio=10, alfa=110)
    yy_ = 70 + y0
    pl = pildora(f, int(28 * k))
    pegar(img, pl, m_, yy_, radio=10, alfa=120)
    yy_ += pl.height + int(30 * k)
    t = titulo(f, int(100 * k))
    pegar(img, t, m_, yy_, radio=18, alfa=170)
    yy_ += t.height + int(28 * k)
    ImageDraw.Draw(img).rounded_rectangle([m_, yy_, m_ + 110, yy_ + 8], radius=4, fill=AMARILLO)
    yy_ += int(30 * k)
    pegar(img, bajada(f, int(36 * k)), m_, yy_, radio=10, alfa=140)
    ct = contacto(f, int(36 * k))
    pegar(img, ct, m_, H - (y0 // 2) - int(160 * k), radio=10, alfa=160)
    img.convert("RGB").save(salida)


def main():
    foto_p, logo_p, fuentes, salida = sys.argv[1:5]
    f = F(fuentes)
    foto = retocar(Image.open(foto_p).convert("RGB"))
    armar(foto, f, logo_p, 1080, 1350, 560, 790, 900,
          f"{salida}/frami_semana_oficina_feed.png")
    armar(foto, f, logo_p, 1080, 1920, 860, 1060, 950,
          f"{salida}/frami_semana_oficina_historia.png", k=1.1, y0=200)


if __name__ == "__main__":
    main()
