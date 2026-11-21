"""Historia de Instagram (1080x1920) con la foto de la picada de Rabbit.

La foto se mejora (Real-ESRGAN x4 + retoque suave), ocupa toda la historia y lleva arriba,
en la zona oscura, el logo chico, la frase y un CTA discreto, sin tapar la picada ni el
cartel de Rabbit de la pared.

Uso: python3 historia_picada.py <foto.jpg> <x4v3.onnx> <emblema.png> <dir_fuentes> <salida.png>
El modelo x4v3.onnx se genera con nitidez/esrgan_onnx.py a partir de
realesr-general-x4v3.pth (Real-ESRGAN).
"""
import os
import sys

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                                "proximamente"))
from flyer_proximamente import F, ROJO, degradado, insignia, sombra  # noqa: E402

W, H = 1080, 1920
LINEAS = ["Tu próxima salida con amigos", "tiene nueva dirección:"]
REMATE = "Rabbit."
CTA = ["Compartile esta historia a esa persona", "con la que vendrías"]
ZOOM = 1.17      # se acerca la foto para dejar afuera los cubiertos y la lata de la derecha
Y0 = 280         # desde qué altura (en la foto ya acercada) empieza el recorte
MEZCLA_IA = 0.75  # peso de la ampliación con IA frente a la Lanczos (evita textura plástica)


# ----------------------------------------------------------------- mejora de la foto
def esrgan_sesion(modelo):
    return ort.InferenceSession(modelo, providers=["CPUExecutionProvider"])


def esrgan(img, modelo, tile=256, solape=16):
    """Amplía x4 con Real-ESRGAN (carga el modelo en cada llamada)."""
    return esrgan_con(esrgan_sesion(modelo), img, tile, solape)


def esrgan_con(ses, img, tile=256, solape=16):
    """Amplía x4 con Real-ESRGAN por bloques (para no usar demasiada memoria)."""
    nombre = ses.get_inputs()[0].name
    a = np.asarray(img.convert("RGB"), np.float32) / 255
    h, w, _ = a.shape
    out = np.zeros((h * 4, w * 4, 3), np.float32)
    for y in range(0, h, tile):
        for x in range(0, w, tile):
            y0, x0 = max(0, y - solape), max(0, x - solape)
            y1, x1 = min(h, y + tile + solape), min(w, x + tile + solape)
            bloque = a[y0:y1, x0:x1].transpose(2, 0, 1)[None]
            r = ses.run(None, {nombre: bloque})[0][0].transpose(1, 2, 0)
            yy, xx = (y - y0) * 4, (x - x0) * 4
            hh, ww = min(tile, h - y) * 4, min(tile, w - x) * 4
            out[y * 4:y * 4 + hh, x * 4:x * 4 + ww] = r[yy:yy + hh, xx:xx + ww]
    return Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8))


def curva_s(img, fuerza=0.10):
    """Contraste suave en S (no quema altas luces ni empasta sombras)."""
    x = np.arange(256, dtype=np.float32) / 255
    y = np.clip(x + fuerza * (x - 0.5) * (1 - np.abs(2 * x - 1)) * 2, 0, 1)
    lut = (y * 255 + 0.5).astype(np.uint8).tolist()
    return img.point(lut * 3)


def calidez(img, k=0.04):
    a = np.asarray(img, np.float32)
    a[..., 0] *= 1 + k
    a[..., 2] *= 1 - k * 0.8
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def mejorar(foto, modelo):
    ancho = W
    alto = round(foto.height * ancho / foto.width)
    ia = esrgan(foto, modelo).resize((ancho, alto), Image.LANCZOS)
    clasica = foto.resize((ancho, alto), Image.LANCZOS)
    img = Image.blend(clasica, ia, MEZCLA_IA)
    img = curva_s(img, 0.10)
    img = ImageEnhance.Color(img).enhance(1.08)
    img = calidez(img, 0.035)
    # nitidez local (claridad) + un toque de enfoque fino
    img = img.filter(ImageFilter.UnsharpMask(radius=18, percent=22, threshold=2))
    img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=3))
    return img


# ----------------------------------------------------------------- composición
def texto_centrado(img, y, texto, fuente, color, sombra_alfa=190):
    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(capa).text((W / 2, y), texto, font=fuente, fill=color, anchor="mm")
    img.alpha_composite(sombra(capa, 10, sombra_alfa, (0, 4)).crop(
        (30, 30, 30 + W, 30 + H)))


def main():
    foto_p, modelo, emblema_p, fuentes, salida = sys.argv[1:6]
    f = F(fuentes)
    foto = mejorar(Image.open(foto_p).convert("RGB"), modelo)
    foto = foto.resize((round(foto.width * ZOOM), round(foto.height * ZOOM)), Image.LANCZOS)
    base = foto.crop((0, Y0, W, Y0 + H)).convert("RGBA")   # anclada a la izquierda
    base.save(salida.rsplit(".", 1)[0] + "_foto.png")   # foto sola, mejorada
    img = base.copy()
    degradado(img, 0, 660, 228, arriba=True)   # más oscuro arriba para el texto

    fl = f("Bold", 54)
    texto_centrado(img, 285, LINEAS[0], fl, (255, 255, 255))
    texto_centrado(img, 348, LINEAS[1], fl, (255, 255, 255))
    # logo chico pegado a "Rabbit."
    fr = f("ExtraBold", 84)
    ins = insignia(Image.open(emblema_p), 78)
    ancho = ins.width + 18 + fr.getlength(REMATE)
    x0 = W / 2 - ancho / 2
    img.alpha_composite(sombra(ins, 8, 170, (0, 4)), (int(x0) - 24, 430 - ins.height // 2 - 24))
    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(capa).text((x0 + ins.width + 18, 430), REMATE, font=fr, fill=ROJO + (255,),
                              anchor="lm")
    img.alpha_composite(sombra(capa, 10, 190, (0, 4)).crop((30, 30, 30 + W, 30 + H)))
    fc = f("SemiBold", 33)
    texto_centrado(img, 503, CTA[0], fc, (255, 255, 255), 245)
    texto_centrado(img, 544, CTA[1], fc, (255, 255, 255), 245)
    img.convert("RGB").save(salida)


if __name__ == "__main__":
    main()
