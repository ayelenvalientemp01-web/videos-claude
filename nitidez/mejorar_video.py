"""Mejora la nitidez de un video con Real-ESRGAN (realesr-general-x4v3, ONNX en CPU).

Uso: python3 mejorar_video.py <entrada> <modelo.onnx> <salida.mp4> [ancho=1920] [mezcla_ia=0.75]

Cada cuadro se amplía x4 con la IA, se reduce al tamaño final y se mezcla con una
ampliación Lanczos (mezcla_ia = peso de la IA) para que las caras no queden "plásticas".
El audio original se conserva.
"""
import json
import subprocess
import sys
import time

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageFilter


def info(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0",
                                   "-show_entries", "stream=width,height,avg_frame_rate",
                                   "-of", "json", path])
    s = json.loads(out)["streams"][0]
    return s["width"], s["height"], s["avg_frame_rate"]


def main():
    entrada, modelo, salida = sys.argv[1:4]
    ancho = int(sys.argv[4]) if len(sys.argv) > 4 else 1920
    peso_ia = float(sys.argv[5]) if len(sys.argv) > 5 else 0.75
    w, h, fps = info(entrada)
    alto = round(h * ancho / w / 2) * 2

    opciones = ort.SessionOptions()
    opciones.intra_op_num_threads = 4
    sesion = ort.InferenceSession(modelo, opciones, providers=["CPUExecutionProvider"])

    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", entrada, "-fps_mode", "passthrough",
                            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{ancho}x{alto}", "-r", fps, "-i", "-", "-i", entrada,
         "-map", "0:v:0", "-map", "1:a:0?", "-c:v", "libx264", "-preset", "slow", "-crf", "17",
         "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709",
         "-color_trc", "bt709", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
         "-shortest", salida], stdin=subprocess.PIPE)

    n, t0 = 0, time.time()
    while True:
        buf = dec.stdout.read(w * h * 3)
        if len(buf) < w * h * 3:
            break
        cuadro = np.frombuffer(buf, np.uint8).reshape(h, w, 3)
        x = np.ascontiguousarray(cuadro.transpose(2, 0, 1)[None].astype(np.float32) / 255)
        y = sesion.run(None, {"entrada": x})[0][0].transpose(1, 2, 0)
        ia = Image.fromarray((np.clip(y, 0, 1) * 255 + 0.5).astype(np.uint8))
        ia = ia.resize((ancho, alto), Image.LANCZOS)
        clasico = Image.fromarray(cuadro).resize((ancho, alto), Image.LANCZOS)
        mezcla = Image.blend(clasico, ia, peso_ia)
        mezcla = mezcla.filter(ImageFilter.UnsharpMask(radius=1.2, percent=35, threshold=2))
        enc.stdin.write(mezcla.tobytes())
        n += 1
        if n % 25 == 0:
            v = (time.time() - t0) / n
            print(f"cuadro {n} ({v:.1f} s/cuadro)", flush=True)
    enc.stdin.close()
    enc.wait()
    dec.wait()
    print(f"Listo: {n} cuadros -> {salida}")


if __name__ == "__main__":
    main()
