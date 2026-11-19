"""Flyer "Tus próximos encuentros tienen un nuevo lugar" de Rabbit Food & Drinks (concepto "próximamente", sin repetir el
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
# (texto, color, tamaño relativo): "NUEVO LUGAR" va en rojo y más grande
TITULO = [("TUS PRÓXIMOS", BLANCO, 0.72), ("ENCUENTROS", BLANCO, 1.0),
          ("TIENEN UN", BLANCO, 0.72), ("NUEVO LUGAR", ROJO, 1.0)]
STICKER = "FALTA POCO"
PIE = "Activá las notificaciones y enterate primero"
PIE_HISTORIA = "No te pierdas nuestras historias y enterate primero"


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


def titulo(f, tam, ancho_max=980):
    while True:
        lineas = [(t, c, f("Anton", int(tam * r))) for t, c, r in TITULO]
        if max(fn.getlength(t) for t, _, fn in lineas) <= ancho_max - 40 or tam < 60:
            break
        tam -= 4
    alturas = [int(fn.size * 1.04) for _, _, fn in lineas]
    w = ancho_max
    im = Image.new("RGBA", (w, sum(alturas) + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    y = 20
    for (t, c, fn), lh in zip(lineas, alturas):
        d.text((w / 2, y + lh / 2), t, font=fn, fill=c, anchor="mm")
        y += lh
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


def sello(f, texto, tam=150, rot=-9, semilla=7):
    """Sello de goma: texto Anton dentro de doble borde, con la tinta gastada."""
    fn = f("Anton", tam)
    tw = fn.getlength(texto)
    pad_x, pad_y, g = 70, 44, 10
    w, h = int(tw + 2 * pad_x), int(tam * 1.12 + 2 * pad_y)
    s = 2
    m = Image.new("L", (w * s, h * s), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([0, 0, w * s - 1, h * s - 1], radius=26 * s, outline=255, width=g * s)
    d.rounded_rectangle([(g + 12) * s, (g + 12) * s, (w - g - 12) * s, (h - g - 12) * s],
                        radius=16 * s, outline=255, width=4 * s)
    d.text((w * s / 2, h * s / 2 - 8 * s), texto, font=f("Anton", tam * s), fill=255,
           anchor="mm")
    m = m.resize((w, h), Image.LANCZOS)
    # desgaste: huecos irregulares + grano fino, como tinta que no cargó pareja
    rng = np.random.default_rng(semilla)
    ruido = Image.fromarray((rng.random((h // 3 + 1, w // 3 + 1)) * 255).astype(np.uint8))
    ruido = ruido.resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(2.2))
    huecos = (np.asarray(ruido, np.float32) > 168).astype(np.float32)
    grano = (rng.random((h, w)) > 0.12).astype(np.float32)
    a = np.asarray(m, np.float32) / 255 * (1 - huecos * 0.8) * (0.82 + 0.18 * grano)
    tinta = np.zeros((h, w, 4), np.uint8)
    tinta[..., :3] = ROJO
    tinta[..., 3] = (np.clip(a, 0, 1) * 245).astype(np.uint8)
    im = Image.fromarray(tinta, "RGBA").rotate(rot, resample=Image.BICUBIC, expand=True)
    return sombra(im, 10, 120, (0, 6))


def sombra_local(img, cx, cy, rx, ry, alfa=150):
    """Oscurece suave una zona elíptica (para que el sello rojo resalte sobre el cartel)."""
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=alfa)
    m = m.filter(ImageFilter.GaussianBlur(min(rx, ry) * 0.45))
    capa = Image.new("RGBA", img.size, OSCURO + (255,))
    capa.putalpha(m)
    img.alpha_composite(capa)


def desenfocar(foto, radio):
    """Desenfoque suave: se reconoce el cartel pero no compite con el texto."""
    return ImageEnhance.Brightness(foto.filter(ImageFilter.GaussianBlur(radio))).enhance(0.8)


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
    img = recortar(desenfocar(foto, 9), W, H, cx=0.5, cy=0.52)
    degradado(img, 0, 520, 150, arriba=True)
    degradado(img, 860, 1180, 235)
    centrar(img, titulo(f, 132), W / 2, 285)
    sombra_local(img, W / 2, 715, 520, 230)
    centrar(img, sello(f, STICKER, 150, -9), W / 2, 715)   # sobre el cartel
    centrar(img, marca(f, emblema), W / 2, 1150)
    d = ImageDraw.Draw(img)
    d.text((W / 2, 1272), PIE, font=f("Medium", 30), fill=(205, 205, 212), anchor="mm")
    img.convert("RGB").save(salida)


def historia(foto, f, emblema, salida):
    W, H = 1080, 1920
    # la foto a pantalla completa (centrada en el cartel), desenfocada
    img = recortar(desenfocar(foto, 10), W, H, cx=0.55, cy=0.5)
    degradado(img, 0, 820, 170, arriba=True)
    degradado(img, 1250, 1800, 235)
    centrar(img, titulo(f, 140), W / 2, 520)
    sombra_local(img, W / 2, 1060, 520, 230)
    centrar(img, sello(f, STICKER, 150, -9), W / 2, 1060)
    centrar(img, marca(f, emblema), W / 2, 1600)
    d = ImageDraw.Draw(img)
    d.text((W / 2, 1712), PIE_HISTORIA, font=f("Medium", 32), fill=(215, 215, 222),
           anchor="mm")
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
