"""Flyer de seguros náuticos de FRAMI (adaptación de la pieza que mandó la dueña).

Usa solo la foto (pescador en la lancha), mejorada con Real-ESRGAN, y arma un diseño propio
con la paleta de FRAMI. Genera feed (1080x1350) e historia / estado (1080x1920).

Uso: python3 flyer_nautico.py <imagen.jpg> <x4v3.onnx> <logo.png> <dir_fuentes> <dir_salida>
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                                "rabbit", "historia_picada"))
from historia_picada import curva_s, esrgan  # noqa: E402

AZUL = (8, 8, 96)
AZUL_2 = (24, 34, 150)
ROJO = (232, 0, 61)
AMARILLO = (245, 196, 0)
BLANCO = (255, 255, 255)
CELESTE = (170, 190, 255)

ETIQUETA = "SEGUROS NÁUTICOS"
TITULO = [("Tu embarcación,", BLANCO), ("siempre ", BLANCO), ("protegida.", AMARILLO)]
TIPOS = ["Lancha", "Moto de agua", "Velero", "Crucero"]
BENEFICIOS = ["Cobertura accesible", "Contratación fácil y rápida",
              "Adaptado a tus necesidades"]
CTA = "COTIZÁ AHORA"
WHATSAPP = "3764 886646"
USUARIO = "@frami.productoresasesores"
RECORTE_FOTO = None  # alto a recortar de la imagen original (None = la foto entera)
CENTRO_X = 0.68      # centro horizontal del encuadre (padre e hijo están a la derecha)
CON_LOGO = False     # la dueña pidió esta versión sin el logo de FRAMI
CON_ETIQUETA = False  # ni la etiqueta "SEGUROS NÁUTICOS"


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


def pildora(w, h, relleno, borde=None, grosor=3):
    s = 3
    im = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, w * s - 1, h * s - 1], radius=h * s // 2,
                                         fill=relleno, outline=borde,
                                         width=grosor * s if borde else 0)
    return im.resize((w, h), Image.LANCZOS)


# ----------------------------------------------------------------- foto
def foto_mejorada(path, modelo):
    im = Image.open(path).convert("RGB")
    if RECORTE_FOTO:
        im = im.crop((0, 0, im.width, RECORTE_FOTO))
    im = esrgan(im, modelo)                       # x4
    im = curva_s(im, 0.08)
    im = ImageEnhance.Color(im).enhance(1.08)
    return im.filter(ImageFilter.UnsharpMask(radius=1.4, percent=50, threshold=3))


def fondo(foto, W, H, alto_foto, cx=0.5, cielo=0):
    """Foto arriba (cubriendo W x alto_foto) que se funde en el azul de FRAMI. 'cielo'
    agrega píxeles arriba continuando el cielo (para bajar la foto en la historia)."""
    alto_img = alto_foto - cielo
    esc = max(W / foto.width, alto_img / foto.height)
    f = foto.resize((round(foto.width * esc), round(foto.height * esc)), Image.LANCZOS)
    x0 = int(min(max(cx * f.width - W / 2, 0), f.width - W))
    f = f.crop((x0, 0, x0 + W, alto_img))
    if cielo:
        franja = np.asarray(f.crop((0, 0, W, 6)).filter(ImageFilter.GaussianBlur(3)),
                            np.float32).mean(axis=0)
        franja = np.asarray(Image.fromarray(franja[None].astype(np.uint8)).filter(
            ImageFilter.GaussianBlur(25)), np.float32)[0]
        # de la franja real (abajo) a un cielo parejo (arriba), sin manchas en las esquinas
        parejo = franja.mean(axis=0, keepdims=True)
        k = (np.arange(cielo, dtype=np.float32) / cielo)[:, None, None] ** 1.5
        arriba = (parejo[None] * (1 - k) + franja[None] * k).astype(np.uint8)
        g = Image.new("RGB", (W, alto_foto))
        g.paste(Image.fromarray(arriba), (0, 0))
        g.paste(f, (0, cielo))
        # costura suave
        costura = g.crop((0, cielo - 30, W, cielo + 30)).filter(ImageFilter.GaussianBlur(8))
        g.paste(costura, (0, cielo - 30))
        f = g
    f = f.convert("RGBA")
    img = Image.new("RGBA", (W, H), AZUL + (255,))
    # degradado vertical del azul de marca (más claro abajo)
    y = np.linspace(0, 1, H)[:, None, None]
    g = np.array(AZUL, np.float32) * (1 - y) + np.array(AZUL_2, np.float32) * y
    img = Image.fromarray(np.broadcast_to(g, (H, W, 3)).astype(np.uint8)).convert("RGBA")
    a = np.ones((alto_foto, W), np.float32)
    ini = int(alto_foto * 0.62)
    a[ini:] = np.linspace(1, 0, alto_foto - ini)[:, None] ** 1.4
    f.putalpha(Image.fromarray((a * 255).astype(np.uint8)))
    img.alpha_composite(f)
    # velo azul suave sobre la parte baja de la foto (para el título)
    v = np.zeros((H, W, 4), np.uint8)
    v[..., :3] = AZUL
    yy = np.arange(H, dtype=np.float32)
    v[..., 3] = (np.clip((yy - alto_foto * 0.35) / (alto_foto * 0.6), 0, 1) ** 1.2
                 * 150).astype(np.uint8)[:, None]
    img.alpha_composite(Image.fromarray(v, "RGBA"))
    return img


# ----------------------------------------------------------------- piezas
def etiqueta(f, tam=26):
    fn = f("Bold", tam)
    w = int(fn.getlength(ETIQUETA)) + 70
    im = pildora(w, int(tam * 2.1), AMARILLO + (255,))
    d = ImageDraw.Draw(im)
    d.ellipse([20, im.height / 2 - 6, 32, im.height / 2 + 6], fill=AZUL)
    d.text((44, im.height / 2), ETIQUETA, font=fn, fill=AZUL, anchor="lm")
    return im


def titulo(f, tam):
    fn = f("ExtraBold", tam)
    lh = int(tam * 1.12)
    w = 1000
    im = Image.new("RGBA", (w, lh * 2 + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((0, lh / 2 + 6), TITULO[0][0], font=fn, fill=TITULO[0][1], anchor="lm")
    x = 0
    for t, c in TITULO[1:]:
        if c == AMARILLO:   # subrayado amarillo detrás de la palabra clave
            tw = fn.getlength(t.rstrip("."))
            d.rounded_rectangle([x - 4, lh * 1.5 + tam * 0.22, x + tw + 6, lh * 1.5 + tam * 0.40],
                                radius=6, fill=(245, 196, 0, 90))
        d.text((x, lh * 1.5 + 6), t, font=fn, fill=c, anchor="lm")
        x += fn.getlength(t)
    return im.crop(im.getbbox())


def chips(f, ancho_max, tam=30):
    fn = f("SemiBold", tam)
    h = int(tam * 2.05)
    piezas = []
    for t in TIPOS:
        w = int(fn.getlength(t)) + 56
        p = pildora(w, h, (255, 255, 255, 30), (255, 255, 255, 170), 2)
        ImageDraw.Draw(p).text((w / 2, h / 2), t, font=fn, fill=BLANCO, anchor="mm")
        piezas.append(p)
    filas, fila, x = [], [], 0
    for p in piezas:
        if fila and x + p.width > ancho_max:
            filas.append(fila)
            fila, x = [], 0
        fila.append(p)
        x += p.width + 14
    filas.append(fila)
    alto = len(filas) * (h + 14) - 14
    im = Image.new("RGBA", (ancho_max, alto), (0, 0, 0, 0))
    for i, fila in enumerate(filas):
        x = 0
        for p in fila:
            im.alpha_composite(p, (x, i * (h + 14)))
            x += p.width + 14
    return im


def check(d, cx, cy, r):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=AMARILLO)
    d.line([(cx - r * 0.45, cy + r * 0.02), (cx - r * 0.1, cy + r * 0.38),
            (cx + r * 0.5, cy - r * 0.35)], fill=AZUL, width=max(3, int(r * 0.24)),
           joint="curve")


def beneficios(f, tam=34, sep=62):
    fn = f("Medium", tam)
    w = int(max(fn.getlength(t) for t in BENEFICIOS)) + 70
    im = Image.new("RGBA", (w, sep * len(BENEFICIOS)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, t in enumerate(BENEFICIOS):
        y = sep * i + sep / 2
        check(d, 20, y, 18)
        d.text((56, y), t, font=fn, fill=BLANCO, anchor="lm")
    return im


def icono_whatsapp(d, cx, cy, r, color):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=max(3, int(r * 0.16)))
    d.polygon([(cx - r * 0.85, cy + r * 1.05), (cx - r * 0.55, cy + r * 0.45),
               (cx - r * 0.2, cy + r * 0.8)], fill=color)
    # auricular simplificado
    d.arc([cx - r * 0.5, cy - r * 0.5, cx + r * 0.5, cy + r * 0.5], 100, 260, fill=color,
          width=max(3, int(r * 0.22)))


def boton_cta(f, tam=38):
    fn = f("ExtraBold", tam)
    w, h = int(fn.getlength(CTA)) + 150, int(tam * 2.5)
    im = pildora(w, h, ROJO + (255,))
    d = ImageDraw.Draw(im)
    d.text((w / 2 - 22, h / 2), CTA, font=fn, fill=BLANCO, anchor="mm")
    # flecha
    x = w / 2 + fn.getlength(CTA) / 2 + 4
    d.line([(x, h / 2), (x + 34, h / 2)], fill=BLANCO, width=6)
    d.polygon([(x + 44, h / 2), (x + 26, h / 2 - 14), (x + 26, h / 2 + 14)], fill=BLANCO)
    return im


def contacto(f, tam=36):
    fn = f("Bold", tam)
    fu = f("Medium", int(tam * 0.7))
    w = int(max(fn.getlength(WHATSAPP) + 70, fu.getlength(USUARIO))) + 10
    h = int(tam * 2.4)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    icono_whatsapp(d, 22, tam * 0.62, 20, BLANCO)
    d.text((62, tam * 0.62), WHATSAPP, font=fn, fill=BLANCO, anchor="lm")
    d.text((0, tam * 1.75), USUARIO, font=fu, fill=CELESTE, anchor="lm")
    return im


def logo_frami(path, ancho):
    lg = Image.open(path).convert("RGBA")
    return lg.resize((ancho, round(lg.height * ancho / lg.width)), Image.LANCZOS)


# ----------------------------------------------------------------- formatos
def armar(foto, f, logo_p, W, H, alto_foto, y_titulo, tam_titulo, salida, k=1.0, cielo=0):
    img = fondo(foto, W, H, alto_foto, cx=CENTRO_X, cielo=cielo)
    m = 70
    if CON_LOGO:
        pegar(img, logo_frami(logo_p, 120), W - m - 120, 52 if H < 1600 else 250, radio=10,
              alfa=120)
    if CON_ETIQUETA:
        pegar(img, etiqueta(f, int(26 * k)), m, 74 if H < 1600 else 272, radio=8, alfa=90)
    t = titulo(f, tam_titulo)
    pegar(img, t, m, y_titulo, radio=16, alfa=170)
    y = y_titulo + t.height + 40
    c = chips(f, W - 2 * m, int(30 * k))
    pegar(img, c, m, y, con_sombra=False)
    y += c.height + 46
    b = beneficios(f, int(34 * k), int(62 * k))
    pegar(img, b, m, y, con_sombra=False)
    y += b.height + 40
    # línea fina separadora
    ImageDraw.Draw(img).line([(m, y), (W - m, y)], fill=(255, 255, 255, 60), width=2)
    y += 40
    bt = boton_cta(f, int(38 * k))
    pegar(img, bt, m, y, radio=14, alfa=170, offset=(0, 10))
    ct = contacto(f, int(36 * k))
    pegar(img, ct, W - m - ct.width, y + bt.height / 2 - 30, con_sombra=False)
    img.convert("RGB").save(salida)
    return y + bt.height


def main():
    path, modelo, logo_p, fuentes, salida = sys.argv[1:6]
    f = F(fuentes)
    foto = foto_mejorada(path, modelo)
    fin_feed = armar(foto, f, logo_p, 1080, 1350, 960, 640, 74,
                     f"{salida}/frami_nautico_feed.png")
    fin_hist = armar(foto, f, logo_p, 1080, 1920, 1240, 900, 92,
                     f"{salida}/frami_nautico_historia.png", k=1.14, cielo=230)
    print("fin del contenido: feed", fin_feed, "/1350, historia", fin_hist, "/1920")


if __name__ == "__main__":
    main()
