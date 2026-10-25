"""Edición del Reel de FRAMI: punch-ins, transiciones, subtítulos, motion graphics y audio.

Uso: python3 editar_reel.py <dir_trabajo> <dir_salida>

<dir_trabajo> debe contener: recortado.mov, segmentos.json, words_cut.json, logo.png,
yunet.onnx (detector de rostros de OpenCV Zoo),
fonts/Poppins-*.ttf y audio/{whoosh,pop,click}.wav (ver paso0_silencios.py y
musica_sfx.py). Escribe en <dir_salida>: frami_reel.mp4, portada.png y subtitulos.srt.
"""
import json
import math
import re
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import graficos

W, H, FPS = 1080, 1920, 30
SAFE_TOP, SAFE_BOTTOM = 250, H - 340

ROJO = (232, 0, 61)
AMARILLO = (245, 196, 0)
AZUL = (8, 8, 96)
BLANCO = (255, 255, 255)
GRIS_CLARO = (244, 244, 244)
GRIS_OSCURO = (51, 51, 51)

T0 = 0.0          # inicio de la voz (sin intro: arranca directo con el video)
CIERRE = 2.6
CENTRO_CARA = (0.5, 0.40)
MENTON_Y = 1050   # altura fija del mentón en pantalla tras el reencuadre
CM = 142          # px por centímetro en un celular típico (1920 px ≈ 13,5 cm)
SUB_Y = MENTON_Y + 3 * CM + 46   # subtítulos 3 cm debajo del mentón (centro del texto)
CLIP_REFERENCIA = "3980"  # clip parada: los del escritorio se igualan a su exposición
# El cuarto cambio de clip queda cubierto por la escena "complementarios" (graficos.Escena).
TRANSICIONES = ["zoom", "barras", "whip", "escena"]

TEXTO = (
    "¿Invertir en la bolsa o tener un seguro de vida? Si pensaste que tenías que tener uno u "
    "otro, te estás perdiendo la mitad de la película. Muchas veces creemos que las finanzas se "
    "tratan de hacer crecer el dinero o crear rentabilidad, pero en realidad esto es solo uno de "
    "los pasos. Los seguros de personas, de capitalización o de retiro, no buscan hacerte rico de "
    "la noche a la mañana. Su objetivo real es garantizar la estabilidad financiera y proteger "
    "este patrimonio que vas a construir a lo largo de los años. Los seguros de retiro y las "
    "inversiones en bolsa no compiten entre sí: son complementarios. Estos tipos de seguros son "
    "una herramienta fundamental para la planificación financiera de cualquier persona. Contame "
    "en los comentarios cómo estás ahorrando y, si no, contactame y podemos armar un plan a "
    "medida para empezar a hacerlo."
)

# Textos de apoyo: (inicio, fin) en segundos de voz, líneas [(texto, color)].
TARJETAS = [
    (0.0, 2.4, [[("¿BOLSA ", BLANCO), ("o ", AMARILLO), ("SEGURO?", BLANCO)]]),
    (12.6, 15.8, [[("RENTABILIDAD", BLANCO)], [("= solo ", BLANCO), ("UNO ", AMARILLO),
                                                ("de los pasos", BLANCO)]]),
    (37.5, 40.0, [[("PLANIFICACIÓN", BLANCO)], [("FINANCIERA", AMARILLO)]]),
    (45.2, 47.1, [[("PLAN ", BLANCO), ("A MEDIDA", AMARILLO)]]),
]


# ----------------------------------------------------------------- utilidades
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = clamp(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_back(x, s=1.7):
    x = clamp(x)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


class Fuentes:
    def __init__(self, d):
        self.d = d
        self.cache = {}

    def __call__(self, peso, tam):
        k = (peso, tam)
        if k not in self.cache:
            self.cache[k] = ImageFont.truetype(f"{self.d}/Poppins-{peso}.ttf", tam)
        return self.cache[k]


def sombra(capa, radio=10, offset=(0, 6), alfa=150):
    """Sombra suave a partir del canal alfa de una capa."""
    a = capa.getchannel("A").point(lambda v: v * alfa // 255)
    s = Image.new("RGBA", capa.size, (0, 0, 0, 0))
    s.putalpha(a.filter(ImageFilter.GaussianBlur(radio)))
    out = Image.new("RGBA", capa.size, (0, 0, 0, 0))
    out.alpha_composite(s, offset)
    out.alpha_composite(capa)
    return out


def pegar_escalado(base, img, cx, cy, escala, alfa=1.0):
    if escala <= 0.01 or alfa <= 0.01:
        return
    w, h = max(1, int(img.width * escala)), max(1, int(img.height * escala))
    im = img.resize((w, h), Image.BILINEAR) if (w, h) != img.size else img
    if alfa < 1:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alfa)))
    base.alpha_composite(im, (int(cx - w / 2), int(cy - h / 2)))


# ----------------------------------------------------------------- subtítulos
def palabras_corregidas(words):
    tokens = TEXTO.split()
    if len(tokens) != len(words):
        raise SystemExit(f"La transcripción tiene {len(words)} palabras y el texto revisado "
                         f"{len(tokens)}: revisá TEXTO.")
    for tok, w in zip(tokens, words):
        a = re.sub(r"[^\wáéíóúñ]", "", tok.lower()).replace("ó", "o")
        b = re.sub(r"[^\wáéíóúñ]", "", w["w"].strip().lower()).replace("ó", "o")
        if a != b:
            raise SystemExit(f"Palabra desalineada: {tok!r} vs {w['w']!r}")
    return [dict(t=tok, s=w["s"], e=w["e"]) for tok, w in zip(tokens, words)]


def agrupar(pal):
    grupos, g = [], []
    for i, p in enumerate(pal):
        if g and (len(g) == 3 or len(" ".join(x["t"] for x in g + [p])) > 16
                  or re.search(r"[.,?:!]$", g[-1]["t"]) or p["s"] - g[-1]["e"] > 0.35):
            grupos.append(g)
            g = []
        g.append(p)
    grupos.append(g)
    out = []
    for i, g in enumerate(grupos):
        ini = g[0]["s"]
        fin = grupos[i + 1][0]["s"] if i + 1 < len(grupos) else g[-1]["e"] + 0.3
        fin = min(fin, g[-1]["e"] + 0.6)
        out.append(dict(pal=g, ini=ini, fin=fin))
    return out


def srt(grupos, path):
    def ts(x):
        ms = int(round(x * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    with open(path, "w", encoding="utf-8") as f:
        for i, g in enumerate(grupos, 1):
            f.write(f"{i}\n{ts(g['ini'] + T0)} --> {ts(g['fin'] + T0)}\n"
                    f"{' '.join(p['t'] for p in g['pal'])}\n\n")


class Subtitulos:
    def __init__(self, grupos, fuentes):
        self.grupos = grupos
        self.f = fuentes
        self.cache = {}

    def imagen(self, gi, activa):
        k = (gi, activa)
        if k in self.cache:
            return self.cache[k]
        pal = [p["t"] for p in self.grupos[gi]["pal"]]
        tam = 92
        while True:
            font = self.f("ExtraBold", tam)
            esp = font.getlength(" ")
            ancho = sum(font.getlength(p) for p in pal) + esp * (len(pal) - 1)
            if ancho <= 940 or tam <= 60:
                break
            tam -= 4
        asc, desc = font.getmetrics()
        capa = Image.new("RGBA", (int(ancho) + 60, asc + desc + 60), (0, 0, 0, 0))
        d = ImageDraw.Draw(capa)
        x = 30
        for i, p in enumerate(pal):
            color = AMARILLO if i == activa else BLANCO
            d.text((x, 30), p, font=font, fill=color, stroke_width=5,
                   stroke_fill=(20, 20, 40))
            x += font.getlength(p) + esp
        img = sombra(capa, radio=12, offset=(0, 6), alfa=170)
        self.cache[k] = img
        return img

    def dibujar(self, base, tv):
        for gi, g in enumerate(self.grupos):
            if g["ini"] - 0.05 <= tv < g["fin"]:
                activa = 0
                for i, p in enumerate(g["pal"]):
                    if tv >= p["s"] - 0.03:
                        activa = i
                img = self.imagen(gi, activa)
                dt = tv - (g["ini"] - 0.05)
                esc = 0.6 + 0.48 * ease_out(dt / 0.12) if dt < 0.12 else \
                    1.08 - 0.08 * ease_out((dt - 0.12) / 0.1)
                pegar_escalado(base, img, W / 2, SUB_Y, esc)
                return


# ----------------------------------------------------------------- tarjetas
class Tarjetas:
    def __init__(self, fuentes):
        self.f = fuentes
        self.imgs = [self.render(lineas) for _, _, lineas in TARJETAS]

    def render(self, lineas):
        tam = 76
        while True:
            font = self.f("ExtraBold", tam)
            anchos = [sum(font.getlength(t) for t, _ in l) for l in lineas]
            if max(anchos) <= 820 or tam <= 50:
                break
            tam -= 4
        asc, desc = font.getmetrics()
        lh = int(tam * 1.12)
        pad_x, pad_y = 48, 30
        cw = int(max(anchos)) + pad_x * 2
        ch = lh * len(lineas) + pad_y * 2 + (desc // 2)
        m = 50  # margen para el círculo decorativo y la sombra
        capa = Image.new("RGBA", (cw + m * 2, ch + m * 2), (0, 0, 0, 0))
        d = ImageDraw.Draw(capa)
        d.ellipse([cw + m - 42, m - 36, cw + m + 34, m + 40], fill=AMARILLO)
        d.rounded_rectangle([m, m, m + cw, m + ch], radius=30, fill=ROJO)
        d.rounded_rectangle([m + 24, m + ch - 12, m + 24 + 110, m + ch - 4], radius=4,
                            fill=AMARILLO)
        y = m + pad_y - int(tam * 0.12)
        for l, aw in zip(lineas, anchos):
            x = m + (cw - aw) / 2
            for t, c in l:
                d.text((x, y), t, font=font, fill=c)
                x += font.getlength(t)
            y += lh
        return sombra(capa, radio=14, offset=(0, 10), alfa=110)

    def dibujar(self, base, tv):
        for (ini, fin, _), img in zip(TARJETAS, self.imgs):
            if ini <= tv < fin:
                cy = SAFE_TOP + 20 + img.height / 2
                dt, resto = tv - ini, fin - tv
                if dt < 0.4:
                    x = -img.width / 2 + (W / 2 + img.width / 2) * ease_back(dt / 0.4, 1.2)
                    esc = 1.0
                    alfa = 1.0
                elif resto < 0.25:
                    k = ease_in_out(1 - resto / 0.25)
                    x = W / 2 + 140 * k
                    esc = 1 - 0.15 * k
                    alfa = 1 - k
                else:
                    x, esc, alfa = W / 2, 1 + 0.01 * math.sin((dt - 0.4) * 3), 1.0
                pegar_escalado(base, img, x, cy, esc, alfa)


# ----------------------------------------------------------------- video base
class Fuente:
    """Lee recortado.mov cuadro a cuadro (sin filtros de color)."""

    def __init__(self, path):
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path,
                                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                                  stdout=subprocess.PIPE)
        self.n = -1
        self.frame = None

    def cuadro(self, n):
        while self.n < n:
            buf = self.p.stdout.read(W * H * 3)
            if len(buf) < W * H * 3:
                break
            self.frame = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
            self.n += 1
        return self.frame


def caras(path, lim, modelo):
    """Mediana del mentón, del centro de la cara y del brillo de la cara en cada segmento."""
    import cv2
    det = cv2.FaceDetectorYN.create(modelo, "", (W // 2, H // 2), 0.7)
    cap = cv2.VideoCapture(path)
    datos = [[] for _ in lim]
    f = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        if f % 5 == 0:
            _, res = det.detect(cv2.resize(fr, (W // 2, H // 2)))
            if res is not None:
                x, y, w, h = res[0][:4] * 2
                si = next(k for k, (a, b, _) in enumerate(lim) if a <= f < b)
                gris = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
                piel = gris[int(y + h / 4):int(y + h * 3 / 4), int(x + w / 4):int(x + w * 3 / 4)]
                datos[si].append((y + h, x + w / 2, piel.mean()))
        f += 1
    out = []
    for d in datos:
        d = np.array(d) if d else np.array([[MENTON_Y, W / 2, np.nan]])
        out.append(tuple(float(v) for v in np.median(d, axis=0)))
    return out


def encuadre(arr, z, menton, cx):
    """Recorta y amplía de modo que el mentón quede en MENTON_Y y la cara centrada."""
    cw, ch = W / z, H / z
    x0 = clamp(cx - cw / 2, 0, W - cw)
    y0 = clamp(menton - MENTON_Y / z, 0, H - ch)
    return Image.fromarray(arr).transform((W, H), Image.EXTENT, (x0, y0, x0 + cw, y0 + ch),
                                          Image.BILINEAR)


def luts_exposicion(lim, cara):
    """Baja la exposición de los clips cuya cara está más iluminada que la del clip de
    referencia. Curva con gamma para oscurecer los medios sin apagar los blancos."""
    brillo = {}
    for (_, _, clip), (_, _, lum) in zip(lim, cara):
        brillo.setdefault(clip, []).append(lum)
    brillo = {c: float(np.nanmedian(v)) for c, v in brillo.items()}
    ref = brillo[CLIP_REFERENCIA]
    x = np.arange(256, dtype=np.float32) / 255
    luts = {}
    for c, lum in brillo.items():
        if np.isnan(lum) or lum <= ref + 8:
            continue
        g = 1.3
        escala = min(1.0, ref / (255 * (lum / 255) ** g))
        luts[c] = np.clip(255 * escala * x ** g, 0, 255).astype(np.uint8)
    return luts


def zoom_minimo(menton):
    """Zoom mínimo para poder subir el mentón hasta MENTON_Y."""
    return max(1.0, (H - MENTON_Y) / (H - menton))


def zoom(arr, z, cx=CENTRO_CARA[0], cy=CENTRO_CARA[1]):
    img = Image.fromarray(arr)
    if z <= 1.0001:
        return img
    cw, ch = W / z, H / z
    x0 = clamp(cx * W - cw / 2, 0, W - cw)
    y0 = clamp(cy * H - ch / 2, 0, H - ch)
    return img.transform((W, H), Image.EXTENT, (x0, y0, x0 + cw, y0 + ch), Image.BILINEAR)


def barras_verticales(base, k, colores=(AMARILLO, ROJO, AZUL)):
    """Barras de marca que cruzan la pantalla de izquierda a derecha (k: 0..1)."""
    d = ImageDraw.Draw(base)
    n = len(colores)
    for i, c in enumerate(colores):
        kk = clamp(k * (1 + 0.25 * (n - 1)) - 0.25 * i)
        x = -W * 1.2 + (W * 2.4) * ease_in_out(kk)
        d.polygon([(x, 0), (x + W * 1.05, 0), (x + W * 1.05 - 260, H), (x - 260, H)], fill=c)


def panel(base, t, t_medio, color, dur=0.6, alto=1.35):
    """Panel a pantalla completa que sube; cubre todo exactamente en t_medio."""
    k = (t - (t_medio - dur / 2)) / dur
    if not 0 <= k <= 1:
        return
    hp = H * alto
    centro = H + hp / 2 - (H + hp) * ease_in_out(k)
    ImageDraw.Draw(base).rectangle([0, centro - hp / 2, W, centro + hp / 2], fill=color)


# ----------------------------------------------------------------- escenas fijas
def escena_intro(t, logo, f):
    img = Image.new("RGBA", (W, H), GRIS_CLARO + (255,))
    d = ImageDraw.Draw(img)
    r = 470 * ease_out(t / 0.45)
    d.ellipse([W / 2 - r + 120, 900 - r - 160, W / 2 + r + 120, 900 + r - 160], fill=AMARILLO)
    largo = 520 * ease_out((t - 0.2) / 0.4)
    d.rounded_rectangle([W / 2 - largo / 2, 1330, W / 2 + largo / 2, 1350], radius=10, fill=ROJO)
    esc = ease_back((t - 0.08) / 0.4) * 0.42
    pegar_escalado(img, logo, W / 2, 900, esc)
    return img


class Cierre:
    def __init__(self, logo, f):
        self.logo = logo
        self.f = f
        self.wa = self.icono_wa()

    def icono_wa(self):
        s = 4
        im = Image.new("RGBA", (90 * s, 90 * s), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.ellipse([6 * s, 4 * s, 84 * s, 82 * s], fill=BLANCO)
        d.polygon([(10 * s, 86 * s), (18 * s, 60 * s), (34 * s, 74 * s)], fill=BLANCO)
        tel = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 54 * s)
        d.text((45 * s, 43 * s), "✆", font=tel, fill=ROJO, anchor="mm")
        return im.resize((90, 90), Image.LANCZOS)

    def __call__(self, t):
        img = Image.new("RGBA", (W, H), AZUL + (255,))
        d = ImageDraw.Draw(img)
        r = 360 + 15 * math.sin(t * 3)
        d.ellipse([W - r * 0.9, H - r * 1.1 + 60, W + r * 1.1, H + r * 0.9 + 60], fill=AMARILLO)
        d.rounded_rectangle([-40, 330, 70 + 160 * ease_out(t / 0.5), 352], radius=11, fill=ROJO)
        pegar_escalado(img, self.logo, W / 2, 590, ease_back((t - 0.05) / 0.4) * 0.27)

        lineas = [("Escribinos y", BLANCO), ("te asesoramos", BLANCO), ("sin compromiso", AMARILLO)]
        font = self.f("ExtraBold", 84)
        for i, (txt, c) in enumerate(lineas):
            k = ease_out((t - 0.25 - i * 0.08) / 0.35)
            if k <= 0:
                continue
            y = 880 + i * 100 + 40 * (1 - k)
            capa = Image.new("RGBA", (W, 130), (0, 0, 0, 0))
            ImageDraw.Draw(capa).text((W / 2, 60), txt, font=font, fill=c + (int(255 * k),),
                                      anchor="mm")
            img.alpha_composite(capa, (0, int(y - 60)))

        k = ease_back((t - 0.6) / 0.35)
        if k > 0:
            fn = self.f("ExtraBold", 66)
            tw = fn.getlength("3764886646")
            pw, ph = int(tw + 90 + 100), 124
            pill = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
            pd = ImageDraw.Draw(pill)
            pd.rounded_rectangle([0, 0, pw - 1, ph - 1], radius=62, fill=ROJO)
            pill.alpha_composite(self.wa, (28, 17))
            pd.text((28 + 90 + 22, ph / 2), "3764886646", font=fn, fill=BLANCO, anchor="lm")
            pegar_escalado(img, sombra(pill, 10, (0, 8), 120), W / 2, 1265, k)

        k = ease_out((t - 0.8) / 0.35)
        if k > 0:
            fn = self.f("Bold", 50)
            capa = Image.new("RGBA", (W, 90), (0, 0, 0, 0))
            ImageDraw.Draw(capa).text((W / 2, 45), "@frami.productoresasesores", font=fn,
                                      fill=BLANCO + (int(255 * k),), anchor="mm")
            img.alpha_composite(capa, (0, int(1440 - 45 + 30 * (1 - k))))
        return img


# ----------------------------------------------------------------- audio
def leer_wav(path):
    with wave.open(path) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        return x.reshape(-1, w.getnchannels()).mean(axis=1), w.getframerate()


def loudnorm_medir(path, filtro_previo=""):
    pre = filtro_previo + "," if filtro_previo else ""
    log = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af",
                          pre + "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    return json.loads(log[log.rindex("{"):log.rindex("}") + 1])


def mezclar_audio(dt, eventos, total, out):
    """Voz procesada + efectos (sin música), normalizado a -14 LUFS."""
    sr = 48000
    sfx = np.zeros(int(total * sr) + sr)
    muestras = {k: leer_wav(f"{dt}/audio/{k}.wav")[0] for k in ("whoosh", "pop", "click")}
    ganancia = {"whoosh": 0.1, "pop": 0.13, "click": 0.09}
    for ev in eventos:
        t, k = ev[:2]
        x = muestras[k] * ganancia[k] * (ev[2] if len(ev) > 2 else 1.0)
        i = int(t * sr)
        sfx[i:i + len(x)] += x[:len(sfx) - i]
    with wave.open(f"{dt}/audio/sfx.wav", "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(sfx, -1, 1) * 32767).astype(np.int16).tobytes())

    retardo = int(T0 * 1000)
    voz = (f"[0:a]aresample=48000,highpass=f=80,afftdn=nf=-30:nr=8,"
           f"acompressor=threshold=-20dB:ratio=3:attack=5:release=90:makeup=2,"
           f"adelay=delays={retardo}:all=1,aformat=channel_layouts=stereo,apad,atrim=0:{total:.3f}[voz]")
    mezcla = ("[voz][1:a]amix=inputs=2:normalize=0:duration=first,"
              "aformat=channel_layouts=stereo[mix]")
    fc = ";".join([voz, mezcla])
    previa = f"{dt}/audio/mezcla_previa.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{dt}/recortado.mov",
                    "-i", f"{dt}/audio/sfx.wav",
                    "-filter_complex", fc, "-map", "[mix]", "-ar", "48000", previa], check=True)
    m = loudnorm_medir(previa)
    norm = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:"
            f"measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
            f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", previa, "-af", norm, "-ar", "48000",
                    out], check=True)


# ----------------------------------------------------------------- principal
def motion_graphics(f, logo, pal):
    """Gráficos extra (graficos.py) sincronizados con palabras de la voz."""
    def t(palabra, desde=0.0):
        return next(p["s"] for p in pal if p["s"] >= desde
                    and re.sub(r"[^\wáéíóúñ]", "", p["t"].lower()) == palabra)

    perfil = graficos.Perfil(f, logo, t("si"), t("película") + 0.25,
                             toque=t("otro") + 0.1)
    enfasis = graficos.Enfasis(f, t("no", 18), t("mañana", 18) + 0.3)
    lista = graficos.Lista(f, t("su", 21), t("años") + 0.3, [
        (t("garantizar"), t("financiera", 21) + 0.2, "Garantizar", "la estabilidad financiera"),
        (t("proteger"), t("patrimonio") + 0.3, "Proteger", "este patrimonio"),
        (t("a", 27.2), t("años") - 0.1, "A lo largo", "de los años"),
    ])
    escena = graficos.Escena(f, t("no", 31) - 0.1, t("estos"), t("compiten") + 0.35,
                             t("son", 33))
    comentario = graficos.Comentario(f, logo, t("contame"), t("no", 42.5) + 0.3,
                                     t("comentarios"), t("ahorrando") + 0.3)
    detras = graficos.TextoDetras(f, t("seguros", 15.5) + 0.12, t("no", 18) - 0.05, "SEGUROS",
                                  cy=690)
    return [perfil, enfasis, lista, comentario, escena], detras, escena


def main():
    dt, out = sys.argv[1], sys.argv[2]
    f = Fuentes(f"{dt}/fonts")
    logo = Image.open(f"{dt}/logo.png").convert("RGBA")
    segs = json.load(open(f"{dt}/segmentos.json"))
    words = json.load(open(f"{dt}/words_cut.json"))["recortado"]

    # Límites de cada segmento (en cuadros del recortado) y tipo de corte.
    lim, n = [], 0
    for s in segs:
        nf = round((s["fin"] - s["ini"]) * FPS)
        lim.append((n, n + nf, s["clip"]))
        n += nf
    voz_frames = n
    voz = voz_frames / FPS
    cortes = []  # (tiempo de voz, tipo)
    ti = 0
    for (a, b, c), (a2, _, c2) in zip(lim, lim[1:]):
        if c != c2:
            cortes.append((a2 / FPS, TRANSICIONES[ti % len(TRANSICIONES)]))
            ti += 1
    t_fin_voz = T0 + voz
    total = t_fin_voz + CIERRE
    n_total = int(round(total * FPS))

    pal = palabras_corregidas(words)
    grupos = agrupar(pal)
    srt(grupos, f"{out}/subtitulos.srt")
    subs = Subtitulos(grupos, f)
    tarjetas = Tarjetas(f)
    cierre = Cierre(logo, f)
    fuente = Fuente(f"{dt}/recortado.mov")
    extras, detras, escena = motion_graphics(f, logo, pal)

    # Efectos de sonido sincronizados con lo que aparece en pantalla.
    eventos = [(0.08, "pop"), (T0 - 0.42, "whoosh")] if T0 > 0 else []
    for tc, tipo in cortes:
        if tipo == "fundido":
            eventos.append((T0 + tc - 0.05, "click"))
        elif tipo != "escena":
            eventos.append((T0 + tc - 0.25, "whoosh"))
    eventos += [(T0 + ini + 0.05, "pop") for ini, _, _ in TARJETAS]
    eventos += [(t_fin_voz - 0.45, "whoosh"), (t_fin_voz + 0.1, "pop"),
                (t_fin_voz + 0.6, "pop"), (t_fin_voz + 0.8, "click")]
    for g in extras + [detras]:
        eventos += [(T0 + t, k, gan) for t, k, gan in g.eventos()]

    enc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "21",
         "-profile:v", "high", "-level", "4.1",
         "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709",
         "-color_trc", "bt709", f"{dt}/video_sin_audio.mp4"], stdin=subprocess.PIPE)

    portada_src = None
    cara = caras(f"{dt}/recortado.mov", lim, f"{dt}/yunet.onnx")
    luts = luts_exposicion(lim, cara)
    for i in range(n_total):
        t = i / FPS
        tv = t - T0
        if t < T0:
            img = escena_intro(t, logo, f)
        elif t < t_fin_voz:
            nv = min(int(round(tv * FPS)), voz_frames - 1)
            arr = fuente.cuadro(nv)
            si = next(k for k, (a, b, _) in enumerate(lim) if a <= nv < b)
            a, b, clip = lim[si]
            menton, cx, _ = cara[si]
            if clip in luts:
                arr = luts[clip][arr]
            # punch-in alternado entre cortes consecutivos + leve acercamiento continuo
            z = zoom_minimo(menton) + (0.0 if si % 2 == 0 else 0.08) \
                + 0.03 * (nv - a) / max(1, b - a)
            dx, blanco, barras = 0.0, 0.0, None
            for tc, tipo in cortes:
                u = tv - tc
                if tipo == "zoom" and -0.25 <= u < 0.3:
                    z += 0.22 * (ease_in_out((u + 0.25) / 0.25) if u < 0 else
                                 1 - ease_out(u / 0.3))
                elif tipo == "whip" and -0.15 <= u < 0.15:
                    dx = -W * 0.9 * (ease_in_out((u + 0.15) / 0.15) if u < 0 else
                                     -(1 - ease_out(u / 0.15)))
                elif tipo == "fundido" and -0.12 <= u < 0.12:
                    blanco = 1 - abs(u) / 0.12
                elif tipo == "barras" and -0.3 <= u < 0.3:
                    barras = (u + 0.3) / 0.6
            img = encuadre(arr, z, menton, cx).convert("RGBA")
            if dx:
                # whip pan: desplazamiento horizontal con desenfoque de movimiento
                a_ = np.roll(np.asarray(img), int(dx), axis=1).astype(np.float32)
                paso = int(abs(dx) / 18) + 1
                acc = sum(np.roll(a_, k * paso, axis=1) for k in range(-4, 5)) / 9
                img = Image.fromarray(acc.astype(np.uint8), "RGBA")
            if blanco:
                img = Image.blend(img, Image.new("RGBA", (W, H), GRIS_CLARO + (255,)),
                                  0.85 * blanco)
            if barras is not None:
                barras_verticales(img, barras)
            if detras.activo(tv):
                # palabra detrás de la persona: texto encima del cuadro y la persona
                # (recortada con la misma transformación) otra vez encima del texto
                m = encuadre(detras.mascara(arr, nv), z, menton, cx)
                m = m.filter(ImageFilter.GaussianBlur(1.2))
                persona = img.copy()
                img.alpha_composite(detras.capa(tv))
                img.paste(persona, (0, 0), m)
            for g in extras:
                g.dibujar(img, tv)
            tarjetas.dibujar(img, tv)
            if not escena.ini <= tv < escena.fin:
                subs.dibujar(img, tv)
            if abs(tv - 17.5) < 0.5 / FPS:
                portada_src = arr.copy()
        else:
            img = cierre(t - t_fin_voz)

        # Paneles de entrada (intro -> video) y salida (video -> cierre)
        if T0 > 0:
            panel(img, t, T0 - 0.08, AMARILLO)
            panel(img, t, T0, ROJO)
        if t < t_fin_voz:
            panel(img, t, t_fin_voz - 0.16, AMARILLO)
            panel(img, t, t_fin_voz - 0.08, ROJO)
            panel(img, t, t_fin_voz, AZUL)
        enc.stdin.write(img.convert("RGB").tobytes())
        if i % 150 == 0:
            print(f"cuadro {i}/{n_total}", flush=True)
    enc.stdin.close()
    enc.wait()

    mezclar_audio(dt, eventos, total, f"{dt}/audio/final.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{dt}/video_sin_audio.mp4",
                    "-i", f"{dt}/audio/final.wav", "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-brand", "mp42",
                    "-movflags", "+faststart", "-shortest", f"{out}/frami_reel.mp4"], check=True)

    portada(portada_src, logo, f, f"{out}/portada.png")
    print(f"Listo: {total:.2f} s")


def portada(arr, logo, f, path):
    img = zoom(arr, 1.08).convert("RGBA")
    # degradado azul en la parte inferior para que el título se lea
    grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = np.zeros((H, W, 4), np.uint8)
    g[..., :3] = AZUL
    g[..., 3] = (np.clip((np.arange(H) - 1120) / 380, 0, 1) ** 1.2 * 235).astype(np.uint8)[:, None]
    img.alpha_composite(Image.fromarray(g, "RGBA"))
    pegar_escalado(img, logo, 150, SAFE_TOP + 115, 0.15)
    d = ImageDraw.Draw(img)
    fn = f("ExtraBold", 104)
    d.rounded_rectangle([W / 2 - 150, 1222, W / 2 + 150, 1240], radius=9, fill=ROJO)
    lineas = [("¿BOLSA", BLANCO), ("o SEGURO", AMARILLO), ("DE VIDA?", BLANCO)]
    y = 1312
    for txt, c in lineas:
        d.text((W / 2, y), txt, font=fn, fill=c, anchor="mm", stroke_width=4,
               stroke_fill=AZUL)
        y += 112
    img.convert("RGB").save(path)


if __name__ == "__main__":
    main()
