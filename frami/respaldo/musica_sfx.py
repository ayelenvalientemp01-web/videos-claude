"""Música original y efectos de sonido generados por código (sin derechos de terceros).

Uso: python3 musica_sfx.py <salida_dir> <duracion_s>
Genera musica.wav (estéreo, 48 kHz) y las muestras whoosh.wav, pop.wav, click.wav.
"""
import sys
import wave

import numpy as np

SR = 48000
BPM = 92
rng = np.random.default_rng(3)


def nota(n):
    """Frecuencia de una nota MIDI."""
    return 440.0 * 2 ** ((n - 69) / 12)


def guardar(path, x):
    x = np.atleast_2d(x.T).T if x.ndim == 1 else x
    x = np.clip(x, -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(x.shape[1] if x.ndim == 2 else 1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def pasabajos(x, fc):
    """Filtro pasabajos suave por FFT (sin scipy)."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X / np.sqrt(1 + (f / fc) ** 4), len(x))


def pasabanda(x, lo, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    g = 1 / np.sqrt(1 + (f / hi) ** 4) * (1 - 1 / np.sqrt(1 + (f / lo) ** 4))
    return np.fft.irfft(X * g, len(x))


# ---------------------------------------------------------------- música
# Progresión cálida en Do: Cmaj9 - Am9 - Fmaj9 - G6, un acorde por compás.
ACORDES = [
    (48, [60, 64, 67, 71, 74]),
    (45, [57, 60, 64, 67, 71]),
    (41, [57, 60, 64, 65, 69]),
    (43, [59, 62, 64, 67, 71]),
]


def pad(freqs, dur):
    t = np.arange(int(dur * SR)) / SR
    y = np.zeros_like(t)
    for f in freqs:
        for det in (-0.12, 0.12):  # leve desafinación para un sonido "ancho"
            ff = f * 2 ** (det / 12)
            y += np.sin(2 * np.pi * ff * t) + 0.25 * np.sin(4 * np.pi * ff * t + 0.3)
    env = np.minimum(1, t / 0.6) * np.minimum(1, (dur - t) / 0.5)
    return y * env / (len(freqs) * 2)


def pluck(f, dur=0.6):
    t = np.arange(int(dur * SR)) / SR
    y = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t)
         + 0.1 * np.sin(6 * np.pi * f * t))
    return y * np.exp(-t * 6) * np.minimum(1, t / 0.004)


def bombo():
    t = np.arange(int(0.35 * SR)) / SR
    f = 50 + 70 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)


def hihat():
    t = np.arange(int(0.06 * SR)) / SR
    return pasabanda(rng.standard_normal(len(t)), 6000, 14000) * np.exp(-t * 70)


def rim():
    t = np.arange(int(0.12 * SR)) / SR
    return pasabanda(rng.standard_normal(len(t)), 900, 3500) * np.exp(-t * 45)


def musica(dur):
    n = int(dur * SR)
    L, R = np.zeros(n + SR * 3), np.zeros(n + SR * 3)
    beat = 60 / BPM
    compas = 4 * beat
    k = bombo(), hihat(), rim()

    def poner(canal, x, t, g=1.0):
        i = int(t * SR)
        canal[i:i + len(x)] += x * g

    b = 0
    while b * compas < dur:
        raiz, acorde = ACORDES[b % 4]
        t0 = b * compas
        p = pad([nota(m) for m in acorde], compas + 0.4)
        poner(L, p, t0, 0.28)
        poner(R, p, t0, 0.28)
        # bajo
        for beat_i in (0, 2.5):
            bj = pluck(nota(raiz), 0.9) * 0.9
            poner(L, bj, t0 + beat_i * beat, 0.45)
            poner(R, bj, t0 + beat_i * beat, 0.45)
        # arpegio en corcheas, alternando paneo
        patron = [0, 2, 4, 3, 1, 2, 4, 2]
        for i, idx in enumerate(patron):
            pl = pluck(nota(acorde[idx] + 12), 0.5)
            pan = 0.35 if i % 2 else 0.65
            poner(L, pl, t0 + i * beat / 2, 0.16 * (1 - pan) * 2)
            poner(R, pl, t0 + i * beat / 2, 0.16 * pan * 2)
        # batería suave (entra después del primer compás)
        if b >= 1:
            for i in range(4):
                if i in (0, 2):
                    poner(L, k[0], t0 + i * beat, 0.55)
                    poner(R, k[0], t0 + i * beat, 0.55)
                else:
                    poner(L, k[2], t0 + i * beat, 0.10)
                    poner(R, k[2], t0 + i * beat, 0.12)
            for i in range(8):
                g = 0.05 if i % 2 else 0.035
                poner(L, k[1], t0 + i * beat / 2, g * 0.8)
                poner(R, k[1], t0 + i * beat / 2, g)
        b += 1

    y = np.stack([L[:n], R[:n]], axis=1)
    y[:, 0] = pasabajos(y[:, 0], 7000)
    y[:, 1] = pasabajos(y[:, 1], 7000)
    t = np.arange(n) / SR
    env = np.minimum(1, t / 0.8) * np.minimum(1, (dur - t) / 1.5)
    y *= env[:, None]
    return 0.8 * y / np.abs(y).max()


# ---------------------------------------------------------------- efectos
def whoosh(dur=0.45):
    """Ruido filtrado cuyo brillo sube y baja (barrido)."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    ruido = rng.standard_normal(n)
    bandas = [(300, 900), (600, 2000), (1200, 4000), (2500, 7000)]
    capas = [pasabanda(ruido, lo, hi) for lo, hi in bandas]
    pos = np.sin(np.pi * t / dur) * (len(bandas) - 1)
    y = np.zeros(n)
    for i, c in enumerate(capas):
        y += c * np.clip(1 - np.abs(pos - i), 0, 1)
    env = np.sin(np.pi * t / dur) ** 2
    y *= env
    return 0.8 * y / np.abs(y).max()


def pop():
    t = np.arange(int(0.09 * SR)) / SR
    f = 260 + 520 * np.exp(-t * 45)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 38) * np.minimum(1, t / 0.002)
    return 0.8 * y / np.abs(y).max()


def click():
    t = np.arange(int(0.03 * SR)) / SR
    y = pasabanda(rng.standard_normal(len(t)), 2500, 9000) * np.exp(-t * 220)
    y += 0.5 * np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 160)
    return 0.8 * y / np.abs(y).max()


if __name__ == "__main__":
    out, dur = sys.argv[1], float(sys.argv[2])
    guardar(f"{out}/musica.wav", musica(dur))
    guardar(f"{out}/whoosh.wav", whoosh())
    guardar(f"{out}/pop.wav", pop())
    guardar(f"{out}/click.wav", click())
    print("ok")
