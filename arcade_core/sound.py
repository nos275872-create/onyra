"""
Generador de efectos de sonido 8-bit retro sintetizados en memoria.
Reproduce mediante aplay en segundo plano sin bloquear el juego ni la CPU.
Si aplay falla o el audio está ocupado, cae suavemente sin molestar.
"""

import io
import math
import os
import struct
import subprocess
import threading
import wave

SAMPLE_RATE = 22050
_SOUND_CACHE = {}
_ENABLED = True


def _generate_wav(samples):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        raw = struct.pack("<" + "h" * len(samples), *samples)
        wf.writeframes(raw)
    return buf.getvalue()


def _synth_square(freq, duration, volume=0.5):
    """Genera onda cuadrada clásica de los chips arcade (NES / Atari / AY-3-8910)."""
    n_samples = int(SAMPLE_RATE * duration)
    samples = []
    period = SAMPLE_RATE / max(freq, 1)
    amp = int(32767 * volume)
    for i in range(n_samples):
        # Onda cuadrada
        val = amp if (i % period) < (period / 2) else -amp
        # Envolvente lineal simple para evitar 'clicks'
        fade = 1.0 - (i / n_samples)
        samples.append(int(val * fade))
    return samples


def _synth_noise(duration, volume=0.4):
    """Genera ruido blanco (explosiones / disparos)."""
    import random
    n_samples = int(SAMPLE_RATE * duration)
    amp = int(32767 * volume)
    samples = []
    for i in range(n_samples):
        fade = 1.0 - (i / n_samples)
        samples.append(int(random.uniform(-amp, amp) * fade))
    return samples


def _synth_slide(f_start, f_end, duration, volume=0.5):
    """Frecuencia deslizante (láseres, saltos, bonus)."""
    n_samples = int(SAMPLE_RATE * duration)
    samples = []
    amp = int(32767 * volume)
    phase = 0.0
    for i in range(n_samples):
        t = i / n_samples
        f = f_start + (f_end - f_start) * t
        phase += 2.0 * math.pi * f / SAMPLE_RATE
        val = amp if (phase % (2 * math.pi)) < math.pi else -amp
        fade = 1.0 - t
        samples.append(int(val * fade))
    return samples


def init_sounds():
    global _SOUND_CACHE
    try:
        # 1. Moneda (Insert Coin / Level up) - Dos tonos armónicos
        coin_samples = _synth_square(987, 0.08, 0.4) + _synth_square(1318, 0.28, 0.45)
        _SOUND_CACHE["coin"] = _generate_wav(coin_samples)

        # 2. Láser (Disparo Space Invaders)
        _SOUND_CACHE["laser"] = _generate_wav(_synth_slide(950, 200, 0.11, 0.35))

        # 3. Explosión (Alienígena / Nave destruida)
        _SOUND_CACHE["explosion"] = _generate_wav(_synth_noise(0.22, 0.5))

        # 4. Golpe / Rebote (Pong / Breakout / Tetris block drop)
        _SOUND_CACHE["hit"] = _generate_wav(_synth_square(240, 0.05, 0.4))

        # 5. Punto / Dot (Pac-Man chomp / comida Snake)
        _SOUND_CACHE["chomp"] = _generate_wav(_synth_square(420, 0.04, 0.35))

        # 6. Salto / Bonus (Tetris línea borrada)
        _SOUND_CACHE["bonus"] = _generate_wav(_synth_slide(440, 880, 0.15, 0.4))

        # 7. Game Over (Escala descendente melancólica)
        go = (
            _synth_square(370, 0.12, 0.4)
            + _synth_square(330, 0.12, 0.4)
            + _synth_square(293, 0.15, 0.4)
            + _synth_square(220, 0.35, 0.45)
        )
        _SOUND_CACHE["gameover"] = _generate_wav(go)

        # 8. Alien March (Paso de los marcianos)
        _SOUND_CACHE["alien_step"] = _generate_wav(_synth_square(120, 0.06, 0.4))

    except Exception:
        pass


def play(name):
    """Reproduce un sonido de forma totalmente asíncrona sin frenar el juego."""
    if not _ENABLED:
        return
    data = _SOUND_CACHE.get(name)
    if not data:
        return

    def _worker():
        try:
            subprocess.run(
                ["aplay", "-q", "-t", "wav"],
                input=data,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=0.6,
            )
        except Exception:
            pass

    threading.Thread(target=_worker, daemon=True).start()


# Inicializar una única vez al importar
init_sounds()
