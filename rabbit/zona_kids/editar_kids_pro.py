"""Zona Kids de Rabbit, versión "pro" (1080x1920, sin música: la agrega la usuaria).

Parte de la base estabilizada y mejorada con IA (base_mejorada.py) y suma:
- aceleración con desenfoque de movimiento en el tramo borroso del tobogán,
- acercamiento lento y continuo (dolly) + golpe de zoom en la aceleración,
- corrección de color con viñeta,
- tipografía animada con máscaras (apertura, textos editoriales con barra roja, etiqueta fija),
- placa final: el último cuadro se congela, se desenfoca y entra el logo.

Uso: python3 editar_kids_pro.py <base_mejorada.mp4> <emblema.png> <dir_fuentes> <dir_sfx> <salida_base>
Genera <salida_base>_sin_audio.mp4, <salida_base>_efectos.mp4 y <salida_base>_portada.png.
<dir_sfx> debe tener whoosh.wav, pop.wav y click.wav.
"""
import math
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", "proximamente"))
from flyer_proximamente import F, ROJO, insignia, sombra  # noqa: E402

W, H, FPS = 1080, 1920, 30
BLANCO = (255, 255, 255)
GRIS = (200, 200, 208)

# ----------------------------------------------------------------- tiempos
SRC_FIN = 11.4                   # se descarta el final (poste fuera de foco)
RAMPA = (3.3, 6.2)               # tramo borroso del tobogán (tiempo de la fuente)
VEL_MAX = 2.8                    # velocidad máxima en la aceleración
PLACA = 2.6                      # duración de la placa final


def velocidad(s):
    if RAMPA[0] <= s <= RAMPA[1]:
        u = (s - RAMPA[0]) / (RAMPA[1] - RAMPA[0])
        return 1 + (VEL_MAX - 1) * math.sin(math.pi * u) ** 2
    return 1.0


def mapa_tiempo():
    """Tabla tiempo de salida -> tiempo de la fuente (integrando 1/velocidad)."""
    ds = 1 / 600
    s, t, tabla = 0.0, 0.0, [(0.0, 0.0)]
    while s < SRC_FIN:
        t += ds / velocidad(s + ds / 2)
        s += ds
        tabla.append((t, s))
    return np.array(tabla)


TABLA = mapa_tiempo()
T_VIDEO = float(TABLA[-1, 0])            # fin del metraje en la salida
T_RAMPA = (float(np.interp(RAMPA[0], TABLA[:, 1], TABLA[:, 0])),
           float(np.interp(RAMPA[1], TABLA[:, 1], TABLA[:, 0])))
DUR = T_VIDEO + PLACA

# Textos (tiempo de salida)
T_TITULO = (0.15, 2.35)
T_ETIQUETA = 2.45
T_TEXTO_A = (2.6, T_RAMPA[1] + 0.2)
T_TEXTO_B = (T_RAMPA[1] + 0.55, T_RAMPA[1] + 3.4)


def fuente_en(t):
    return float(np.interp(t, TABLA[:, 0], TABLA[:, 1]))


# ----------------------------------------------------------------- utilidades
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in(x):
    x = clamp(x)
    return x ** 3


def ease_in_out(x):
    x = clamp(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_back(x, s=1.6):
    x = clamp(x)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


# ----------------------------------------------------------------- lectura de cuadros
class Fuente:
    """Lee la base en orden y devuelve el promedio de los cuadros entre s0 y s1
    (desenfoque de movimiento natural en la aceleración)."""

    def __init__(self, path):
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo",
                                   "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.buf = {}
        self.leidos = 0
        self.fin = False

    def _hasta(self, n):
        while self.leidos <= n and not self.fin:
            b = self.p.stdout.read(W * H * 3)
            if len(b) < W * H * 3:
                self.fin = True
                break
            self.buf[self.leidos] = np.frombuffer(b, np.uint8).reshape(H, W, 3)
            self.leidos += 1

    def cuadro(self, s0, s1):
        a, b = int(round(s0 * FPS)), max(int(round(s0 * FPS)), int(round(s1 * FPS)))
        self._hasta(b)
        for k in [k for k in self.buf if k < a - 2]:
            del self.buf[k]
        idx = [k for k in range(a, b + 1) if k in self.buf] or [max(self.buf)]
        if len(idx) == 1:
            return self.buf[idx[0]].astype(np.float32)
        return np.mean([self.buf[k].astype(np.float32) for k in idx], axis=0)


# ----------------------------------------------------------------- color
def preparar_color():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
    viñeta = (1 - 0.38 * np.clip(r - 0.35, 0, 1) ** 1.6)[..., None]
    x = np.arange(256, dtype=np.float32) / 255
    curva = np.clip(x + 0.16 * (x - 0.5) * (1 - np.abs(2 * x - 1)) * 2, 0, 1)
    return viñeta, (curva * 255).astype(np.float32)


VIÑETA, CURVA = preparar_color()


def corregir(a):
    a = CURVA[np.clip(a, 0, 255).astype(np.uint8)]
    gris = a.mean(axis=2, keepdims=True)
    a = gris + (a - gris) * 1.06                       # un poco más de color
    a[..., 0] *= 1.015                                 # luces apenas cálidas
    a[..., 2] *= 0.99
    return np.clip(a * VIÑETA, 0, 255).astype(np.uint8)


def dolly(img, z, cx=0.5, cy=0.5):
    if z <= 1.0005:
        return img
    cw, ch = W / z, H / z
    x0 = clamp(cx * W - cw / 2, 0, W - cw)
    y0 = clamp(cy * H - ch / 2, 0, H - ch)
    return img.transform((W, H), Image.EXTENT, (x0, y0, x0 + cw, y0 + ch), Image.BICUBIC)


# ----------------------------------------------------------------- tipografía
def texto(fn, t, color, espaciado=0):
    """Capa RGBA con el texto (con espaciado entre letras opcional)."""
    asc, desc = fn.getmetrics()
    ancho = int(sum(fn.getlength(c) for c in t) + espaciado * (len(t) - 1)) + 4
    im = Image.new("RGBA", (ancho, asc + desc), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 0
    for c in t:
        d.text((x, 0), c, font=fn, fill=color)
        x += fn.getlength(c) + espaciado
    return im


def revelar(base, capa, x, y, k, desde="abajo"):
    """Pega 'capa' en (x, y) recortada a su propia caja: entra deslizándose (máscara)."""
    if k <= 0:
        return
    w, h = capa.size
    if desde == "abajo":
        dy = int(h * (1 - ease_out(k)))
        rec = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        rec.alpha_composite(capa, (0, dy))
    elif desde == "arriba":              # salida: se va hacia arriba
        dy = int(h * ease_in(k))
        rec = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        rec.alpha_composite(capa, (0, -dy))
    else:                                # desde la izquierda
        dx = int(w * (1 - ease_out(k)))
        rec = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        rec.alpha_composite(capa, (-dx, 0))
    base.alpha_composite(rec, (int(x), int(y)))


class Titulo:
    """Apertura: LOS CHICOS / TAMBIÉN TIENEN / SU LUGAR (línea sobre banda roja)."""

    def __init__(self, f):
        self.kicker = texto(f("Bold", 30), "ZONA KIDS", BLANCO, espaciado=8)
        self.lineas = []
        for t, tam, banda in (("LOS CHICOS", 168, False), ("TAMBIÉN TIENEN", 118, False),
                              ("SU LUGAR", 168, True)):
            capa = texto(f("Anton", tam), t, BLANCO)
            if banda:
                pad = 26
                b = Image.new("RGBA", (capa.width + 2 * pad, capa.height + 10), (0, 0, 0, 0))
                ImageDraw.Draw(b).rounded_rectangle([0, int(capa.height * 0.18),
                                                     b.width - 1, b.height - 1],
                                                    radius=10, fill=ROJO)
                b.alpha_composite(capa, (pad, 0))
                capa = b
            self.lineas.append(capa)
        self.ys = [500, 690, 880]

    def dibujar(self, img, t):
        ini, fin = T_TITULO
        if not ini <= t < fin + 0.5:
            return
        sombra_capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        # kicker con punto rojo
        k = (t - ini) / 0.35
        kout = (t - fin) / 0.3
        kx = W / 2 - self.kicker.width / 2 + 16
        if kout < 1:
            d = ImageDraw.Draw(sombra_capa)
            a = int(255 * clamp(k * 2) * (1 - clamp(kout)))
            d.ellipse([kx - 34, 330 - 9, kx - 16, 330 + 9], fill=ROJO + (a,))
            kk = self.kicker.copy()
            kk.putalpha(kk.getchannel("A").point(lambda v: v * a // 255))
            sombra_capa.alpha_composite(kk, (int(kx), 330 - self.kicker.height // 2 - 2))
        for i, (capa, y) in enumerate(zip(self.lineas, self.ys)):
            x = W / 2 - capa.width / 2
            k_in = (t - ini - 0.12 - i * 0.11) / 0.45
            k_out = (t - fin - i * 0.07) / 0.35
            if k_out > 0:
                revelar(sombra_capa, capa, x, y - capa.height / 2, k_out, "arriba")
            else:
                revelar(sombra_capa, capa, x, y - capa.height / 2, k_in, "abajo")
        img.alpha_composite(sombra(sombra_capa, 16, 170, (0, 8)).crop((48, 48, 48 + W, 48 + H)))


class Editorial:
    """Texto abajo a la izquierda con barra roja vertical (estilo editorial)."""

    def __init__(self, f, l1, l2, ini, fin, color2=BLANCO, tam1=50, tam2=82, peso1="Medium"):
        self.l1 = texto(f(peso1, tam1), l1, (235, 235, 240))
        self.l2 = texto(f("ExtraBold", tam2), l2, color2)
        self.ini, self.fin = ini, fin
        self.x, self.y = 104, 1330

    def activo(self, t):
        return self.ini <= t < self.fin + 0.4

    def dibujar(self, img, t):
        if not self.activo(t):
            return
        capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(capa)
        alto = self.l1.height + self.l2.height + 6
        k_bar = ease_out((t - self.ini) / 0.35)
        k_out = clamp((t - self.fin) / 0.35)
        h_bar = alto * k_bar * (1 - ease_in(k_out))
        d.rectangle([self.x - 34, self.y + (alto - h_bar) * (1 if k_out else 0),
                     self.x - 26, self.y + (alto - h_bar) * (1 if k_out else 0) + h_bar],
                    fill=ROJO)
        for i, (capa_t, dy) in enumerate(((self.l1, 0), (self.l2, self.l1.height + 6))):
            k_in = (t - self.ini - 0.15 - i * 0.12) / 0.4
            if k_out > 0:
                revelar(capa, capa_t, self.x, self.y + dy, 1 - k_out, "izquierda")
            else:
                revelar(capa, capa_t, self.x, self.y + dy, k_in, "izquierda")
        img.alpha_composite(sombra(capa, 14, 190, (0, 6)).crop((42, 42, 42 + W, 42 + H)))


class Etiqueta:
    """Etiqueta fija arriba a la izquierda: · ZONA KIDS · RABBIT"""

    def __init__(self, f):
        t = texto(f("SemiBold", 26), "ZONA KIDS  ·  RABBIT", BLANCO, espaciado=2)
        w, h = t.width + 74, 54
        s = 2
        im = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
        ImageDraw.Draw(im).rounded_rectangle([0, 0, w * s - 1, h * s - 1], radius=27 * s,
                                             fill=(10, 10, 12, 150))
        im = im.resize((w, h), Image.LANCZOS)
        d = ImageDraw.Draw(im)
        d.ellipse([20, h / 2 - 7, 34, h / 2 + 7], fill=ROJO)
        im.alpha_composite(t, (48, (h - t.height) // 2 - 2))
        self.im = im

    def dibujar(self, img, t):
        if t < T_ETIQUETA or t >= T_VIDEO:
            return
        k = ease_out((t - T_ETIQUETA) / 0.4)
        k_out = clamp((t - (T_VIDEO - 0.3)) / 0.3)
        im = self.im
        a = k * (1 - k_out)
        if a < 0.999:
            im = im.copy()
            im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
        img.alpha_composite(im, (int(56 - 40 * (1 - k)), 250))


class Placa:
    """Placa final sobre el último cuadro congelado y desenfocado."""

    def __init__(self, f, emblema):
        self.ins = insignia(emblema, 250)
        self.titulo = texto(f("Anton", 128), "ZONA KIDS", BLANCO, espaciado=4)
        self.sub = texto(f("SemiBold", 32), "RABBIT  ·  FOOD & DRINKS  ·  EVENTOS", GRIS,
                         espaciado=2)
        self.frase = texto(f("Bold", 46), "¡Los esperamos en familia!", BLANCO)

    def dibujar(self, fondo, t):
        u = t - T_VIDEO
        k = ease_in_out(u / 0.6)
        img = fondo.filter(ImageFilter.GaussianBlur(26 * k)) if k > 0.02 else fondo.copy()
        img.alpha_composite(Image.new("RGBA", (W, H), (8, 8, 10, int(150 * k))))
        capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ki = ease_back((u - 0.25) / 0.5)
        if ki > 0:
            ins = self.ins.resize((max(1, int(250 * ki)),) * 2, Image.LANCZOS)
            capa.alpha_composite(ins, (int(W / 2 - ins.width / 2), int(700 - ins.height / 2)))
        revelar(capa, self.titulo, W / 2 - self.titulo.width / 2, 880, (u - 0.5) / 0.45)
        revelar(capa, self.sub, W / 2 - self.sub.width / 2, 1050, (u - 0.7) / 0.45)
        kl = ease_out((u - 0.85) / 0.5)
        if kl > 0:
            ImageDraw.Draw(capa).rectangle([W / 2 - 60 * kl, 1130, W / 2 + 60 * kl, 1136],
                                           fill=ROJO)
        revelar(capa, self.frase, W / 2 - self.frase.width / 2, 1170, (u - 1.0) / 0.45)
        img.alpha_composite(sombra(capa, 16, 170, (0, 8)).crop((48, 48, 48 + W, 48 + H)))
        return img


def degradado_abajo(img, y0, y1, alfa):
    g = np.zeros((H, W, 4), np.uint8)
    y = np.arange(H, dtype=np.float32)
    g[..., 3] = (np.clip((y - y0) / (y1 - y0), 0, 1) ** 1.3 * alfa).astype(np.uint8)[:, None]
    img.alpha_composite(Image.fromarray(g, "RGBA"))


# ----------------------------------------------------------------- audio (solo efectos)
def leer_wav(path):
    with wave.open(path) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        return x.reshape(-1, w.getnchannels()).mean(axis=1)


def efectos(dir_sfx, eventos, out, tmp):
    sr = 48000
    n = int(DUR * sr)
    mix = np.zeros(n, np.float32)
    sfx = {k: leer_wav(f"{dir_sfx}/{k}.wav") for k in ("whoosh", "pop", "click")}
    for tt, k, g in eventos:
        x = sfx[k] * g
        i = int(tt * sr)
        mix[i:i + len(x)] += x[:n - i]
    previa = os.path.join(tmp, "sfx.wav")
    with wave.open(previa, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", previa, "-af",
                    "loudnorm=I=-18:TP=-2:LRA=11", "-ac", "2", "-ar", str(sr), out], check=True)


# ----------------------------------------------------------------- principal
def main():
    base, emblema_p, fuentes, dir_sfx, salida = sys.argv[1:6]
    f = F(fuentes)
    titulo = Titulo(f)
    etiqueta = Etiqueta(f)
    texto_a = Editorial(f, "Un espacio", "pensado para ellos", *T_TEXTO_A)
    texto_b = Editorial(f, "Ellos juegan.", "Vos disfrutás.", *T_TEXTO_B, color2=(255, 70, 70),
                        tam1=82, peso1="ExtraBold")
    placa = Placa(f, Image.open(emblema_p))
    fuente = Fuente(base)

    with tempfile.TemporaryDirectory() as tmp:
        video = os.path.join(tmp, "video.mp4")
        enc = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow",
             "-crf", "17", "-pix_fmt", "yuv420p", "-colorspace", "bt709",
             "-color_primaries", "bt709", "-color_trc", "bt709", "-movflags", "+faststart",
             video], stdin=subprocess.PIPE)
        n = int(round(DUR * FPS))
        ultimo = None
        portada = None
        for i in range(n):
            t = i / FPS
            if t < T_VIDEO:
                s0 = fuente_en(t - 0.25 / FPS)
                s1 = fuente_en(t + 0.25 / FPS)
                img = Image.fromarray(corregir(fuente.cuadro(max(0, s0), min(SRC_FIN, s1))))
                # dolly continuo + golpe de zoom en la aceleración
                z = 1.0 + 0.07 * t / T_VIDEO
                if T_RAMPA[0] <= t <= T_RAMPA[1]:
                    z += 0.07 * math.sin(math.pi * (t - T_RAMPA[0]) / (T_RAMPA[1] - T_RAMPA[0]))
                img = dolly(img, z).convert("RGBA")
                ultimo = img.copy()
                if texto_a.activo(t) or texto_b.activo(t):
                    degradado_abajo(img, 1080, 1720, 190)
                titulo.dibujar(img, t)
                etiqueta.dibujar(img, t)
                texto_a.dibujar(img, t)
                texto_b.dibujar(img, t)
                if abs(t - 1.3) < 0.5 / FPS:
                    portada = img.copy()
            else:
                img = placa.dibujar(ultimo, t)
            enc.stdin.write(img.convert("RGB").tobytes())
            if i % 30 == 0:
                print(f"cuadro {i}/{n}", flush=True)
        enc.stdin.close()
        enc.wait()

        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-c", "copy",
                        f"{salida}_sin_audio.mp4"], check=True)
        eventos = [(T_TITULO[0] + 0.1, "whoosh", 0.5), (T_TITULO[0] + 0.15, "pop", 0.35),
                   (T_TITULO[1], "whoosh", 0.45), (T_ETIQUETA, "click", 0.4),
                   (T_TEXTO_A[0] + 0.1, "pop", 0.35), (T_RAMPA[0] + 0.1, "whoosh", 0.8),
                   (T_TEXTO_B[0] + 0.1, "pop", 0.35), (T_VIDEO - 0.05, "whoosh", 0.6),
                   (T_VIDEO + 0.3, "pop", 0.45), (T_VIDEO + 1.0, "click", 0.4)]
        audio = os.path.join(tmp, "sfx_final.wav")
        efectos(dir_sfx, eventos, audio, tmp)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", audio, "-map", "0:v",
                        "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                        "-shortest", "-movflags", "+faststart", f"{salida}_efectos.mp4"],
                       check=True)
    if portada is not None:
        portada.convert("RGB").save(f"{salida}_portada.png")
    print(f"Listo: {DUR:.2f} s (metraje {T_VIDEO:.2f} s, aceleración {T_RAMPA[0]:.2f}-"
          f"{T_RAMPA[1]:.2f})")


if __name__ == "__main__":
    main()
