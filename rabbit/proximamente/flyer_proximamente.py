"""Flyer "¿Estás listo?" de Rabbit Food & Drinks (concepto "próximamente", sin repetir el
"muy pronto" ya publicado). Fondo: foto de la entrada de noche.

Uso: python3 flyer_proximamente.py <foto_entrada.jpg> <emblema.png> <dir_fuentes> <dir_salida>
Genera rabbit_proximamente_feed.png (1080x1350) y rabbit_proximamente_historia.png
(1080x1920).
"""
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROJO = (255, 18, 18)
VERDE = (0, 200, 70)
CREMA = (242, 232, 212)
BLANCO = (255, 255, 255)
OSCURO = (14, 14, 16)

KICKER = "SE VIENE ALGO NUEVO"
TITULO = [("¿ESTÁS", BLANCO), ("LISTO?", ROJO)]
STICKER = "FALTA POCO"
PIE = "Activá las notificaciones y enterate primero"


class F:
    def __init__(self, d):
        self.d = d

    def __call__(self, nombre, tam):
        archivo = "Anton-Regular.ttf" if nombre == "Anton" else f"Poppins-{nombre}.ttf"
        return ImageFont.truetype(f"{self.d}/{archivo}", tam)


def sombra(capa, radio=16, alfa=170, offset=(0, 12)):
    pad = radio * 3
    out = Image.new("RGBA", (capa.width + pad * 2, capa.height + pad * 2), (0, 0, 0, 0))
    s = Image.new("RGBA", capa.size, (0, 0, 0, 0))
    s.putalpha(capa.getchannel("A").point(lambda v: v * alfa // 255))
    out.alpha_composite(s, (pad + offset[0], pad + offset[1]))
    out = out.filter(ImageFilter.GaussianBlur(radio))
    out.alpha_composite(capa, (pad, pad))
    return out


def centrar(base, im, cx, cy):
    base.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


def degradado(base, y0, y1, alfa_max, arriba=False):
    """Oscurece hacia abajo (o hacia arriba) entre y0 e y1."""
    w, h = base.size
    g = np.zeros((h, w, 4), np.uint8)
    g[..., :3] = OSCURO
    y = np.arange(h, dtype=np.float32)
    k = np.clip((y - y0) / max(1, y1 - y0), 0, 1)
    if arriba:
        k = 1 - k
    g[..., 3] = (k ** 1.4 * alfa_max).astype(np.uint8)[:, None]
    base.alpha_composite(Image.fromarray(g, "RGBA"))


def kicker(f, tam=34):
    fn = f("Bold", tam)
    tw = fn.getlength(KICKER)
    w, h = int(tw + 2 * 110), int(tam * 1.6)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, h / 2 - 4, 80, h / 2 + 4], radius=4, fill=VERDE)
    d.rounded_rectangle([w - 80, h / 2 - 4, w, h / 2 + 4], radius=4, fill=ROJO)
    d.text((w / 2, h / 2), KICKER, font=fn, fill=BLANCO, anchor="mm")
    return sombra(im, 8, 200, (0, 3))


def titulo(f, tam):
    fn = f("Anton", tam)
    lh = int(tam * 1.02)
    w = int(max(fn.getlength(t) for t, _ in TITULO)) + 40
    im = Image.new("RGBA", (w, lh * len(TITULO) + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, (t, c) in enumerate(TITULO):
        d.text((w / 2, 20 + lh * i + lh / 2), t, font=fn, fill=c, anchor="mm")
    return sombra(im, 18, 220, (0, 10))


def sticker(f, tam=96, rot=-4):
    """Cartel rojo con borde blanco y texto Anton (estilo 'CONVOCATORIA CERRADA')."""
    fn = f("Anton", tam)
    w, h = int(fn.getlength(STICKER)) + 110, int(tam * 1.08) + 70
    s = 2
    im = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w * s - 1, h * s - 1], radius=22 * s, fill=ROJO)
    d.rounded_rectangle([12 * s, 12 * s, (w - 12) * s, (h - 12) * s], radius=14 * s,
                        outline=BLANCO, width=5 * s)
    im = im.resize((w, h), Image.LANCZOS)
    ImageDraw.Draw(im).text((w / 2, h / 2 - 6), STICKER, font=fn, fill=BLANCO, anchor="mm")
    return sombra(im.rotate(rot, resample=Image.BICUBIC, expand=True), 16, 190, (0, 12))


def insignia(emblema, d=150):
    s = 3
    e = emblema.convert("RGB")
    lado = min(e.size)
    e = e.crop(((e.width - lado) // 2, e.height - lado, (e.width + lado) // 2, e.height))
    e = e.resize((int(d * s * 0.96),) * 2, Image.LANCZOS)
    fondo = Image.new("RGB", (d * s, d * s), (44, 40, 40))
    fondo.paste(e, ((d * s - e.width) // 2, (d * s - e.height) // 2))
    m = Image.new("L", (d * s, d * s), 0)
    ImageDraw.Draw(m).ellipse([0, 0, d * s - 1, d * s - 1], fill=255)
    im = Image.new("RGBA", (d * s, d * s), (0, 0, 0, 0))
    im.paste(fondo, (0, 0), m)
    ImageDraw.Draw(im).ellipse([0, 0, d * s - 1, d * s - 1], outline=CREMA, width=7 * s)
    return im.resize((d, d), Image.LANCZOS)


def marca(f, emblema):
    """Insignia + 'Rabbit' + 'FOOD & DRINKS - EVENTOS' (como el cartel)."""
    ins = insignia(emblema, 130)
    fr = f("SemiBold", 96)
    fs = f("Bold", 24)
    sub = "FOOD & DRINKS - EVENTOS"
    tw = max(fr.getlength("Rabbit"), fs.getlength(sub) + 120)
    w, h = int(130 + 28 + tw), 140
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    im.alpha_composite(ins, (0, 5))
    d = ImageDraw.Draw(im)
    x = 158
    d.text((x, 58), "Rabbit", font=fr, fill=ROJO, anchor="lm")
    y = 112
    d.rounded_rectangle([x, y - 3, x + 44, y + 3], radius=3, fill=VERDE)
    d.text((x + 56, y), sub, font=fs, fill=BLANCO, anchor="lm")
    xe = x + 56 + fs.getlength(sub) + 12
    d.rounded_rectangle([xe, y - 3, xe + 44, y + 3], radius=3, fill=ROJO)
    return sombra(im, 10, 200, (0, 4))


def recortar(foto, w, h, cx=0.5, cy=0.5):
    """Recorte que cubre w x h (como object-fit: cover) centrado en (cx, cy)."""
    esc = max(w / foto.width, h / foto.height)
    im = foto.resize((int(foto.width * esc + 0.5), int(foto.height * esc + 0.5)),
                     Image.LANCZOS)
    x0 = int(min(max(cx * im.width - w / 2, 0), im.width - w))
    y0 = int(min(max(cy * im.height - h / 2, 0), im.height - h))
    return im.crop((x0, y0, x0 + w, y0 + h)).convert("RGBA")


def preparar(foto):
    foto = ImageEnhance.Contrast(foto).enhance(1.08)
    return ImageEnhance.Color(foto).enhance(1.08)


def feed(foto, f, emblema, salida):
    W, H = 1080, 1350
    img = recortar(foto, W, H, cx=0.5, cy=0.52)
    degradado(img, 0, 520, 150, arriba=True)
    degradado(img, 760, 1150, 235)
    centrar(img, kicker(f), W / 2, 112)
    centrar(img, titulo(f, 172), W / 2, 330)
    centrar(img, sticker(f, 92, -4), W / 2 + 150, 935)
    centrar(img, marca(f, emblema), W / 2, 1150)
    d = ImageDraw.Draw(img)
    d.text((W / 2, 1272), PIE, font=f("Medium", 30), fill=(205, 205, 212), anchor="mm")
    img.convert("RGB").save(salida)


def historia(foto, f, emblema, salida):
    W, H = 1080, 1920
    # fondo: la misma foto desenfocada y oscura
    img = recortar(foto, W, H).filter(ImageFilter.GaussianBlur(28))
    img = Image.blend(img, Image.new("RGBA", (W, H), OSCURO + (255,)), 0.55)
    # la foto completa, con bordes redondeados y filete rojo
    fw = W - 80
    fh = int(foto.height * fw / foto.width)
    ft = foto.resize((fw, fh), Image.LANCZOS).convert("RGBA")
    m = Image.new("L", (fw * 2, fh * 2), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, fw * 2 - 1, fh * 2 - 1], radius=56, fill=255)
    ft.putalpha(m.resize((fw, fh), Image.LANCZOS))
    marco = Image.new("RGBA", (fw + 12, fh + 12), (0, 0, 0, 0))
    ImageDraw.Draw(marco).rounded_rectangle([0, 0, fw + 11, fh + 11], radius=34, fill=ROJO)
    marco.alpha_composite(ft, (6, 6))
    y_foto = 735
    centrar(img, sombra(marco, 22, 200, (0, 16)), W / 2, y_foto + fh / 2)
    centrar(img, kicker(f, 34), W / 2, 265)
    centrar(img, titulo(f, 170), W / 2, 505)
    centrar(img, sticker(f, 92, -4), W / 2 + 170, y_foto + fh - 60)
    centrar(img, marca(f, emblema), W / 2, 1620)
    img.convert("RGB").save(salida)


def main():
    foto_p, emblema_p, fuentes, salida = sys.argv[1:5]
    foto = preparar(Image.open(foto_p).convert("RGB"))
    emblema = Image.open(emblema_p)
    f = F(fuentes)
    feed(foto, f, emblema, f"{salida}/rabbit_proximamente_feed.png")
    historia(foto, f, emblema, f"{salida}/rabbit_proximamente_historia.png")


if __name__ == "__main__":
    main()
