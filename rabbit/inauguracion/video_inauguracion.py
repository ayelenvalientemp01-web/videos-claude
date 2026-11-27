"""Video de la GRAN APERTURA de Rabbit (1080x1920, 30 fps, 20 s).

Estructura tomada de la referencia (TikTok) y rediseñada con la marca de Rabbit:
  0.0-1.5   cuenta regresiva 3-2-1 sobre el mini golf en blanco y negro
  1.5-2.0   destello
  2.0-3.5   "¿ESTÁS LISTO?" (espaciado que se cierra) sobre el cartel
  3.5-5.5   "ESTE SÁBADO" con ecos tipo glitch
  5.5-9.0   fecha "28.11" + "19 HS" con cortes de fotos y destellos
  9.0-10.5  pausa en negro (suspenso)
  10.5-11.5 revelación del emblema con estallido de luz
  11.5-17.0 "GRAN APERTURA" + "SÁBADO 28 · 19 HS" con cortes rápidos
  17.0-20.0 placa final con marca, fecha, hora y dirección

Uso: python3 video_inauguracion.py <dir_fotos> <minigolf.mp4> <kids.mp4> <insignia.png>
                                   <dir_fuentes> <musica.wav> <salida_base>
Genera <salida_base>.mp4 (con música original), <salida_base>_sin_musica.mp4 y
<salida_base>_portada.png.
"""
import math
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
DUR = 20.0
ROJO = (255, 18, 18)
CREMA = (242, 232, 212)
VERDE = (0, 200, 70)
BLANCO = (255, 255, 255)

DIA = "SÁBADO"
FECHA = "28.11"
HORA = "19 HS"
FECHA_LARGA = "Sábado 28 de noviembre · 19 h"
DIRECCION = "Av. Lavalle 3288 · Posadas"

# fotos (nombre de archivo dentro de dir_fotos) y centro de encuadre (cx, cy)
FOTOS = {
    "cartel": ("c02059ea-image.jpg", (0.5, 0.52)),
    "cartel2": ("9757c115-image.jpg", (0.5, 0.52)),
    "minigolf": ("554b5859-image.jpg", (0.45, 0.55)),
    "kids1": ("edb8b42f-image.jpg", (0.5, 0.55)),
    "kids2": ("3485d026-image.jpg", (0.5, 0.55)),
    "mesas": ("2f674494-image.jpg", (0.5, 0.55)),
    "mesas2": ("837d8a35-image.jpg", (0.5, 0.5)),
    "picada": ("54fc1d51-image.jpg", (0.4, 0.5)),
    "fachada": ("82c4fca1-image.jpg", (0.5, 0.5)),
}


# ----------------------------------------------------------------- utilidades
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def eo(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def eio(x):
    x = clamp(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def eback(x, s=1.7):
    x = clamp(x)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


class F:
    def __init__(self, d):
        self.d, self.c = d, {}

    def __call__(self, nombre, tam):
        k = (nombre, tam)
        if k not in self.c:
            archivo = "Anton-Regular.ttf" if nombre == "Anton" else f"Poppins-{nombre}.ttf"
            self.c[k] = ImageFont.truetype(f"{self.d}/{archivo}", tam)
        return self.c[k]


def cubrir(im, cx=0.5, cy=0.5, w=W * 1.35, h=H * 1.35):
    """Recorte que cubre w x h (con margen para mover la cámara)."""
    w, h = int(w), int(h)
    esc = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * esc), round(im.height * esc)), Image.LANCZOS)
    x0 = int(min(max(cx * im.width - w / 2, 0), im.width - w))
    y0 = int(min(max(cy * im.height - h / 2, 0), im.height - h))
    return im.crop((x0, y0, x0 + w, y0 + h))


def camara(im, z, dx=0.0, dy=0.0):
    """Ventana W x H de 'im' (que es 1.35x) con zoom z (>=1) y desplazamiento relativo."""
    cw = im.width / 1.35 / z
    ch = cw * H / W
    x0 = (im.width - cw) / 2 + dx * (im.width - cw) / 2
    y0 = (im.height - ch) / 2 + dy * (im.height - ch) / 2
    return im.transform((W, H), Image.EXTENT, (x0, y0, x0 + cw, y0 + ch), Image.BILINEAR)


def zoom_blur(img, fuerza):
    """Desenfoque de zoom (promedia copias escaladas)."""
    if fuerza <= 0.01:
        return img
    a = np.asarray(img, np.float32)
    acc = a.copy()
    n = 6
    for i in range(1, n):
        z = 1 + fuerza * 0.12 * i / n
        cw, ch = W / z, H / z
        x0, y0 = (W - cw) / 2, (H - ch) / 2
        acc += np.asarray(img.transform((W, H), Image.EXTENT, (x0, y0, x0 + cw, y0 + ch),
                                        Image.BILINEAR), np.float32)
    return Image.fromarray((acc / n).astype(np.uint8))


def oscurecer(img, k):
    return ImageEnhance.Brightness(img).enhance(k)


def gris(img, contraste=1.25):
    return ImageEnhance.Contrast(img.convert("L").convert("RGB")).enhance(contraste)


YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)


def luz(img, t, semilla, fuerza=1.0, color=(255, 80, 30)):
    """Destello de luz (light leak) cálido que cruza la pantalla; mezcla 'screen'."""
    rng = np.random.default_rng(semilla)
    a = np.asarray(img, np.float32) / 255
    cx = W * (-0.3 + 1.6 * t)
    cy = H * rng.uniform(0.2, 0.8)
    r = W * rng.uniform(0.45, 0.7)
    g = np.exp(-(((XX - cx) / r) ** 2 + ((YY - cy) / (r * 1.6)) ** 2)) * fuerza
    c = np.array(color, np.float32) / 255
    capa = g[..., None] * c
    out = 1 - (1 - a) * (1 - np.clip(capa, 0, 1))
    return Image.fromarray((out * 255).astype(np.uint8))


def destello(img, k):
    """Fundido a blanco (k 0..1)."""
    if k <= 0:
        return img
    return Image.blend(img, Image.new("RGB", (W, H), (255, 245, 235)), clamp(k))


def viñeta(img, fuerza=0.55):
    r = np.sqrt(((XX - W / 2) / (W * 0.7)) ** 2 + ((YY - H / 2) / (H * 0.7)) ** 2)
    v = (1 - fuerza * np.clip(r - 0.3, 0, 1) ** 1.5)[..., None]
    return Image.fromarray((np.asarray(img, np.float32) * v).astype(np.uint8))


VIÑ = None


# ----------------------------------------------------------------- tipografía
def texto(fn, t, color, espaciado=0, sombra=True):
    asc, desc = fn.getmetrics()
    ancho = int(sum(fn.getlength(c) for c in t) + espaciado * max(0, len(t) - 1)) + 40
    im = Image.new("RGBA", (ancho, asc + desc + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 20
    for c in t:
        d.text((x, 20), c, font=fn, fill=color)
        x += fn.getlength(c) + espaciado
    if sombra:
        s = Image.new("RGBA", im.size, (0, 0, 0, 0))
        s.putalpha(im.getchannel("A").filter(ImageFilter.GaussianBlur(10)).point(
            lambda v: v * 170 // 255))
        s.alpha_composite(im)
        im = s
    return im


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


def espaciado_anim(f, peso, tam, t, k, color=BLANCO, desde=40, hasta=4):
    """Texto cuyo espaciado entre letras se cierra (k 0..1)."""
    return texto(f(peso, tam), t, color, espaciado=desde + (hasta - desde) * eo(k))


def etiqueta_roja(f, t, tam=46):
    fn = f("ExtraBold", tam)
    w, h = int(fn.getlength(t)) + 70, int(tam * 1.75)
    s = 2
    im = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, w * s - 1, h * s - 1], radius=18 * s, fill=ROJO)
    im = im.resize((w, h), Image.LANCZOS)
    ImageDraw.Draw(im).text((w / 2, h / 2), t, font=fn, fill=BLANCO, anchor="mm")
    return im


# ----------------------------------------------------------------- video
def leer_video(path, ini, dur, cx=0.5, cy=0.5):
    """Cuadros (a 30 fps) de un video, recortados a 1.35x para mover la cámara."""
    out = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0",
                                   "-show_entries", "stream=width,height", "-of", "csv=p=0",
                                   path], text=True)
    w, h = map(int, out.strip().split(","))
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(ini), "-i", path, "-t", str(dur),
                        "-r", str(FPS), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       capture_output=True, check=True).stdout
    n = len(p) // (w * h * 3)
    return [cubrir(Image.fromarray(np.frombuffer(p[i * w * h * 3:(i + 1) * w * h * 3],
                                                 np.uint8).reshape(h, w, 3)), cx, cy)
            for i in range(n)]


# ----------------------------------------------------------------- principal
def main():
    dir_fotos, v_golf, v_kids, insignia_p, fuentes, musica, salida = sys.argv[1:8]
    f = F(fuentes)
    fotos = {}
    for k, (archivo, (cx, cy)) in FOTOS.items():
        im = Image.open(os.path.join(dir_fotos, archivo)).convert("RGB")
        im = ImageEnhance.Contrast(im).enhance(1.08)
        fotos[k] = cubrir(ImageEnhance.Color(im).enhance(1.1), cx, cy)
    golf = leer_video(v_golf, 0.0, 5.2, 0.5, 0.5)
    kids = leer_video(v_kids, 6.0, 2.0, 0.5, 0.5)
    insignia = Image.open(insignia_p).convert("RGBA")

    # piezas de texto fijas
    numeros = {n: texto(f("Anton", 980), str(n), ROJO, sombra=True) for n in (3, 2, 1)}
    listo = texto(f("ExtraBold", 150), "LISTO?", BLANCO)
    dia = texto(f("ExtraBold", 150), DIA, BLANCO)
    este = texto(f("Medium", 60), "E S T E", CREMA)
    fecha = texto(f("ExtraBold", 290), FECHA, BLANCO)
    hora = etiqueta_roja(f, HORA, 58)
    gran = texto(f("ExtraBold", 178), "GRAN", BLANCO)
    apertura = texto(f("ExtraBold", 178), "APERTURA", ROJO)
    sup = etiqueta_roja(f, f"{DIA} 28 · {HORA}", 44)
    sup_ext = texto(f("SemiBold", 34), "FOOD & DRINKS · EVENTOS", CREMA)
    # placa final
    rabbit = texto(f("SemiBold", 200), "Rabbit", ROJO)
    sub = texto(f("Bold", 34), "FOOD & DRINKS - EVENTOS", BLANCO, espaciado=2)
    p_gran = texto(f("ExtraBold", 76), "GRAN APERTURA", BLANCO)
    p_fecha = texto(f("SemiBold", 44), FECHA_LARGA, CREMA)
    p_dir = texto(f("Medium", 36), DIRECCION, (200, 200, 210))
    p_te = texto(f("ExtraBold", 54), "¡Te esperamos!", ROJO)

    cortes_e = [(5.5, "mesas"), (6.25, "minigolf"), (7.0, "kids1"), (7.75, "picada"),
                (8.5, "cartel2")]
    cortes_h = [(11.5, "kids2"), (12.5, "golfvid"), (13.5, "mesas2"), (14.5, "kidsvid"),
                (15.5, "picada"), (16.25, "minigolf")]

    with tempfile.TemporaryDirectory() as tmp:
        vid = os.path.join(tmp, "v.mp4")
        enc = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
             "-crf", "18", "-pix_fmt", "yuv420p", "-colorspace", "bt709",
             "-color_primaries", "bt709", "-color_trc", "bt709", vid], stdin=subprocess.PIPE)
        portada = None
        for i in range(int(DUR * FPS)):
            t = i / FPS
            img = None
            texto_capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))

            if t < 1.5:                                   # cuenta regresiva
                n = 3 - int(t / 0.5)
                u = (t % 0.5) / 0.5
                fr = golf[min(len(golf) - 1, int(t * FPS * 1.6))]
                img = oscurecer(gris(camara(fr, 1.05 + 0.25 * u, dy=-0.2)), 0.75)
                img = zoom_blur(img, 1 - u) if u < 0.25 else img
                pegar(texto_capa, numeros[n], W / 2, H / 2 + 60, 1.25 - 0.25 * eo(u * 2))
            elif t < 2.0:                                 # destello
                u = (t - 1.5) / 0.5
                img = Image.new("RGB", (W, H), (0, 0, 0))
                img = luz(img, u, 3, 1.4 * math.sin(math.pi * u), (255, 120, 60))
            elif t < 3.5:                                 # ¿ESTÁS LISTO?
                u = (t - 2.0) / 1.5
                img = oscurecer(camara(fotos["cartel"], 1.35 - 0.2 * eo(u)), 0.45 * eo(u * 3))
                img = img.filter(ImageFilter.GaussianBlur(6))
                k = eo((t - 2.05) / 0.8)
                pegar(texto_capa, espaciado_anim(f, "Medium", 70, "¿ESTÁS",
                                                 k, CREMA, 60, 10), W / 2, 830, 1, clamp(k * 2))
                kl = (t - 2.35) / 0.45
                pegar(texto_capa, listo, W / 2, 960, 0.85 + 0.15 * eback(kl), clamp(kl * 2.5))
            elif t < 5.5:                                 # ESTE SÁBADO con ecos
                u = (t - 3.5) / 2.0
                img = oscurecer(camara(fotos["mesas2"], 1.1 + 0.18 * u, dx=0.2 - 0.4 * u),
                                0.25 + 0.4 * eo(u * 2))
                k = eo((t - 3.55) / 0.5)
                pegar(texto_capa, este, W / 2, 820, 1, k)
                for j, off in enumerate((-110, 110)):       # ecos que se juntan
                    a = (1 - eo((t - 3.6) / 0.6)) * 0.5
                    pegar(texto_capa, dia, W / 2, 950 + off * (1 - eo((t - 3.6) / 0.6)), 1, a)
                pegar(texto_capa, dia, W / 2, 950, 1, eo((t - 3.65) / 0.35))
            elif t < 9.0:                                 # fecha con cortes
                j = max(k for k, (tc, _) in enumerate(cortes_e) if t >= tc)
                tc, nombre = cortes_e[j]
                u = (t - tc) / 0.75
                img = oscurecer(camara(fotos[nombre], 1.25 - 0.12 * eo(u), dy=0.05), 0.6)
                if t - tc < 0.1:
                    img = zoom_blur(img, 1 - (t - tc) / 0.1)
                    img = destello(img, 0.5 * (1 - (t - tc) / 0.1))
                img = luz(img, u, 10 + j, 0.55)
                if t > 8.5:
                    img = oscurecer(img, 1 - eio((t - 8.5) / 0.5))
                k = (t - 5.5) / 0.6
                pegar(texto_capa, espaciado_anim(f, "ExtraBold", 290, FECHA, k, BLANCO, 70, 0),
                      W / 2, 900, 1, clamp(k * 2) * (1 - eio((t - 8.6) / 0.4)))
                kh = (t - 5.9) / 0.4
                pegar(texto_capa, hora, W / 2, 1110, 0.8 + 0.2 * eback(kh),
                      clamp(kh * 2) * (1 - eio((t - 8.6) / 0.4)))
            elif t < 10.5:                                # pausa en negro
                u = (t - 9.0) / 1.5
                img = Image.new("RGB", (W, H), (0, 0, 0))
                if u > 0.6:   # pulso rojo tenue que anticipa el impacto
                    img = luz(img, 0.5, 21, 0.25 * (u - 0.6) / 0.4, ROJO)
            elif t < 11.5:                                # revelación del emblema
                u = (t - 10.5) / 1.0
                img = oscurecer(camara(fotos["cartel"], 1.3 - 0.15 * u), 0.35).filter(
                    ImageFilter.GaussianBlur(12))
                img = luz(img, 0.5, 30, 1.2 * (1 - eo(u * 2)), (255, 150, 90))
                img = destello(img, 1 - eo(u / 0.18))
                pegar(texto_capa, insignia, W / 2, 880, 0.55 + 0.25 * eback(u / 0.45), 1)
                pegar(texto_capa, sup_ext, W / 2, 1210, 1, eo((u - 0.3) / 0.4))
            elif t < 17.0:                                # GRAN APERTURA con cortes
                j = max(k for k, (tc, _) in enumerate(cortes_h) if t >= tc)
                tc, nombre = cortes_h[j]
                tf = cortes_h[j + 1][0] if j + 1 < len(cortes_h) else 17.0
                u = (t - tc) / (tf - tc)
                if nombre == "golfvid":
                    fr = golf[min(len(golf) - 1, int((t - tc) * FPS * 1.4) + 40)]
                    img = camara(fr, 1.1 + 0.1 * u)
                elif nombre == "kidsvid":
                    img = camara(kids[min(len(kids) - 1, int((t - tc) * FPS))], 1.05)
                else:
                    img = camara(fotos[nombre], 1.22 - 0.14 * eo(u), dx=0.15 - 0.3 * u)
                img = oscurecer(img, 0.62)
                if t - tc < 0.1:
                    img = zoom_blur(img, 1 - (t - tc) / 0.1)
                    img = destello(img, 0.6 * (1 - (t - tc) / 0.1))
                img = luz(img, u, 40 + j, 0.5 if j % 2 == 0 else 0.3,
                          (255, 70, 40) if j % 2 == 0 else (255, 160, 60))
                kg = (t - 11.55) / 0.4
                pegar(texto_capa, gran, W / 2, 830, 0.8 + 0.2 * eback(kg), clamp(kg * 2.5))
                ka = (t - 11.7) / 0.4
                pegar(texto_capa, apertura, W / 2, 1010, 0.8 + 0.2 * eback(ka), clamp(ka * 2.5))
                ks = (t - 12.0) / 0.4
                pegar(texto_capa, sup, W / 2, 640 + 30 * (1 - eo(ks)), 1, clamp(ks * 2))
                ke = (t - 12.2) / 0.4
                pegar(texto_capa, sup_ext, W / 2, 1180, 1, clamp(ke * 2))
                if t > 16.7:
                    img = destello(img, (t - 16.7) / 0.3)
            else:                                         # placa final
                u = t - 17.0
                base = np.zeros((H, W, 3), np.float32)
                g = np.exp(-(((XX - W / 2) / (W * 0.8)) ** 2 + ((YY - 760) / (H * 0.35)) ** 2))
                base += g[..., None] * np.array((90, 0, 8), np.float32)
                img = Image.fromarray(base.astype(np.uint8))
                img = destello(img, 1 - eo(u / 0.25))
                pegar(texto_capa, insignia, W / 2, 560, 0.45 * eback(u / 0.5), clamp(u * 4))
                pegar(texto_capa, rabbit, W / 2, 860, 0.85 + 0.15 * eback((u - 0.2) / 0.45),
                      clamp((u - 0.2) * 4))
                ks = clamp((u - 0.45) / 0.4)
                if ks > 0:
                    pegar(texto_capa, sub, W / 2, 1010, 1, ks)
                    d = ImageDraw.Draw(texto_capa)
                    lw = 90 * eo(ks)
                    d.rounded_rectangle([W / 2 - sub.width / 2 - 10 - lw, 1008,
                                         W / 2 - sub.width / 2 - 10, 1016], radius=4, fill=VERDE)
                    d.rounded_rectangle([W / 2 + sub.width / 2 + 10, 1008,
                                         W / 2 + sub.width / 2 + 10 + lw, 1016], radius=4,
                                        fill=ROJO)
                for k_, (pieza, y, t0) in enumerate(((p_gran, 1150, 0.7), (p_fecha, 1245, 0.85),
                                                     (p_dir, 1315, 1.0), (p_te, 1430, 1.2))):
                    kk = (u - t0) / 0.4
                    pegar(texto_capa, pieza, W / 2, y + 30 * (1 - eo(kk)), 1, clamp(kk * 2))

            img = viñeta(img, 0.5).convert("RGBA")
            img.alpha_composite(texto_capa)
            if abs(t - 12.6) < 0.5 / FPS:
                portada = img.copy()
            enc.stdin.write(img.convert("RGB").tobytes())
            if i % 60 == 0:
                print(f"cuadro {i}/{int(DUR * FPS)}", flush=True)
        enc.stdin.close()
        enc.wait()

        audio = os.path.join(tmp, "a.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", musica, "-af",
                        "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", audio], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", vid, "-i", audio, "-map", "0:v",
                        "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                        "-movflags", "+faststart", salida + ".mp4"], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", vid, "-c", "copy",
                        "-movflags", "+faststart", salida + "_sin_musica.mp4"], check=True)
    if portada is not None:
        portada.convert("RGB").save(salida + "_portada.png")
    print("Listo")


if __name__ == "__main__":
    main()
