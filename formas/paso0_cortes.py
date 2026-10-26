"""Paso 0 (FORMAS): corta silencios en las partes con voz y acelera el recorrido de
máquinas sin voz.

Uso: python3 paso0_cortes.py <dir_clips_sdr> <salida_dir>
Genera segmentos.json, recortado.mov y recortado.wav.
"""
import json
import re
import subprocess
import sys

FPS = 30
# (clip, inicio, fin, velocidad). velocidad 1 = parte con voz (se cortan los silencios);
# > 1 = recorrido de máquinas sin voz, acelerado.
PLAN = [
    ("clipA", 0.0, 26.6, 1),
    ("clipA", 26.6, 35.0, 5),
    ("clipB", 0.0, 14.2, 5),
    ("clipB", 14.2, 35.45, 1),
]
UMBRAL_DB = -38
PAUSA_MIN = 0.4
COLA, ANTES = 0.06, 0.07   # respiro de ~0.13 s entre frases
PAD_INI, PAD_FIN = 0.08, 0.15
SEG_MIN = 0.25
FADE = 0.008


def silencios(path, a, b):
    log = subprocess.run(["ffmpeg", "-hide_banner", "-ss", str(a), "-to", str(b), "-i", path,
                          "-vn", "-af", f"silencedetect=noise={UMBRAL_DB}dB:d=0.2",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    ini = [float(x) + a for x in re.findall(r"silence_start: ([\d.]+)", log)]
    fin = [float(x) + a for x in re.findall(r"silence_end: ([\d.]+)", log)]
    return list(zip(ini, fin + [None] * (len(ini) - len(fin))))


def tramos_con_voz(path, a, b):
    ini, fin, cortes = a, b, []
    for s, e in silencios(path, a, b):
        if s <= a + 0.05:
            ini = max(a, e - PAD_INI)
        elif e is None or e >= b - 0.05:
            fin = min(b, s + PAD_FIN)
        elif e - s > PAUSA_MIN:
            cortes.append((s + COLA, e - ANTES))
    out, t = [], ini
    for s, e in cortes:
        out.append((t, s))
        t = e
    out.append((t, fin))
    return [(round(x * FPS) / FPS, round(y * FPS) / FPS) for x, y in out if y - x > SEG_MIN]


def main():
    src, out = sys.argv[1], sys.argv[2]
    lista = []
    for clip, a, b, vel in PLAN:
        if vel == 1:
            lista += [dict(clip=clip, ini=x, fin=y, vel=1) for x, y in
                      tramos_con_voz(f"{src}/{clip}.mov", a, b)]
        else:
            lista.append(dict(clip=clip, ini=a, fin=b, vel=vel))
    json.dump(lista, open(f"{out}/segmentos.json", "w"), indent=1)

    clips = list(dict.fromkeys(x["clip"] for x in lista))
    entradas = [v for c in clips for v in ("-i", f"{src}/{c}.mov")]
    filtros = []
    for i, x in enumerate(lista):
        k = clips.index(x["clip"])
        rango = f"start={x['ini']:.6f}:end={x['fin']:.6f}"
        d = round((x["fin"] - x["ini"]) / x["vel"] * FPS) / FPS
        x["dur"] = d
        if x["vel"] == 1:
            filtros.append(f"[{k}:v]trim={rango},setpts=PTS-STARTPTS[v{i}];"
                           f"[{k}:a]atrim={rango},asetpts=PTS-STARTPTS,afade=in:d={FADE},"
                           f"afade=out:st={d - FADE:.4f}:d={FADE}[a{i}]")
        else:
            filtros.append(f"[{k}:v]trim={rango},setpts=(PTS-STARTPTS)/{x['vel']},fps={FPS},"
                           f"trim=end_frame={round(d * FPS)}[v{i}];"
                           f"aevalsrc=0:s=48000:c=stereo:d={d:.4f}[a{i}]")
    concat = "".join(f"[v{i}][a{i}]" for i in range(len(lista)))
    fc = ";".join(filtros) + f";{concat}concat=n={len(lista)}:v=1:a=1[v][a]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *entradas, "-filter_complex", fc,
                    "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "16",
                    "-preset", "veryfast", "-c:a", "pcm_s16le", "-ar", "48000",
                    f"{out}/recortado.mov"], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{out}/recortado.mov", "-ac", "1",
                    "-ar", "16000", f"{out}/recortado.wav"], check=True)
    json.dump(lista, open(f"{out}/segmentos.json", "w"), indent=1)

    voz_orig = sum(b - a for c, a, b, v in PLAN if v == 1)
    voz_final = sum(x["dur"] for x in lista if x["vel"] == 1)
    rap_orig = sum(b - a for c, a, b, v in PLAN if v > 1)
    rap_final = sum(x["dur"] for x in lista if x["vel"] > 1)
    print(f"Segmentos: {len(lista)}")
    print(f"Partes con voz: {voz_orig:.2f} s -> {voz_final:.2f} s "
          f"(silencios eliminados: {voz_orig - voz_final:.2f} s)")
    print(f"Recorrido de máquinas: {rap_orig:.2f} s -> {rap_final:.2f} s (x5)")
    print(f"Duración total sin cierre: {voz_final + rap_final:.2f} s")


if __name__ == "__main__":
    main()
