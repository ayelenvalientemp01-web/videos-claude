"""Flyer "Horario de atención" de FRAMI (historia / estado 1080x1920 y feed 1080x1350).

Foto de la dueña en la oficina arriba, que se funde en el azul de marca; tarjeta blanca
con un reloj despertador rojo (dibujado) asomando, "Horario de atención", las dos franjas
horarias, la dirección y, abajo, el WhatsApp. Sin logo.

Uso: python3 flyer_horario.py <foto.jpg> <dir_fuentes> <dir_salida>
(dir_fuentes: Poppins-*.ttf y DancingScript-Bold.ttf)
"""
import math
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

AZUL = (8, 8, 96)
AZUL_2 = (24, 34, 150)
ROJO = (232, 0, 61)
ROJO_OSC = (160, 0, 40)
AMARILLO = (245, 196, 0)
BLANCO = (255, 255, 255)
CREMA = (252, 250, 244)
VERDE_WA = (37, 211, 102)
SS = 3

FRANJAS = [("Mañana", "9 a 12 h"), ("Tarde", "17 a 20 h")]
DIRECCION = "Las Rosas 10976 · Itaembé Guazú, Posadas"
WHATSAPP = "3764 886646"
USUARIO = "@frami.productoresasesores"


class F:
    def __init__(self, d):
        self.d, self.c = d, {}

    def __call__(self, nombre, tam):
        k = (nombre, tam)
        if k not in self.c:
            archivo = "DancingScript-Bold.ttf" if nombre == "Script" else f"Poppins-{nombre}.ttf"
            self.c[k] = ImageFont.truetype(f"{self.d}/{archivo}", tam)
        return self.c[k]


def sombra(capa, radio=16, alfa=150, offset=(0, 12)):
    pad = radio * 3
    out = Image.new("RGBA", (capa.width + 2 * pad, capa.height + 2 * pad), (0, 0, 0, 0))
    s = Image.new("RGBA", capa.size, (0, 0, 30, 0))
    s.putalpha(capa.getchannel("A").point(lambda v: v * alfa // 255))
    out.alpha_composite(s, (pad + offset[0], pad + offset[1]))
    out = out.filter(ImageFilter.GaussianBlur(radio))
    out.alpha_composite(capa, (pad, pad))
    return out, pad


def centrar(base, capa, cx, cy, **kw):
    capa, pad = sombra(capa, **kw) if kw.get("radio", 1) else (capa, 0)
    base.alpha_composite(capa, (int(cx - capa.width / 2), int(cy - capa.height / 2)))


# ----------------------------------------------------------------- reloj despertador
def reloj(f, d=300):
    """Reloj despertador rojo con campanas, martillo, patas y brillo (agujas a las 9)."""
    s = SS
    W = H = int(d * 1.32)
    im = Image.new("RGBA", (W * s, H * s), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    cx, cy, r = W / 2, H * 0.56, d * 0.42

    def P(*v):
        return [x * s for x in v]

    # patas
    for lado in (-1, 1):
        x0 = cx + lado * r * 0.62
        dr.line(P(x0, cy + r * 0.7, x0 + lado * r * 0.22, cy + r * 1.08), fill=ROJO_OSC,
                width=int(r * 0.13 * s))
    # campanas y martillo
    for lado in (-1, 1):
        bx, by = cx + lado * r * 0.66, cy - r * 0.86
        dr.line(P(cx + lado * r * 0.35, cy - r * 0.6, bx, by), fill=ROJO_OSC,
                width=int(r * 0.09 * s))
        br = r * 0.36
        campana = Image.new("RGBA", (int(br * 2.2 * s),) * 2, (0, 0, 0, 0))
        dc = ImageDraw.Draw(campana)
        dc.pieslice([0, 0, campana.width - 1, campana.height - 1], 180, 360, fill=ROJO)
        dc.rectangle([0, campana.height / 2 - 2, campana.width, campana.height / 2 + br * 0.18 * s],
                     fill=ROJO_OSC)
        campana = campana.rotate(-lado * 32, resample=Image.BICUBIC, expand=True)
        im.alpha_composite(campana, (int(bx * s - campana.width / 2),
                                     int(by * s - campana.height / 2)))
    dr.line(P(cx, cy - r * 1.02, cx, cy - r * 1.22), fill=ROJO_OSC, width=int(r * 0.08 * s))
    dr.ellipse(P(cx - r * 0.1, cy - r * 1.32, cx + r * 0.1, cy - r * 1.12), fill=ROJO_OSC)
    # cuerpo con sombreado radial
    yy, xx = np.mgrid[0:H * s, 0:W * s].astype(np.float32)
    dist = np.sqrt((xx - (cx - r * 0.3) * s) ** 2 + (yy - (cy - r * 0.35) * s) ** 2) / (r * 2 * s)
    k = np.clip(dist, 0, 1)[..., None]
    col = np.array((255, 70, 100), np.float32) * (1 - k) + np.array(ROJO_OSC, np.float32) * k
    mascara = Image.new("L", (W * s, H * s), 0)
    ImageDraw.Draw(mascara).ellipse(P(cx - r, cy - r, cx + r, cy + r), fill=255)
    cuerpo = Image.fromarray(col.astype(np.uint8)).convert("RGBA")
    cuerpo.putalpha(mascara)
    im.alpha_composite(cuerpo)
    # esfera
    rf = r * 0.8
    dr.ellipse(P(cx - rf, cy - rf, cx + rf, cy + rf), fill=CREMA)
    dr.ellipse(P(cx - rf, cy - rf, cx + rf, cy + rf), outline=(225, 220, 210), width=int(4 * s))
    for i in range(12):
        a = math.radians(i * 30 - 90)
        r0, r1 = rf * (0.8 if i % 3 else 0.74), rf * 0.9
        dr.line(P(cx + r0 * math.cos(a), cy + r0 * math.sin(a), cx + r1 * math.cos(a),
                  cy + r1 * math.sin(a)), fill=AZUL, width=int((5 if i % 3 == 0 else 3) * s))
    fn = f("Bold", int(rf * 0.3 * s))
    for n, i in ((12, 0), (3, 3), (6, 6), (9, 9)):
        a = math.radians(i * 30 - 90)
        dr.text(((cx + rf * 0.56 * math.cos(a)) * s, (cy + rf * 0.56 * math.sin(a)) * s), str(n),
                font=fn, fill=AZUL, anchor="mm")
    # agujas: las 9 en punto
    dr.line(P(cx, cy, cx - rf * 0.45, cy), fill=AZUL, width=int(rf * 0.075 * s))
    dr.line(P(cx, cy, cx, cy - rf * 0.66), fill=AZUL, width=int(rf * 0.05 * s))
    dr.line(P(cx, cy + rf * 0.15, cx + rf * 0.5, cy - rf * 0.5), fill=ROJO,
            width=int(rf * 0.02 * s))
    dr.ellipse(P(cx - rf * 0.07, cy - rf * 0.07, cx + rf * 0.07, cy + rf * 0.07), fill=ROJO)
    # brillo
    brillo = Image.new("RGBA", (W * s, H * s), (0, 0, 0, 0))
    ImageDraw.Draw(brillo).ellipse(P(cx - r * 0.78, cy - r * 0.9, cx - r * 0.25, cy - r * 0.45),
                                   fill=(255, 255, 255, 110))
    im.alpha_composite(brillo.filter(ImageFilter.GaussianBlur(10 * s)))
    return im.resize((W, H), Image.LANCZOS)


# ----------------------------------------------------------------- piezas
def titulo(f, tam):
    f1 = f("ExtraBold", tam)
    f2 = f("Script", int(tam * 1.4))
    w = int(max(f1.getlength("Horario de"), f2.getlength("atención"))) + 60
    h = int(tam * 2.45)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((w / 2, tam * 0.55), "Horario de", font=f1, fill=AZUL, anchor="mm")
    d.text((w / 2, tam * 1.62), "atención", font=f2, fill=ROJO, anchor="mm")
    return im.crop(im.getbbox())


def franja(f, etiqueta, hora, w, h):
    """Píldora de dos tonos: etiqueta en amarillo, hora en azul."""
    s = SS
    im = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w * s - 1, h * s - 1], radius=h * s // 2, fill=AZUL)
    corte = int(w * 0.44)
    m = Image.new("L", (w * s, h * s), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w * s - 1, h * s - 1], radius=h * s // 2,
                                        fill=255)
    ImageDraw.Draw(m).rectangle([corte * s, 0, w * s, h * s], fill=0)
    amarillo = Image.new("RGBA", (w * s, h * s), AMARILLO + (255,))
    im.paste(amarillo, (0, 0), m)
    im = im.resize((w, h), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    d.text((corte / 2, h / 2), etiqueta, font=f("Bold", int(h * 0.42)), fill=AZUL, anchor="mm")
    d.text((corte + (w - corte) / 2, h / 2), hora, font=f("ExtraBold", int(h * 0.46)),
           fill=BLANCO, anchor="mm")
    return im


def direccion(f, tam):
    fn = f("Medium", tam)
    r = int(tam * 0.5)
    w = int(fn.getlength(DIRECCION)) + 2 * r + 18
    im = Image.new("RGBA", (w, int(tam * 2.4)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cy = tam * 0.9
    d.ellipse([0, cy - r * 1.15, 2 * r, cy + r * 0.85], fill=ROJO)
    d.polygon([(r * 0.28, cy + r * 0.35), (r * 1.72, cy + r * 0.35), (r, cy + r * 1.5)], fill=ROJO)
    d.ellipse([r * 0.62, cy - r * 0.53, r * 1.38, cy + r * 0.23], fill=CREMA)
    d.text((2 * r + 18, cy), DIRECCION, font=fn, fill=(70, 78, 130), anchor="lm")
    return im.crop(im.getbbox())


def contacto(f, tam):
    fn = f("Bold", tam)
    fu = f("Medium", int(tam * 0.68))
    rw = int(tam * 0.55)
    w = int(max(fn.getlength(WHATSAPP) + 2 * rw + 20, fu.getlength(USUARIO))) + 20
    im = Image.new("RGBA", (w, int(tam * 2.6)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    tw = fn.getlength(WHATSAPP) + 2 * rw + 20
    x0, cy = (w - tw) / 2, tam * 0.7
    d.ellipse([x0, cy - rw, x0 + 2 * rw, cy + rw], fill=VERDE_WA)
    d.arc([x0 + rw * 0.5, cy - rw * 0.5, x0 + rw * 1.5, cy + rw * 0.5], 100, 260, fill=BLANCO,
          width=max(3, int(rw * 0.22)))
    d.text((x0 + 2 * rw + 20, cy), WHATSAPP, font=fn, fill=BLANCO, anchor="lm")
    d.text((w / 2, tam * 1.95), USUARIO, font=fu, fill=(190, 200, 255), anchor="mm")
    return im


# ----------------------------------------------------------------- armado
def armar(foto, f, W, H, caja_foto, alto_foto, y_tarjeta, alto_tarjeta, k, salida):
    # fondo azul con degradado
    y = np.linspace(0, 1, H)[:, None, None]
    base = np.broadcast_to(np.array(AZUL_2, np.float32) * (1 - y) +
                           np.array(AZUL, np.float32) * y, (H, W, 3))
    img = Image.fromarray(base.astype(np.uint8)).convert("RGBA")
    # foto arriba, que se funde en el azul
    ft = foto.crop(caja_foto).resize((W, alto_foto), Image.LANCZOS).convert("RGBA")
    a = np.ones((alto_foto, W), np.float32)
    ini = int(alto_foto * 0.55)
    a[ini:] = np.linspace(1, 0, alto_foto - ini)[:, None] ** 1.2
    ft.putalpha(Image.fromarray((a * 255).astype(np.uint8)))
    img.alpha_composite(ft)
    velo = np.zeros((H, W, 4), np.uint8)
    velo[..., :3] = AZUL
    yy = np.arange(H, dtype=np.float32)
    velo[..., 3] = (np.clip((yy - alto_foto * 0.45) / (alto_foto * 0.5), 0, 1) * 120
                    ).astype(np.uint8)[:, None]
    img.alpha_composite(Image.fromarray(velo, "RGBA"))

    # tarjeta
    m = int(70 * k)
    tw, th = W - 2 * m, alto_tarjeta
    t = Image.new("RGBA", (tw * SS, th * SS), (0, 0, 0, 0))
    ImageDraw.Draw(t).rounded_rectangle([0, 0, tw * SS - 1, th * SS - 1], radius=56 * SS,
                                        fill=CREMA)
    t = t.resize((tw, th), Image.LANCZOS)
    st, pad = sombra(t, 26, 170, (0, 18))
    img.alpha_composite(st, (m - pad, y_tarjeta - pad))

    rl = reloj(f, int(250 * k))
    centrar(img, rl, W / 2, y_tarjeta - int(10 * k), radio=14, alfa=110)
    yb = y_tarjeta + int(150 * k)
    ti = titulo(f, int(84 * k))
    img.alpha_composite(ti, (int(W / 2 - ti.width / 2), yb))
    yb += ti.height + int(40 * k)
    fw, fh = int(tw * 0.82), int(92 * k)
    for et, hora in FRANJAS:
        fr = franja(f, et, hora, fw, fh)
        centrar(img, fr, W / 2, yb + fh / 2, radio=8, alfa=70, offset=(0, 5))
        yb += fh + int(22 * k)
    yb += int(14 * k)
    dr = direccion(f, int(30 * k))
    img.alpha_composite(dr, (int(W / 2 - dr.width / 2), yb))

    ct = contacto(f, int(40 * k))
    yc = y_tarjeta + th + int(60 * k)
    img.alpha_composite(ct, (int(W / 2 - ct.width / 2), yc))
    img.convert("RGB").save(salida)
    return yb + dr.height, yc + ct.height


def main():
    foto_p, fuentes, salida = sys.argv[1:4]
    f = F(fuentes)
    foto = Image.open(foto_p).convert("RGB")
    foto = ImageEnhance.Contrast(foto).enhance(1.05)
    foto = ImageEnhance.Color(foto).enhance(1.06)
    # historia: la cara queda debajo de la barra de perfil de Instagram
    print("historia", armar(foto, f, 1080, 1920, (0, 560, 1150, 1625), 1000, 760, 730, 1.0,
                            f"{salida}/frami_horario_historia.png"))
    print("feed", armar(foto, f, 1080, 1350, (0, 690, 1150, 1440), 705, 560, 610, 0.86,
                        f"{salida}/frami_horario_feed.png"))


if __name__ == "__main__":
    main()
