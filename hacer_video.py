"""Genera un video animado corto (MP4) con Python + ffmpeg.

Uso: python3 hacer_video.py [salida.mp4]
"""
import math
import random
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1280, 720, 30
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# (inicio, fin, título, subtítulo) en segundos
ESCENAS = [
    (0.0, 3.5, "¡Hola!", "Este video fue hecho con código"),
    (3.5, 7.0, "Python + ffmpeg", "Cada cuadro se dibuja con un script"),
    (7.0, 10.5, "Formas y colores", "Todo se anima con matemática"),
    (10.5, 14.0, "¡Gracias por mirar!", "videos-claude"),
]
DURACION = ESCENAS[-1][1]

random.seed(7)
BURBUJAS = [
    dict(x=random.uniform(0, W), y=random.uniform(0, H), r=random.uniform(20, 90),
         vx=random.uniform(-40, 40), vy=random.uniform(-60, -15),
         fase=random.uniform(0, math.tau), hue=random.random())
    for _ in range(28)
]

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)


def fondo(t):
    """Degradado que rota lentamente de color."""
    a = t * 0.25
    d = (xx * math.cos(a) + yy * math.sin(a)) / (W + H)
    r = 40 + 60 * np.sin(d * 3 + t * 0.6)
    g = 20 + 40 * np.sin(d * 3 + t * 0.6 + 2.0)
    b = 110 + 70 * np.sin(d * 3 + t * 0.6 + 4.0)
    img = np.stack([r, g, b], axis=-1).clip(0, 255).astype(np.uint8)
    return Image.fromarray(img, "RGB")


def hsv(h, s=0.6, v=1.0):
    i = int(h * 6) % 6
    f = h * 6 - int(h * 6)
    p, q, u = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    rgb = [(v, u, p), (q, v, p), (p, v, u), (p, q, v), (u, p, v), (v, p, q)][i]
    return tuple(int(c * 255) for c in rgb)


def burbujas(t):
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    for b in BURBUJAS:
        x = (b["x"] + b["vx"] * t + 30 * math.sin(t + b["fase"])) % (W + 200) - 100
        y = (b["y"] + b["vy"] * t) % (H + 200) - 100
        r = b["r"] * (1 + 0.15 * math.sin(2 * t + b["fase"]))
        color = hsv((b["hue"] + t * 0.05) % 1) + (70,)
        d.ellipse([x - r, y - r, x + r, y + r], fill=color)
    return capa.filter(ImageFilter.GaussianBlur(4))


def suave(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def texto(img, t):
    for ini, fin, titulo, sub in ESCENAS:
        if not (ini <= t < fin):
            continue
        local = t - ini
        entrada = suave(local / 0.6)
        salida = 1 - suave((local - (fin - ini - 0.5)) / 0.5)
        alfa = entrada * salida
        capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(capa)

        escala = 0.8 + 0.2 * entrada
        f1 = ImageFont.truetype(FONT_BOLD, int(88 * escala))
        f2 = ImageFont.truetype(FONT_REG, 36)
        dy = (1 - entrada) * 40

        w1 = d.textlength(titulo, font=f1)
        d.text(((W - w1) / 2 + 4, H / 2 - 90 + dy + 4), titulo, font=f1,
               fill=(0, 0, 0, int(120 * alfa)))
        d.text(((W - w1) / 2, H / 2 - 90 + dy), titulo, font=f1,
               fill=(255, 255, 255, int(255 * alfa)))

        # subtítulo con efecto máquina de escribir
        n = int(len(sub) * suave((local - 0.4) / 1.2))
        w2 = d.textlength(sub, font=f2)
        d.text(((W - w2) / 2, H / 2 + 55), sub[:n], font=f2,
               fill=(230, 230, 255, int(230 * alfa)))

        # línea decorativa que crece
        largo = 300 * entrada
        d.rounded_rectangle([W / 2 - largo / 2, H / 2 + 30, W / 2 + largo / 2, H / 2 + 36],
                            radius=3, fill=(255, 200, 120, int(255 * alfa)))
        img.alpha_composite(capa)

    # barra de progreso
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - 6, W * t / DURACION, H], fill=(255, 200, 120, 255))


def cuadro(t):
    img = fondo(t).convert("RGBA")
    img.alpha_composite(burbujas(t))
    texto(img, t)
    return img.convert("RGB")


def main():
    salida = sys.argv[1] if len(sys.argv) > 1 else "video.mp4"
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-f", "lavfi", "-t", str(DURACION),
         "-i", "aevalsrc='0.04*(sin(2*PI*220*t)+sin(2*PI*277.2*t)+sin(2*PI*329.6*t))"
               "*(0.7+0.3*sin(2*PI*0.5*t))':s=44100",
         "-af", f"afade=in:d=1.5,afade=out:st={DURACION - 2}:d=2",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
         "-c:a", "aac", "-shortest", "-movflags", "+faststart", salida],
        stdin=subprocess.PIPE,
    )
    total = int(DURACION * FPS)
    for i in range(total):
        ff.stdin.write(cuadro(i / FPS).tobytes())
    ff.stdin.close()
    ff.wait()
    print(f"Listo: {salida} ({DURACION:.0f}s, {W}x{H})")


if __name__ == "__main__":
    main()
