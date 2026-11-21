"""Reel / historia de la Zona Kids de Rabbit (1080x1920).

1. Estabiliza el video (vidstab, dos pasadas).
2. Mejora cada cuadro con Real-ESRGAN x4 (mezclado con Lanczos para que no quede plástico)
   y le da un poco más de contraste y color.
3. Agrega los textos sincronizados con lo que se ve, música y efectos.

Uso: python3 editar_kids.py <video> <x4v3.onnx> <emblema.png> <dir_fuentes> <dir_audio> <salida.mp4>
<dir_audio> debe tener musica.wav, whoosh.wav, pop.wav y click.wav (frami/musica_sfx.py).
"""
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", "proximamente"))
sys.path.insert(0, os.path.join(AQUI, "..", "historia_picada"))
sys.path.insert(0, os.path.join(AQUI, "..", "minigolf"))
from flyer_proximamente import F, ROJO, degradado, marca, sombra  # noqa: E402
from historia_picada import curva_s, esrgan_sesion, esrgan_con  # noqa: E402
from portada_minigolf import cartel  # noqa: E402

W, H, FPS = 1080, 1920, 30
FIN = 11.4            # se corta el último tramo (un poste fuera de foco)
MEZCLA_IA = 0.7
BLANCO = (255, 255, 255)

# (inicio, fin) de cada texto, en segundos del video
T_KIDS = (0.15, 3.0)
T_ESPACIO = (3.1, 6.15)
T_JUEGAN = (6.4, 8.95)
T_CIERRE = (9.2, FIN)


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_back(x, s=1.7):
    x = clamp(x)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def pegar(base, im, cx, cy, esc=1.0, alfa=1.0):
    if esc <= 0.01 or alfa <= 0.01:
        return
    if abs(esc - 1) > 1e-3:
        im = im.resize((max(1, int(im.width * esc)), max(1, int(im.height * esc))),
                       Image.BILINEAR)
    if alfa < 0.999:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alfa)))
    base.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


def entrada_salida(t, ini, fin, t_in=0.35, t_out=0.25):
    """(escala, alfa, dy) con entrada con rebote y salida suave; None si no está activo."""
    if not ini <= t < fin:
        return None
    if t - ini < t_in:
        k = (t - ini) / t_in
        return 0.8 + 0.2 * ease_back(k), clamp(k * 2.5), 50 * (1 - ease_out(k))
    if fin - t < t_out and fin < FIN - 0.01:
        k = 1 - (fin - t) / t_out
        return 1 - 0.08 * k, 1 - ease_out(k), -40 * ease_out(k)
    return 1.0, 1.0, 0.0


# ----------------------------------------------------------------- piezas de texto
def lineas(f, partes, tam=62, peso="ExtraBold", interlineado=1.22):
    """Bloque de texto centrado. partes: [[(texto, resaltado)], ...]; lo resaltado va en
    blanco sobre una banda roja redondeada."""
    fn = f(peso, tam)
    lh = int(tam * interlineado)
    ancho = int(max(sum(fn.getlength(t) for t, _ in l) for l in partes)) + 80
    im = Image.new("RGBA", (ancho, lh * len(partes) + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, l in enumerate(partes):
        tw = sum(fn.getlength(t) for t, _ in l)
        x = (ancho - tw) / 2
        y = 20 + lh * i + lh / 2
        for t, res in l:
            w = fn.getlength(t)
            if res:
                d.rounded_rectangle([x - 14, y - tam * 0.62, x + w + 14, y + tam * 0.62],
                                    radius=14, fill=ROJO)
            d.text((x, y), t, font=fn, fill=BLANCO, anchor="lm")
            x += w
    return sombra(im, 14, 220, (0, 8))


# ----------------------------------------------------------------- video
def leer_cuadros(path, hasta=None):
    hasta = FIN if hasta is None else hasta
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-t", str(hasta), "-r", str(FPS),
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    out = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0",
                                   "-show_entries", "stream=width,height", "-of", "csv=p=0",
                                   path], text=True)
    w, h = map(int, out.strip().split(","))
    while True:
        buf = p.stdout.read(w * h * 3)
        if len(buf) < w * h * 3:
            break
        yield Image.fromarray(np.frombuffer(buf, np.uint8).reshape(h, w, 3))


def estabilizar(entrada, salida, tmp):
    trf = os.path.join(tmp, "transforms.trf")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", entrada, "-vf",
                    f"vidstabdetect=shakiness=6:accuracy=12:result={trf}", "-f", "null", "-"],
                   check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", entrada, "-vf",
                    f"vidstabtransform=input={trf}:smoothing=14:zoom=2:optzoom=0:"
                    "interpol=bicubic", "-c:v", "libx264", "-crf", "12", "-preset", "fast",
                    "-an", salida], check=True)


def mejorar(cuadro, ses):
    ia = esrgan_con(ses, cuadro).resize((W, H), Image.LANCZOS)
    clasica = cuadro.resize((W, H), Image.LANCZOS)
    img = Image.blend(clasica, ia, MEZCLA_IA)
    img = curva_s(img, 0.08)
    img = ImageEnhance.Color(img).enhance(1.12)
    return img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=45, threshold=3))


# ----------------------------------------------------------------- audio
def leer_wav(path):
    with wave.open(path) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        return x.reshape(-1, w.getnchannels()), w.getframerate()


def mezclar_audio(video, dir_audio, eventos, out, tmp):
    sr = 48000
    n = int(FIN * sr)
    amb = os.path.join(tmp, "ambiente.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-t", str(FIN), "-vn", "-ac",
                    "2", "-ar", str(sr), amb], check=True)
    ambiente, _ = leer_wav(amb)
    ambiente = np.pad(ambiente, ((0, max(0, n - len(ambiente))), (0, 0)))[:n] * 0.22
    mus, _ = leer_wav(f"{dir_audio}/musica.wav")
    mus = mus if mus.shape[1] == 2 else np.repeat(mus, 2, axis=1)
    mus = np.pad(mus, ((0, max(0, n - len(mus))), (0, 0)))[:n] * 0.6
    t = np.arange(n) / sr
    env = np.clip(t / 0.3, 0, 1) * np.clip((FIN - t) / 0.8, 0, 1)
    mix = (mus + ambiente) * env[:, None]
    sfx = {k: leer_wav(f"{dir_audio}/{k}.wav")[0].mean(axis=1) for k in ("whoosh", "pop", "click")}
    gan = {"whoosh": 0.3, "pop": 0.4, "click": 0.3}
    for tt, k in eventos:
        x = sfx[k] * gan[k]
        i = int(tt * sr)
        mix[i:i + len(x)] += x[:n - i, None]
    previa = os.path.join(tmp, "mezcla.wav")
    with wave.open(previa, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", previa, "-af",
                    "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", str(sr), out], check=True)


# ----------------------------------------------------------------- principal
def main():
    video, modelo, emblema_p, fuentes, dir_audio, salida = sys.argv[1:7]
    f = F(fuentes)
    ses = esrgan_sesion(modelo)
    kids = cartel(f, "ZONA KIDS", 170, rot=-3)
    sub_kids = lineas(f, [[("Los chicos también", False)], [("tienen su lugar en Rabbit", False)]],
                      52, "Bold")
    espacio = lineas(f, [[("Un espacio", False)], [("pensado para ellos", True)]], 70)
    juegan = lineas(f, [[("Ellos juegan,", False)], [("vos disfrutás.", True)]], 72)
    logo = marca(f, Image.open(emblema_p))
    familia = lineas(f, [[("¡Los esperamos en familia!", False)]], 46, "Bold")

    with tempfile.TemporaryDirectory() as tmp:
        estable = os.path.join(tmp, "estable.mp4")
        estabilizar(video, estable, tmp)
        enc = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
             "-crf", "18", "-pix_fmt", "yuv420p", "-colorspace", "bt709",
             "-color_primaries", "bt709", "-color_trc", "bt709",
             os.path.join(tmp, "video.mp4")], stdin=subprocess.PIPE)
        portada = None
        for i, cuadro in enumerate(leer_cuadros(estable)):
            t = i / FPS
            img = mejorar(cuadro, ses).convert("RGBA")
            if t >= T_CIERRE[0] - 0.3:
                degradado(img, 1250, 1760, int(200 * clamp((t - T_CIERRE[0] + 0.3) / 0.4)))
            if t < T_JUEGAN[1]:
                degradado(img, 0, 820, 150, arriba=True)
            e = entrada_salida(t, *T_KIDS)
            if e:
                pegar(img, kids, W / 2, 380 + e[2], e[0], e[1])
                e2 = entrada_salida(t, T_KIDS[0] + 0.25, T_KIDS[1])
                if e2:
                    pegar(img, sub_kids, W / 2, 620 + e2[2], e2[0], e2[1])
            for pieza, (ini, fin), y in ((espacio, T_ESPACIO, 450), (juegan, T_JUEGAN, 430)):
                e = entrada_salida(t, ini, fin)
                if e:
                    pegar(img, pieza, W / 2, y + e[2], e[0], e[1])
            e = entrada_salida(t, *T_CIERRE)
            if e:
                pegar(img, logo, W / 2, 1480 + e[2], e[0], e[1])
                e2 = entrada_salida(t, T_CIERRE[0] + 0.3, T_CIERRE[1])
                if e2:
                    pegar(img, familia, W / 2, 1610 + e2[2], e2[0], e2[1])
            if abs(t - 1.0) < 0.5 / FPS:
                portada = img.copy()
            enc.stdin.write(img.convert("RGB").tobytes())
            if i % 30 == 0:
                print(f"cuadro {i}", flush=True)
        enc.stdin.close()
        enc.wait()

        eventos = [(T_KIDS[0], "pop"), (T_KIDS[0] + 0.3, "pop"), (T_ESPACIO[0] - 0.1, "whoosh"),
                   (T_ESPACIO[0] + 0.2, "pop"), (T_JUEGAN[0] - 0.1, "whoosh"),
                   (T_JUEGAN[0] + 0.2, "pop"), (T_CIERRE[0], "pop"), (T_CIERRE[0] + 0.35, "click")]
        audio = os.path.join(tmp, "final.wav")
        mezclar_audio(video, dir_audio, eventos, audio, tmp)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(tmp, "video.mp4"),
                        "-i", audio, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest",
                        salida], check=True)
    if portada is not None:
        portada.convert("RGB").save(salida.rsplit(".", 1)[0] + "_portada.png")
    print("Listo")


if __name__ == "__main__":
    main()
