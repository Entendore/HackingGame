#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
H4CK://MAINFRAME  —  a retro coding/hacking arcade game (pygame)

Break into the mainframe over 8 levels: steal DATA packets, hack TERMINALS
to drop firewall gates, defuse FORK BOMBS, DECRYPT locked packets, dodge
patrol ICE, HUNTER ICE, laser grids and honeypots - then bail out through
the exit portal before the trace completes.

All sound is synthesized in code: 3 chiptune tracks + 15 retro SFX.
No external assets needed.

Controls
--------
  Arrows / WASD .... move
  E ................ interact: HACK terminal / DEFUSE bomb / DECRYPT packet
                     (then TYPE the shown code, ESC to jack out)
  M ................ mute / unmute
  ENTER ............ confirm / continue
  R ................ retry after game over

Requires:  pip install pygame numpy
"""

import os
import sys
import math
import random

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

try:
    import numpy as np
    HAVE_NUMPY = True
except Exception:                                    # sound will be disabled
    HAVE_NUMPY = False

# ----------------------------------------------------------------------------
# constants
# ----------------------------------------------------------------------------
TILE        = 40
COLS, ROWS  = 24, 16
W, H        = 960, 768
GRID_OX     = 0            # grid origin on screen
GRID_OY     = 88
FPS         = 60

# neon palette
BG          = (2, 10, 5)
GRID_LINE   = (6, 26, 13)
WALL_DARK   = (8, 40, 20)
WALL_LITE   = (20, 90, 45)
GREEN       = (57, 255, 20)
DIM_GREEN   = (25, 130, 60)
CYAN        = (0, 240, 255)
MAGENTA     = (255, 40, 200)
PURPLE      = (170, 60, 255)
RED         = (255, 45, 60)
AMBER       = (255, 190, 40)
GOLD        = (255, 210, 70)
WHITE       = (220, 255, 225)

SR = 22050                 # audio sample-rate (chunky + retro)


# ----------------------------------------------------------------------------
# tiny software synthesizer  ->  chiptune music & sfx (pure square/saw/noise)
# ----------------------------------------------------------------------------
def _sq(ph, duty=0.5):  return np.where(np.mod(ph, 1.0) < duty, 1.0, -1.0)
def _tri(ph):           return 2.0 * np.abs(2.0 * np.mod(ph, 1.0) - 1.0) - 1.0
def _saw(ph):           return 2.0 * np.mod(ph, 1.0) - 1.0
def _sin(ph):           return np.sin(2.0 * np.pi * ph)

_WAVES = {"square": _sq, "tri": _tri, "saw": _saw, "sin": _sin}


def _env(n, decay=10.0, attack=0.004):
    t = np.arange(n) / SR
    e = np.exp(-t * decay)
    an = max(1, int(attack * SR))
    if an < n:
        e[:an] *= np.linspace(0.0, 1.0, an)
    return e


def midi(n):
    return 440.0 * 2.0 ** ((n - 69) / 12.0)


def tone(freq, dur, wave="square", vol=0.3, duty=0.5, decay=10.0, detune=0.0):
    n = max(1, int(dur * SR))
    t = np.arange(n) / SR
    ph = freq * (1.0 + detune) * t
    w = _sq(ph, duty) if wave == "square" else _WAVES[wave](ph)
    return (w * _env(n, decay) * vol).astype(np.float64)


def sweep(f0, f1, dur, wave="square", vol=0.3, duty=0.5, decay=8.0):
    n = max(1, int(dur * SR))
    t = np.arange(n) / SR
    ph = f0 * t + (f1 - f0) * t * t / (2.0 * dur)
    w = _sq(ph, duty) if wave == "square" else _WAVES[wave](ph)
    return (w * _env(n, decay) * vol).astype(np.float64)


def noise(dur, vol=0.3, decay=14.0):
    n = max(1, int(dur * SR))
    w = np.random.uniform(-1.0, 1.0, n)
    return (w * _env(n, decay) * vol).astype(np.float64)


def kick(dur=0.12, vol=0.85):
    n = max(1, int(dur * SR))
    t = np.arange(n) / SR
    f0, f1 = 150.0, 42.0
    ph = f0 * t + (f1 - f0) * t * t / (2.0 * dur)
    return (np.sin(2 * np.pi * ph) * _env(n, 12.0) * vol).astype(np.float64)


class Track:
    """Minimal 16th-note tracker used to render a music loop."""
    def __init__(self, bpm, steps=64):
        self.step = 60.0 / bpm / 4.0
        self.buf = np.zeros(int(steps * self.step * SR) + SR // 4)

    def _drop(self, step, sig):
        i = int(step * self.step * SR)
        j = min(len(self.buf), i + len(sig))
        if j > i:
            self.buf[i:j] += sig[: j - i]

    def note(self, step, m, dur_steps=1, wave="square", vol=0.2,
             duty=0.5, decay=18.0, detune=0.0):
        self._drop(step, tone(midi(m), dur_steps * self.step * 0.98,
                              wave, vol, duty, decay, detune))

    def kick(self, step):
        self._drop(step, kick())

    def hat(self, step, vol=0.07):
        self._drop(step, noise(0.03, vol, 60.0))

    def snare(self, step, vol=0.16):
        s = noise(0.12, vol, 22.0) + tone(190, 0.12, "tri", vol * 0.5,
                                          decay=24.0)
        self._drop(step, s)


def build_neon():
    """Main theme - driving A-minor synthwave loop (levels 1-3)."""
    t = Track(150)
    bass   = [33, 29, 36, 31]                      # A1 F1 C2 G1
    chords = [[57, 60, 64], [53, 57, 60],          # Am  F
              [55, 60, 64], [55, 59, 62]]          # C   G
    arp = [0, 1, 2, 1, 0, 1, 2, 1, 0, 1, 2, 3, 2, 1, 2, 3]
    for bar in range(4):
        root = bass[bar]
        for e in range(8):                          # octave-jumping bass
            t.note(bar * 16 + e * 2, root + (12 if e % 2 else 0),
                   2, "square", 0.30, duty=0.25, decay=20.0)
        ch = chords[bar]
        for i in range(16):                         # sparkle arpeggio lead
            idx = arp[i]
            n = ch[idx % 3] + (12 if idx == 3 else 0) + 12
            t.note(bar * 16 + i, n, 1, "square", 0.10, duty=0.125, decay=28.0)
            t.note(bar * 16 + i, n, 1, "square", 0.06, duty=0.125,
                   decay=28.0, detune=0.005)
        for s in (0, 4, 8, 12):
            t.kick(bar * 16 + s)
        for s in (4, 12):
            t.snare(bar * 16 + s)
        for s in range(16):
            if s % 2 == 0:
                t.hat(bar * 16 + s, 0.05 if s % 4 else 0.08)
    return t.buf


def build_overclock():
    """Faster, darker E-minor loop (levels 4-6)."""
    t = Track(172)
    bass   = [28, 28, 36, 38]                      # E1 E1 C2 D2
    chords = [[64, 67, 71], [64, 67, 71],          # Em  Em
              [60, 64, 67], [62, 66, 69]]          # C   D
    arp = [0, 1, 2, 3, 2, 1, 0, 1, 2, 3, 2, 1, 2, 1, 0, 1]
    for bar in range(4):
        root = bass[bar]
        for s in range(16):                         # relentless 16th bass
            n = root + (12 if s in (6, 12, 14) else 0)
            t.note(bar * 16 + s, n, 1, "square", 0.22, duty=0.25, decay=26.0)
        ch = chords[bar]
        for i in range(16):
            idx = arp[i]
            n = ch[idx % 3] + (12 if idx == 3 else 0)
            t.note(bar * 16 + i, n, 1, "square", 0.09, duty=0.125, decay=30.0)
            t.note(bar * 16 + i, n, 1, "square", 0.05, duty=0.125,
                   decay=30.0, detune=0.006)
        for s in (0, 4, 8, 12):
            t.kick(bar * 16 + s)
        for s in (4, 12):
            t.snare(bar * 16 + s)
        t.snare(bar * 16 + 15, 0.08)                # little fill
        for s in range(0, 16, 2):
            t.hat(bar * 16 + s + 1, 0.06)
    return t.buf


def build_blackice():
    """Aggressive D-minor loop for the endgame (levels 7-8)."""
    t = Track(184)
    bass   = [26, 26, 34, 36]                      # D1 D1 Bb1 C2
    chords = [[62, 65, 69], [62, 65, 69],          # Dm  Dm
              [58, 62, 65], [60, 64, 67]]          # Bb  C
    arp = [0, 2, 1, 2, 0, 2, 1, 3, 0, 2, 1, 2, 3, 2, 1, 2]
    for bar in range(4):
        root = bass[bar]
        for s in range(16):                         # pounding 16th bass
            n = root + (12 if s in (4, 12) else 0)
            t.note(bar * 16 + s, n, 1, "square", 0.24, duty=0.25, decay=28.0)
        ch = chords[bar]
        for i in range(16):
            idx = arp[i]
            n = ch[idx % 3] + (12 if idx == 3 else 0)
            t.note(bar * 16 + i, n, 1, "square", 0.10, duty=0.125, decay=32.0)
            t.note(bar * 16 + i, n, 1, "square", 0.06, duty=0.125,
                   decay=32.0, detune=0.007)
        for s in (0, 4, 8, 12):
            t.kick(bar * 16 + s)
        for s in (4, 12):
            t.snare(bar * 16 + s)
        t.snare(bar * 16 + 14, 0.09)
        for s in range(16):
            if s % 2:
                t.hat(bar * 16 + s, 0.05 if bar < 3 else 0.07)
    return t.buf


class SoundEngine:
    """Generates every sound at startup; degrades silently without a mixer."""
    def __init__(self):
        self.enabled = False
        self.muted = False
        self.sfx = {}
        self.music = {}
        self._music_name = None
        if not HAVE_NUMPY:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(SR, -16, 2, 512)
            self.enabled = True
        except Exception:
            self.enabled = False
            return
        try:
            self._build_sfx()
            self.music["neon"] = self._snd(build_neon(), 0.5)
            self.music["overclock"] = self._snd(build_overclock(), 0.5)
            self.music["blackice"] = self._snd(build_blackice(), 0.5)
        except Exception:
            self.enabled = False

    # -- helpers ------------------------------------------------------
    def _snd(self, mono, vol=1.0):
        m = np.tanh(np.asarray(mono) * 0.9)
        peak = max(1e-9, float(np.max(np.abs(m))))
        m = m / peak * 0.9 * vol
        st = np.ascontiguousarray(np.column_stack([m, m]))
        return pygame.sndarray.make_sound((st * 32767).astype(np.int16))

    def _seq(self, parts):
        out = []
        gap = np.zeros(int(0.012 * SR))
        for p in parts:
            out.append(p)
            out.append(gap)
        return np.concatenate(out) if out else np.zeros(1)

    # -- sfx ----------------------------------------------------------
    def _build_sfx(self):
        self.sfx["pickup"] = self._snd(self._seq([
            tone(880, 0.05, "square", 0.25, decay=14),
            tone(1174.7, 0.05, "square", 0.25, decay=14),
            tone(1568.0, 0.07, "square", 0.25, decay=12)]))
        self.sfx["key"] = self._snd(tone(990, 0.035, "square", 0.20, decay=22))
        self.sfx["err"] = self._snd(self._seq([
            tone(150, 0.09, "saw", 0.28, decay=14),
            tone(105, 0.11, "saw", 0.28, decay=12)]))
        self.sfx["hack"] = self._snd(self._seq([
            sweep(320, 1500, 0.16, "square", 0.22, duty=0.25, decay=7),
            tone(midi(69), 0.07, "square", 0.20, decay=16),
            tone(midi(73), 0.07, "square", 0.20, decay=16),
            tone(midi(76), 0.14, "square", 0.20, decay=10)]))
        self.sfx["gate"] = self._snd(
            noise(0.35, 0.22, 9) + sweep(240, 60, 0.35, "saw", 0.20, decay=9))
        self.sfx["hurt"] = self._snd(
            sweep(300, 55, 0.35, "saw", 0.38, decay=9)
            + noise(0.35, 0.25, 16))
        self.sfx["clear"] = self._snd(self._seq([
            tone(midi(69), 0.09, "square", 0.24, duty=0.25, decay=14),
            tone(midi(72), 0.09, "square", 0.24, duty=0.25, decay=14),
            tone(midi(76), 0.09, "square", 0.24, duty=0.25, decay=14),
            tone(midi(81), 0.22, "square", 0.26, duty=0.25, decay=9)]))
        self.sfx["over"] = self._snd(self._seq([
            tone(midi(64), 0.16, "saw", 0.26, decay=10),
            tone(midi(60), 0.16, "saw", 0.26, decay=10),
            tone(midi(57), 0.16, "saw", 0.26, decay=10),
            tone(midi(52), 0.34, "saw", 0.26, decay=7)]))
        self.sfx["portal"] = self._snd(self._seq([
            tone(midi(69 + i * 2), 0.05, "tri", 0.22, decay=18)
            for i in range(8)]))
        self.sfx["beep"] = self._snd(tone(1240, 0.06, "sin", 0.22, decay=20))
        self.sfx["ui"] = self._snd(tone(520, 0.04, "square", 0.16, decay=24))
        self.sfx["start"] = self._snd(self._seq([
            tone(660, 0.06, "square", 0.22, decay=16),
            tone(1320, 0.10, "square", 0.22, decay=12)]))
        self.sfx["alert"] = self._snd(self._seq([
            tone(740, 0.055, "square", 0.22, duty=0.25, decay=18),
            tone(988, 0.075, "square", 0.22, duty=0.25, decay=16)]))
        self.sfx["explode"] = self._snd(
            noise(0.5, 0.40, 7) + sweep(220, 30, 0.5, "saw", 0.35, decay=7))
        self.sfx["keypick"] = self._snd(self._seq([
            tone(1046.5, 0.06, "square", 0.24, decay=16),
            tone(1568.0, 0.10, "square", 0.24, decay=12)]))
        self.sfx["zap"] = self._snd(
            noise(0.18, 0.30, 24) + sweep(900, 120, 0.18, "square", 0.22,
                                          duty=0.15, decay=20))

    # -- playback -----------------------------------------------------
    def play(self, name):
        if self.enabled and not self.muted and name in self.sfx:
            self.sfx[name].play()

    def play_music(self, name):
        if not self.enabled or self._music_name == name:
            return
        self._music_name = name
        for s in self.music.values():
            s.stop()
        if name in self.music:
            self.music[name].set_volume(0.0 if self.muted else 0.5)
            self.music[name].play(loops=-1, fade_ms=250)

    def toggle_mute(self):
        self.muted = not self.muted
        if self.enabled and self._music_name in self.music:
            self.music[self._music_name].set_volume(0.0 if self.muted else 0.5)


# ----------------------------------------------------------------------------
# level data
#   #  wall         .  floor       P  player spawn    D  data packet
#   E  exit portal  T  terminal    G  firewall gate   H  drone (horiz)
#   V  drone (vert) x  HUNTER ICE  z  laser grid      b  honeypot (decoy)
#   c  encrypted packet  f  fork bomb  k  keycard     q  key door
# ----------------------------------------------------------------------------
LEVELS = [
    {
        "name": "LEVEL 01 :: MAINFRAME BREACH",
        "tip": "STEAL ALL DATA, HACK THE TERMINAL, REACH THE PORTAL",
        "music": "neon", "time": 150.0, "drone_speed": 85.0,
        "map": [
            "########################",
            "#P.........#...........#",
            "#...D......#.....D.....#",
            "#..........#...........#",
            "#....###...#....###....#",
            "#....#.....#....#......#",
            "#..D.#..D..#....#...D..#",
            "#....#.....#....#......#",
            "#....#.....#....#..##..#",
            "#..#.#..........#......#",
            "#..#.....H....#..#..D..#",
            "#..#.............##G##.#",
            "#..#......H......#...#.#",
            "#..........D.....#.E.#.#",
            "#..#....T........#...#.#",
            "########################",
        ],
    },
    {
        "name": "LEVEL 02 :: FIREWALL GRID",
        "tip": "THE EXIT ROOM IS GATED - FIND THE TERMINAL",
        "music": "neon", "time": 165.0, "drone_speed": 100.0,
        "map": [
            "########################",
            "#P....#..........#.....#",
            "#.D...#....D.....#..D.E#",
            "#.....#..........#.....#",
            "#..####..######..#..#..#",
            "#..#.........#...#..#..#",
            "#..#..D..H...#...G..#..#",
            "#..######..###..########",
            "#.......#......#.......#",
            "#..D....#..T...#....D..#",
            "#..##...#......#..##...#",
            "#..##...###.####..##...#",
            "#..H..................V#",
            "#......#...D....#......#",
            "#..D...#........#..D...#",
            "########################",
        ],
    },
    {
        "name": "LEVEL 03 :: PHISHING POND",
        "tip": "HONEYPOTS POSE AS DATA - THEY FLASH RED. GRAB ONE = TRACE +12s",
        "music": "neon", "time": 160.0, "drone_speed": 95.0,
        "map": [
            "########################",
            "#P......#.........#....#",
            "#..D....#....D.....#.D.#",
            "#.....b.#.........#....#",
            "#..##...#..##....##....#",
            "#..##......##....#.....#",
            "#....D...#....b..#..H..#",
            "#........#.............#",
            "#.H......#..D....#..##.#",
            "#.....##.#.......#.....#",
            "#..b...##....D...#..b..#",
            "#.............##G##....#",
            "#..D....H......#...#...#",
            "#......b.......#.E.#...#",
            "#........T.....#...#...#",
            "########################",
        ],
    },
    {
        "name": "LEVEL 04 :: DATA STORM",
        "tip": "POCKETS HOLD BONUS DATA - WATCH THE CROSSFIRE",
        "music": "overclock", "time": 175.0, "drone_speed": 118.0,
        "map": [
            "########################",
            "#P..........#..........#",
            "#..D........#.....D....#",
            "#.....##....#....##...V#",
            "#.....##..........##...#",
            "#..........H...........#",
            "#..D.....####..####....#",
            "#........#..#..#..#..D.#",
            "#....H...#.D#..#..#....#",
            "#........#..#.D#..#....#",
            "#..##...............H..#",
            "#..##....D......##G##..#",
            "#......#........#...#..#",
            "#..D....#....T..#.E.#..#",
            "#......#........#...#..#",
            "########################",
        ],
    },
    {
        "name": "LEVEL 05 :: LASER LATTICE",
        "tip": "LASER GRIDS CYCLE ON/OFF - CROSS ON THE DARK BEAT",
        "music": "overclock", "time": 175.0, "drone_speed": 110.0,
        "laser_period": 3.0, "laser_on": 1.3,
        "map": [
            "########################",
            "#P....#......#......#..#",
            "#.D...#..D...#..D...#.E#",
            "#.....#......#......#..#",
            "#..##....z...#...##....#",
            "#..##...#....#...##....#",
            "#..z....#..H.#....z....#",
            "#.......#..............#",
            "#..D....#....#..D...z..#",
            "#.####.#####.#####.###.#",
            "#......#.......#.......#",
            "#..H...#...........D...#",
            "#......#.......#.......#",
            "#..z...#..z....#..H..z.#",
            "#....D..........#....D.#",
            "########################",
        ],
    },
    {
        "name": "LEVEL 06 :: CRYPTO VAULT",
        "tip": "DECRYPT LOCKED PACKETS WITH E - AND DEFUSE THE FORK BOMB",
        "music": "overclock", "time": 180.0, "drone_speed": 120.0,
        "bomb_time": 75.0,
        "map": [
            "########################",
            "#P......#.......#......#",
            "#..D....#...c....#..D..#",
            "#.......#.......#......#",
            "#..##...#..##....#..#..#",
            "#..##......##....#..#..#",
            "#....c...#..........#..#",
            "#........#..H....#..#..#",
            "#..#.....#.......#.....#",
            "#..#...D..#..c...#.##..#",
            "#..#.....#.......#..f..#",
            "#..##..H.....###G##....#",
            "#.......#......#...#...#",
            "#..c....#..T...#.#E.#..#",
            "#.......#......#...#...#",
            "########################",
        ],
    },
    {
        "name": "LEVEL 07 :: HUNTER'S RUN",
        "tip": "HUNTER ICE SMELLS YOU AT CLOSE RANGE - GRAB THE KEYCARD, RUN",
        "music": "blackice", "time": 180.0, "drone_speed": 125.0,
        "hunter_speed": 112.0,
        "map": [
            "########################",
            "#P......#.......#.....k#",
            "#..D....#...D...#..D...#",
            "#.......#.......#......#",
            "#..##...#..##...#..##..#",
            "#..##......##......##..#",
            "#....x...#....x...#....#",
            "#........#.......#.....#",
            "#..D.....#..D....#..D..#",
            "#....##..#.......##....#",
            "#.H..##..#...H...#..##.#",
            "#........#.......#.....#",
            "#..D..#......#....D....#",
            "#.....#......#......####",
            "#.....#..H..........q.E#",
            "########################",
        ],
    },
    {
        "name": "LEVEL 08 :: KERNEL PANIC",
        "tip": "EVERYTHING AT ONCE. OWN THE KERNEL OR GET DUMPED",
        "music": "blackice", "time": 200.0, "drone_speed": 140.0,
        "hunter_speed": 122.0, "laser_period": 2.6, "laser_on": 1.1,
        "bomb_time": 90.0,
        "map": [
            "########################",
            "#P....#.......#........#",
            "#..D..#...D...#...c..T.#",
            "#.....#.......#........#",
            "#.##..#..##...#..##....#",
            "#.##..#..##...z..##....#",
            "#.....#.......#....x...#",
            "#..c..#...H...#........#",
            "#.....#.......#..##....#",
            "#..##.#..f....#..##.D..#",
            "#..##.#.......#....z...#",
            "#......#..x........#G###",
            "#..D....#..........#...#",
            "#.......z......#...#.E.#",
            "#..H........D......#...#",
            "########################",
        ],
    },
]

HACK_WORDS = ["sudo", "nmap", "chmod", "r00t", "0day", "k3rn3l", "sh3ll",
              "inj3ct", "d3crypt", "brut3", "x0ffee", "r3boot", "pwn3d",
              "trac3", "crypt0", "fir3wall", "ov3rride", "m4inframe",
              "r00tk1t", "b4ckd00r", "privesc", "payload", "exfil",
              "sqli", "xss", "forkbomb", "icepick", "nullptr"]


# ----------------------------------------------------------------------------
# entities
# ----------------------------------------------------------------------------
class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max", "color", "size")

    def __init__(self, x, y, color, speed=90.0, life=0.5, size=3):
        a = random.uniform(0, math.tau)
        v = random.uniform(speed * 0.3, speed)
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(a) * v, math.sin(a) * v
        self.life = self.max = life
        self.color = color
        self.size = size

    def update(self, dt):
        self.life -= dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.92
        self.vy *= 0.92

    def draw(self, surf):
        if self.life <= 0:
            return
        a = self.life / self.max
        s = max(1, int(self.size * a))
        r = pygame.Rect(int(self.x) - s, int(self.y) - s, s * 2, s * 2)
        c = tuple(int(v * a) for v in self.color)
        surf.fill(c, r)


class Player:
    SIZE = 24
    SPEED = 190.0

    def __init__(self, c, r):
        self.x = c * TILE + TILE / 2
        self.y = r * TILE + TILE / 2
        self.invuln = 0.0
        self.trail = []

    @property
    def rect(self):
        return pygame.Rect(int(self.x - self.SIZE / 2),
                           int(self.y - self.SIZE / 2),
                           self.SIZE, self.SIZE)

    def move(self, dx, dy, dt, is_solid):
        # axis-separated collision against the tile grid
        nx = self.x + dx * self.SPEED * dt
        r = pygame.Rect(int(nx - self.SIZE / 2), int(self.y - self.SIZE / 2),
                        self.SIZE, self.SIZE)
        if not any(is_solid(cx, cy) for cx, cy in _tiles_of(r)):
            self.x = nx
        ny = self.y + dy * self.SPEED * dt
        r = pygame.Rect(int(self.x - self.SIZE / 2), int(ny - self.SIZE / 2),
                        self.SIZE, self.SIZE)
        if not any(is_solid(cx, cy) for cx, cy in _tiles_of(r)):
            self.y = ny

    def update(self, dt):
        self.invuln = max(0.0, self.invuln - dt)
        self.trail.append((self.x, self.y))
        if len(self.trail) > 14:
            self.trail.pop(0)

    def draw(self, surf, t):
        # fading cursor trail
        for i, (tx, ty) in enumerate(self.trail):
            a = i / len(self.trail)
            s = int(3 + 8 * a)
            pygame.draw.rect(surf, (0, int(70 * a), int(30 * a)),
                             (GRID_OX + tx - s // 2, GRID_OY + ty - s // 2,
                              s, s))
        if self.invuln > 0 and int(t * 14) % 2 == 0:
            return                                   # i-frame blink
        x, y = GRID_OX + self.x, GRID_OY + self.y
        glow = 0.75 + 0.25 * math.sin(t * 6)
        c = tuple(int(v * glow) for v in GREEN)
        pts = [(x - 9, y - 11), (x - 9, y + 11), (x - 1, y + 4),
               (x + 3, y + 10), (x + 7, y + 7), (x + 2, y + 2),
               (x + 11, y + 2)]
        pygame.draw.polygon(surf, (4, 60, 20),
                            [(px + 2, py + 2) for px, py in pts])
        pygame.draw.polygon(surf, c, pts)
        pygame.draw.polygon(surf, WHITE, pts, 1)


class Drone:
    """Patrolling ICE - bounces along its axis, lethal on contact."""
    SIZE = 26

    def __init__(self, c, r, axis, speed):
        self.x = c * TILE + TILE / 2
        self.y = r * TILE + TILE / 2
        self.axis = axis
        self.speed = speed
        self.dir = 1
        self.spin = random.uniform(0, math.tau)
        self.chasing = False

    @property
    def rect(self):
        return pygame.Rect(int(self.x - self.SIZE / 2),
                           int(self.y - self.SIZE / 2),
                           self.SIZE, self.SIZE)

    def _try(self, dx, dy, is_solid):
        r = pygame.Rect(int(self.x + dx - self.SIZE / 2),
                        int(self.y + dy - self.SIZE / 2),
                        self.SIZE, self.SIZE)
        if any(is_solid(cx, cy) for cx, cy in _tiles_of(r)):
            return False
        self.x += dx
        self.y += dy
        return True

    def update(self, dt, is_solid, player=None):
        d = self.dir * self.speed * dt
        if not self._try(d if self.axis == "H" else 0,
                         d if self.axis == "V" else 0, is_solid):
            self.dir *= -1
        self.spin += dt * 5

    def draw(self, surf, t):
        x, y = GRID_OX + self.x, GRID_OY + self.y
        pulse = 0.7 + 0.3 * math.sin(t * 8 + self.spin)
        col = tuple(int(v * pulse) for v in RED)
        pygame.draw.circle(surf, (60, 6, 10), (int(x + 2), int(y + 2)), 13)
        pygame.draw.circle(surf, col, (int(x), int(y)), 13)
        pygame.draw.circle(surf, (90, 8, 14), (int(x), int(y)), 13, 2)
        # scanning eye
        ex = math.cos(self.spin) * 5
        ey = math.sin(self.spin) * 5
        pygame.draw.circle(surf, WHITE, (int(x + ex), int(y + ey)), 3)
        # motion ticks
        for i in range(3):
            a = self.spin + i * math.tau / 3
            tx, ty = x + math.cos(a) * 17, y + math.sin(a) * 17
            pygame.draw.circle(surf, col, (int(tx), int(ty)), 2)


class Hunter(Drone):
    """HUNTER ICE - patrols until you get close, then gives chase."""
    AGGRO = 175.0

    def __init__(self, c, r, speed, chase_speed):
        super().__init__(c, r, "H", speed)
        self.chase_speed = chase_speed
        self.was_chasing = False

    def update(self, dt, is_solid, player=None):
        self.chasing = False
        if player is not None:
            dx, dy = player.x - self.x, player.y - self.y
            if math.hypot(dx, dy) < self.AGGRO:
                self.chasing = True
                sp = self.chase_speed * dt
                # greedy: dominant axis first, then the other one
                axes = sorted(((dx, 0), (0, dy)), key=lambda v: -abs(v[0] + v[1]))
                for mx, my in axes:
                    step = (1 if (mx or my) > 0 else -1) * sp
                    if mx and self._try(step, 0, is_solid):
                        break
                    if my and self._try(0, step, is_solid):
                        break
        if not self.chasing:
            d = self.dir * self.speed * 0.55 * dt
            if not self._try(d, 0, is_solid):
                self.dir *= -1
        self.spin += dt * (10 if self.chasing else 4)

    def draw(self, surf, t):
        x, y = GRID_OX + self.x, GRID_OY + self.y
        col = PURPLE if not self.chasing else MAGENTA
        pulse = 0.7 + 0.3 * math.sin(t * (10 if self.chasing else 5))
        c = tuple(int(v * pulse) for v in col)
        if self.chasing:                            # threat ring
            pygame.draw.circle(surf, (70, 10, 60), (int(x), int(y)),
                               int(20 + 3 * math.sin(t * 10)), 1)
        pygame.draw.circle(surf, (35, 6, 45), (int(x + 2), int(y + 2)), 13)
        pygame.draw.circle(surf, c, (int(x), int(y)), 13)
        pygame.draw.circle(surf, (60, 14, 80), (int(x), int(y)), 13, 2)
        # triangular hunter eye, tracks spin
        a = self.spin
        pts = [(x + math.cos(a) * 8, y + math.sin(a) * 8),
               (x + math.cos(a + 2.5) * 5, y + math.sin(a + 2.5) * 5),
               (x + math.cos(a - 2.5) * 5, y + math.sin(a - 2.5) * 5)]
        pygame.draw.polygon(surf, WHITE, pts)


def _tiles_of(rect):
    c0, c1 = rect.left // TILE, (rect.right - 1) // TILE
    r0, r1 = rect.top // TILE, (rect.bottom - 1) // TILE
    for cy in range(r0, r1 + 1):
        for cx in range(c0, c1 + 1):
            yield cx, cy


# ----------------------------------------------------------------------------
# game
# ----------------------------------------------------------------------------
class Game:
    def __init__(self):
        try:
            pygame.mixer.pre_init(SR, -16, 2, 512)
        except Exception:
            pass
        pygame.init()
        pygame.display.set_caption("H4CK://MAINFRAME")
        self.screen = pygame.display.set_mode((W, H))
        self.clock = pygame.time.Clock()
        self._fonts = {}
        self.snd = SoundEngine()

        self.state = "title"
        self.level_idx = 0
        self.score = 0
        self.checkpoint = 0
        self.keys = set()
        self.t = 0.0
        self.level_t = 0.0
        self.state_t = 0.0
        self.shake = 0.0
        self.flash_t = 0.0
        self.banner_msg = None
        self.banner_t = 0.0
        self.last_beep = -1
        self.particles = []
        self.hacking = None          # {"kind","ref","code","prog"}
        self.hack_lock = 0.0

        # title matrix rain
        glyphs = "01<>/\\{}[]#$%&*+=;:"
        self.rain = [{"x": random.randrange(0, W, 18),
                      "y": random.uniform(-H, 0),
                      "v": random.uniform(90, 260),
                      "trail": [random.choice(glyphs) for _ in range(9)]}
                     for _ in range(52)]

        # CRT overlay (scanlines + vignette), built once
        self.crt = pygame.Surface((W, H), pygame.SRCALPHA)
        for y in range(0, H, 3):
            self.crt.fill((0, 0, 0, 46), (0, y, W, 1))
        vig = pygame.Surface((W, H), pygame.SRCALPHA)
        for i in range(70):
            a = int(2.2 * i)
            pygame.draw.rect(vig, (0, 0, 0, a),
                             (i, i, W - 2 * i, H - 2 * i), 1)
        self.crt.blit(vig, (0, 0))

        self.load_level(0)

    # -- fonts ---------------------------------------------------------
    def font(self, size):
        if size not in self._fonts:
            self._fonts[size] = pygame.font.Font(None, size)
        return self._fonts[size]

    # -- level handling -------------------------------------------------
    def load_level(self, idx):
        self.level_idx = idx
        spec = LEVELS[idx]
        rows = spec["map"]
        self.walls, self.gates, self.keydoors = set(), set(), set()
        self.lasers = {}                 # (c,r) -> orientation "H"/"V"
        self.packets, self.terminals, self.drones, self.bombs = [], [], [], []
        self.portal = None
        self.keycard = None
        hspeed = spec.get("hunter_speed", 110.0)
        fast = {(c, r): (ax, sp) for c, r, ax, sp in spec.get("fast_drones", [])}
        for r, row in enumerate(rows):
            for c, ch in enumerate(row):
                if ch == "#":
                    self.walls.add((c, r))
                elif ch == "G":
                    self.gates.add((c, r))
                elif ch == "q":
                    self.keydoors.add((c, r))
                elif ch == "z":
                    self.lasers[(c, r)] = None      # orientation set below
                elif ch == "D":
                    self.packets.append({"c": c, "r": r, "got": False,
                                         "kind": "data"})
                elif ch == "b":
                    self.packets.append({"c": c, "r": r, "got": False,
                                         "kind": "bait"})
                elif ch == "c":
                    self.packets.append({"c": c, "r": r, "got": False,
                                         "kind": "crypt", "locked": True,
                                         "code": self._make_code(4)})
                elif ch == "f":
                    self.bombs.append({"c": c, "r": r,
                                       "timer": spec.get("bomb_time", 75.0),
                                       "code": self._make_code(6),
                                       "defused": False, "boom": False})
                elif ch == "k":
                    self.keycard = {"c": c, "r": r, "got": False}
                elif ch == "T":
                    self.terminals.append({"c": c, "r": r, "hacked": False,
                                           "code": self._make_code(5 + idx)})
                elif ch == "E":
                    self.portal = {"c": c, "r": r}
                elif ch in "HV":
                    self.drones.append(Drone(c, r, ch, spec["drone_speed"]))
                elif ch == "x":
                    self.drones.append(Hunter(c, r, spec["drone_speed"],
                                              hspeed))
                elif ch == "P":
                    self.player = Player(c, r)
        for (c, r), (ax, sp) in fast.items():
            self.drones.append(Drone(c, r, ax, sp))
        # laser orientation: walls above+below -> beam runs horizontally
        for (c, r) in self.lasers:
            ud = ((c, r - 1) in self.walls) and ((c, r + 1) in self.walls)
            self.lasers[(c, r)] = "H" if ud else "V"
        self.laser_period = spec.get("laser_period", 3.0)
        self.laser_on_time = spec.get("laser_on", 1.3)
        self.gates_open = False
        self.keydoor_open = False
        self.integrity = 3
        self.time_left = spec["time"]
        self.level_t = 0.0
        self.hacking = None
        self.flash_t = 0.0
        self.banner_t = 0.0
        self.particles.clear()
        self.checkpoint = self.score
        if self.bombs:
            self.banner("!! FORK BOMB ARMED — DEFUSE IT !!", RED, 3.0)

    def _make_code(self, n):
        out = random.choice(HACK_WORDS)
        while len(out) < n:
            out += random.choice(["_", "-", "."]) + random.choice(HACK_WORDS)
        return out[: n + 3]

    def is_solid(self, c, r):
        if c < 0 or r < 0 or c >= COLS or r >= ROWS:
            return True
        if (c, r) in self.walls:
            return True
        if (c, r) in self.gates and not self.gates_open:
            return True
        if (c, r) in self.keydoors and not self.keydoor_open:
            return True
        return False

    def required_packets(self):
        return [p for p in self.packets if p["kind"] != "bait"]

    def banner(self, msg, color=GREEN, dur=2.2):
        self.banner_msg, self.banner_t, self.banner_c = msg, dur, color

    def burst(self, x, y, color, n=14, speed=110.0):
        for _ in range(n):
            self.particles.append(Particle(x, y, color, speed,
                                           random.uniform(0.3, 0.7),
                                           random.choice((2, 3, 4))))
        if len(self.particles) > 500:
            del self.particles[: len(self.particles) - 500]

    # -- state transitions ---------------------------------------------
    def start_run(self):
        self.score = 0
        self.load_level(0)
        self.state = "intro"
        self.state_t = 0.0
        self.snd.play("start")
        self.snd.play_music(LEVELS[0]["music"])

    def next_level(self):
        nxt = self.level_idx + 1
        if nxt >= len(LEVELS):
            self.state = "victory"
            self.state_t = 0.0
            self.snd.play_music("neon")
        else:
            self.load_level(nxt)
            self.state = "intro"
            self.state_t = 0.0
            self.snd.play_music(LEVELS[nxt]["music"])

    def game_over(self, reason):
        self.state = "gameover"
        self.state_t = 0.0
        self.over_reason = reason
        self.hacking = None
        self.snd.play("over")

    # -- events ----------------------------------------------------------
    def handle_events(self, events):
        for e in events:
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            if e.type == pygame.KEYDOWN:
                self.keys.add(e.key)
                self.on_key(e)
            elif e.type == pygame.KEYUP:
                self.keys.discard(e.key)

    def on_key(self, e):
        k = e.key
        if k == pygame.K_m and self.hacking is None:
            self.snd.toggle_mute()
            self.banner("MUTED" if self.snd.muted else "SOUND ON", AMBER, 1.0)
            return

        if self.state == "title":
            if k in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.start_run()
            return

        if self.state == "intro":
            if k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.state_t = 99.0
            return

        if self.state == "clear":
            if k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.next_level()
            return

        if self.state == "gameover":
            if k == pygame.K_r:
                self.score = self.checkpoint
                self.load_level(self.level_idx)
                self.state = "intro"
                self.state_t = 0.0
                self.snd.play("start")
            elif k in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.state = "title"
                self.state_t = 0.0
            return

        if self.state == "victory":
            if k in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.state = "title"
                self.state_t = 0.0
            return

        # ---------------- playing ----------------
        if self.hacking is not None:
            if k == pygame.K_ESCAPE:
                self.hacking = None
                self.banner("JACKED OUT", AMBER, 1.2)
                self.snd.play("ui")
                return
            ch = (e.unicode or "").lower()
            if ch and ch.isprintable() and self.hack_lock <= 0:
                hack = self.hacking
                if ch == hack["code"][hack["prog"]]:
                    hack["prog"] += 1
                    self.snd.play("key")
                    ref = hack["ref"]
                    self.burst(ref["c"] * TILE + TILE / 2,
                               ref["r"] * TILE + TILE / 2, CYAN, 3, 60.0)
                    if hack["prog"] >= len(hack["code"]):
                        self.finish_hack(hack)
                else:
                    self.snd.play("err")
                    self.hack_lock = 0.28
            return

        if k == pygame.K_e:
            target = self.nearest_interactable()
            if target is not None:
                kind, ref = target
                self.hacking = {"kind": kind, "ref": ref,
                                "code": ref["code"], "prog": 0}
                self.snd.play("ui")

    # -- interactables --------------------------------------------------
    def nearest_interactable(self):
        """Closest hackable thing near the player: terminal/bomb/crypt."""
        best, best_d = None, 1e9
        px, py = self.player.x, self.player.y
        for tm in self.terminals:
            if tm["hacked"]:
                continue
            d = math.hypot(tm["c"] * TILE + 20 - px, tm["r"] * TILE + 20 - py)
            if d < 72 and d < best_d:
                best, best_d = ("terminal", tm), d
        for bm in self.bombs:
            if bm["defused"] or bm["boom"]:
                continue
            d = math.hypot(bm["c"] * TILE + 20 - px, bm["r"] * TILE + 20 - py)
            if d < 72 and d < best_d:
                best, best_d = ("bomb", bm), d
        for pk in self.packets:
            if pk["kind"] != "crypt" or pk["got"] or not pk["locked"]:
                continue
            d = math.hypot(pk["c"] * TILE + 20 - px, pk["r"] * TILE + 20 - py)
            if d < 64 and d < best_d:
                best, best_d = ("crypt", pk), d
        return best

    def finish_hack(self, hack):
        kind, ref = hack["kind"], hack["ref"]
        self.hacking = None
        self.snd.play("hack")
        x, y = ref["c"] * TILE + 20, ref["r"] * TILE + 20
        if kind == "terminal":
            ref["hacked"] = True
            self.score += 250
            self.burst(x, y, GREEN, 24, 140.0)
            if all(t["hacked"] for t in self.terminals) \
                    and not self.gates_open and self.gates:
                self.gates_open = True
                self.snd.play("gate")
                for (c, r) in self.gates:
                    self.burst(c * TILE + 20, r * TILE + 20, MAGENTA, 18,
                               130.0)
                self.banner("FIREWALL DOWN — GATES OPEN", MAGENTA)
            else:
                self.banner("TERMINAL OWNED  +250", GREEN, 1.6)
        elif kind == "bomb":
            ref["defused"] = True
            self.score += 300
            self.burst(x, y, CYAN, 30, 150.0)
            self.banner("FORK BOMB DEFUSED  +300", CYAN)
        elif kind == "crypt":
            ref["locked"] = False
            self.score += 150
            self.burst(x, y, CYAN, 20, 120.0)
            self.banner("PACKET DECRYPTED  +150 — GO GRAB IT", CYAN, 1.8)

    # -- damage ---------------------------------------------------------
    def damage_player(self, src_x, src_y, reason, sfx="hurt"):
        pl = self.player
        if pl.invuln > 0:
            return False
        self.integrity -= 1
        self.snd.play(sfx)
        self.shake = 1.0
        self.flash_t = 0.35
        self.burst(pl.x, pl.y, RED, 26, 170.0)
        if self.integrity <= 0:
            self.game_over(reason)
            return True
        pl.invuln = 1.6
        kx = 1 if pl.x >= src_x else -1
        ky = 1 if pl.y >= src_y else -1
        for _ in range(6):
            pl.move(kx, 0, 0.02, self.is_solid)
            pl.move(0, ky, 0.02, self.is_solid)
        return True

    def laser_state(self, c, r):
        """(on, warning) for a laser tile, desynced per tile."""
        off = (c * 7 + r * 13) % int(self.laser_period * 10) / 10.0
        ph = (self.level_t + off) % self.laser_period
        return ph < self.laser_on_time, ph >= self.laser_period - 0.6

    # -- main update ------------------------------------------------------
    def update(self, dt):
        self.t += dt
        self.state_t += dt
        self.shake = max(0.0, self.shake - dt * 3.2)
        self.flash_t = max(0.0, self.flash_t - dt)
        self.banner_t = max(0.0, self.banner_t - dt)
        self.hack_lock = max(0.0, self.hack_lock - dt)
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]

        if self.state == "title":
            glyphs = "01<>/\\{}[]#$%&*+=;:"
            for d in self.rain:
                d["y"] += d["v"] * dt
                if random.random() < 0.06:
                    d["trail"][random.randrange(9)] = random.choice(glyphs)
                if d["y"] > H + 160:
                    d["y"] = random.uniform(-160, -10)
                    d["x"] = random.randrange(0, W, 18)
                    d["trail"] = [random.choice(glyphs) for _ in range(9)]
            return

        if self.state == "intro":
            if self.state_t > 3.0:
                self.state = "playing"
                self.state_t = 0.0
            return

        if self.state == "clear":
            if self.state_t > 3.2:
                self.next_level()
            return

        if self.state in ("gameover", "victory"):
            return

        # ---------------- playing ----------------
        self.level_t += dt
        pl = self.player
        if self.hacking is None:
            dx = (pygame.K_d in self.keys or pygame.K_RIGHT in self.keys) - \
                 (pygame.K_a in self.keys or pygame.K_LEFT in self.keys)
            dy = (pygame.K_s in self.keys or pygame.K_DOWN in self.keys) - \
                 (pygame.K_w in self.keys or pygame.K_UP in self.keys)
            if dx and dy:
                dx *= 0.7071
                dy *= 0.7071
            pl.move(dx, dy, dt, self.is_solid)
        pl.update(dt)

        for d in self.drones:
            was = d.chasing
            d.update(dt, self.is_solid, pl)
            if d.chasing and not was:
                self.snd.play("alert")

        # fork bombs tick
        for bm in self.bombs:
            if bm["defused"] or bm["boom"]:
                continue
            bm["timer"] -= dt
            if bm["timer"] < 10 and random.random() < dt * 6:
                self.burst(bm["c"] * TILE + 20, bm["r"] * TILE + 20,
                           AMBER, 1, 60.0)
            if bm["timer"] <= 0:
                bm["boom"] = True
                if self.hacking and self.hacking["ref"] is bm:
                    self.hacking = None
                self.burst(bm["c"] * TILE + 20, bm["r"] * TILE + 20,
                           RED, 46, 240.0)
                self.snd.play("explode")
                self.shake = 1.0
                self.flash_t = 0.5
                self.integrity -= 1
                self.banner("FORK BOMB DETONATED", RED)
                if self.integrity <= 0:
                    self.game_over("FORK BOMB — KERNEL PANIC")
                    return

        # trace countdown
        self.time_left -= dt
        if self.time_left <= 15.0:
            sec = int(self.time_left)
            if sec != self.last_beep:
                self.last_beep = sec
                self.snd.play("beep")
        if self.time_left <= 0:
            self.game_over("TRACE COMPLETE — CONNECTION TERMINATED")
            return

        pr = pl.rect

        # keycard
        if self.keycard and not self.keycard["got"]:
            r = pygame.Rect(self.keycard["c"] * TILE + 8,
                            self.keycard["r"] * TILE + 10, 24, 20)
            if pr.colliderect(r):
                self.keycard["got"] = True
                self.keydoor_open = True
                self.score += 50
                self.snd.play("keypick")
                self.burst(self.keycard["c"] * TILE + 20,
                           self.keycard["r"] * TILE + 20, GOLD, 18, 130.0)
                for (c, rr) in self.keydoors:
                    self.burst(c * TILE + 20, rr * TILE + 20, GOLD, 14,
                               120.0)
                self.banner("KEYCARD ACQUIRED — DOOR UNLOCKED", GOLD)

        # packets
        for pk in self.packets:
            if pk["got"]:
                continue
            if pk["kind"] == "crypt" and pk["locked"]:
                continue                       # must be decrypted first
            r = pygame.Rect(pk["c"] * TILE + 10, pk["r"] * TILE + 10, 20, 20)
            if pr.colliderect(r):
                pk["got"] = True
                if pk["kind"] == "bait":
                    self.time_left = max(1.0, self.time_left - 12.0)
                    self.snd.play("err")
                    self.shake = 0.5
                    self.burst(pk["c"] * TILE + 20, pk["r"] * TILE + 20,
                               RED, 16, 130.0)
                    self.banner("HONEYPOT!  TRACE +12s", RED, 1.6)
                else:
                    self.score += 100
                    self.snd.play("pickup")
                    self.burst(pk["c"] * TILE + 20, pk["r"] * TILE + 20,
                               GREEN, 12)
                    if all(p["got"] for p in self.required_packets()):
                        self.snd.play("portal")
                        self.banner("ALL DATA SECURED — EXIT ONLINE", CYAN)

        # laser grids (safe while jacked in)
        if self.hacking is None and pl.invuln <= 0:
            for (c, r), ori in self.lasers.items():
                on, _ = self.laser_state(c, r)
                if on and pr.colliderect((c * TILE, r * TILE, TILE, TILE)):
                    if self.damage_player(c * TILE + 20, r * TILE + 20,
                                          "FRIED BY LASER GRID", "zap"):
                        if self.state == "gameover":
                            return
                        break

        # drone contact (safe while jacked in)
        if self.hacking is None and pl.invuln <= 0:
            for d in self.drones:
                if pr.colliderect(d.rect):
                    if self.damage_player(d.x, d.y,
                                          "INTEGRITY LOST — ICE WIN"):
                        if self.state == "gameover":
                            return
                        break

        # exit portal
        if self.portal and all(p["got"] for p in self.required_packets()):
            r = pygame.Rect(self.portal["c"] * TILE + 4,
                            self.portal["r"] * TILE + 4, TILE - 8, TILE - 8)
            if pr.colliderect(r):
                bonus = 500 + int(self.time_left) * 10
                self.score += bonus
                self.clear_bonus = bonus
                self.state = "clear"
                self.state_t = 0.0
                self.snd.play("clear")
                self.burst(pl.x, pl.y, CYAN, 40, 200.0)

    # -- drawing -------------------------------------------------------
    def text(self, surf, s, size, color, pos, center=True, glow=None,
             align=None):
        img = self.font(size).render(s, True, color)
        r = img.get_rect()
        if align == "r":
            r.topright = pos
        elif center:
            r.center = pos
        else:
            r.topleft = pos
        if glow:
            g = self.font(size).render(s, True, glow)
            for ox, oy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
                surf.blit(g, r.move(ox, oy))
        surf.blit(img, r)
        return r

    def draw(self):
        self.screen.fill(BG)
        if self.state == "title":
            self.draw_title()
        else:
            self.draw_world()
            if self.state == "intro":
                self.draw_intro()
            elif self.state == "clear":
                self.draw_clear()
            elif self.state == "gameover":
                self.draw_gameover()
            elif self.state == "victory":
                self.draw_victory()
        # CRT: scanlines + vignette + faint rolling band
        self.screen.blit(self.crt, (0, 0))
        band_y = int((self.t * 45) % (H + 160)) - 80
        band = pygame.Surface((W, 80), pygame.SRCALPHA)
        band.fill((40, 255, 120, 10))
        self.screen.blit(band, (0, band_y))
        pygame.display.flip()

    # ---- title ----
    def draw_rain(self):
        for d in self.rain:
            for i, ch in enumerate(d["trail"]):
                yy = int(d["y"]) - i * 17
                if -20 < yy < H + 20:
                    shade = GREEN if i == 0 else \
                        (DIM_GREEN if i < 4 else (9, 48, 22))
                    self.text(self.screen, ch, 22, shade,
                              (int(d["x"]), yy))

    def draw_title(self):
        self.draw_rain()
        # glitch logo
        cx, cy = W // 2, 210
        if random.random() < 0.08:
            ox = random.randint(-6, 6)
            self.text(self.screen, "H4CK://MAINFRAME", 96, MAGENTA,
                      (cx + ox, cy + 3), glow=None)
            self.text(self.screen, "H4CK://MAINFRAME", 96, CYAN,
                      (cx - ox, cy - 3), glow=None)
        self.text(self.screen, "H4CK://MAINFRAME", 96, GREEN, (cx, cy),
                  glow=(6, 50, 18))
        self.text(self.screen, "A  R E T R O  I N T R U S I O N", 30,
                  DIM_GREEN, (cx, cy + 56))

        lines = [
            ("ARROWS / WASD", "move through the grid"),
            ("E", "HACK terminals / DEFUSE bombs / DECRYPT packets"),
            ("DATA", "steal every real packet to power the exit portal"),
            ("HONEYPOT", "decoys flash red - touching one costs 12s of trace"),
            ("ICE / LASERS", "patrols, hunters and grids - 3 hits = dumped"),
            ("TRACE", "finish all 8 levels before the trace runs out"),
        ]
        y = 360
        for k, v in lines:
            self.text(self.screen, k, 28, CYAN, (cx - 300, y), center=False)
            self.text(self.screen, v, 28, WHITE, (cx - 110, y), center=False)
            y += 40
        if int(self.t * 2) % 2 == 0:
            self.text(self.screen, ">> PRESS ENTER TO JACK IN <<", 40,
                      AMBER, (cx, 648), glow=(60, 40, 0))
        self.text(self.screen, "M = mute", 22, DIM_GREEN, (cx, 712))

    # ---- world ----
    def draw_world(self):
        ox = oy = 0
        if self.shake > 0:
            ox = random.randint(-6, 6) * self.shake
            oy = random.randint(-6, 6) * self.shake
        world = pygame.Surface((W, H))
        world.fill(BG)

        # floor grid
        for c in range(COLS + 1):
            pygame.draw.line(world, GRID_LINE,
                             (GRID_OX + c * TILE, GRID_OY),
                             (GRID_OX + c * TILE, GRID_OY + ROWS * TILE))
        for r in range(ROWS + 1):
            pygame.draw.line(world, GRID_LINE,
                             (GRID_OX, GRID_OY + r * TILE),
                             (GRID_OX + COLS * TILE, GRID_OY + r * TILE))

        # walls
        for (c, r) in self.walls:
            x, y = GRID_OX + c * TILE, GRID_OY + r * TILE
            pygame.draw.rect(world, WALL_DARK, (x, y, TILE, TILE))
            pygame.draw.rect(world, WALL_LITE, (x, y, TILE, 3))
            if (c, r + 1) not in self.walls:
                pygame.draw.rect(world, (12, 60, 30),
                                 (x, y + TILE - 3, TILE, 3))

        # firewall gates
        for (c, r) in self.gates:
            x, y = GRID_OX + c * TILE, GRID_OY + r * TILE
            if not self.gates_open:
                n = 5
                for i in range(n):
                    bx = x + 4 + i * (TILE - 8) / (n - 1)
                    h = TILE - 8 - 6 * abs(math.sin(self.t * 5 + i))
                    pygame.draw.line(world, MAGENTA,
                                     (bx, y + TILE / 2 - h / 2),
                                     (bx, y + TILE / 2 + h / 2), 3)
                pygame.draw.rect(world, (70, 8, 55), (x, y, TILE, TILE), 1)
            else:
                pygame.draw.rect(world, (30, 8, 26),
                                 (x + 3, y + 3, TILE - 6, TILE - 6), 1)

        # key doors (gold)
        for (c, r) in self.keydoors:
            x, y = GRID_OX + c * TILE, GRID_OY + r * TILE
            if not self.keydoor_open:
                n = 5
                for i in range(n):
                    bx = x + 4 + i * (TILE - 8) / (n - 1)
                    h = TILE - 8 - 5 * abs(math.sin(self.t * 4 + i))
                    pygame.draw.line(world, GOLD,
                                     (bx, y + TILE / 2 - h / 2),
                                     (bx, y + TILE / 2 + h / 2), 3)
                pygame.draw.rect(world, (70, 55, 8), (x, y, TILE, TILE), 1)
            else:
                pygame.draw.rect(world, (34, 28, 8),
                                 (x + 3, y + 3, TILE - 6, TILE - 6), 1)

        # laser grids
        for (c, r), ori in self.lasers.items():
            x, y = GRID_OX + c * TILE, GRID_OY + r * TILE
            on, warn = self.laser_state(c, r)
            # emitter posts
            post = (80, 40, 60) if not on else (200, 60, 120)
            if ori == "V":
                pygame.draw.rect(world, post, (x + 16, y, 8, 5))
                pygame.draw.rect(world, post, (x + 16, y + TILE - 5, 8, 5))
            else:
                pygame.draw.rect(world, post, (x, y + 16, 5, 8))
                pygame.draw.rect(world, post, (x + TILE - 5, y + 16, 5, 8))
            if on:
                for i in range(3):
                    pts = []
                    for s in range(6):
                        f = s / 5
                        jx = random.randint(-4, 4)
                        jy = random.randint(-4, 4)
                        if ori == "V":
                            pts.append((x + 20 + jx + (i - 1) * 6,
                                        y + 3 + f * (TILE - 6)))
                        else:
                            pts.append((x + 3 + f * (TILE - 6),
                                        y + 20 + jy + (i - 1) * 6))
                    pygame.draw.lines(world, (255, 120, 220) if i else WHITE,
                                      False, pts, 2 if i else 1)
            elif warn:
                pygame.draw.rect(world, AMBER, (x + 4, y + 4,
                                                TILE - 8, TILE - 8), 1)
            else:
                pygame.draw.rect(world, (50, 16, 40),
                                 (x + 6, y + 6, TILE - 12, TILE - 12), 1)

        # exit portal
        if self.portal:
            px = GRID_OX + self.portal["c"] * TILE + TILE / 2
            py = GRID_OY + self.portal["r"] * TILE + TILE / 2
            online = all(p["got"] for p in self.required_packets())
            col = CYAN if online else (70, 30, 34)
            for i in range(3):
                rad = 6 + i * 5 + 2 * math.sin(self.t * 4 - i)
                pygame.draw.circle(world, col, (int(px), int(py)),
                                   max(2, int(rad)), 1)
            a = self.t * (3 if online else 0.8)
            for i in range(4):
                ang = a + i * math.pi / 2
                tx = px + math.cos(ang) * 14
                ty = py + math.sin(ang) * 14
                pygame.draw.circle(world, col, (int(tx), int(ty)), 2)
            if online:
                self.text(world, "EXIT", 18, CYAN, (px, py - 26))

        # data / honeypot / encrypted packets
        for pk in self.packets:
            if pk["got"]:
                continue
            x = GRID_OX + pk["c"] * TILE + TILE / 2
            y = GRID_OY + pk["r"] * TILE + TILE / 2
            s = 7 + int(2 * math.sin(self.t * 6 + pk["r"]))
            if pk["kind"] == "bait":
                # looks like data... except for the red flicker
                flick = math.sin(self.t * 2.5 + pk["c"] * 1.3) > 0.82
                col = RED if flick else \
                    tuple(int(v * (0.7 + 0.3 * math.sin(self.t * 6)))
                          for v in GREEN)
                pygame.draw.rect(world, (50, 4, 16) if flick else (4, 50, 16),
                                 (x - s - 3, y - s - 3, 2 * s + 6, 2 * s + 6))
                pygame.draw.rect(world, col, (x - s, y - s, 2 * s, 2 * s))
                self.text(world, "01" if int(self.t * 2 + pk["c"]) % 2
                          else "10", 18, BG, (x, y))
            elif pk["kind"] == "crypt" and pk["locked"]:
                pulse = 0.7 + 0.3 * math.sin(self.t * 4 + pk["c"])
                col = tuple(int(v * pulse) for v in CYAN)
                pygame.draw.rect(world, (4, 30, 44),
                                 (x - s - 3, y - s - 3, 2 * s + 6, 2 * s + 6))
                pygame.draw.rect(world, col, (x - s, y - s, 2 * s, 2 * s))
                self.text(world, "#?", 18, BG, (x, y))
                pygame.draw.arc(world, col, (x - 6, y - s - 10, 12, 12),
                                0, math.pi, 2)
            else:
                pulse = 0.7 + 0.3 * math.sin(self.t * 6 + pk["c"])
                col = tuple(int(v * pulse) for v in GREEN)
                pygame.draw.rect(world, (4, 50, 16),
                                 (x - s - 3, y - s - 3, 2 * s + 6, 2 * s + 6))
                pygame.draw.rect(world, col, (x - s, y - s, 2 * s, 2 * s))
                self.text(world, "01" if int(self.t * 2 + pk["c"]) % 2
                          else "10", 18, BG, (x, y))

        # fork bombs
        for bm in self.bombs:
            if bm["defused"]:
                x, y = GRID_OX + bm["c"] * TILE, GRID_OY + bm["r"] * TILE
                pygame.draw.rect(world, (8, 30, 20), (x + 8, y + 10, 24, 22))
                self.text(world, "OK", 18, DIM_GREEN, (x + 20, y + 21))
                continue
            if bm["boom"]:
                continue
            x, y = GRID_OX + bm["c"] * TILE, GRID_OY + bm["r"] * TILE
            urgent = bm["timer"] < 10
            blink = int(self.t * (8 if urgent else 3)) % 2 == 0
            pygame.draw.rect(world, (16, 8, 10), (x + 6, y + 8, 28, 26))
            pygame.draw.rect(world, RED if blink else (90, 20, 26),
                             (x + 6, y + 8, 28, 26), 2)
            pygame.draw.line(world, (90, 20, 26), (x + 20, y + 8),
                             (x + 20, y + 3), 2)
            pygame.draw.circle(world, RED if blink else (90, 20, 26),
                               (x + 20, y + 3), 2)
            self.text(world, "%d" % max(0, int(bm["timer"])), 22,
                      RED if urgent else AMBER, (x + 20, y + 22))

        # keycard
        if self.keycard and not self.keycard["got"]:
            x = GRID_OX + self.keycard["c"] * TILE
            y = GRID_OY + self.keycard["r"] * TILE
            bob = int(2 * math.sin(self.t * 4))
            pygame.draw.rect(world, (60, 45, 8),
                             (x + 8, y + 12 + bob, 24, 16))
            pygame.draw.rect(world, GOLD, (x + 8, y + 12 + bob, 24, 16), 2)
            pygame.draw.rect(world, GOLD, (x + 12, y + 16 + bob, 6, 4))
            pygame.draw.circle(world, GOLD, (x + 26, y + 20 + bob), 3, 1)

        # terminals
        for tm in self.terminals:
            x = GRID_OX + tm["c"] * TILE
            y = GRID_OY + tm["r"] * TILE
            pygame.draw.rect(world, (10, 24, 16), (x + 4, y + 6, 32, 26))
            pygame.draw.rect(world, DIM_GREEN, (x + 4, y + 6, 32, 26), 1)
            scr = (6, 34, 18) if tm["hacked"] else (8, 18, 26)
            pygame.draw.rect(world, scr, (x + 8, y + 10, 24, 14))
            tag = "OK" if tm["hacked"] else ">"
            col = GREEN if tm["hacked"] else CYAN
            if tm["hacked"] or int(self.t * 2) % 2 == 0:
                self.text(world, tag, 20, col, (x + 20, y + 17))
            pygame.draw.rect(world, DIM_GREEN, (x + 14, y + 33, 12, 3))

        # drones + player
        for d in self.drones:
            d.draw(world, self.t)
        self.player.draw(world, self.t)

        # particles
        for p in self.particles:
            p.draw(world)

        self.draw_hud(world)
        self.draw_prompts(world)

        # red damage flash
        if self.flash_t > 0:
            fl = pygame.Surface((W, H), pygame.SRCALPHA)
            fl.fill((255, 0, 30, int(120 * self.flash_t / 0.5)))
            world.blit(fl, (0, 0))

        self.screen.blit(world, (ox, oy))

        if self.hacking is not None:
            self.draw_hack_panel()

        if self.banner_t > 0:
            a = min(1.0, self.banner_t / 0.4)
            col = tuple(int(v * a) for v in self.banner_c)
            self.text(self.screen, self.banner_msg, 44, col,
                      (W // 2, GRID_OY + 40), glow=(0, 20, 8))

    def draw_hud(self, surf):
        pygame.draw.rect(surf, (3, 14, 7), (0, 0, W, GRID_OY))
        pygame.draw.line(surf, (14, 60, 30), (0, GRID_OY - 2),
                         (W, GRID_OY - 2), 2)
        spec = LEVELS[self.level_idx]
        self.text(surf, spec["name"], 28, GREEN, (16, 12), center=False)
        self.text(surf, "SCORE %06d" % self.score, 28, AMBER, (16, 44),
                  center=False)

        req = self.required_packets()
        got = sum(1 for p in req if p["got"])
        self.text(surf, "DATA %d/%d" % (got, len(req)), 28, CYAN,
                  (330, 44), center=False)

        # fork-bomb warning
        armed = [b for b in self.bombs if not b["defused"] and not b["boom"]]
        if armed:
            tmin = min(b["timer"] for b in armed)
            col = RED if (tmin < 10 and int(self.t * 4) % 2 == 0) else AMBER
            self.text(surf, "BOMB %ds" % max(0, int(tmin)), 26, col,
                      (330, 12), center=False)

        # integrity pips
        self.text(surf, "INTEGRITY", 24, DIM_GREEN, (560, 12), center=False)
        for i in range(3):
            col = RED if i < self.integrity else (40, 12, 14)
            pygame.draw.rect(surf, col, (560 + i * 30, 40, 22, 14))
            pygame.draw.rect(surf, (90, 20, 24),
                             (560 + i * 30, 40, 22, 14), 1)

        # trace bar
        frac = max(0.0, self.time_left / spec["time"])
        low = self.time_left <= 15.0
        col = RED if low and int(self.t * 4) % 2 == 0 else \
            (AMBER if frac < 0.35 else GREEN)
        self.text(surf, "TRACE", 24, DIM_GREEN, (760, 12), center=False)
        pygame.draw.rect(surf, (10, 24, 14), (760, 38, 150, 16))
        pygame.draw.rect(surf, col, (760, 38, int(150 * frac), 16))
        pygame.draw.rect(surf, (20, 70, 35), (760, 38, 150, 16), 1)
        self.text(surf, "%3ds" % max(0, int(self.time_left)), 22, col,
                  (950, 37), align="r")

        pygame.draw.line(surf, (10, 40, 20), (0, H - 41), (W, H - 41), 1)
        hint = "ARROWS move   E hack   M mute"
        self.text(surf, hint, 22, (16, 70, 36), (W // 2, H - 22))

    def draw_prompts(self, surf):
        if self.state != "playing" or self.hacking is not None:
            return
        target = self.nearest_interactable()
        if target is not None:
            kind, ref = target
            label = {"terminal": "[E] HACK", "bomb": "[E] DEFUSE",
                     "crypt": "[E] DECRYPT"}[kind]
            col = {"terminal": AMBER, "bomb": RED, "crypt": CYAN}[kind]
            x = GRID_OX + ref["c"] * TILE + TILE / 2
            y = GRID_OY + ref["r"] * TILE - 12
            if int(self.t * 3) % 2 == 0:
                self.text(surf, label, 24, col, (x, y), glow=(50, 30, 0))

    def draw_hack_panel(self):
        hack = self.hacking
        pw, ph = 560, 150
        px, py = (W - pw) // 2, H - ph - 60
        kind = hack["kind"]
        title = {"terminal": ">> INJECT PAYLOAD — TYPE THE CODE",
                 "crypt": ">> DECRYPT PACKET — TYPE THE KEY",
                 "bomb": "!! DEFUSE FORK BOMB — TYPE THE KILL CODE"}[kind]
        tcol = {"terminal": DIM_GREEN, "crypt": CYAN, "bomb": RED}[kind]
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((2, 16, 10, 235))
        pygame.draw.rect(panel, RED if kind == "bomb" else GREEN,
                         (0, 0, pw, ph), 2)
        self.screen.blit(panel, (px, py))
        self.text(self.screen, title + "  (ESC to abort)", 24, tcol,
                  (W // 2, py + 24))
        code = hack["code"]
        done = code[: hack["prog"]]
        todo = code[hack["prog"]:]
        x0 = W // 2 - 240
        self.text(self.screen, "root@mainframe:~# ", 30, DIM_GREEN,
                  (x0, py + 66), center=False)
        x = x0 + self.font(30).size("root@mainframe:~# ")[0]
        self.text(self.screen, done, 30, GREEN, (x, py + 66), center=False)
        x += self.font(30).size(done)[0]
        if int(self.t * 4) % 2 == 0 and todo:
            cur, rest = todo[0], todo[1:]
        else:
            cur, rest = "_", todo[1:] if todo else ""
        self.text(self.screen, cur, 30, AMBER if todo else DIM_GREEN,
                  (x, py + 66), center=False)
        x += self.font(30).size(cur)[0]
        self.text(self.screen, rest, 30, (60, 160, 90), (x, py + 66),
                  center=False)
        # progress bar
        frac = hack["prog"] / max(1, len(code))
        pygame.draw.rect(self.screen, (10, 30, 16), (x0, py + 110, 480, 12))
        pygame.draw.rect(self.screen, CYAN, (x0, py + 110,
                                             int(480 * frac), 12))
        if self.hack_lock > 0:
            self.text(self.screen, "!! SYNTAX ERROR !!", 26, RED,
                      (W // 2, py + 40))

    # ---- cards ----
    def draw_intro(self):
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((0, 6, 2, 215))
        self.screen.blit(ov, (0, 0))
        spec = LEVELS[self.level_idx]
        self.text(self.screen, spec["name"], 64, GREEN, (W // 2, 280),
                  glow=(6, 50, 18))
        self.text(self.screen, spec["tip"], 28, AMBER, (W // 2, 350))
        got = len(self.required_packets())
        parts = ["%d DATA" % got, "%d ICE" % len(self.drones),
                 "TRACE %ds" % int(spec["time"])]
        if self.terminals:
            parts.append("%d TERMINAL" % len(self.terminals))
        if self.bombs:
            parts.append("FORK BOMB")
        if self.lasers:
            parts.append("LASERS")
        self.text(self.screen, "  ·  ".join(parts), 30, WHITE,
                  (W // 2, 408))
        if int(self.t * 2) % 2 == 0:
            self.text(self.screen, "ENTER = SKIP", 24, DIM_GREEN,
                      (W // 2, 480))

    def draw_clear(self):
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((0, 10, 4, 200))
        self.screen.blit(ov, (0, 0))
        self.text(self.screen, "LEVEL COMPLETE", 72, CYAN, (W // 2, 300),
                  glow=(0, 40, 50))
        self.text(self.screen, "BONUS +%d" % self.clear_bonus, 40, AMBER,
                  (W // 2, 380))
        self.text(self.screen, "SCORE %06d" % self.score, 36, GREEN,
                  (W // 2, 436))
        if int(self.t * 2) % 2 == 0:
            self.text(self.screen, ">> ENTER FOR NEXT LEVEL <<", 30, WHITE,
                      (W // 2, 520))

    def draw_gameover(self):
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((20, 0, 4, 210))
        self.screen.blit(ov, (0, 0))
        if random.random() < 0.12:
            ox = random.randint(-8, 8)
            self.text(self.screen, "CONNECTION TERMINATED", 64, CYAN,
                      (W // 2 + ox, 296))
        self.text(self.screen, "CONNECTION TERMINATED", 64, RED,
                  (W // 2, 300), glow=(60, 0, 10))
        self.text(self.screen, self.over_reason, 30, WHITE, (W // 2, 380))
        self.text(self.screen, "SCORE %06d" % self.score, 36, AMBER,
                  (W // 2, 440))
        self.text(self.screen, "R = RETRY LEVEL      ENTER = TITLE", 30,
                  GREEN, (W // 2, 520))

    def draw_victory(self):
        for d in self.rain:
            d["y"] += d["v"] * 0.016
            if d["y"] > H + 160:
                d["y"] = random.uniform(-160, -10)
        self.draw_rain()
        self.text(self.screen, "SYSTEM OWNED", 88, GREEN, (W // 2, 260),
                  glow=(6, 60, 20))
        self.text(self.screen, "ALL 8 MAINFRAME LAYERS BREACHED", 36, CYAN,
                  (W // 2, 350))
        self.text(self.screen, "FINAL SCORE %06d" % self.score, 44, AMBER,
                  (W // 2, 430))
        self.text(self.screen, "you are l33t.  now go outside.", 28,
                  DIM_GREEN, (W // 2, 500))
        if int(self.t * 2) % 2 == 0:
            self.text(self.screen, ">> ENTER FOR TITLE <<", 30, WHITE,
                      (W // 2, 580))

    # -- main loop ------------------------------------------------------
    def run(self):
        while True:
            dt = min(0.05, self.clock.tick(FPS) / 1000.0)
            self.handle_events(pygame.event.get())
            self.update(dt)
            self.draw()


if __name__ == "__main__":
    Game().run()
