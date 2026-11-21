"""Paso 1 de la Zona Kids: estabiliza y mejora cada cuadro con IA, sin textos.

Uso: python3 base_mejorada.py <video> <x4v3.onnx> <salida.mp4>
La salida (1080x1920, 30 fps, casi sin pérdida) es la base de editar_kids_pro.py, así los
cambios de diseño no obligan a repetir la mejora con IA (que tarda ~4 s por cuadro).
"""
import os
import subprocess
import sys
import tempfile

from editar_kids import FPS, H, W, esrgan_sesion, estabilizar, leer_cuadros, mejorar


def main():
    video, modelo, salida = sys.argv[1:4]
    ses = esrgan_sesion(modelo)
    with tempfile.TemporaryDirectory() as tmp:
        estable = os.path.join(tmp, "estable.mp4")
        estabilizar(video, estable, tmp)
        enc = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow",
             "-crf", "10", "-pix_fmt", "yuv420p", salida], stdin=subprocess.PIPE)
        for i, cuadro in enumerate(leer_cuadros(estable, hasta=12.4)):
            enc.stdin.write(mejorar(cuadro, ses).tobytes())
            if i % 30 == 0:
                print(f"cuadro {i}", flush=True)
        enc.stdin.close()
        enc.wait()
    print("Listo")


if __name__ == "__main__":
    main()
