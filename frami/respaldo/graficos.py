"""Motion graphics del Reel de FRAMI "Respaldo" (seguro de vida + adicional de enfermedades
graves), en el mismo estilo de UI "vidrio" que el Reel anterior: lista con checks / pregunta,
alerta con ícono, comparación, escena a pantalla completa, barra de comentario que se escribe
sola y texto detrás de la persona.

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

    def __init__(self, f, ini, fin, items, titulo="Su objetivo real…"):
        # items: [(t_aparece, t_check, línea1, línea2[, "check" | "pregunta"])]
        self.f, self.ini, self.fin, self.items, self.titulo = f, ini, fin, items, titulo
        fz = 74
        while f("ExtraBold", fz).getlength(titulo) > W - 90:
            fz -= 2
        self.fz = fz

    def dibujar(self, img, tv):
        if not self.ini <= tv < self.fin:
            return
        salida = 1 - ease_out(clamp((tv - (self.fin - 0.3)) / 0.3))
        # título arriba
        k = ease_out((tv - self.ini) / 0.4)
        tit = Image.new("RGBA", (W, 140), (0, 0, 0, 0))
        ImageDraw.Draw(tit).text((W / 2, 70), self.titulo, font=self.f("ExtraBold", self.fz),
                                 fill=BLANCO, anchor="mm")
        pegar(img, sombra(tit, 12, 160, (0, 6)), W / 2, 330 - 30 * (1 - k), 1, k * salida)
        # ítems entre el mentón y los subtítulos
        for i, item in enumerate(self.items):
            ta, tc, l1, l2 = item[:4]
            pregunta = len(item) > 4 and item[4] == "pregunta"
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
            d.text((34, 52), f"0{i + 1}", font=self.f("Bold", 30),
                   fill=ROJO if pregunta else AMARILLO, anchor="lm")
            if l2:
                d.text((96, 36), l1, font=self.f("ExtraBold", 38), fill=BLANCO, anchor="lm")
                d.text((96, 74), l2, font=self.f("SemiBold", 32), fill=(140, 190, 255),
                       anchor="lm")
            else:
                d.text((96, 52), l1, font=self.f("ExtraBold", 42), fill=BLANCO, anchor="lm")
            kc = (tv - tc) / 0.3
            if kc > 0 and pregunta:
                r = 26 * (0.7 + 0.3 * ease_back(min(kc * 1.5, 1)))
                d.ellipse([880 - 60 - r, 52 - r, 880 - 60 + r, 52 + r], fill=ROJO)
                d.text((880 - 60, 50), "?", font=self.f("ExtraBold", max(8, int(r * 1.5))),
                       fill=BLANCO, anchor="mm")
            elif kc > 0:
                check(d, 880 - 60, 52, 26 * (0.7 + 0.3 * ease_back(min(kc * 1.5, 1))), kc)
            else:
                d.ellipse([880 - 86, 26, 880 - 34, 78], outline=(255, 255, 255, 90), width=3)
            pegar(img, capa, cx, cy, esc, alfa)

    def eventos(self):
        ev = [(self.ini + 0.03, "pop", 0.9)]
        for item in self.items:
            ta, tc = item[:2]
            ev += [(ta + 0.03, "pop", 0.8), (tc, "click", 1.2)]
        return ev


# ------------------------------------------------------------------ escena completa
class Escena:
    """Pantalla completa: dos tarjetas (A + B) -> resultado. Entra con un círculo que se abre
    y sale deslizándose hacia arriba. En este Reel: SEGURO DE VIDA + ADICIONAL ENFERMEDADES
    GRAVES -> 'al diagnóstico contás con una SUMA DE DINERO'."""

    def __init__(self, f, ini, fin, t_mas, t_comp, titulo="Seguro de vida",
                 subtitulo="+ adicional de enfermedades graves",
                 nombres=("SEGURO\nDE VIDA", "ENFERMEDADES\nGRAVES"),
                 resultado=("al diagnóstico contás con una", "SUMA DE DINERO")):
        self.f, self.ini, self.fin, self.t_mas, self.t_comp = f, ini, fin, t_mas, t_comp
        self.titulo, self.subtitulo, self.nombres, self.resultado = \
            titulo, subtitulo, nombres, resultado
        self.fondo = self._fondo()
        self.iconos = (self._icono_seguro(), self._icono_salud())

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

    def _icono_salud(self):
        """Corazón con línea de pulso."""
        s = 3
        im = Image.new("RGBA", (190 * s, 170 * s), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        r = 46
        d.ellipse([(95 - 2 * r + 4) * s, 14 * s, (95 + 4) * s, (14 + 2 * r) * s], fill=ROJO)
        d.ellipse([(95 - 4) * s, 14 * s, (95 + 2 * r - 4) * s, (14 + 2 * r) * s], fill=ROJO)
        d.polygon([((95 - 2 * r + 9) * s, (14 + r + 20) * s), (95 * s, 160 * s),
                   ((95 + 2 * r - 9) * s, (14 + r + 20) * s), (95 * s, 50 * s)], fill=ROJO)
        pts = [(8, 88), (58, 88), (74, 60), (94, 118), (112, 70), (126, 88), (182, 88)]
        d.line([(x * s, y * s) for x, y in pts], fill=BLANCO, width=10 * s, joint="curve")
        return im.resize((190, 170), Image.LANCZOS)

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
        dt.text((W / 2, 80), self.titulo, font=self.f("ExtraBold", 100), fill=BLANCO,
                anchor="mm")
        fs = 58
        while self.f("SemiBold", fs).getlength(self.subtitulo) > W - 100:
            fs -= 2
        dt.text((W / 2, 185), self.subtitulo, font=self.f("SemiBold", fs),
                fill=(170, 190, 255), anchor="mm")
        pegar(esc_, tit, W / 2, 470 - 40 * (1 - k), 1, k)
        # dos tarjetas de vidrio con íconos
        for i, (nombre, icono) in enumerate(zip(self.nombres, self.iconos)):
            kk = (tv - self.ini - 0.15 - i * 0.15) / 0.4
            if kk <= 0:
                continue
            cx = 290 if i == 0 else 790
            cy = 900 + 60 * (1 - ease_out(kk))
            esc = 0.8 + 0.2 * ease_back(kk)
            vidrio(esc_, cx, cy, 380, 400, radio=40, tinte=(255, 255, 255, 28),
                   alfa=clamp(kk * 2), esc=esc)
            capa = Image.new("RGBA", (380, 400), (0, 0, 0, 0))
            capa.alpha_composite(icono, ((380 - icono.width) // 2, 50))
            fn = 56
            while max(self.f("ExtraBold", fn).getlength(l) for l in nombre.split("\n")) > 330:
                fn -= 2
            ImageDraw.Draw(capa).multiline_text((190, 315), nombre, font=self.f("ExtraBold", fn),
                                                fill=BLANCO, anchor="mm", align="center",
                                                spacing=4)
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
            pre, grande = self.resultado
            fp = 60
            while self.f("SemiBold", fp).getlength(pre) > W - 100:
                fp -= 2
            dc.text((W / 2, 50), pre, font=self.f("SemiBold", fp), fill=BLANCO, anchor="mm")
            fz = 104
            while self.f("ExtraBold", fz).getlength(grande) > W - 100:
                fz -= 4
            dc.text((W / 2, 150), grande, font=self.f("ExtraBold", fz),
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
    """Barra de comentario donde se escribe un texto (acá, 'RESPALDO') y se envía."""

    def __init__(self, f, logo, ini, fin, t_escribe, t_fin_escribe, texto="RESPALDO"):
        self.TEXTO = texto
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


# ------------------------------------------------------------------ alerta (hogar)
class Alerta:
    """Casa con '$' y una alerta roja: 'pone a prueba la ESTABILIDAD económica de tu hogar'."""

    def __init__(self, f, ini, fin, t_alerta):
        self.f, self.ini, self.fin, self.t_alerta = f, ini, fin, t_alerta

    def _casa(self, k):
        s = 3
        im = Image.new("RGBA", (220 * s, 200 * s), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.polygon([(100 * s, 18 * s), (190 * s, 92 * s), (10 * s, 92 * s)], fill=ROJO,
                  outline=BLANCO, width=4 * s)
        d.rectangle([32 * s, 88 * s, 168 * s, 186 * s], fill=BLANCO)
        d.rectangle([84 * s, 128 * s, 116 * s, 186 * s], fill=AZUL)
        d.ellipse([42 * s, 104 * s, 80 * s, 142 * s], fill=AMARILLO)
        d.text((61 * s, 122 * s), "$", font=self.f("ExtraBold", 30 * s), fill=AZUL, anchor="mm")
        if k > 0:
            # grieta que baja por la pared mientras aparece la alerta
            pts = [(140, 92), (128, 112), (146, 128), (132, 150), (150, 170), (142, 186)]
            n = 1 + int((len(pts) - 1) * clamp(k))
            d.line([(x * s, y * s) for x, y in pts[:n]], fill=AZUL, width=5 * s,
                   joint="curve")
            r = 38 * s * (0.6 + 0.4 * ease_back(k))
            cx, cy = 182 * s, 44 * s
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=AMARILLO, outline=BLANCO, width=5 * s)
            d.text((cx, cy - 2 * s), "!", font=self.f("ExtraBold", int(max(8, r * 1.4))),
                   fill=AZUL, anchor="mm")
        return im.resize((220, 200), Image.LANCZOS)

    def dibujar(self, img, tv):
        e = entrada_salida(tv, self.ini, self.fin)
        if not e:
            return
        esc, alfa, dy = e
        cx, cy = W / 2, 395 + dy  # más arriba: en el 3993 la cabeza queda alta
        vidrio(img, cx, cy, 900, 300, alfa=alfa, esc=esc)
        capa = Image.new("RGBA", (900, 300), (0, 0, 0, 0))
        capa.alpha_composite(self._casa((tv - self.t_alerta) / 0.4), (30, 50))
        d = ImageDraw.Draw(capa)
        d.text((280, 80), "Pone a prueba la", font=self.f("Bold", 46), fill=BLANCO, anchor="lm")
        d.text((280, 150), "ESTABILIDAD", font=self.f("ExtraBold", 66), fill=ROJO, anchor="lm")
        d.text((280, 220), "económica de tu hogar", font=self.f("SemiBold", 40),
               fill=AMARILLO, anchor="lm")
        pegar(img, capa, cx, cy, esc, alfa)

    def eventos(self):
        return [(self.ini + 0.03, "pop", 1.0), (self.t_alerta, "click", 1.2)]


# ------------------------------------------------------------------ comparación
class Comparacion:
    """Dos píldoras ('SIN obra social' / 'CON la mejor obra social') y, debajo, una banda
    roja: 'igual hay GASTOS NO CONTEMPLADOS'."""

    def __init__(self, f, ini, fin, t_a, t_b, t_res):
        self.f, self.ini, self.fin = f, ini, fin
        self.t_a, self.t_b, self.t_res = t_a, t_b, t_res

    def _pildora(self, tit, sub, color):
        w, h = 420, 150
        capa = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(capa)
        d.text((w / 2, 56), tit, font=self.f("ExtraBold", 52), fill=color, anchor="mm")
        d.text((w / 2, 108), sub, font=self.f("SemiBold", 32), fill=BLANCO, anchor="mm")
        return capa

    def dibujar(self, img, tv):
        if not self.ini <= tv < self.fin:
            return
        salida = 1 - ease_out(clamp((tv - (self.fin - 0.3)) / 0.3))
        for i, (t, tit, sub, color, cx) in enumerate([
                (self.t_a, "SIN", "obra social", AMARILLO, 300),
                (self.t_b, "CON", "la mejor obra social", AMARILLO, 780)]):
            k = (tv - t) / 0.35
            if k <= 0:
                continue
            esc = 0.85 + 0.15 * ease_back(k)
            alfa = clamp(k * 2.5) * salida
            cy = 345 + 40 * (1 - ease_out(k))
            vidrio(img, cx, cy, 440, 170, radio=40, alfa=alfa, esc=esc)
            pegar(img, self._pildora(tit, sub, color), cx, cy, esc, alfa)
        # "=" entre las píldoras y la banda
        k = (tv - self.t_res) / 0.35
        if k > 0:
            alfa = clamp(k * 2.5) * salida
            w, h = 900, 150
            banda = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            bd = ImageDraw.Draw(banda)
            bd.rounded_rectangle([0, 0, w - 1, h - 1], radius=36, fill=ROJO)
            bd.rounded_rectangle([30, h - 16, 150, h - 8], radius=4, fill=AMARILLO)
            bd.text((w / 2, 46), "igual hay", font=self.f("SemiBold", 36), fill=BLANCO,
                    anchor="mm")
            bd.text((w / 2, 100), "GASTOS NO CONTEMPLADOS", font=self.f("ExtraBold", 54),
                    fill=BLANCO, anchor="mm")
            x = W / 2 - 200 * (1 - ease_out(k))
            pegar(img, sombra(banda, 14, 110, (0, 10)), x, 528, 0.85 + 0.15 * ease_back(k), alfa)

    def eventos(self):
        return [(self.t_a + 0.03, "pop", 0.9), (self.t_b + 0.03, "pop", 0.9),
                (self.t_res, "click", 1.2)]
