"""Transcripción palabra por palabra del audio recortado (faster-whisper, modelo medium).

Uso: python3 transcribir.py <dir_trabajo>
Lee recortado.wav y escribe words_cut.json ({"recortado": [{w, s, e}, ...]}).
El texto revisado (con correcciones) está en editar_reel.py -> TEXTO.
"""
import json
import subprocess
import sys

import numpy as np
from faster_whisper import WhisperModel

PISTA = "Seguro de vida con adicional de enfermedades graves. Comentá la palabra respaldo."


def main():
    dt = sys.argv[1]
    pcm = subprocess.check_output(["ffmpeg", "-v", "error", "-i", f"{dt}/recortado.wav",
                                   "-ac", "1", "-ar", "16000", "-f", "s16le", "-"])
    audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
    modelo = WhisperModel("medium", device="cpu", compute_type="int8")
    segs, _ = modelo.transcribe(audio, language="es", word_timestamps=True,
                                initial_prompt=PISTA)
    words = [dict(w=w.word, s=round(w.start, 3), e=round(w.end, 3))
             for s in segs for w in s.words]
    json.dump({"recortado": words}, open(f"{dt}/words_cut.json", "w"), ensure_ascii=False,
              indent=0)
    print(len(words), "palabras")
    print(" ".join(w["w"].strip() for w in words))


if __name__ == "__main__":
    main()
