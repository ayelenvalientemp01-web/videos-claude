"""Historia de Instagram (1080x1920) del tema "Respaldo", pensada para la interacción:
pregunta que engancha, espacio reservado para el sticker de encuesta (se agrega desde la app
de Instagram) y llamado a escribir RESPALDO por mensaje. Mismo estilo que la portada del Reel.

Uso: python3 flyer_historia.py <foto_recortada.png> <logo.png> <dir_fonts> <salida.png> [modo]
modo "instagram" (por defecto): recuadro para el sticker de encuesta + CTA "RESPALDO".
modo "estado": para estados de WhatsApp que puede subir cualquier persona; sin CTA de marca,
con las opciones A/B impresas y "Respondé este estado con A o B".
Zonas seguras: nada importante arriba de y=250 (perfil) ni debajo de y=1650 (barra de
mensaje).
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

# Caja reservada para el sticker de encuesta (x0, y0, x1, y1)
ENCUESTA = (110, 975, 970, 1265)
OPCIONES = [("A", "Con mis ahorros", AMARILLO, AZUL), ("B", "No lo había pensado", ROJO, BLANCO)]


def fuente(d, peso, tam):
    return ImageFont.truetype(f"{d}/Poppins-{peso}.ttf", tam)


def sombra(im, radio=14, alfa=140, offset=(0, 12)):
    s = Image.new("RGBA", im.size, (0, 0, 0, 0))
    s.putalpha(im.getchannel("A").point(lambda v: v * alfa // 255)
               .filter(ImageFilter.GaussianBlur(radio)))
    out = Image.new("RGBA", (im.width + 80, im.height + 80), (0, 0, 0, 0))
    out.alpha_composite(s, (40 + offset[0], 40 + offset[1]))
    out.alpha_composite(im, (40, 40))
    return out


def fondo():
    y = np.linspace(0, 1, H)[:, None, None]
    base = np.broadcast_to(np.array(AZUL, np.float32) * (1 - y) +
                           np.array(AZUL_2, np.float32) * y, (H, W, 3)).copy()
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    for cx, cy, r, col, a in [(1000, 1650, 700, ROJO, 0.5), (80, 380, 620, (60, 90, 255), 0.45)]:
        g = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / r ** 2))[..., None] * a
        base = base * (1 - g) + np.array(col, np.float32) * g
    img = Image.fromarray(base.clip(0, 255).astype(np.uint8)).convert("RGBA")
    # grilla de puntos sutil arriba a la derecha
    d = ImageDraw.Draw(img)
    for y in range(400, 700, 40):
        for x in range(830, 1060, 40):
            d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(255, 255, 255, 40))
    return img


def etiqueta(texto, f, bg, fg, ang, pad=(40, 20)):
    w = int(f.getlength(texto)) + pad[0] * 2
    asc, desc = f.getmetrics()
    h = asc + desc + pad[1] * 2 - 18
    im = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, w * SS - 1, h * SS - 1], radius=22 * SS,
                                         fill=bg)
    im = im.resize((w, h), Image.LANCZOS)
    ImageDraw.Draw(im).text((w / 2, h / 2 + 2), texto, font=f, fill=fg, anchor="mm")
    return sombra(im.rotate(ang, resample=Image.BICUBIC, expand=True))


def pegar_centro(img, im, cx, cy):
    img.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


def caja_punteada(img, caja, color=(255, 255, 255, 170), largo=26, hueco=16, grosor=5,
                  radio=48):
    """Rectángulo redondeado con borde punteado (supermuestreado)."""
    x0, y0, x1, y1 = caja
    c = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.rounded_rectangle([x0 * SS, y0 * SS, x1 * SS, y1 * SS], radius=radio * SS,
                        fill=(255, 255, 255, 22))
    borde = Image.new("L", (W * SS, H * SS), 0)
    ImageDraw.Draw(borde).rounded_rectangle([x0 * SS, y0 * SS, x1 * SS, y1 * SS],
                                            radius=radio * SS, outline=255, width=grosor * SS)
    # máscara de guiones diagonales para cortar el borde
    m = Image.new("L", (W * SS, H * SS), 0)
    dm = ImageDraw.Draw(m)
    paso = (largo + hueco) * SS
    for k in range(-H * SS, W * SS + H * SS, paso):
        dm.polygon([(k, 0), (k + largo * SS, 0), (k + largo * SS - H * SS, H * SS),
                    (k - H * SS, H * SS)], fill=255)
    borde = Image.fromarray(np.minimum(np.asarray(borde), np.asarray(m)))
    capa = Image.new("RGBA", (W * SS, H * SS), color)
    c.paste(capa, (0, 0), borde)
    img.alpha_composite(c.resize((W, H), Image.LANCZOS))


def flecha(img, p0, p1, p2, color=AMARILLO, grosor=8):
    """Flecha curva dibujada a mano (bezier cuadrática) de p0 a p2."""
    c = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    pts = []
    for i in range(41):
        t = i / 40
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
        pts.append((x * SS, y * SS))
    d.line(pts, fill=color, width=grosor * SS, joint="curve")
    # punta
    (xa, ya), (xb, yb) = pts[-4], pts[-1]
    v = np.array([xb - xa, yb - ya], float)
    v /= np.linalg.norm(v)
    n = np.array([-v[1], v[0]])
    L = 30 * SS
    for s in (1, -1):
        q = np.array([xb, yb]) - v * L + n * L * 0.6 * s
        d.line([(xb, yb), tuple(q)], fill=color, width=grosor * SS)
    img.alpha_composite(c.resize((W, H), Image.LANCZOS))


def encuesta(img, fonts):
    """Recuadro punteado para pegar el sticker de encuesta de Instagram."""
    caja_punteada(img, ENCUESTA)
    d = ImageDraw.Draw(img)
    fv = fuente(fonts, "ExtraBold", 40)
    vt = "¡VOTÁ ACÁ!"
    d.text((W - 90, ENCUESTA[1] - 45), vt, font=fv, fill=AMARILLO, anchor="rm")
    xa = W - 90 - fv.getlength(vt) - 22
    flecha(img, (xa, ENCUESTA[1] - 45), (xa - 120, ENCUESTA[1] - 50), (xa - 170, ENCUESTA[1] + 40))


def opciones(img, fonts):
    """Opciones A/B impresas, en tarjetas de vidrio (para estados sin sticker de encuesta)."""
    x0, y0, x1, y1 = ENCUESTA
    alto, sep = 125, 40
    fo = fuente(fonts, "ExtraBold", 50)
    fl = fuente(fonts, "Black", 52)
    for i, (letra, txt, col, fg) in enumerate(OPCIONES):
        ya = y0 + 10 + i * (alto + sep)
        c = Image.new("RGBA", ((x1 - x0) * SS, alto * SS), (0, 0, 0, 0))
        dc = ImageDraw.Draw(c)
        dc.rounded_rectangle([0, 0, (x1 - x0) * SS - 1, alto * SS - 1], radius=alto * SS // 2,
                             fill=(255, 255, 255, 34), outline=(255, 255, 255, 150),
                             width=3 * SS)
        r = (alto - 30) // 2
        cx, cy = 15 + r, alto // 2
        dc.ellipse([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS], fill=col)
        c = c.resize((x1 - x0, alto), Image.LANCZOS)
        dd = ImageDraw.Draw(c)
        dd.text((cx, cy + 2), letra, font=fl, fill=fg, anchor="mm")
        dd.text((cx + r + 34, cy + 2), txt, font=fo, fill=BLANCO, anchor="lm")
        img.alpha_composite(c, (x0, ya))


def main():
    foto, logo_p, fonts, salida = sys.argv[1:5]
    modo = sys.argv[5] if len(sys.argv) > 5 else "instagram"
    img = fondo()
    d = ImageDraw.Draw(img)

    # Encabezado: píldora "PREGUNTA RÁPIDA" + logo
    fe = fuente(fonts, "Bold", 32)
    txt = "PREGUNTA RÁPIDA"
    tw = fe.getlength(txt)
    d.rounded_rectangle([70, 285, 70 + tw + 100, 349], radius=32, fill=AMARILLO)
    d.ellipse([92, 303, 120, 331], fill=ROJO)
    d.text((136, 317), txt, font=fe, fill=AZUL, anchor="lm")
    logo = Image.open(logo_p).convert("RGBA")
    lw = 130
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    img.alpha_composite(logo, (W - lw - 60, 262))

    # Pregunta
    d = ImageDraw.Draw(img)
    d.text((80, 470), "Si mañana te diagnostican", font=fuente(fonts, "Bold", 58), fill=BLANCO,
           anchor="lm")
    pegar_centro(img, etiqueta("una ENFERMEDAD GRAVE", fuente(fonts, "Black", 72), ROJO, BLANCO,
                               -3), W / 2 - 20, 580)
    d = ImageDraw.Draw(img)
    d.text((80, 700), "¿con qué pagarías", font=fuente(fonts, "ExtraBold", 74), fill=BLANCO,
           anchor="lm")
    pegar_centro(img, etiqueta("LAS CUENTAS?", fuente(fonts, "Black", 84), AMARILLO, AZUL, 2.5),
                 W / 2 - 110, 815)

    if modo == "estado":
        opciones(img, fonts)
    else:
        encuesta(img, fonts)

    # Línea de pulso al pie
    c = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    y0 = 1700
    pts = [(-20, y0), (120, y0), (150, y0 - 26), (185, y0 + 32), (225, y0 - 52), (260, y0 + 16),
           (285, y0), (W + 20, y0)]
    ImageDraw.Draw(c).line([(x * SS, y * SS) for x, y in pts], fill=ROJO + (255,),
                           width=8 * SS, joint="curve")
    img.alpha_composite(c.resize((W, H), Image.LANCZOS))

    # Persona abajo a la derecha
    p = Image.open(foto).convert("RGBA")
    p = p.crop(p.getbbox())
    esc = 640 / p.width
    p = p.resize((int(p.width * esc), int(p.height * esc)), Image.LANCZOS)
    px, py = W - p.width + 110, 1300
    halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    m = p.getchannel("A").filter(ImageFilter.GaussianBlur(26)).point(lambda v: v * 110 // 255)
    halo.paste(Image.new("RGBA", p.size, (120, 150, 255, 255)), (px, py), m)
    img.alpha_composite(halo)
    img.alpha_composite(p, (px, py))

    if modo == "estado":
        d = ImageDraw.Draw(img)
        d.text((70, 1390), "Respondé", font=fuente(fonts, "ExtraBold", 54), fill=BLANCO,
               anchor="lm")
        d.text((70, 1455), "este estado", font=fuente(fonts, "ExtraBold", 54), fill=BLANCO,
               anchor="lm")
        fa = fuente(fonts, "Black", 54)
        x = 70
        for txt, col in [("con ", BLANCO), ("A", AMARILLO), (" o ", BLANCO), ("B", ROJO)]:
            d.text((x, 1525), txt, font=fa, fill=col, anchor="lm")
            x += fa.getlength(txt)
        img.convert("RGB").save(salida)
        return

    # Llamado a la acción (izquierda, encima de la barra de mensaje)
    d = ImageDraw.Draw(img)
    d.text((70, 1340), "¿Querés saber", font=fuente(fonts, "Bold", 46), fill=BLANCO, anchor="lm")
    d.text((70, 1398), "cómo cubrirte?", font=fuente(fonts, "Bold", 46), fill=BLANCO,
           anchor="lm")
    d.text((70, 1475), "Escribime por mensaje", font=fuente(fonts, "SemiBold", 34),
           fill=(190, 200, 255), anchor="lm")
    fp = fuente(fonts, "Black", 54)
    pw, ph = int(fp.getlength("RESPALDO")) + 90, 104
    pill = Image.new("RGBA", (pw * SS, ph * SS), (0, 0, 0, 0))
    ImageDraw.Draw(pill).rounded_rectangle([0, 0, pw * SS - 1, ph * SS - 1], radius=52 * SS,
                                           fill=ROJO)
    pill = pill.resize((pw, ph), Image.LANCZOS)
    ImageDraw.Draw(pill).text((pw / 2, ph / 2 + 2), "RESPALDO", font=fp, fill=BLANCO,
                              anchor="mm")
    pill = sombra(pill.rotate(-3, resample=Image.BICUBIC, expand=True))
    img.alpha_composite(pill, (70 - 40, 1515 - 40))

    img.convert("RGB").save(salida)


if __name__ == "__main__":
    main()
