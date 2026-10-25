"""Portada del Reel para el feed de FRAMI: persona recortada sobre un círculo amarillo,
líneas geométricas de marca y bloque azul diagonal con el título.

Uso: python3 portada_feed.py <foto_recortada.png> <logo.png> <Inter.ttf> <salida.png>
La foto recortada es un cuadro del video con el fondo quitado (rembg, u2net_human_seg).
"""
import math
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
SS = 2  # supermuestreo para bordes suaves

# Paleta de marca (mismos tonos que el resto del feed).
AZUL = (3, 64, 126)
ROJO = (233, 24, 63)
AMARILLO = (255, 185, 41)
BLANCO = (255, 255, 255)
GRIS = (244, 244, 244)

TITULO_1 = "BOLSA"
TITULO_2 = "SEGURO"
PILDORA = "¿uno u otro?"


def capa():
    return Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))


def bajar(c):
    return c.resize((W, H), Image.LANCZOS)


def s(*v):
    return [x * SS for x in v]


def inter(path, tam, peso):
    f = ImageFont.truetype(path, tam)
    f.set_variation_by_axes([32, peso])
    return f


def sombra_de(im, radio, alfa, offset):
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh.putalpha(im.getchannel("A").point(lambda v: v * alfa // 255)
                .filter(ImageFilter.GaussianBlur(radio)))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.alpha_composite(sh, offset)
    out.alpha_composite(im)
    return out


def main():
    foto, logo_p, fuente, salida = sys.argv[1:5]
    img = Image.new("RGBA", (W, H), GRIS + (255,))

    # Puntos suaves en grilla (textura sutil arriba a la izquierda)
    c = capa()
    d = ImageDraw.Draw(c)
    for y in range(330, 780, 46):
        for x in range(46, 330, 46):
            d.ellipse(s(x - 4, y - 4, x + 4, y + 4), fill=AZUL + (60,))
    img.alpha_composite(bajar(c))

    # Franja roja diagonal detrás de todo
    c = capa()
    ang = math.radians(-24)
    dx, dy = math.cos(ang), math.sin(ang)
    nx, ny = -dy, dx
    cx, cy, largo, g = 540, 860, 1600, 64
    pts = [(cx - dx * largo + nx * g, cy - dy * largo + ny * g),
           (cx + dx * largo + nx * g, cy + dy * largo + ny * g),
           (cx + dx * largo - nx * g, cy + dy * largo - ny * g),
           (cx - dx * largo - nx * g, cy - dy * largo - ny * g)]
    ImageDraw.Draw(c).polygon([(x * SS, y * SS) for x, y in pts], fill=ROJO)
    img.alpha_composite(bajar(c))

    # Círculo amarillo (halo) + anillo azul fino + arco punteado rojo
    c = capa()
    d = ImageDraw.Draw(c)
    ccx, ccy, r = 560, 840, 400
    d.ellipse(s(ccx - r, ccy - r, ccx + r, ccy + r), fill=AMARILLO)
    r2 = r + 48
    d.arc(s(ccx - r2, ccy - r2, ccx + r2, ccy + r2), 150, 330, fill=AZUL, width=7 * SS)
    r3 = r + 92
    for a in range(200, 300, 7):
        t = math.radians(a)
        x, y = ccx + r3 * math.cos(t), ccy + r3 * math.sin(t)
        d.ellipse(s(x - 7, y - 7, x + 7, y + 7), fill=ROJO)
    img.alpha_composite(bajar(c))

    # Persona recortada
    p = Image.open(foto).convert("RGBA")
    p = p.crop(p.getbbox())
    esc = 1.24
    p = p.resize((int(p.width * esc), int(p.height * esc)), Image.LANCZOS)
    img.alpha_composite(sombra_de(p, 18, 70, (0, 10)), (int(W / 2 - p.width / 2) + 20, 470))

    # Bloque azul diagonal al frente, con línea amarilla paralela y rayas finas
    c = capa()
    d = ImageDraw.Draw(c)
    y_izq, y_der = 1250, 1110
    d.polygon(s(0, y_izq, W, y_der, W, H, 0, H), fill=AZUL)
    d.line(s(0, y_izq - 34, W, y_der - 34), fill=AMARILLO, width=12 * SS)
    for i in range(6):
        x0 = 760 + i * 52
        d.line(s(x0, H + 20, x0 + 300, H - 280), fill=BLANCO + (40,), width=10 * SS)
    img.alpha_composite(bajar(c))

    # Logo arriba a la derecha
    logo = Image.open(logo_p).convert("RGBA")
    lw = 170
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    img.alpha_composite(sombra_de(logo, 10, 60, (0, 6)), (W - lw - 78, 96))

    # Título alineado a la izquierda
    x0 = 80
    d = ImageDraw.Draw(img)
    d.text((x0, 1330), TITULO_1, font=inter(fuente, 150, 850), fill=BLANCO, anchor="lm")

    # "o" blanca liviana + "SEGURO" en amarillo
    oy = 1480
    fo = inter(fuente, 130, 400)
    d.text((x0, oy), "o", font=fo, fill=BLANCO, anchor="lm")
    xs = x0 + fo.getlength("o") + 28
    tam = 170
    while inter(fuente, tam, 900).getlength(TITULO_2) > W - xs - 60:
        tam -= 4
    d.text((xs, oy), TITULO_2, font=inter(fuente, tam, 900), fill=AMARILLO, anchor="lm")

    # Etiqueta roja inclinada
    f = inter(fuente, 62, 600)
    pw, ph = int(f.getlength(PILDORA) + 76), 96
    et = Image.new("RGBA", (pw * SS, ph * SS), (0, 0, 0, 0))
    ImageDraw.Draw(et).rounded_rectangle([0, 0, pw * SS - 1, ph * SS - 1], radius=48 * SS,
                                         fill=ROJO)
    et = et.resize((pw, ph), Image.LANCZOS)
    ImageDraw.Draw(et).text((pw / 2, ph / 2 - 2), PILDORA, font=f, fill=BLANCO, anchor="mm")
    et = et.rotate(4, resample=Image.BICUBIC, expand=True)
    img.alpha_composite(sombra_de(et, 10, 90, (0, 6)), (x0 - 6, 1560))

    img.convert("RGB").save(salida)


if __name__ == "__main__":
    main()
