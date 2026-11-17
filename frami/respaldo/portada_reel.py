"""Portada del Reel "Respaldo" con diseño propio (distinto al del Reel anterior), con la paleta
de FRAMI: persona recortada sobre azul, "RESPALDO" gigante detrás de ella, título en
etiquetas inclinadas tipo sticker y línea de pulso debajo.

Uso: python3 portada_reel.py <foto_recortada.png> <logo.png> <dir_fonts> <salida.png>
La foto recortada es un cuadro del video (1080x1920) con el fondo quitado
(rembg, u2net_human_seg). Lo importante queda dentro del recorte 3:4 de la grilla
(y entre 240 y 1680).
"""
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
SS = 2

ROJO = (232, 0, 61)
AMARILLO = (245, 196, 0)
AZUL = (8, 8, 96)
AZUL_2 = (24, 34, 150)
BLANCO = (255, 255, 255)

PALABRA_FONDO = "RESPALDO"
ETIQUETA_SUP = "SEGURO DE VIDA + ENFERMEDADES GRAVES"
LINEAS = [  # (texto, fondo, color de texto, inclinación en grados)
    ("¿QUIÉN PAGA", ROJO, BLANCO, -4),
    ("LAS CUENTAS", AMARILLO, AZUL, 2.5),
]
REMATE = "si te enfermás?"


def fuente(d, peso, tam):
    return ImageFont.truetype(f"{d}/Poppins-{peso}.ttf", tam)


def sombra(im, radio=16, alfa=120, offset=(0, 12)):
    s = Image.new("RGBA", im.size, (0, 0, 0, 0))
    s.putalpha(im.getchannel("A").point(lambda v: v * alfa // 255)
               .filter(ImageFilter.GaussianBlur(radio)))
    out = Image.new("RGBA", (im.width + 80, im.height + 80), (0, 0, 0, 0))
    out.alpha_composite(s, (40 + offset[0], 40 + offset[1]))
    out.alpha_composite(im, (40, 40))
    return out


def fondo():
    """Degradado azul con dos brillos suaves (rojo abajo a la derecha, azul arriba)."""
    y = np.linspace(0, 1, H)[:, None, None]
    base = np.broadcast_to(np.array(AZUL, np.float32) * (1 - y) +
                           np.array(AZUL_2, np.float32) * y, (H, W, 3)).copy()
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    for cx, cy, r, col, a in [(980, 1500, 650, ROJO, 0.45), (120, 300, 600, (60, 90, 255), 0.4)]:
        g = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / r ** 2))[..., None] * a
        base = base * (1 - g) + np.array(col, np.float32) * g
    return Image.fromarray(base.clip(0, 255).astype(np.uint8)).convert("RGBA")


def etiqueta(texto, f, bg, fg, ang, pad=(46, 22)):
    w = int(f.getlength(texto)) + pad[0] * 2
    asc, desc = f.getmetrics()
    h = asc + desc + pad[1] * 2 - 20
    im = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w * SS - 1, h * SS - 1], radius=22 * SS, fill=bg)
    im = im.resize((w, h), Image.LANCZOS)
    ImageDraw.Draw(im).text((w / 2, h / 2 + 2), texto, font=f, fill=fg, anchor="mm")
    return sombra(im.rotate(ang, resample=Image.BICUBIC, expand=True), 14, 140, (0, 12))


def main():
    foto, logo_p, fonts, salida = sys.argv[1:5]
    img = fondo()

    # Palabra gigante con contorno, detrás de la persona
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    tam = 260
    while fuente(fonts, "Black", tam).getlength(PALABRA_FONDO) > W - 30:
        tam -= 4
    fp = fuente(fonts, "Black", tam)
    ImageDraw.Draw(c).text((W / 2, 610), PALABRA_FONDO, font=fp, fill=AMARILLO + (40,),
                           anchor="mm", stroke_width=5, stroke_fill=AMARILLO + (255,))
    img.alpha_composite(c)

    # Persona recortada (encima de la palabra y del pulso)
    p = Image.open(foto).convert("RGBA")
    p = p.crop(p.getbbox())
    esc = 1.2
    p = p.resize((int(p.width * esc), int(p.height * esc)), Image.LANCZOS)
    x, y = int(W / 2 - p.width / 2), 400
    halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    m = p.getchannel("A").filter(ImageFilter.GaussianBlur(30)).point(lambda v: v * 120 // 255)
    halo.paste(Image.new("RGBA", p.size, (120, 150, 255, 255)), (x, y), m)
    img.alpha_composite(halo)
    img.alpha_composite(p, (x, y))

    # Fundido azul bajo la persona para apoyar el título
    g = np.zeros((H, W, 4), np.uint8)
    g[..., :3] = AZUL
    g[..., 3] = (np.clip((np.arange(H) - 1050) / 260, 0, 1) ** 1.3 * 245).astype(np.uint8)[:, None]
    img.alpha_composite(Image.fromarray(g, "RGBA"))

    # Etiqueta superior (píldora con borde) y logo arriba a la derecha
    d = ImageDraw.Draw(img)
    fe = fuente(fonts, "Bold", 30)
    tw = fe.getlength(ETIQUETA_SUP)
    d.rounded_rectangle([70, 270, 70 + tw + 60, 330], radius=30, outline=AMARILLO, width=3,
                        fill=AZUL + (200,))
    d.text((100, 300), ETIQUETA_SUP, font=fe, fill=BLANCO, anchor="lm")
    logo = Image.open(logo_p).convert("RGBA")
    lw = 140
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    img.alpha_composite(logo, (W - lw - 60, 240))

    # Título en etiquetas inclinadas
    ft = fuente(fonts, "Black", 112)
    y = 1170
    for i, (txt, bg, fg, ang) in enumerate(LINEAS):
        e = etiqueta(txt, ft, bg, fg, ang)
        cx = W / 2 + (-30 if i == 0 else 40)
        img.alpha_composite(e, (int(cx - e.width / 2), int(y - e.height / 2)))
        y += 168
    fr = fuente(fonts, "ExtraBold", 84)
    d = ImageDraw.Draw(img)
    d.text((W / 2, y + 10), REMATE, font=fr, fill=BLANCO, anchor="mm")

    # Línea de pulso (ECG) que cruza la pantalla debajo del título
    c = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    y0 = y + 130
    pts = [(-20, y0), (400, y0), (440, y0 - 30), (490, y0 + 38), (545, y0 - 60), (595, y0 + 20),
           (630, y0), (W + 20, y0)]
    ImageDraw.Draw(c).line([(x * SS, yy * SS) for x, yy in pts], fill=ROJO + (255,),
                           width=10 * SS, joint="curve")
    ImageDraw.Draw(c).ellipse([(W - 70) * SS, (y0 - 13) * SS, (W - 44) * SS, (y0 + 13) * SS],
                              fill=AMARILLO + (255,))
    img.alpha_composite(c.resize((W, H), Image.LANCZOS))

    img.convert("RGB").save(salida)


if __name__ == "__main__":
    main()
