"""Música original para el video de la gran apertura de Rabbit (120 BPM, 20 s, sin derechos
de terceros). Sigue la estructura del video: golpes en la cuenta regresiva 3-2-1, ritmo
tenso, silencio con subida (riser), impacto en el logo, drop y cierre.

Uso: python3 musica_inauguracion.py <salida.wav>
"""
import sys
import wave

import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000
DUR = 20.0
BEAT = 0.5           # 120 BPM
N = int(DUR * SR)
rng = np.random.default_rng(7)


def t_(d):
    return np.arange(int(d * SR)) / SR


def filtro(x, tipo, f):
    return sosfilt(butter(2, f, btype=tipo, fs=SR, output="sos"), x)


def poner(pista, x, t, g=1.0):
    i = int(t * SR)
    if i >= len(pista):
        return
    n = min(len(x), len(pista) - i)
    pista[i:i + n] += x[:n] * g


# ----------------------------------------------------------------- instrumentos
def kick(d=0.45):
    t = t_(d)
    f = 45 + 110 * np.exp(-t * 28)
    fase = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(fase) * np.exp(-t * 7)
    x[:200] += rng.normal(0, 0.5, 200) * np.linspace(1, 0, 200)
    return np.tanh(x * 1.6)


def boom(d=2.2):
    """Impacto grave cinematográfico con cola."""
    t = t_(d)
    f = 32 + 70 * np.exp(-t * 9)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.2)
    ruido = filtro(rng.normal(0, 1, len(t)), "lowpass", 900) * np.exp(-t * 5) * 0.6
    golpe = filtro(rng.normal(0, 1, len(t)), "highpass", 2000) * np.exp(-t * 35) * 0.5
    return np.tanh((x + ruido + golpe) * 1.4)


def clap(d=0.25):
    t = t_(d)
    env = np.zeros_like(t)
    for k in (0, 0.012, 0.024):
        env += np.where(t >= k, np.exp(-(t - k) * 60), 0)
    env += np.exp(-t * 18) * 0.5
    return filtro(rng.normal(0, 1, len(t)), "bandpass", [900, 3500]) * env * 0.8


def hat(d=0.05, abierto=False):
    t = t_(0.18 if abierto else d)
    return filtro(rng.normal(0, 1, len(t)), "highpass", 7000) * np.exp(-t * (18 if abierto else 90))


def tick():
    t = t_(0.04)
    return np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 120) * 0.6


def bajo(nota_hz, d):
    t = t_(d)
    x = np.sin(2 * np.pi * nota_hz * t) + 0.35 * np.sin(2 * np.pi * nota_hz * 2 * t)
    env = np.minimum(1, t / 0.01) * np.exp(-t * 1.2)
    return np.tanh(x * env * 1.8) * 0.8


def pad(frecs, d):
    t = t_(d)
    x = np.zeros_like(t)
    for f in frecs:
        for det in (-0.08, 0.0, 0.08):
            ff = f * 2 ** (det / 12)
            x += 2 * ((t * ff) % 1) - 1          # sierra
    env = np.minimum(1, t / 0.6) * np.minimum(1, (d - t) / 0.6)
    return filtro(x, "lowpass", 1400) * env / (len(frecs) * 3)


def riser(d):
    t = t_(d)
    k = t / d
    sweep = np.sin(2 * np.pi * np.cumsum(180 + 1800 * k ** 2) / SR) * 0.25
    ruido = filtro(rng.normal(0, 1, len(t)), "highpass", 1500) * 0.5
    return (sweep + ruido) * k ** 2.2


def whoosh(d=0.6):
    t = t_(d)
    env = np.sin(np.pi * t / d) ** 2
    return filtro(rng.normal(0, 1, len(t)), "bandpass", [400, 4000]) * env * 0.6


# ----------------------------------------------------------------- arreglo
def main():
    salida = sys.argv[1]
    bat = np.zeros(N)
    mel = np.zeros(N)
    fx = np.zeros(N)

    # 0-1.5: cuenta regresiva (3 golpes) con tic-tac
    for k in range(3):
        poner(fx, boom(1.0), k * BEAT, 0.9)
    for k in range(12):
        poner(fx, tick(), k * 0.125, 0.5 if k % 4 else 0.0)
    poner(fx, whoosh(0.5), 1.5, 0.7)                  # flash

    # 2.0-9.0: ritmo tenso
    acordes = [(55.0, [220.0, 261.6, 329.6]), (43.65, [174.6, 220.0, 261.6]),
               (65.4, [261.6, 329.6, 392.0]), (49.0, [196.0, 246.9, 293.7])]   # Am F C G
    def groove(ini, fin, lleno=True):
        nb = int(round((fin - ini) / BEAT))
        for b in range(nb):
            t = ini + b * BEAT
            poner(bat, kick(), t, 0.95)
            if lleno and b % 2 == 1:
                poner(bat, clap(), t, 0.7)
            poner(bat, hat(), t + BEAT / 2, 0.35)
            if lleno:
                poner(bat, hat(), t + BEAT / 4, 0.18)
                poner(bat, hat(), t + 3 * BEAT / 4, 0.18)
        for c in range(int(np.ceil(nb / 4))):
            t = ini + c * 4 * BEAT
            d = min(4 * BEAT, fin - t)
            raiz, notas = acordes[c % 4]
            poner(mel, bajo(raiz, d), t, 0.9)
            poner(mel, pad(notas, d), t, 0.55)
    groove(2.0, 5.5, lleno=False)
    groove(5.5, 9.0, lleno=True)

    # 9.0-10.5: silencio de suspenso con subida
    poner(fx, riser(1.5), 9.0, 0.9)
    poner(fx, pad([110.0, 164.8], 1.5), 9.0, 0.5)

    # 10.5: impacto en el logo
    poner(fx, boom(2.6), 10.5, 1.1)

    # 11.5-17.0: drop
    groove(11.5, 17.0, lleno=True)
    for t in (12.5, 13.5, 14.5, 15.5, 16.25):
        poner(fx, whoosh(0.45), t - 0.3, 0.45)

    # 17.0-20.0: cierre
    poner(fx, boom(3.0), 17.0, 1.0)
    poner(mel, pad([220.0, 261.6, 329.6, 440.0], 3.0), 17.0, 0.7)
    poner(mel, bajo(55.0, 3.0), 17.0, 0.8)

    mix = bat * 0.85 + mel * 0.75 + fx * 0.9
    t = np.arange(N) / SR
    mix *= np.clip((DUR - t) / 1.2, 0, 1)                 # fade final
    mix = np.tanh(mix * 1.1)
    mix /= np.max(np.abs(mix)) + 1e-9
    est = np.stack([mix, np.roll(mix, int(0.012 * SR)) * 0.92 + mix * 0.08], axis=1)
    with wave.open(salida, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((est * 0.9 * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    main()
