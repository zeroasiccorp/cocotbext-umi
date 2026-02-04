import math
import random


def random_toggle_generator(on_range=(0, 15), off_range=(0, 15)):
    return bit_toggler_generator(
        gen_on=(random.randint(*on_range) for _ in iter(int, 1)),
        gen_off=(random.randint(*off_range) for _ in iter(int, 1))
    )


def sine_wave_generator(amplitude, w, offset=0):
    while True:
        for idx in (i / float(w) for i in range(int(w))):
            yield amplitude * math.sin(2 * math.pi * idx) + offset


def bit_toggler_generator(gen_on, gen_off):
    for n_on, n_off in zip(gen_on, gen_off):
        yield int(abs(n_on)), int(abs(n_off))


def wave_generator(on_ampl=30, on_freq=200, off_ampl=10, off_freq=100):
    return bit_toggler_generator(sine_wave_generator(on_ampl, on_freq),
                                 sine_wave_generator(off_ampl, off_freq))
