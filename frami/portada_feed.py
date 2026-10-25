"""Portada del Reel en el estilo del feed de FRAMI (persona recortada, curvas de marca,
título grande con píldora roja).

Uso: python3 portada_feed.py <foto_recortada.png> <logo.png> <Inter.ttf> <salida.png>
La foto recortada es un cuadro del video con el fondo quitado (rembg, u2net_human_seg).
"""
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
SS = 2  # supermuestreo para curvas suaves

# Colores tomados de la portada del Reel anterior, para que el feed quede combinado.
AZUL = (3, 64, 126)
ROJO = (233, 24, 63)
AMARILLO = (255, 185, 41)
BLANCO = (255, 255, 255)

TITULO_1 = "Bolsa o"
TITULO_2 = "SEGURO"
PILDORA = "¿uno u otro?"


def bezier(pts, n=200):
    """Curva de Bézier cúbica encadenada: pts = [p0, c1, c2, p1, c1, c2, p2, ...]."""
    out = []
    for i in range(0, len(pts) - 1, 3):
        p0, c1, c2, p1 = (np.array(p, float) for p in pts[i:i + 4])
        for t in np.linspace(0, 1, n):
            out.append((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * c1
                       + 3 * (1 - t) * t ** 2 * c2 + t ** 3 * p1)
    return out


def trazo(d, pts, grosor, color):
    """Trazo grueso con extremos redondeados (círculos a lo largo de la curva)."""
    r = grosor * SS / 2
    for x, y in bezier(pts):
        d.ellipse([x * SS - r, y * SS - r, x * SS + r, y * SS + r], fill=color)


def capa_vacia(escala=1):
    return Image.new("RGBA", (W * escala, H * escala), (0, 0, 0, 0))


def degradado_vertical(color, y0, y1, a0, a1, curva=1.0):
    g = np.zeros((H, W, 4), np.uint8)
    g[..., :3] = color
    k = np.clip((np.arange(H) - y0) / (y1 - y0), 0, 1) ** curva
    k = k * k * (3 - 2 * k)  # sin quiebres visibles en los extremos
    g[..., 3] = (255 * (a0 + (a1 - a0) * k)).astype(np.uint8)[:, None]
    return Image.fromarray(g, "RGBA")


def inter(path, tam, peso):
    f = ImageFont.truetype(path, tam)
    f.set_variation_by_axes([32, peso])
    return f


def texto_con_sombra(base, xy, txt, font, relleno=BLANCO, sombra=90, degradado=True):
    w = int(font.getlength(txt)) + 80
    asc, desc = font.getmetrics()
    capa = Image.new("RGBA", (w, asc + desc + 80), (0, 0, 0, 0))
    ImageDraw.Draw(capa).text((40, 40), txt, font=font, fill=relleno + (255,))
    if degradado:  # leve degradado blanco -> gris perla, como en la portada anterior
        g = np.asarray(capa).astype(np.float32)
        k = np.linspace(1.0, 0.86, capa.height)[:, None]
        g[..., :3] *= k[..., None]
        capa = Image.fromarray(g.astype(np.uint8), "RGBA")
    s = Image.new("RGBA", capa.size, (0, 0, 0, 0))
    s.putalpha(capa.getchannel("A").point(lambda v: v * sombra // 255)
               .filter(ImageFilter.GaussianBlur(14)))
    x, y = xy
    base.alpha_composite(s, (int(x - w / 2), int(y - capa.height / 2) + 8))
    base.alpha_composite(capa, (int(x - w / 2), int(y - capa.height / 2)))


def main():
    foto, logo_p, fuente, salida = sys.argv[1:5]
    img = Image.new("RGBA", (W, H), BLANCO + (255,))

    # Cielo azul arriba que se funde en blanco
    img.alpha_composite(degradado_vertical(AZUL, 0, 620, 1, 0, curva=0.8))

    # Curva roja superior (entra por la izquierda y sale por arriba)
    deco = capa_vacia(SS)
    d = ImageDraw.Draw(deco)
    trazo(d, [(-80, 420), (160, 440), (250, 260), (390, 190),
              (520, 125), (560, 40), (700, -70)], 92, ROJO)
    img.alpha_composite(deco.resize((W, H), Image.LANCZOS))

    # Arco rojo detrás de los hombros
    arco = capa_vacia(SS)
    ImageDraw.Draw(arco).ellipse([(-520) * SS, 1150 * SS, (W + 520) * SS, 3400 * SS], fill=ROJO)
    img.alpha_composite(arco.resize((W, H), Image.LANCZOS))

    # Persona recortada: más grande y centrada, cabeza por debajo de la zona del logo
    p = Image.open(foto).convert("RGBA")
    p = p.crop(p.getbbox())
    esc = 1.30
    p = p.resize((int(p.width * esc), int(p.height * esc)), Image.LANCZOS)
    img.alpha_composite(p, (int(W / 2 - p.width / 2) + 10, 560))

    # Azul que sube desde abajo y funde el arco y el torso
    img.alpha_composite(degradado_vertical(AZUL, 1000, 1640, 0, 1, curva=0.8))

    # Curva amarilla inferior (abajo a la derecha)
    deco = capa_vacia(SS)
    trazo(ImageDraw.Draw(deco), [(1160, 1480), (980, 1520), (900, 1700), (760, 1780),
                                 (640, 1850), (560, 1900), (520, 2000)], 120, AMARILLO)
    img.alpha_composite(deco.resize((W, H), Image.LANCZOS))

    # Logo arriba a la derecha
    logo = Image.open(logo_p).convert("RGBA")
    lw = 190
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    img.alpha_composite(logo, (W - lw - 92, 82))

    # Título
    texto_con_sombra(img, (W / 2, 1300), TITULO_1, inter(fuente, 150, 650))
    tam = 260
    while inter(fuente, tam, 850).getlength(TITULO_2) > 900:
        tam -= 6
    texto_con_sombra(img, (W / 2, 1445), TITULO_2, inter(fuente, tam, 850), degradado=False)

    f = inter(fuente, 76, 420)
    tw = f.getlength(PILDORA)
    pw, ph = int(tw + 80), 104
    pil = Image.new("RGBA", (pw * SS, ph * SS), (0, 0, 0, 0))
    ImageDraw.Draw(pil).rounded_rectangle([0, 0, pw * SS - 1, ph * SS - 1], radius=30 * SS,
                                          fill=ROJO)
    pil = pil.resize((pw, ph), Image.LANCZOS)
    ImageDraw.Draw(pil).text((pw / 2, ph / 2 - 2), PILDORA, font=f, fill=BLANCO, anchor="mm")
    img.alpha_composite(pil, (int(W / 2 - pw / 2), 1580))

    img.convert("RGB").save(salida)


if __name__ == "__main__":
    main()
