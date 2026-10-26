"""Motion graphics del Reel de FORMAS Personalizado (paleta naranja / verde del logo).

Usa las utilidades de frami/graficos.py (tarjetas de vidrio, animaciones, tildes).
Cada gráfico expone dibujar(img, tv) y eventos() -> [(tv, tipo, ganancia)].
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "frami"))
from graficos import (clamp, con_alfa, ease_back, ease_out, entrada_salida,  # noqa: E402
                      pegar, rect_redondeado, sombra, vidrio)

W, H = 1080, 1920
SS = 2

NARANJA = (245, 130, 32)
NARANJA_OSC = (237, 89, 3)
VERDE = (65, 108, 1)
LIMA = (206, 223, 0)
OSCURO = (17, 17, 17)
BLANCO = (255, 255, 255)
GRIS = (190, 196, 200)
TINTE = (20, 22, 18, 170)   # vidrio oscuro


def texto_grande(f, txt, tam, relleno=NARANJA, borde=BLANCO, grosor=0, sombra_col=None):
    """Texto Anton con sombra desplazada de color (estilo deportivo)."""
    font = f("Anton", tam)
    w = int(font.getlength(txt)) + 40
    asc, desc = font.getmetrics()
    im = Image.new("RGBA", (w, asc + desc + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if sombra_col:
        d.text((24, 26), txt, font=font, fill=sombra_col)
    d.text((20, 20), txt, font=font, fill=relleno, stroke_width=grosor, stroke_fill=borde)
    return im


def check(d, cx, cy, r, k=1.0, fondo=LIMA, tilde=OSCURO):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fondo)
    p0, p1, p2 = (cx - r * 0.45, cy + r * 0.02), (cx - r * 0.1, cy + r * 0.38), \
        (cx + r * 0.5, cy - r * 0.35)
    ancho = max(2, int(r * 0.24))
    k1 = clamp(k / 0.4)
    if k1 > 0:
        d.line([p0, (p0[0] + (p1[0] - p0[0]) * k1, p0[1] + (p1[1] - p0[1]) * k1)],
               fill=tilde, width=ancho)
    if k > 0.4:
        k2 = clamp((k - 0.4) / 0.6)
        d.line([p1, (p1[0] + (p2[0] - p1[0]) * k2, p1[1] + (p2[1] - p1[1]) * k2)],
               fill=tilde, width=ancho)


# ------------------------------------------------------------------ íconos
def icono_pin(tam=150, color=NARANJA):
    s = 3
    im = Image.new("RGBA", (tam * s, int(tam * 1.3) * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = tam * s * 0.42
    cx, cy = tam * s / 2, r + 6 * s
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    d.polygon([(cx - r * 0.82, cy + r * 0.55), (cx + r * 0.82, cy + r * 0.55),
               (cx, im.height - 8 * s)], fill=color)
    r2 = r * 0.42
    d.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], fill=BLANCO)
    return im.resize((tam, int(tam * 1.3)), Image.LANCZOS)


def icono_barras(tam=150, k=1.0):
    s = 3
    im = Image.new("RGBA", (tam * s, tam * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, h in enumerate([0.35, 0.6, 0.9]):
        x = (0.12 + i * 0.3) * tam * s
        hh = h * tam * s * clamp(k * 3 - i)
        col = LIMA if i < 2 else NARANJA
        d.rounded_rectangle([x, tam * s * 0.95 - hh, x + 0.2 * tam * s, tam * s * 0.95],
                            radius=6 * s, fill=col)
    return im.resize((tam, tam), Image.LANCZOS)


def icono_objetivo(tam=150, k=1.0):
    s = 3
    im = Image.new("RGBA", (tam * s, tam * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = tam * s / 2
    for i, (r, col) in enumerate([(0.46, NARANJA), (0.33, BLANCO), (0.2, NARANJA), (0.08, BLANCO)]):
        rr = r * tam * s
        d.ellipse([c - rr, c - rr, c + rr, c + rr], fill=col)
    # flecha que llega al centro
    kk = ease_out(k)
    x1, y1 = c + 0.62 * tam * s * (1 - kk) + 0.04 * tam * s, c - 0.62 * tam * s * (1 - kk) - 0.04 * tam * s
    d.line([(x1, y1), (x1 + 0.35 * tam * s, y1 - 0.35 * tam * s)], fill=LIMA, width=7 * s)
    d.polygon([(x1, y1), (x1 + 0.13 * tam * s, y1 - 0.02 * tam * s),
               (x1 + 0.02 * tam * s, y1 - 0.13 * tam * s)], fill=LIMA)
    return im.resize((tam, tam), Image.LANCZOS)


def icono_mancuerna(tam=90, color=OSCURO):
    s = 3
    im = Image.new("RGBA", (tam * s, int(tam * 0.6) * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    h = im.height
    d.rounded_rectangle([0.18 * tam * s, h * 0.42, 0.82 * tam * s, h * 0.58], radius=3 * s, fill=color)
    for x in (0.04, 0.78):
        d.rounded_rectangle([x * tam * s, h * 0.1, (x + 0.18) * tam * s, h * 0.9], radius=6 * s,
                            fill=color)
    return im.resize((tam, int(tam * 0.6)), Image.LANCZOS)


def icono_telefono(tam=110, color=BLANCO):
    s = 3
    im = Image.new("RGBA", (tam * s, tam * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    t = tam * s
    # auricular estilizado: dos extremos redondeados unidos por un arco grueso
    d.arc([0.12 * t, 0.12 * t, 0.98 * t, 0.98 * t], 100, 260, fill=color, width=int(0.17 * t))
    d.rounded_rectangle([0.1 * t, 0.1 * t, 0.38 * t, 0.32 * t], radius=int(0.08 * t), fill=color)
    d.rounded_rectangle([0.1 * t, 0.68 * t, 0.38 * t, 0.9 * t], radius=int(0.08 * t), fill=color)
    im = im.rotate(-40, resample=Image.BICUBIC)
    return im.resize((tam, tam), Image.LANCZOS)


def simbolo_genero(tam, mujer=True, color=BLANCO):
    s = 3
    im = Image.new("RGBA", (tam * s, tam * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    t = tam * s
    g = int(0.11 * t)
    if mujer:
        d.ellipse([0.22 * t, 0.06 * t, 0.78 * t, 0.62 * t], outline=color, width=g)
        d.line([(0.5 * t, 0.62 * t), (0.5 * t, 0.96 * t)], fill=color, width=g)
        d.line([(0.32 * t, 0.8 * t), (0.68 * t, 0.8 * t)], fill=color, width=g)
    else:
        d.ellipse([0.06 * t, 0.34 * t, 0.62 * t, 0.9 * t], outline=color, width=g)
        d.line([(0.53 * t, 0.43 * t), (0.9 * t, 0.08 * t)], fill=color, width=g)
        d.line([(0.56 * t, 0.08 * t), (0.92 * t, 0.08 * t)], fill=color, width=g)
        d.line([(0.92 * t, 0.06 * t), (0.92 * t, 0.42 * t)], fill=color, width=g)
    return im.resize((tam, tam), Image.LANCZOS)


# ------------------------------------------------------------------ gráficos
class Ubicacion:
    """'¿Sos de ITAEMBÉ GUAZÚ?' con un pin que cae."""

    def __init__(self, f, ini, fin, cy=1090):
        self.f, self.ini, self.fin, self.cy = f, ini, fin, cy
        self.pin = icono_pin(120)
        self.txt = texto_grande(f, "ITAEMBÉ GUAZÚ", 120, NARANJA, sombra_col=VERDE)

    def dibujar(self, img, tv):
        e = entrada_salida(tv, self.ini, self.fin)
        if not e:
            return
        esc, alfa, dy = e
        cy = self.cy + dy
        w = max(self.txt.width + 210, 760)
        vidrio(img, W / 2, cy, w, 260, radio=40, tinte=TINTE, alfa=alfa, esc=esc)
        capa = Image.new("RGBA", (w, 260), (0, 0, 0, 0))
        d = ImageDraw.Draw(capa)
        k = (tv - self.ini - 0.15) / 0.45
        py = -120 + 150 * ease_back(k, 2.2) if k < 1 else 30
        capa.alpha_composite(self.pin, (40, int(py) + 40))
        d.text((190, 62), "¿Sos de", font=self.f("Bold", 46), fill=BLANCO, anchor="lm")
        capa.alpha_composite(self.txt, (166, 78))
        pegar(img, capa, W / 2, cy, esc, alfa)

    def eventos(self):
        return [(self.ini + 0.03, "pop", 1.0), (self.ini + 0.5, "click", 1.0)]


class Lista:
    """Título y ítems numerados con tilde (vidrio oscuro)."""

    def __init__(self, f, ini, fin, titulo, items, y0=380):
        self.f, self.ini, self.fin, self.titulo, self.items, self.y0 = f, ini, fin, titulo, items, y0

    def dibujar(self, img, tv):
        if not self.ini <= tv < self.fin:
            return
        salida = 1 - ease_out(clamp((tv - (self.fin - 0.3)) / 0.3))
        k = ease_out((tv - self.ini) / 0.4)
        tam = 92
        while self.f("Anton", tam).getlength(self.titulo) > W - 160:
            tam -= 4
        tit = texto_grande(self.f, self.titulo, tam, BLANCO, sombra_col=NARANJA_OSC)
        pegar(img, sombra(tit, 12, 150, (0, 6)), W / 2, self.y0 - 30 * (1 - k), 1, k * salida)
        for i, (ta, tc, txt) in enumerate(self.items):
            if tv < ta:
                continue
            k = (tv - ta) / 0.35
            esc = 0.85 + 0.15 * ease_back(k)
            alfa = clamp(k * 2.5) * salida
            cx = W / 2 + 180 * (1 - ease_out(k))
            cy = self.y0 + 150 + i * 128
            vidrio(img, cx, cy, 860, 108, radio=26, tinte=TINTE, alfa=alfa, esc=esc)
            capa = Image.new("RGBA", (860, 108), (0, 0, 0, 0))
            d = ImageDraw.Draw(capa)
            d.rounded_rectangle([18, 18, 90, 90], radius=18, fill=NARANJA)
            d.text((54, 54), f"0{i + 1}", font=self.f("Anton", 44), fill=BLANCO, anchor="mm")
            d.text((114, 56), txt, font=self.f("Anton", 54), fill=BLANCO, anchor="lm")
            kc = (tv - tc) / 0.3
            if kc > 0:
                check(d, 860 - 58, 54, 28 * (0.7 + 0.3 * ease_back(min(kc * 1.5, 1))), kc)
            else:
                d.ellipse([860 - 86, 26, 860 - 30, 82], outline=(255, 255, 255, 90), width=3)
            pegar(img, capa, cx, cy, esc, alfa)

    def eventos(self):
        ev = [(self.ini + 0.03, "pop", 0.9)]
        for ta, tc, _ in self.items:
            ev += [(ta + 0.03, "pop", 0.8), (tc, "click", 1.1)]
        return ev


class NivelObjetivos:
    """Dos tarjetas con íconos (TU NIVEL / TUS OBJETIVOS) y una barra de etapas."""

    def __init__(self, f, ini, fin, t_nivel, t_obj, t_etapa):
        self.f, self.ini, self.fin = f, ini, fin
        self.t_nivel, self.t_obj, self.t_etapa = t_nivel, t_obj, t_etapa

    def dibujar(self, img, tv):
        if not self.ini <= tv < self.fin:
            return
        salida = 1 - ease_out(clamp((tv - (self.fin - 0.3)) / 0.3))
        k = ease_out((tv - self.ini) / 0.4)
        tit = texto_grande(self.f, "ADAPTAMOS LAS RUTINAS", 90, BLANCO, sombra_col=NARANJA_OSC)
        pegar(img, sombra(tit, 12, 150, (0, 6)), W / 2, 420 - 30 * (1 - k), 1, k * salida)
        for i, (t0, nombre, icono) in enumerate([(self.t_nivel, "TU NIVEL", icono_barras),
                                                 (self.t_obj, "TUS OBJETIVOS", icono_objetivo)]):
            if tv < t0:
                continue
            kk = (tv - t0) / 0.4
            cx = 290 if i == 0 else 790
            cy = 760 + 50 * (1 - ease_out(kk))
            esc = 0.8 + 0.2 * ease_back(kk)
            a = clamp(kk * 2) * salida
            vidrio(img, cx, cy, 420, 400, radio=36, tinte=TINTE, alfa=a, esc=esc)
            capa = Image.new("RGBA", (420, 400), (0, 0, 0, 0))
            ic = icono(170, clamp((tv - t0) / 0.6))
            capa.alpha_composite(ic, ((420 - ic.width) // 2, 50))
            ImageDraw.Draw(capa).text((210, 320), nombre, font=self.f("Anton", 62),
                                      fill=NARANJA if i else LIMA, anchor="mm")
            pegar(img, capa, cx, cy, esc, a)
        # barra de etapas
        if tv >= self.t_etapa:
            ke = (tv - self.t_etapa) / 0.35
            a = clamp(ke * 2) * salida
            vidrio(img, W / 2, 1110, 900, 150, radio=34, tinte=TINTE, alfa=a)
            capa = Image.new("RGBA", (900, 150), (0, 0, 0, 0))
            d = ImageDraw.Draw(capa)
            d.text((450, 38), "EN CADA ETAPA", font=self.f("Anton", 40), fill=BLANCO, anchor="mm")
            x0, x1, y = 120, 780, 100
            prog = clamp((tv - self.t_etapa - 0.2) / 1.0)
            d.rounded_rectangle([x0, y - 7, x1, y + 7], radius=7, fill=(255, 255, 255, 60))
            d.rounded_rectangle([x0, y - 7, x0 + (x1 - x0) * prog, y + 7], radius=7, fill=LIMA)
            for j in range(3):
                x = x0 + (x1 - x0) * j / 2
                on = prog >= j / 2 - 1e-3
                r = 22
                d.ellipse([x - r, y - r, x + r, y + r], fill=NARANJA if on else (80, 80, 80),
                          outline=BLANCO, width=3)
                d.text((x, y - 1), str(j + 1), font=self.f("Anton", 26), fill=BLANCO, anchor="mm")
            pegar(img, capa, W / 2, 1110, 1, a)

    def eventos(self):
        return [(self.ini + 0.03, "pop", 0.9), (self.t_nivel, "pop", 0.9),
                (self.t_obj, "pop", 0.9), (self.t_etapa, "pop", 0.8),
                (self.t_etapa + 0.2, "click", 0.6), (self.t_etapa + 0.7, "click", 0.6),
                (self.t_etapa + 1.2, "click", 0.8)]


class Rapido:
    """Overlay del recorrido acelerado: estelas de velocidad y destellos en los bordes."""

    def __init__(self, ini, fin):
        self.ini, self.fin = ini, fin
        rng = np.random.default_rng(5)
        self.lineas = [(rng.uniform(0, H), rng.uniform(80, 260), rng.uniform(2, 6),
                        rng.choice([0, 1]), rng.uniform(0, 1)) for _ in range(26)]

    def dibujar(self, img, tv):
        if not self.ini - 0.15 <= tv < self.fin + 0.15:
            return
        capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(capa)
        for y, largo, g, c, fase in self.lineas:
            x = ((tv * 2.6 + fase) % 1.0) * (W + 600) - 300
            col = (NARANJA if c else LIMA) + (150,)
            d.rounded_rectangle([x, y, x + largo * 2, y + g * 2], radius=g, fill=col)
        img.alpha_composite(capa)
        # destello blanco al entrar y al salir
        for t0 in (self.ini, self.fin):
            u = abs(tv - t0)
            if u < 0.12:
                img.alpha_composite(Image.new("RGBA", (W, H), BLANCO + (int(200 * (1 - u / 0.12)),)))

    def eventos(self):
        return [(self.ini - 0.25, "whoosh", 1.0), (self.ini + 1.5, "whoosh", 0.6),
                (self.ini + 3.0, "whoosh", 0.6), (self.fin - 0.25, "whoosh", 1.0)]


class Generos:
    """MUJERES (✓) + HOMBRES (NUEVO) + PERSONAL TRAINER."""

    def __init__(self, f, ini, fin, t_muj, t_hom, t_pt, y0=860):
        self.f, self.ini, self.fin = f, ini, fin
        self.t_muj, self.t_hom, self.t_pt, self.y0 = t_muj, t_hom, t_pt, y0
        self.sim = (simbolo_genero(70, True), simbolo_genero(70, False))
        self.mancuerna = icono_mancuerna(80)

    def dibujar(self, img, tv):
        if not self.ini <= tv < self.fin:
            return
        salida = 1 - ease_out(clamp((tv - (self.fin - 0.3)) / 0.3))
        for i, (t0, nombre, col) in enumerate([(self.t_muj, "MUJERES", NARANJA),
                                               (self.t_hom, "HOMBRES", VERDE)]):
            if tv < t0:
                continue
            k = (tv - t0) / 0.35
            esc = 0.85 + 0.15 * ease_back(k)
            a = clamp(k * 2.5) * salida
            cx = W / 2 - 200 * (1 - ease_out(k)) * (1 if i == 0 else -1)
            cy = self.y0 + i * 140
            vidrio(img, cx, cy, 760, 118, radio=30, tinte=TINTE, alfa=a, esc=esc)
            capa = Image.new("RGBA", (760, 118), (0, 0, 0, 0))
            d = ImageDraw.Draw(capa)
            d.ellipse([18, 14, 108, 104], fill=col)
            capa.alpha_composite(self.sim[i], (28, 24))
            d.text((132, 59), nombre, font=self.f("Anton", 66), fill=BLANCO, anchor="lm")
            if i == 0:
                kc = (tv - t0 - 0.3) / 0.3
                if kc > 0:
                    check(d, 760 - 62, 59, 30, kc)
            else:
                kb = ease_back((tv - t0 - 0.25) / 0.35, 2.2)
                if kb > 0:
                    b = rect_redondeado(190, 70, 35, LIMA + (255,))
                    ImageDraw.Draw(b).text((95, 34), "¡NUEVO!", font=self.f("Anton", 40),
                                           fill=OSCURO, anchor="mm")
                    b = b.rotate(-6, resample=Image.BICUBIC, expand=True)
                    pegar(capa, b, 760 - 120, 59, kb)
            pegar(img, capa, cx, cy, esc, a)
        if tv >= self.t_pt:
            k = (tv - self.t_pt) / 0.35
            a = clamp(k * 2.5) * salida
            cy = self.y0 + 280
            p = rect_redondeado(640, 104, 52, NARANJA + (255,))
            d = ImageDraw.Draw(p)
            p.alpha_composite(self.mancuerna, (36, 28))
            d.text((140, 52), "PERSONAL TRAINER", font=self.f("Anton", 56), fill=BLANCO,
                   anchor="lm")
            pegar(img, sombra(p, 12, 120, (0, 8)), W / 2, cy, 0.8 + 0.2 * ease_back(k), a)

    def eventos(self):
        return [(self.t_muj, "pop", 0.9), (self.t_muj + 0.3, "click", 1.0),
                (self.t_hom, "pop", 0.9), (self.t_hom + 0.25, "pop", 1.0),
                (self.t_pt, "pop", 1.0)]


class Telefono:
    """Tarjeta con el número de contacto y un teléfono que vibra."""

    NUMERO = "3764380373"

    def __init__(self, f, ini, fin, cy=1060):
        self.f, self.ini, self.fin, self.cy = f, ini, fin, cy
        self.tel = icono_telefono(96)

    def dibujar(self, img, tv):
        e = entrada_salida(tv, self.ini, self.fin)
        if not e:
            return
        esc, alfa, dy = e
        cy = self.cy + dy
        vidrio(img, W / 2, cy, 900, 250, radio=44, tinte=TINTE, alfa=alfa, esc=esc)
        capa = Image.new("RGBA", (900, 250), (0, 0, 0, 0))
        d = ImageDraw.Draw(capa)
        d.text((450, 52), "COMUNICATE AL", font=self.f("Anton", 44), fill=LIMA, anchor="mm")
        # botón redondo con teléfono que vibra
        d.ellipse([40, 100, 170, 230], fill=NARANJA)
        ang = 12 * math.sin(tv * 40) if (tv - self.ini) % 1.2 < 0.5 else 0
        tel = self.tel.rotate(ang, resample=Image.BICUBIC)
        capa.alpha_composite(tel, (105 - tel.width // 2, 165 - tel.height // 2))
        n = texto_grande(self.f, self.NUMERO, 118, BLANCO, sombra_col=NARANJA_OSC)
        capa.alpha_composite(n, (190, 165 - n.height // 2 + 8))
        pegar(img, capa, W / 2, cy, esc, alfa)

    def eventos(self):
        return [(self.ini + 0.03, "pop", 1.1), (self.ini + 0.4, "click", 0.8),
                (self.ini + 1.6, "click", 0.8)]


class TextoDetras:
    """Palabra gigante detrás de la persona (recortada con rembg)."""

    def __init__(self, f, ini, fin, palabra, cy, destellos=False):
        self.f, self.ini, self.fin, self.palabra, self.cy = f, ini, fin, palabra, cy
        self.destellos = destellos
        fz = 360
        while f("Anton", fz).getlength(palabra) > W - 60:
            fz -= 6
        self.font = f("Anton", fz)
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
            y = self.cy + 180 * (1 - k) - 120 * ease_out(salida)
            a = int(255 * clamp(k * 1.5) * (1 - salida))
            d.text((x + 12, y + 12), letra, font=self.font, fill=VERDE + (a,), anchor="lm")
            d.text((x, y), letra, font=self.font, fill=NARANJA + (a,), anchor="lm")
            x += self.font.getlength(letra)
        if self.destellos:
            for j, (sx, sy) in enumerate([(150, -170), (930, -140), (880, 170), (200, 150)]):
                kk = clamp((tv - self.ini - 0.3 - j * 0.12) / 0.3)
                if kk <= 0 or salida >= 1:
                    continue
                r = 34 * math.sin(math.pi * clamp(kk)) + 14
                cx, cy = sx, self.cy + sy
                pts = []
                for q in range(8):
                    rr = r if q % 2 == 0 else r * 0.3
                    a_ = math.pi / 4 * q
                    pts.append((cx + rr * math.cos(a_), cy + rr * math.sin(a_)))
                d.polygon(pts, fill=LIMA + (int(255 * (1 - salida)),))
        return capa

    def eventos(self):
        return [(self.ini, "whoosh", 0.9)]


class Cierre:
    """Logo del gimnasio, 'Te esperamos', número y ubicación sobre fondo oscuro."""

    def __init__(self, f, logo):
        self.f = f
        self.logo = logo
        self.fondo = self._fondo()
        self.tel = icono_telefono(64)
        self.pin = icono_pin(56, LIMA)

    def _fondo(self):
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        base = np.zeros((H, W, 3), np.float32) + np.array(OSCURO, np.float32)
        for cx, cy, r, col, a in [(1000, 300, 650, NARANJA_OSC, 0.35), (60, 1650, 700, VERDE, 0.45)]:
            g = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / r ** 2))[..., None] * a
            base = base * (1 - g) + np.array(col, np.float32) * g
        return Image.fromarray(base.clip(0, 255).astype(np.uint8)).convert("RGBA")

    def __call__(self, t):
        img = self.fondo.copy()
        d = ImageDraw.Draw(img)
        # arcos de marca que giran (como los del logo)
        for i, (r, col, a0) in enumerate([(600, NARANJA, 200), (660, LIMA, 20), (720, VERDE, 230)]):
            k = ease_out((t - i * 0.08) / 0.6)
            if k <= 0:
                continue
            ext = 110 * k
            rot = t * (25 + 10 * i)
            d.arc([W / 2 - r, 780 - r, W / 2 + r, 780 + r], a0 + rot, a0 + rot + ext,
                  fill=col, width=18)
        lw = 560
        lg = self.logo.resize((lw, int(self.logo.height * lw / self.logo.width)), Image.LANCZOS)
        pegar(img, lg, W / 2, 760, ease_back((t - 0.05) / 0.45))
        k = ease_out((t - 0.45) / 0.35)
        if k > 0:
            tx = texto_grande(self.f, "¡TE ESPERAMOS!", 120, NARANJA, sombra_col=VERDE)
            pegar(img, tx, W / 2, 1180 + 40 * (1 - k), 1, k)
        k = ease_back((t - 0.7) / 0.35)
        if k > 0:
            p = rect_redondeado(660, 120, 60, NARANJA + (255,))
            p.alpha_composite(self.tel, (34, 28))
            ImageDraw.Draw(p).text((390, 58), Telefono.NUMERO, font=self.f("Anton", 72),
                                   fill=BLANCO, anchor="mm")
            pegar(img, sombra(p, 12, 140, (0, 8)), W / 2, 1360, k)
        k = ease_out((t - 0.9) / 0.35)
        if k > 0:
            c = Image.new("RGBA", (W, 90), (0, 0, 0, 0))
            dc = ImageDraw.Draw(c)
            font = self.f("Bold", 46)
            tw = font.getlength("Itaembé Guazú")
            x0 = (W - tw - 70) / 2
            c.alpha_composite(self.pin, (int(x0), 8))
            dc.text((x0 + 70, 45), "Itaembé Guazú", font=font, fill=BLANCO, anchor="lm")
            pegar(img, c, W / 2, 1500 + 20 * (1 - k), 1, k)
        return img

    def eventos(self, t0):
        return [(t0 - 0.3, "whoosh", 1.0), (t0 + 0.08, "pop", 1.1), (t0 + 0.47, "pop", 0.9),
                (t0 + 0.72, "pop", 0.9), (t0 + 0.92, "click", 0.8)]
