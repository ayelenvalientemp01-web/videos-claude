"""Portada del Reel del mini golf de Rabbit (1080x1920): foto del hoyo 1, "MINI GOLF" en
el cartel rojo de la marca y el logo abajo. Lo importante queda dentro del recorte 3:4 de la
grilla de Instagram (y entre 240 y 1680).

Uso: python3 portada_minigolf.py <foto.jpg> <emblema.png> <dir_fuentes> <salida.png>
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                                "proximamente"))
from flyer_proximamente import (BLANCO, F, ROJO, centrar, degradado, marca,  # noqa: E402
                                recortar, sombra)

TITULO = "MINI GOLF"


def cartel(f, texto, tam=210, rot=-3):
    """Cartel rojo con filete blanco y texto Anton (estilo de las piezas de Rabbit)."""
    fn = f("Anton", tam)
    w, h = int(fn.getlength(texto)) + 130, int(tam * 1.1) + 80
    s = 2
    im = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w * s - 1, h * s - 1], radius=26 * s, fill=ROJO)
    d.rounded_rectangle([14 * s, 14 * s, (w - 14) * s, (h - 14) * s], radius=16 * s,
                        outline=BLANCO, width=6 * s)
    im = im.resize((w, h), Image.LANCZOS)
    ImageDraw.Draw(im).text((w / 2, h / 2 - 8), texto, font=fn, fill=BLANCO, anchor="mm")
    return sombra(im.rotate(rot, resample=Image.BICUBIC, expand=True), 20, 200, (0, 14))


def main():
    foto_p, emblema_p, fuentes, salida = sys.argv[1:5]
    f = F(fuentes)
    foto = Image.open(foto_p).convert("RGB")
    foto = ImageEnhance.Contrast(foto).enhance(1.06)
    W, H = 1080, 1920
    # fondo: la misma foto desenfocada y oscura; encima la foto a lo ancho, bajada para que
    # la bandera con el "1" quede entera debajo del título
    img = recortar(foto, W, H).filter(ImageFilter.GaussianBlur(30))
    img = Image.blend(img, Image.new("RGBA", (W, H), (14, 14, 16, 255)), 0.6)
    fh = int(foto.height * W / foto.width)
    y_foto = H - fh
    ft = foto.resize((W, fh), Image.LANCZOS).convert("RGBA")
    a = np.clip(np.arange(fh, dtype=np.float32) / 220, 0, 1) ** 1.5   # borde superior suave
    ft.putalpha(Image.fromarray((np.tile(a[:, None], (1, W)) * 255).astype(np.uint8)))
    img.alpha_composite(ft, (0, y_foto))
    degradado(img, 1380, 1820, 210)               # abajo para el logo
    centrar(img, cartel(f, TITULO, 200), W / 2, 418)
    centrar(img, marca(f, Image.open(emblema_p)), W / 2, 1560)
    img.convert("RGB").save(salida)


if __name__ == "__main__":
    main()
