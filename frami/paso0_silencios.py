"""Paso 0: elimina silencios > 0.4 s dejando un respiro de ~0.13 s.

Uso: python3 paso0_silencios.py <dir_clips_sdr> <salida_dir>
Genera segmentos.json, recortado.mp4 y recortado.wav.
"""
import json
import re
import subprocess
import sys

# Orden narrativo. IMG_3974 + IMG_3976 son una toma anterior del mismo
# texto que IMG_3980 (repetición), por eso se descartan.
CLIPS = ["3967", "3972", "3980", "3982", "3987"]
UMBRAL_DB = -38
PAUSA_MIN = 0.4
COLA = 0.06       # se deja después de la última palabra
ANTES = 0.07      # se deja antes de la siguiente palabra -> respiro ~0.13 s
PAD_INI, PAD_FIN = 0.08, 0.12
SEG_MIN = 0.25    # descarta ruidos sueltos (golpes, chasquidos)
FADE = 0.008
FPS = 30      # fundido de audio en cada corte (8 ms)


def duracion(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "csv=p=0", path], text=True)
    return float(out)


def silencios(path, minimo=0.2):
    log = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-vn", "-af",
                          f"silencedetect=noise={UMBRAL_DB}dB:d={minimo}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    ini = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
    fin = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
    return list(zip(ini, fin + [None] * (len(ini) - len(fin))))


def segmentos_de(path):
    dur = duracion(path)
    a, b = 0.0, dur
    cortes = []
    for s, e in silencios(path):
        if s <= 0.05:
            a = max(0.0, e - PAD_INI)
        elif e is None or e >= dur - 0.05:
            b = min(dur, s + PAD_FIN)
        elif e - s > PAUSA_MIN:
            cortes.append((s + COLA, e - ANTES))
    segs, t = [], a
    for s, e in cortes:
        segs.append((t, s))
        t = e
    segs.append((t, b))
    return dur, [(round(x * FPS) / FPS, round(y * FPS) / FPS) for x, y in segs if y - x > SEG_MIN]


def main():
    src, out = sys.argv[1], sys.argv[2]
    lista, original = [], 0.0
    for c in CLIPS:
        dur, segs = segmentos_de(f"{src}/{c}.mov")
        original += dur
        lista += [dict(clip=c, ini=s, fin=e) for s, e in segs]
    final = sum(x["fin"] - x["ini"] for x in lista)
    json.dump(lista, open(f"{out}/segmentos.json", "w"), indent=1)

    clips = list(dict.fromkeys(x["clip"] for x in lista))
    entradas = [a for c in clips for a in ("-i", f"{src}/{c}.mov")]
    filtros = []
    for i, x in enumerate(lista):
        k = clips.index(x["clip"])
        d = x["fin"] - x["ini"]
        rango = f"start={x['ini']:.6f}:end={x['fin']:.6f}"
        filtros.append(f"[{k}:v]trim={rango},setpts=PTS-STARTPTS[v{i}];"
                       f"[{k}:a]atrim={rango},asetpts=PTS-STARTPTS,afade=in:d={FADE},"
                       f"afade=out:st={d - FADE:.4f}:d={FADE}[a{i}]")
    concat = "".join(f"[v{i}][a{i}]" for i in range(len(lista)))
    fc = ";".join(filtros) + f";{concat}concat=n={len(lista)}:v=1:a=1[v][a]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *entradas, "-filter_complex", fc,
                    "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "16",
                    "-preset", "veryfast", "-c:a", "pcm_s16le", f"{out}/recortado.mov"], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{out}/recortado.mov", "-ac", "1",
                    "-ar", "16000", f"{out}/recortado.wav"], check=True)

    print(f"Segmentos: {len(lista)}")
    print(f"Duración clips usados: {original:.2f} s")
    print(f"Eliminado: {original - final:.2f} s")
    print(f"Duración final: {final:.2f} s")


if __name__ == "__main__":
    main()
