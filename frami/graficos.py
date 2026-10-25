"""Motion graphics extra del Reel de FRAMI, inspirados en el estilo de UI "vidrio":
tarjeta de perfil, lista con checks, ícono de énfasis, escena a pantalla completa,
barra de comentario que se escribe sola y texto detrás de la persona.

Cada gráfico expone dibujar(img, tv) (tv = segundos de voz) y eventos() con los efectos
de sonido [(tv, tipo, ganancia)].
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1080, 1920
SS = 2

ROJO = (232, 0, 61)
AMARILLO = (245, 196, 0)
AZUL = (8, 8, 96)
BLANCO = (255, 255, 255)
GRIS = (200, 205, 220)


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_back(x, s=1.6):
    x = clamp(x)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def entrada_salida(tv, ini, fin, t_in=0.35, t_out=0.25):
    """(escala, alfa, desplazamiento_y) para una entrada con rebote y salida suave."""
    if tv < ini or tv >= fin:
        return None
    if tv - ini < t_in:
        k = (tv - ini) / t_in
        return 0.85 + 0.15 * ease_back(k), clamp(k * 2.5), 40 * (1 - ease_out(k))
    if fin - tv < t_out:
        k = 1 - (fin - tv) / t_out
        return 1 - 0.06 * k, 1 - ease_out(k), -30 * ease_out(k)
    return 1.0, 1.0, 0.0


def con_alfa(im, alfa):
    if alfa >= 0.999:
        return im
    im = im.copy()
    im.putalpha(im.getchannel("A").point(lambda v: int(v * alfa)))
    return im


def pegar(base, im, cx, cy, esc=1.0, alfa=1.0):
    if esc <= 0.01 or alfa <= 0.01:
        return
    if abs(esc - 1) > 1e-3:
        im = im.resize((max(1, int(im.width * esc)), max(1, int(im.height * esc))),
                       Image.BILINEAR)
    base.alpha_composite(con_alfa(im, alfa), (int(cx - im.width / 2), int(cy - im.height / 2)))


def sombra(capa, radio=16, alfa=110, offset=(0, 10)):
    s = Image.new("RGBA", capa.size, (0, 0, 0, 0))
    s.putalpha(capa.getchannel("A").point(lambda v: v * alfa // 255)
               .filter(ImageFilter.GaussianBlur(radio)))
    out = Image.new("RGBA", capa.size, (0, 0, 0, 0))
    out.alpha_composite(s, offset)
    out.alpha_composite(capa)
    return out


def rect_redondeado(w, h, radio, relleno, borde=None, grosor=3):
    im = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([grosor * SS, grosor * SS, (w - grosor) * SS - 1,
                                          (h - grosor) * SS - 1], radius=radio * SS,
                                         fill=relleno, outline=borde,
                                         width=grosor * SS if borde else 0)
    return im.resize((w, h), Image.LANCZOS)


def vidrio(base, cx, cy, w, h, radio=34, tinte=(12, 16, 90, 165), alfa=1.0, esc=1.0):
    """Tarjeta de vidrio esmerilado: desenfoca lo que hay detrás y lo tiñe de azul."""
    w2, h2 = int(w * esc), int(h * esc)
    x0, y0 = int(cx - w2 / 2), int(cy - h2 / 2)
    caja = (max(0, x0), max(0, y0), min(W, x0 + w2), min(H, y0 + h2))
    if caja[2] <= caja[0] or caja[3] <= caja[1]:
        return
    fondo = base.crop(caja).filter(ImageFilter.GaussianBlur(22))
    mascara = rect_redondeado(w2, h2, int(radio * esc), (255, 255, 255, 255)).getchannel("A")
    mascara = mascara.crop((caja[0] - x0, caja[1] - y0, caja[2] - x0, caja[3] - y0))
    mascara = mascara.point(lambda v: int(v * alfa))
    base.paste(fondo, caja[:2], mascara)
    capa = rect_redondeado(w2, h2, int(radio * esc), tinte, (255, 255, 255, 110), 3)
    base.alpha_composite(con_alfa(capa, alfa), (x0, y0))


def check(d, cx, cy, r, k=1.0, color=AMARILLO):
    """Círculo con tilde; k (0..1) anima el trazo."""
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    p0, p1, p2 = (cx - r * 0.45, cy + r * 0.02), (cx - r * 0.1, cy + r * 0.38), \
        (cx + r * 0.5, cy - r * 0.35)
    ancho = max(2, int(r * 0.22))
    if k <= 0:
        return
    k1 = clamp(k / 0.4)
    d.line([p0, (p0[0] + (p1[0] - p0[0]) * k1, p0[1] + (p1[1] - p0[1]) * k1)],
           fill=AZUL, width=ancho)
    if k > 0.4:
        k2 = clamp((k - 0.4) / 0.6)
        d.line([p1, (p1[0] + (p2[0] - p1[0]) * k2, p1[1] + (p2[1] - p1[1]) * k2)],
               fill=AZUL, width=ancho)


# ------------------------------------------------------------------ tarjeta de perfil
class Perfil:
    """Tarjeta de perfil de Instagram con botón "Seguir" que se toca."""

    def __init__(self, f, logo, ini, fin, toque):
        self.ini, self.fin, self.toque = ini, fin, toque
        self.f = f
        w, h = 720, 170
        self.w, self.h = w, h
        self.avatar = self._avatar(logo, 118)

    def _avatar(self, logo, d):
        im = Image.new("RGBA", (d * SS, d * SS), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        dr.ellipse([0, 0, d * SS - 1, d * SS - 1], fill=BLANCO)
        im = im.resize((d, d), Image.LANCZOS)
        lw = int(d * 0.62)
        lg = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
        im.alpha_composite(lg, ((d - lg.width) // 2, (d - lg.height) // 2))
        anillo = Image.new("RGBA", (d * SS + 16 * SS, d * SS + 16 * SS), (0, 0, 0, 0))
        ImageDraw.Draw(anillo).ellipse([0, 0, anillo.width - 1, anillo.height - 1],
                                       outline=AMARILLO, width=5 * SS)
        anillo = anillo.resize((d + 16, d + 16), Image.LANCZOS)
        anillo.alpha_composite(im, (8, 8))
        return anillo

    def dibujar(self, img, tv):
        e = entrada_salida(tv, self.ini, self.fin)
        if not e:
            return
        esc, alfa, dy = e
        cx, cy = 470, 1250 + dy
        vidrio(img, cx, cy, self.w, self.h, radio=44, alfa=alfa, esc=esc)
        capa = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        d = ImageDraw.Draw(capa)
        capa.alpha_composite(self.avatar, (24, (self.h - self.avatar.height) // 2))
        d.text((172, 50), "FRAMI", font=self.f("ExtraBold", 44), fill=BLANCO, anchor="lm")
        d.text((172, 96), "@frami.productoresasesores", font=self.f("SemiBold", 26),
               fill=GRIS, anchor="lm")
        d.text((172, 132), "Productores Asesores de Seguros", font=self.f("SemiBold", 22),
               fill=(160, 170, 200), anchor="lm")
        # botón: "Seguir" -> "Siguiendo" al tocarlo
        tocado = tv >= self.toque
        pulso = 1 - 0.12 * math.sin(math.pi * clamp((tv - self.toque) / 0.2))
        bw, bh = 170, 64
        boton = rect_redondeado(bw, bh, 32, (70, 76, 120, 255) if tocado else ROJO + (255,))
        ImageDraw.Draw(boton).text((bw / 2, bh / 2 - 1), "Siguiendo" if tocado else "Seguir",
                                   font=self.f("Bold", 26), fill=BLANCO, anchor="mm")
        pegar(capa, boton, self.w - 24 - bw / 2, 50, pulso)
        pegar(img, capa, cx, cy, esc, alfa)
        # dedo / cursor que toca el botón
        k = (tv - (self.toque - 0.5)) / 0.5
        if 0 <= k < 1.6:
            bx = cx + (self.w / 2 - 24 - bw / 2) * esc
            by = cy - self.h / 2 + 50
            x = bx + 140 * (1 - ease_out(min(k, 1)))
            y = by + 40 + 160 * (1 - ease_out(min(k, 1)))
            a = 1 - clamp((k - 1.2) / 0.4)
            cap = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            dc = ImageDraw.Draw(cap)
            if k >= 1:
                rr = 30 + 40 * clamp(k - 1)
                dc.ellipse([bx - rr, by - rr, bx + rr, by + rr],
                           outline=BLANCO + (int(160 * (1 - clamp(k - 1))),), width=4)
            dc.ellipse([x - 22, y - 22, x + 22, y + 22], fill=BLANCO + (int(220 * a),),
                       outline=AZUL + (int(120 * a),), width=3)
            img.alpha_composite(cap)

    def eventos(self):
        return [(self.ini + 0.03, "pop", 1.0), (self.toque, "click", 1.3)]


# ------------------------------------------------------------------ énfasis con ícono
class Enfasis:
    """Monedas con una cruz roja: 'No buscan hacerte RICO de la noche a la mañana'."""

    def __init__(self, f, ini, fin):
        self.f, self.ini, self.fin = f, ini, fin

    def _monedas(self, k_cruz):
        s = 3
        im = Image.new("RGBA", (220 * s, 200 * s), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        for i in range(4):
            y = (150 - i * 30) * s
            d.ellipse([30 * s, y - 22 * s, 170 * s, y + 22 * s], fill=(200, 150, 0),
                      outline=AZUL, width=3 * s)
            d.rectangle([30 * s, y - 34 * s, 170 * s, y], fill=AMARILLO)
            d.line([30 * s, y - 34 * s, 30 * s, y], fill=AZUL, width=3 * s)
            d.line([170 * s, y - 34 * s, 170 * s, y], fill=AZUL, width=3 * s)
            d.ellipse([30 * s, y - 56 * s, 170 * s, y - 12 * s], fill=AMARILLO,
                      outline=AZUL, width=3 * s)
        d.text((100 * s, 34 * s), "$", font=self.f("ExtraBold", 40 * s), fill=AZUL, anchor="mm")
        if k_cruz > 0:
            r = 40 * s * (0.6 + 0.4 * ease_back(k_cruz))
            cx, cy = 175 * s, 45 * s
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ROJO, outline=BLANCO, width=5 * s)
            a = r * 0.42
            d.line([cx - a, cy - a, cx + a, cy + a], fill=BLANCO, width=int(9 * s))
            d.line([cx - a, cy + a, cx + a, cy - a], fill=BLANCO, width=int(9 * s))
        return im.resize((220, 200), Image.LANCZOS)

    def dibujar(self, img, tv):
        e = entrada_salida(tv, self.ini, self.fin)
        if not e:
            return
        esc, alfa, dy = e
        cx, cy = W / 2, 420 + dy
        vidrio(img, cx, cy, 900, 300, alfa=alfa, esc=esc)
        capa = Image.new("RGBA", (900, 300), (0, 0, 0, 0))
        capa.alpha_composite(self._monedas((tv - self.ini - 0.35) / 0.3), (30, 50))
        d = ImageDraw.Draw(capa)
        d.text((280, 80), "No buscan", font=self.f("Bold", 48), fill=BLANCO, anchor="lm")
        d.text((280, 150), "hacerte ", font=self.f("ExtraBold", 64), fill=BLANCO, anchor="lm")
        x = 280 + self.f("ExtraBold", 64).getlength("hacerte ")
        d.text((x, 150), "RICO", font=self.f("ExtraBold", 64), fill=ROJO, anchor="lm")
        d.text((280, 220), "de la noche a la mañana", font=self.f("SemiBold", 38),
               fill=AMARILLO, anchor="lm")
        pegar(img, capa, cx, cy, esc, alfa)

    def eventos(self):
        return [(self.ini + 0.03, "pop", 1.0), (self.ini + 0.4, "click", 1.2)]


# ------------------------------------------------------------------ lista con checks
class Lista:
    """'Su objetivo real…' y tres ítems que aparecen y se tildan con la voz."""

    def __init__(self, f, ini, fin, items):
        # items: [(t_aparece, t_check, línea1, línea2)]
        self.f, self.ini, self.fin, self.items = f, ini, fin, items

    def dibujar(self, img, tv):
        if not self.ini <= tv < self.fin:
            return
        salida = 1 - ease_out(clamp((tv - (self.fin - 0.3)) / 0.3))
        # título arriba
        k = ease_out((tv - self.ini) / 0.4)
        tit = Image.new("RGBA", (W, 140), (0, 0, 0, 0))
        ImageDraw.Draw(tit).text((W / 2, 70), "Su objetivo real…", font=self.f("ExtraBold", 74),
                                 fill=BLANCO, anchor="mm")
        pegar(img, sombra(tit, 12, 160, (0, 6)), W / 2, 330 - 30 * (1 - k), 1, k * salida)
        # ítems entre el mentón y los subtítulos
        for i, (ta, tc, l1, l2) in enumerate(self.items):
            if tv < ta:
                continue
            k = (tv - ta) / 0.35
            esc = 0.85 + 0.15 * ease_back(k)
            alfa = clamp(k * 2.5) * salida
            cx = W / 2 - 160 * (1 - ease_out(k))
            cy = 1135 + i * 118
            vidrio(img, cx, cy, 880, 104, radio=28, alfa=alfa, esc=esc)
            capa = Image.new("RGBA", (880, 104), (0, 0, 0, 0))
            d = ImageDraw.Draw(capa)
            d.text((34, 52), f"0{i + 1}", font=self.f("Bold", 30), fill=AMARILLO, anchor="lm")
            d.text((96, 36), l1, font=self.f("ExtraBold", 38), fill=BLANCO, anchor="lm")
            d.text((96, 74), l2, font=self.f("SemiBold", 32), fill=(140, 190, 255), anchor="lm")
            kc = (tv - tc) / 0.3
            if kc > 0:
                check(d, 880 - 60, 52, 26 * (0.7 + 0.3 * ease_back(min(kc * 1.5, 1))), kc)
            else:
                d.ellipse([880 - 86, 26, 880 - 34, 78], outline=(255, 255, 255, 90), width=3)
            pegar(img, capa, cx, cy, esc, alfa)

    def eventos(self):
        ev = [(self.ini + 0.03, "pop", 0.9)]
        for ta, tc, _, _ in self.items:
            ev += [(ta + 0.03, "pop", 0.8), (tc, "click", 1.2)]
        return ev


# ------------------------------------------------------------------ escena completa
class Escena:
    """Pantalla completa: BOLSA + SEGURO -> 'son COMPLEMENTARIOS'. Entra con un círculo
    que se abre y sale deslizándose hacia arriba."""

    def __init__(self, f, ini, fin, t_mas, t_comp):
        self.f, self.ini, self.fin, self.t_mas, self.t_comp = f, ini, fin, t_mas, t_comp
        self.fondo = self._fondo()
        self.iconos = (self._icono_bolsa(), self._icono_seguro())

    def _fondo(self):
        y = np.linspace(0, 1, H)[:, None, None]
        arriba, abajo = np.array(AZUL, np.float32), np.array((24, 34, 150), np.float32)
        base = np.broadcast_to(arriba * (1 - y) + abajo * y, (H, W, 3)).copy()
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        for (cx, cy, r, col, a) in [(900, 1700, 700, ROJO, 0.55), (150, 250, 600, (60, 90, 255), 0.5),
                                    (540, 900, 500, (90, 60, 200), 0.25)]:
            g = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (r ** 2)))[..., None] * a
            base = base * (1 - g) + np.array(col, np.float32) * g
        return Image.fromarray(base.clip(0, 255).astype(np.uint8), "RGB").convert("RGBA")

    def _icono_bolsa(self):
        s = 3
        im = Image.new("RGBA", (200 * s, 160 * s), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        for i, h in enumerate([50, 80, 65, 110]):
            x = (20 + i * 42) * s
            d.rounded_rectangle([x, (150 - h) * s, x + 28 * s, 150 * s], radius=6 * s,
                                fill=(255, 255, 255, 70))
        pts = [(15, 120), (60, 90), (100, 105), (175, 35)]
        d.line([(x * s, y * s) for x, y in pts], fill=AMARILLO, width=9 * s, joint="curve")
        d.polygon([(185 * s, 22 * s), (150 * s, 30 * s), (175 * s, 58 * s)], fill=AMARILLO)
        return im.resize((200, 160), Image.LANCZOS)

    def _icono_seguro(self):
        s = 3
        im = Image.new("RGBA", (160 * s, 180 * s), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        pts = [(80, 8), (148, 34), (140, 110), (80, 172), (20, 110), (12, 34)]
        d.polygon([(x * s, y * s) for x, y in pts], fill=ROJO, outline=BLANCO, width=6 * s)
        d.line([(50 * s, 92 * s), (72 * s, 116 * s), (114 * s, 66 * s)], fill=BLANCO,
               width=12 * s, joint="curve")
        return im.resize((160, 180), Image.LANCZOS)

    def activo(self, tv):
        return self.ini <= tv < self.fin + 0.35

    def dibujar(self, img, tv):
        if not self.activo(tv):
            return
        esc_ = Image.new("RGBA", (W, H))
        esc_.paste(self.fondo)
        d = ImageDraw.Draw(esc_)
        k = ease_out((tv - self.ini) / 0.4)
        tit = Image.new("RGBA", (W, 260), (0, 0, 0, 0))
        dt = ImageDraw.Draw(tit)
        dt.text((W / 2, 80), "No compiten", font=self.f("ExtraBold", 100), fill=BLANCO,
                anchor="mm")
        dt.text((W / 2, 185), "entre sí", font=self.f("SemiBold", 58), fill=(170, 190, 255),
                anchor="mm")
        pegar(esc_, tit, W / 2, 470 - 40 * (1 - k), 1, k)
        # dos tarjetas de vidrio con íconos
        for i, (nombre, icono) in enumerate(zip(("BOLSA", "SEGURO"), self.iconos)):
            kk = (tv - self.ini - 0.15 - i * 0.15) / 0.4
            if kk <= 0:
                continue
            cx = 290 if i == 0 else 790
            cy = 900 + 60 * (1 - ease_out(kk))
            esc = 0.8 + 0.2 * ease_back(kk)
            vidrio(esc_, cx, cy, 380, 400, radio=40, tinte=(255, 255, 255, 28),
                   alfa=clamp(kk * 2), esc=esc)
            capa = Image.new("RGBA", (380, 400), (0, 0, 0, 0))
            capa.alpha_composite(icono, ((380 - icono.width) // 2, 70))
            ImageDraw.Draw(capa).text((190, 320), nombre, font=self.f("ExtraBold", 56),
                                      fill=BLANCO, anchor="mm")
            pegar(esc_, capa, cx, cy, esc, clamp(kk * 2))
        # "+" que aparece entre las tarjetas
        kp = (tv - self.t_mas) / 0.3
        if kp > 0:
            r = 58 * ease_back(kp)
            d.ellipse([540 - r, 900 - r, 540 + r, 900 + r], fill=AMARILLO)
            d.text((540, 896), "+", font=self.f("ExtraBold", int(max(8, 96 * clamp(kp)))),
                   fill=AZUL, anchor="mm")
        # "son COMPLEMENTARIOS"
        kc = (tv - self.t_comp) / 0.35
        if kc > 0:
            cap = Image.new("RGBA", (W, 240), (0, 0, 0, 0))
            dc = ImageDraw.Draw(cap)
            dc.text((W / 2, 50), "son", font=self.f("SemiBold", 60), fill=BLANCO, anchor="mm")
            fz = 104
            while self.f("ExtraBold", fz).getlength("COMPLEMENTARIOS") > W - 100:
                fz -= 4
            dc.text((W / 2, 150), "COMPLEMENTARIOS", font=self.f("ExtraBold", fz),
                    fill=AMARILLO, anchor="mm")
            pegar(esc_, cap, W / 2, 1330, 0.8 + 0.2 * ease_back(kc), clamp(kc * 2))
        # entrada: círculo que se abre; salida: la escena sube y deja ver el video
        if tv >= self.fin:
            img.alpha_composite(esc_, (0, -int(H * ease_out((tv - self.fin) / 0.35) ** 1.5)))
            return
        r = 1150 * ease_out((tv - self.ini) / 0.4) if tv < self.ini + 0.4 else 1200
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).ellipse([W / 2 - r, 900 - r, W / 2 + r, 900 + r], fill=255)
        img.paste(esc_, (0, 0), m)

    def eventos(self):
        return [(self.ini - 0.1, "whoosh", 1.0), (self.t_mas, "pop", 1.0),
                (self.t_comp, "pop", 1.0), (self.fin - 0.1, "whoosh", 0.8)]


# ------------------------------------------------------------------ barra de comentario
class Comentario:
    """Barra de comentario donde se escribe '¿Cómo estás ahorrando?' y se envía."""

    TEXTO = "¿Cómo estás ahorrando?"

    def __init__(self, f, logo, ini, fin, t_escribe, t_fin_escribe):
        self.f, self.ini, self.fin = f, ini, fin
        self.t0, self.t1 = t_escribe, t_fin_escribe
        lw = 52
        self.logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)

    def dibujar(self, img, tv):
        e = entrada_salida(tv, self.ini, self.fin)
        if not e:
            return
        esc, alfa, dy = e
        cx, cy = W / 2, 1250 + dy
        # etiqueta
        et = Image.new("RGBA", (W, 60), (0, 0, 0, 0))
        ImageDraw.Draw(et).text((W / 2 - 400, 30), "DEJÁ TU COMENTARIO", font=self.f("Bold", 30),
                                fill=AMARILLO, anchor="lm")
        pegar(img, sombra(et, 8, 150, (0, 3)), cx, cy - 100, esc, alfa)
        vidrio(img, cx, cy, 860, 120, radio=60, alfa=alfa, esc=esc)
        capa = Image.new("RGBA", (860, 120), (0, 0, 0, 0))
        d = ImageDraw.Draw(capa)
        d.ellipse([20, 22, 96, 98], fill=BLANCO)
        capa.alpha_composite(self.logo, (58 - self.logo.width // 2, 60 - self.logo.height // 2))
        n = int(len(self.TEXTO) * clamp((tv - self.t0) / (self.t1 - self.t0)))
        txt = self.TEXTO[:n]
        font = self.f("SemiBold", 42)
        if n == 0:
            d.text((120, 60), "Agregá un comentario…", font=font, fill=(150, 160, 190),
                   anchor="lm")
        else:
            d.text((120, 60), txt, font=font, fill=BLANCO, anchor="lm")
        if n < len(self.TEXTO) and int(tv * 3) % 2 == 0:  # cursor titilante
            x = 120 + font.getlength(txt) + 6
            d.rectangle([x, 36, x + 4, 84], fill=AMARILLO)
        # botón enviar (avión de papel) que se activa al terminar de escribir
        listo = tv >= self.t1
        pulso = 1 + 0.18 * math.sin(math.pi * clamp((tv - self.t1 - 0.25) / 0.25))
        bcx, bcy, r = 860 - 64, 60, 40 * pulso
        d.ellipse([bcx - r, bcy - r, bcx + r, bcy + r],
                  fill=ROJO if listo else (70, 76, 120))
        s = r / 40
        d.polygon([(bcx - 18 * s, bcy - 16 * s), (bcx + 20 * s, bcy), (bcx - 18 * s, bcy + 16 * s),
                   (bcx - 10 * s, bcy)], fill=BLANCO)
        pegar(img, capa, cx, cy, esc, alfa)

    def eventos(self):
        ev = [(self.ini + 0.03, "pop", 0.9)]
        n = len(self.TEXTO)
        for i in range(0, n, 2):
            ev.append((self.t0 + (self.t1 - self.t0) * i / n, "click", 0.35))
        ev.append((self.t1 + 0.25, "click", 1.2))
        return ev


# ------------------------------------------------------------------ texto detrás
class TextoDetras:
    """Palabra gigante detrás de la persona (la persona se recorta con rembg)."""

    def __init__(self, f, ini, fin, palabra, cy=600):
        self.f, self.ini, self.fin, self.palabra, self.cy = f, ini, fin, palabra, cy
        fz = 300
        while f("ExtraBold", fz).getlength(palabra) > W - 40:
            fz -= 6
        self.font = f("ExtraBold", fz)
        self.sesion = None
        self.cache = {}

    def activo(self, tv):
        return self.ini <= tv < self.fin

    def mascara(self, arr, nv):
        if nv not in self.cache:
            from rembg import new_session, remove
            if self.sesion is None:
                self.sesion = new_session("u2net_human_seg")
            m = remove(Image.fromarray(arr), session=self.sesion, only_mask=True,
                       post_process_mask=True)
            self.cache[nv] = np.asarray(m.convert("L"))
        return self.cache[nv]

    def capa(self, tv):
        capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(capa)
        salida = clamp((tv - (self.fin - 0.3)) / 0.3)
        x = (W - self.font.getlength(self.palabra)) / 2
        for i, letra in enumerate(self.palabra):
            k = ease_out((tv - self.ini - i * 0.05) / 0.35)
            if k <= 0:
                break
            y = self.cy + 160 * (1 - k) - 120 * ease_out(salida)
            a = int(255 * clamp(k * 1.5) * (1 - salida))
            d.text((x + 10, y + 10), letra, font=self.font, fill=AMARILLO + (a,), anchor="lm")
            d.text((x, y), letra, font=self.font, fill=ROJO + (a,), anchor="lm")
            x += self.font.getlength(letra)
        return capa

    def eventos(self):
        return [(self.ini, "whoosh", 0.9)]
