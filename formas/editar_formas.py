"""Edición del Reel de FORMAS Personalizado: subtítulos con palabras clave, motion graphics,
recorrido acelerado, efectos de sonido y cierre con el logo.

Uso: python3 editar_formas.py <dir_trabajo> <dir_salida>

<dir_trabajo> debe contener: recortado.mov, segmentos.json, words_cut.json (paso0_cortes.py
y la transcripción), logo.png, yunet.onnx, fonts/{Anton-Regular,Poppins-*}.ttf y
audio/{whoosh,pop,click}.wav. Escribe en <dir_salida>: formas_reel.mp4 y subtitulos.srt.
"""
import json
import re
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import graficos_formas as gf

W, H, FPS = 1080, 1920, 30
CIERRE = 3.0
SUB_Y = 1360
NARANJA, LIMA, BLANCO = gf.NARANJA, gf.LIMA, gf.BLANCO

TEXTO = (
    "Si sos de Itaembé Guazú y estás buscando un lugar para entrenar, este video es para vos. "
    "Te presentamos FORMAS Personalizado, un espacio pensado para que entrenes con comodidad, "
    "con máquinas de alto nivel y atención personalizada. Adaptamos las rutinas según tu nivel "
    "y tus objetivos para poder acompañarte en cada etapa de tu entrenamiento. Tenemos una "
    "novedad. Además de nuestros entrenamientos personalizados para mujeres, sumamos "
    "entrenamiento personalizado para hombres, a cargo de un personal trainer. ¿Quieres saber "
    "más sobre nuestro espacio y cómo puedes empezar a entrenar? Comunicate al número que "
    "aparece en pantalla y te brindamos toda la información. Te esperamos."
)
# Palabras que se muestran grandes (Anton, naranja) dentro del subtítulo.
CLAVE = {"entrenar", "formas", "comodidad", "máquinas", "nivel", "objetivos", "novedad",
         "mujeres", "hombres", "trainer", "número", "esperamos"}


def limpia(t):
    return re.sub(r"[^\wáéíóúñü]", "", t.lower())


class Fuentes:
    def __init__(self, d):
        self.d, self.cache = d, {}

    def __call__(self, nombre, tam):
        k = (nombre, tam)
        if k not in self.cache:
            archivo = "Anton-Regular" if nombre == "Anton" else f"Poppins-{nombre}"
            self.cache[k] = ImageFont.truetype(f"{self.d}/{archivo}.ttf", tam)
        return self.cache[k]


# ----------------------------------------------------------------- subtítulos
def palabras_corregidas(words):
    tokens = TEXTO.split()
    if len(tokens) != len(words):
        raise SystemExit(f"Transcripción: {len(words)} palabras; texto revisado: {len(tokens)}")
    return [dict(t=tok, s=w["s"], e=w["e"]) for tok, w in zip(tokens, words)]


def agrupar(pal):
    grupos, g = [], []
    for p in pal:
        if g and (len(g) == 3 or len(" ".join(x["t"] for x in g + [p])) > 17
                  or re.search(r"[.,?:!]$", g[-1]["t"]) or p["s"] - g[-1]["e"] > 0.35
                  or (limpia(p["t"]) in CLAVE and len(g) >= 2)):
            grupos.append(g)
            g = []
        g.append(p)
    grupos.append(g)
    out = []
    for i, g in enumerate(grupos):
        fin = grupos[i + 1][0]["s"] if i + 1 < len(grupos) else g[-1]["e"] + 0.3
        out.append(dict(pal=g, ini=g[0]["s"], fin=min(fin, g[-1]["e"] + 0.6)))
    return out


def srt(grupos, path):
    def ts(x):
        ms = int(round(x * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    with open(path, "w", encoding="utf-8") as f:
        for i, g in enumerate(grupos, 1):
            f.write(f"{i}\n{ts(g['ini'])} --> {ts(g['fin'])}\n"
                    f"{' '.join(p['t'] for p in g['pal'])}\n\n")


class Subtitulos:
    def __init__(self, grupos, f):
        self.grupos, self.f, self.cache = grupos, f, {}

    def imagen(self, gi, activa):
        k = (gi, activa)
        if k in self.cache:
            return self.cache[k]
        pal = [p["t"] for p in self.grupos[gi]["pal"]]
        esc = 1.0
        while True:
            fn = [self.f("Anton", int(124 * esc)) if limpia(p) in CLAVE
                  else self.f("ExtraBold", int(80 * esc)) for p in pal]
            esp = self.f("ExtraBold", int(80 * esc)).getlength(" ")
            ancho = sum(fo.getlength(p) for fo, p in zip(fn, pal)) + esp * (len(pal) - 1)
            if ancho <= 960 or esc < 0.6:
                break
            esc -= 0.06
        alto = int(170 * esc) + 60
        capa = Image.new("RGBA", (int(ancho) + 60, alto), (0, 0, 0, 0))
        d = ImageDraw.Draw(capa)
        x, base = 30, alto - 40
        for i, (p, fo) in enumerate(zip(pal, fn)):
            clave = limpia(p) in CLAVE
            color = NARANJA if (clave or i == activa) else BLANCO
            if clave and i == activa:
                color = LIMA
            d.text((x, base), p, font=fo, fill=color, anchor="ls", stroke_width=5,
                   stroke_fill=(15, 15, 15))
            x += fo.getlength(p) + esp
        img = gf.sombra(capa, 12, 170, (0, 6))
        self.cache[k] = img
        return img

    def dibujar(self, base, tv):
        for gi, g in enumerate(self.grupos):
            if g["ini"] - 0.05 <= tv < g["fin"]:
                activa = max([i for i, p in enumerate(g["pal"]) if tv >= p["s"] - 0.03] or [0])
                img = self.imagen(gi, activa)
                dt = tv - (g["ini"] - 0.05)
                esc = 0.6 + 0.48 * gf.ease_out(dt / 0.12) if dt < 0.12 else \
                    1.08 - 0.08 * gf.ease_out((dt - 0.12) / 0.1)
                gf.pegar(base, img, W / 2, SUB_Y, esc)
                return


# ----------------------------------------------------------------- video
class Fuente:
    def __init__(self, path):
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo",
                                   "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.n, self.frame = -1, None

    def cuadro(self, n):
        while self.n < n:
            buf = self.p.stdout.read(W * H * 3)
            if len(buf) < W * H * 3:
                break
            self.frame = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
            self.n += 1
        return self.frame


def centros_cara(path, lim, modelo):
    """Centro de la cara (mediana) por segmento con voz, para centrar los punch-in."""
    import cv2
    det = cv2.FaceDetectorYN.create(modelo, "", (W // 2, H // 2), 0.7)
    cap = cv2.VideoCapture(path)
    datos = [[] for _ in lim]
    f = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        if f % 6 == 0:
            si = next(k for k, s in enumerate(lim) if s["a"] <= f < s["b"])
            if lim[si]["vel"] == 1:
                _, res = det.detect(cv2.resize(fr, (W // 2, H // 2)))
                if res is not None:
                    x, y, w, h = res[0][:4] * 2
                    datos[si].append((x + w / 2, y + h / 2))
        f += 1
    return [tuple(np.median(np.array(d), axis=0)) if d else (W / 2, H * 0.4) for d in datos]


def barras(base, k, colores=(gf.LIMA, gf.NARANJA, gf.OSCURO)):
    """Barras diagonales de marca que cruzan la pantalla (k: 0..1); tapan todo en k=0.5."""
    d = ImageDraw.Draw(base)
    n = len(colores)
    for i, c in enumerate(colores):
        kk = gf.clamp(k * (1 + 0.25 * (n - 1)) - 0.25 * i)
        e = 4 * kk ** 3 if kk < 0.5 else 1 - (-2 * kk + 2) ** 3 / 2
        x = -W * 1.3 + W * 2.6 * e
        d.polygon([(x, 0), (x + W * 1.1, 0), (x + W * 1.1 - 300, H), (x - 300, H)], fill=c)


def zoom(arr, z, cx, cy):
    if z <= 1.0001:
        return Image.fromarray(arr)
    cw, ch = W / z, H / z
    x0 = gf.clamp(cx - cw / 2, 0, W - cw)
    y0 = gf.clamp(cy - ch / 2, 0, H - ch)
    return Image.fromarray(arr).transform((W, H), Image.EXTENT, (x0, y0, x0 + cw, y0 + ch),
                                          Image.BILINEAR)


# ----------------------------------------------------------------- audio
def leer_wav(path):
    with wave.open(path) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        return x.reshape(-1, w.getnchannels()).mean(axis=1)


def mezclar_audio(dt, eventos, total, out):
    """Voz procesada + efectos de sonido, normalizado a -14 LUFS (sin música)."""
    sr = 48000
    sfx = np.zeros(int(total * sr) + sr)
    muestras = {k: leer_wav(f"{dt}/audio/{k}.wav") for k in ("whoosh", "pop", "click")}
    ganancia = {"whoosh": 0.1, "pop": 0.13, "click": 0.09}
    for t, k, g in eventos:
        x = muestras[k] * ganancia[k] * g
        i = max(0, int(t * sr))
        sfx[i:i + len(x)] += x[:len(sfx) - i]
    with wave.open(f"{dt}/audio/sfx.wav", "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(sfx, -1, 1) * 32767).astype(np.int16).tobytes())
    fc = (f"[0:a]aresample=48000,highpass=f=80,afftdn=nf=-30:nr=8,"
          f"acompressor=threshold=-20dB:ratio=3:attack=5:release=90:makeup=2,"
          f"aformat=channel_layouts=stereo,apad,atrim=0:{total:.3f}[voz];"
          f"[voz][1:a]amix=inputs=2:normalize=0:duration=first,"
          f"aformat=channel_layouts=stereo[mix]")
    previa = f"{dt}/audio/mezcla_previa.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{dt}/recortado.mov",
                    "-i", f"{dt}/audio/sfx.wav", "-filter_complex", fc, "-map", "[mix]",
                    "-ar", "48000", previa], check=True)
    log = subprocess.run(["ffmpeg", "-hide_banner", "-i", previa, "-af",
                          "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    m = json.loads(log[log.rindex("{"):log.rindex("}") + 1])
    norm = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:"
            f"measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
            f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", previa, "-af", norm, "-ar", "48000",
                    out], check=True)


# ----------------------------------------------------------------- principal
def motion_graphics(f, pal, t_rapido):
    def t(palabra, desde=0.0):
        return next(p["s"] for p in pal if p["s"] >= desde and limpia(p["t"]) == palabra)

    def fin_de(palabra, desde=0.0):
        return next(p["e"] for p in pal if p["s"] >= desde and limpia(p["t"]) == palabra)

    extras = [
        gf.Ubicacion(f, 0.05, fin_de("entrenar") + 0.35),
        gf.Lista(f, t("un", 7), fin_de("personalizada") + 0.5, "UN ESPACIO PENSADO PARA VOS", [
            (t("comodidad"), t("comodidad") + 0.5, "COMODIDAD"),
            (t("máquinas"), fin_de("nivel") - 0.1, "MÁQUINAS DE ALTO NIVEL"),
            (t("atención"), fin_de("personalizada") - 0.2, "ATENCIÓN PERSONALIZADA"),
        ]),
        gf.NivelObjetivos(f, t("adaptamos"), t_rapido[0] - 0.05, t("nivel", 16),
                          t("objetivos"), t("cada")),
        gf.Rapido(*t_rapido),
        gf.Generos(f, t("además"), fin_de("trainer") + 0.12, t("mujeres"), t("hombres"),
                   t("personal")),
        gf.Telefono(f, t("comunicate"), fin_de("información") + 0.3, cy=1660),
    ]
    detras = [
        gf.TextoDetras(f, t("formas") - 0.1, t("un", 7) - 0.05, "FORMAS", cy=860),
        gf.TextoDetras(f, t("tenemos") + 0.05, t("además") - 0.05, "NOVEDAD", cy=400,
                       destellos=True),
    ]
    return extras, detras


def main():
    dt, out = sys.argv[1], sys.argv[2]
    f = Fuentes(f"{dt}/fonts")
    logo = Image.open(f"{dt}/logo.png").convert("RGBA")
    segs = json.load(open(f"{dt}/segmentos.json"))
    words = json.load(open(f"{dt}/words_cut.json"))["recortado"]

    lim, n = [], 0
    for s in segs:
        nf = round(s["dur"] * FPS)
        lim.append(dict(a=n, b=n + nf, clip=s["clip"], vel=s["vel"]))
        n += nf
    voz_frames = n
    t_fin = voz_frames / FPS
    total = t_fin + CIERRE
    rapidos = [s for s in lim if s["vel"] > 1]
    t_rapido = (rapidos[0]["a"] / FPS, rapidos[-1]["b"] / FPS)

    pal = palabras_corregidas(words)
    grupos = agrupar(pal)
    srt(grupos, f"{out}/subtitulos.srt")
    subs = Subtitulos(grupos, f)
    extras, detras = motion_graphics(f, pal, t_rapido)
    cierre = gf.Cierre(f, logo)
    fuente = Fuente(f"{dt}/recortado.mov")
    caras = centros_cara(f"{dt}/recortado.mov", lim, f"{dt}/yunet.onnx")

    eventos = [ev for g in extras + detras for ev in g.eventos()] + cierre.eventos(t_fin)
    # transición con barras entre el clip sentada (hombres / personal trainer) y el del número
    t_quieres = next(p["s"] for p in pal if limpia(p["t"]) == "quieres")
    t_barras = max(s["a"] / FPS for s in lim if s["a"] / FPS <= t_quieres)
    eventos.append((t_barras - 0.3, "whoosh", 1.1))

    enc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "21",
         "-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p", "-colorspace", "bt709",
         "-color_primaries", "bt709", "-color_trc", "bt709", f"{dt}/video_sin_audio.mp4"],
        stdin=subprocess.PIPE)

    n_total = int(round(total * FPS))
    for i in range(n_total):
        tv = i / FPS
        if i < voz_frames:
            arr = fuente.cuadro(i)
            si = next(k for k, s in enumerate(lim) if s["a"] <= i < s["b"])
            s = lim[si]
            cx, cy = caras[si]
            if s["vel"] == 1:
                # punch-in alternado entre cortes + leve acercamiento continuo
                z = (1.0 if si % 2 == 0 else 1.08) + 0.03 * (i - s["a"]) / max(1, s["b"] - s["a"])
            else:
                z = 1.0
            u = tv - t_barras
            if -0.3 <= u < 0.3:  # zoom rápido que acompaña a las barras
                z += 0.18 * (1 - abs(u) / 0.3)
            img = zoom(arr, z, cx, cy).convert("RGBA")
            for g in detras:
                if g.activo(tv):
                    m = zoom(g.mascara(arr, i), z, cx, cy).filter(ImageFilter.GaussianBlur(1.2))
                    persona = img.copy()
                    img.alpha_composite(g.capa(tv))
                    img.paste(persona, (0, 0), m)
            if -0.3 <= u < 0.3:
                barras(img, (u + 0.3) / 0.6)
            for g in extras:
                g.dibujar(img, tv)
            subs.dibujar(img, tv)
            # paneles de salida hacia el cierre
            for col, dtm in ((gf.LIMA, 0.16), (gf.NARANJA, 0.08), (gf.OSCURO, 0.0)):
                k = (tv - (t_fin - dtm - 0.3)) / 0.6
                if 0 <= k <= 1:
                    hp = H * 1.35
                    c = H + hp / 2 - (H + hp) * gf.ease_out(k) ** 1.2
                    ImageDraw.Draw(img).rectangle([0, c - hp / 2, W, c + hp / 2], fill=col)
        else:
            img = cierre(tv - t_fin)
        enc.stdin.write(img.convert("RGB").tobytes())
        if i % 150 == 0:
            print(f"cuadro {i}/{n_total}", flush=True)
    enc.stdin.close()
    enc.wait()

    mezclar_audio(dt, eventos, total, f"{dt}/audio/final.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{dt}/video_sin_audio.mp4",
                    "-i", f"{dt}/audio/final.wav", "-map", "0:v:0", "-map", "1:a:0",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-brand", "mp42",
                    "-movflags", "+faststart", "-shortest", f"{out}/formas_reel.mp4"], check=True)
    print(f"Listo: {total:.2f} s")


if __name__ == "__main__":
    main()
