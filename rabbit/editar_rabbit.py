"""Reel "Convocatoria cerrada" para Rabbit Food & Drinks.

Uso: python3 editar_rabbit.py <video.mov> <logo.png> <fuentes_dir> <sfx_dir> <salida.mp4>

El video de fondo (pantalla de WhatsApp con los CV) va desenfocado y oscurecido para que
el texto se lea bien y para no mostrar los números de teléfono de los postulantes.
"""
import math
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
DUR = 15.0
ROJO = (255, 18, 18)
VERDE = (0, 200, 70)
BLANCO = (255, 255, 255)

VIDEO, LOGO, FUENTES, SFX, SALIDA = sys.argv[1:6]


def fuente(nombre, tam):
    return ImageFont.truetype(f"{FUENTES}/{nombre}", tam)


def ease_out_back(x):
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def ease_out(x):
    return 1 - (1 - x) ** 3


def prog(t, t0, d):
    return min(1.0, max(0.0, (t - t0) / d))


# --- logo: el fondo negro pasa a transparente --------------------------------------------
logo = Image.open(LOGO).convert("RGB").crop((40, 305, 1220, 862))
arr = np.asarray(logo).astype(np.float32)
alfa = np.clip((arr.max(2) - 18) * 4, 0, 255).astype(np.uint8)
logo = logo.convert("RGBA")
logo.putalpha(Image.fromarray(alfa))
LOGO_W = 540
logo = logo.resize((LOGO_W, round(logo.height * LOGO_W / logo.width)), Image.LANCZOS)
LOGO_Y = 210

# --- sello "CONVOCATORIA CERRADA" ---------------------------------------------------------
def crear_sello():
    f1 = fuente("Anton-Regular.ttf", 104)
    f2 = fuente("Anton-Regular.ttf", 132)
    w = 720
    sello = Image.new("RGBA", (w, 330), (0, 0, 0, 0))
    d = ImageDraw.Draw(sello)
    d.rounded_rectangle((10, 10, w - 10, 320), 30, fill=(255, 18, 18, 255))
    d.rounded_rectangle((26, 26, w - 26, 304), 22, outline=(255, 255, 255, 255), width=5)
    for txt, f, y in (("CONVOCATORIA", f1, 38), ("CERRADA", f2, 148)):
        tw = d.textlength(txt, font=f)
        d.text(((w - tw) / 2, y), txt, font=f, fill=BLANCO)
    return sello.rotate(-4, resample=Image.BICUBIC, expand=True)


SELLO = crear_sello()
SELLO_CY = LOGO_Y + 250 + 190

# --- mensaje -------------------------------------------------------------------------------
F_TXT = fuente("Poppins-SemiBold.ttf", 42)
F_DEST = fuente("Poppins-ExtraBold.ttf", 42)
F_GRACIAS = fuente("Poppins-ExtraBold.ttf", 48)
EMOJI = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", 109)

# (texto, palabras destacadas en rojo, momento de entrada)
BLOQUES = [
    ("Recibimos todos los CV y los estamos leyendo uno por uno.", {"todos", "uno", "por"}, 2.0),
    ("Por la cantidad, ya no estamos recibiendo más y no podemos responder cada mensaje.",
     {"ya", "no", "estamos", "recibiendo", "más"}, 4.2),
    ("Si quedás seleccionado/a, te escribimos nosotros.", {"te", "escribimos", "nosotros."}, 6.8),
]
GRACIAS_T = 8.8
MARGEN = 90
ANCHO_TXT = W - 2 * MARGEN


def partir(texto, f):
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    lineas, actual = [], []
    for p in texto.split():
        prueba = " ".join(actual + [p])
        if actual and d.textlength(prueba, font=f) > ANCHO_TXT:
            lineas.append(actual)
            actual = [p]
        else:
            actual.append(p)
    lineas.append(actual)
    return lineas


def render_bloque(texto, destacadas):
    lineas = partir(texto, F_TXT)
    alto_l = 58
    img = Image.new("RGBA", (W, alto_l * len(lineas) + 10), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    esp = d.textlength(" ", font=F_TXT)
    for i, palabras in enumerate(lineas):
        anchos = [d.textlength(p, font=F_DEST if p in destacadas else F_TXT) for p in palabras]
        x = (W - sum(anchos) - esp * (len(palabras) - 1)) / 2
        for p, a in zip(palabras, anchos):
            dest = p in destacadas
            d.text((x, i * alto_l), p, font=F_DEST if dest else F_TXT,
                   fill=(255, 70, 70) if dest else BLANCO)
            x += a + esp
    return img


def render_gracias():
    txt = "¡Gracias por sumarse y por la paciencia!"
    lineas = partir(txt, F_GRACIAS)
    img = Image.new("RGBA", (W, 70 * len(lineas) + 120), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, l in enumerate(lineas):
        s = " ".join(l)
        d.text(((W - d.textlength(s, font=F_GRACIAS)) / 2, i * 70), s, font=F_GRACIAS, fill=BLANCO)
    # emojis 🐰❤️ (Noto Color Emoji solo existe en 109 px: se dibuja y se escala)
    em = Image.new("RGBA", (300, 140), (0, 0, 0, 0))
    ImageDraw.Draw(em).text((0, 0), "🐰❤️", font=EMOJI, embedded_color=True)
    em = em.crop(em.getbbox())
    em = em.resize((round(em.width * 76 / em.height), 76), Image.LANCZOS)
    img.alpha_composite(em, ((W - em.width) // 2, 70 * len(lineas) + 24))
    return img


IMG_BLOQUES = [(render_bloque(t, d), t0) for t, d, t0 in BLOQUES]
IMG_GRACIAS = render_gracias()

# posiciones verticales del mensaje
y = SELLO_CY + SELLO.height // 2 + 22
POS = []
for img, _ in IMG_BLOQUES:
    POS.append(y)
    y += img.height + 18
GRACIAS_Y = y + 6
assert GRACIAS_Y + IMG_GRACIAS.height < H - 290, GRACIAS_Y + IMG_GRACIAS.height

# --- fondo: video desenfocado, a mitad de velocidad, oscurecido ----------------------------
fondo_cmd = ["ffmpeg", "-v", "error", "-stream_loop", "-1", "-i", VIDEO, "-t", str(DUR), "-vf",
             f"setpts=2.0*PTS,fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,"
             f"crop={W}:{H},gblur=sigma=14,eq=brightness=-0.06:saturation=0.8",
             "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
dec = subprocess.Popen(fondo_cmd, stdout=subprocess.PIPE)
enc = subprocess.Popen(
    ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
     "-r", str(FPS), "-i", "-", "-i", f"{SFX}/mezcla.wav", "-map", "0:v", "-map", "1:a",
     "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
     "-c:a", "aac", "-b:a", "192k", "-brand", "mp42", "-movflags", "+faststart", "-shortest",
     SALIDA], stdin=subprocess.PIPE)

# viñeta oscura (más oscura arriba y abajo)
yy = np.linspace(-1, 1, H)[:, None]
xx = np.linspace(-1, 1, W)[None, :]
oscuro = np.clip(0.55 + 0.25 * (yy ** 2) + 0.1 * (xx ** 2), 0, 0.9)[..., None]

N = int(DUR * FPS)
for n in range(N):
    t = n / FPS
    buf = dec.stdout.read(W * H * 3)
    if len(buf) < W * H * 3:
        break
    fr = np.frombuffer(buf, np.uint8).reshape(H, W, 3).astype(np.float32)
    fr = fr * (1 - oscuro)
    cuadro = Image.fromarray(fr.astype(np.uint8)).convert("RGBA")
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    # logo: aparece con fundido y leve escala; "respira" suave después
    p = ease_out(prog(t, 0.1, 0.6))
    if p > 0:
        s = (0.9 + 0.1 * p) * (1 + 0.012 * math.sin(t * 2.2))
        lg = logo.resize((round(logo.width * s), round(logo.height * s)), Image.BICUBIC)
        lg.putalpha(lg.getchannel("A").point(lambda a: int(a * p)))
        capa.alpha_composite(lg, ((W - lg.width) // 2, LOGO_Y + (logo.height - lg.height) // 2))

    # sello: golpe de escala 1.8 → 1 con sacudida
    p = prog(t, 0.8, 0.35)
    if p > 0:
        s = 1.8 - 0.8 * ease_out(p)
        sl = SELLO.resize((round(SELLO.width * s), round(SELLO.height * s)), Image.BICUBIC)
        sl.putalpha(sl.getchannel("A").point(lambda a: int(a * min(1, p * 2.5))))
        temblor = 0
        if 1.15 < t < 1.45:
            temblor = int(10 * math.sin((t - 1.15) * 90) * (1.45 - t) / 0.3)
        # sombra
        sombra = Image.new("RGBA", sl.size, (0, 0, 0, 0))
        sombra.putalpha(sl.getchannel("A").point(lambda a: int(a * 0.5)))
        sombra = sombra.filter(ImageFilter.GaussianBlur(18))
        x0 = (W - sl.width) // 2 + temblor
        y0 = SELLO_CY - sl.height // 2
        capa.alpha_composite(sombra, (x0 + 8, y0 + 16))
        capa.alpha_composite(sl, (x0, y0))

    # bloques de texto: suben y aparecen
    for (img, t0), y in zip(IMG_BLOQUES, POS):
        p = ease_out(prog(t, t0, 0.5))
        if p > 0:
            im = img.copy()
            im.putalpha(im.getchannel("A").point(lambda a: int(a * p)))
            capa.alpha_composite(im, (0, int(y + 40 * (1 - p))))

    # agradecimiento con pop
    p = prog(t, GRACIAS_T, 0.45)
    if p > 0:
        s = max(0.01, ease_out_back(p))
        gi = IMG_GRACIAS.resize((round(W * s), max(1, round(IMG_GRACIAS.height * s))), Image.BICUBIC)
        gi.putalpha(gi.getchannel("A").point(lambda a: int(a * min(1, p * 2))))
        capa.alpha_composite(gi, ((W - gi.width) // 2, GRACIAS_Y + (IMG_GRACIAS.height - gi.height) // 2))

    # fundido final
    if t > DUR - 0.5:
        k = (DUR - t) / 0.5
        cuadro = Image.blend(Image.new("RGBA", (W, H), (0, 0, 0, 255)), cuadro, k)
        capa.putalpha(capa.getchannel("A").point(lambda a: int(a * k)))

    cuadro.alpha_composite(capa)
    enc.stdin.write(cuadro.convert("RGB").tobytes())

enc.stdin.close()
enc.wait()
dec.kill()
print("Listo:", SALIDA)
