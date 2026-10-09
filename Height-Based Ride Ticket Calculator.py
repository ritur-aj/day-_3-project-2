import math
import os
import random
import re
import shutil
import sys
import time

# =============================================================================
#  PROJECT CONFIGURATION  (edit these)
# =============================================================================
PROJECT_NAME = "Height-Based Ride Ticket Calculator "
PROJECT_VERSION = "v1.0.0"
DEVELOPER = "Ritu Raj"
ROLE = "Data Science & AI Developer"
CREATED_ON = "Oct 2026"
DESCRIPTION = ["A simple and user-friendly", " Height-Based Ride Ticket Calculator", "project built with Python."]
TECHNOLOGIES = "Python  |  CLI  |  OOP"

LOAD_PERCENT = 55      # where the loading bar stops (55 = exactly like the image, 100 = full)
WIDTH = 71             # width of the whole splash layout (columns)
SPEED = 1.0            # 1.0 = normal, 0.5 = twice as fast, 0 = no delays (--fast)

# =============================================================================
#  COLOURS  (24-bit RGB)
# =============================================================================
RESET = "\033[0m"
BOLD = "\033[1m"

GOLD = (255, 205, 60)
AMBER = (255, 150, 20)
BLUE = (60, 160, 255)
WHITE = (238, 243, 252)
MUTED = (105, 135, 170)
BORDER = (205, 155, 35)
TRACK = (26, 44, 80)
SEPARATOR = (24, 42, 72)
GREEN = (80, 230, 140)


def rgb(c):
    return f"\033[38;2;{c[0]};{c[1]};{c[2]}m"


def paint(text, color, bold=False):
    return f"{BOLD if bold else ''}{rgb(color)}{text}{RESET}"


def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def gradient(text, c0, c1, bold=False):
    n = max(1, len(text) - 1)
    body = "".join(
        (BOLD if bold else "") + rgb(lerp(c0, c1, i / n)) + ch
        for i, ch in enumerate(text)
    )
    return body + RESET


_ANSI = re.compile(r"\033\[[0-9;?]*[A-Za-z]")


def vlen(s):
    """Visible length of a string (ANSI codes removed)."""
    return len(_ANSI.sub("", s))


def center(s):
    return " " * max(0, (WIDTH - vlen(s)) // 2) + s


# =============================================================================
#  TERMINAL HELPERS
# =============================================================================
def out(text):
    sys.stdout.write(text)


def flush():
    sys.stdout.flush()


def pause(seconds):
    if SPEED > 0:
        flush()
        time.sleep(seconds * SPEED)


def clear_screen():
    out("\033[2J\033[3J\033[H")
    flush()


def setup_terminal():
    if os.name == "nt":
        os.system("")  # switches on ANSI escape support in Windows consoles
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


class Region:
    """A block of N terminal rows that can be redrawn in place (animation)."""

    def __init__(self, height):
        self.height = height
        self.drawn = False

    def draw(self, lines):
        assert len(lines) == self.height, (len(lines), self.height)
        buf = []
        if self.drawn:
            buf.append(f"\033[{self.height}A")
        for line in lines:
            buf.append("\r" + line + "\033[K\n")
        out("".join(buf))
        flush()
        self.drawn = True


# =============================================================================
#  BRAILLE CANVAS  (2x4 dots per character cell -> smooth curves)
# =============================================================================
_BITS = {
    (0, 0): 0x01, (0, 1): 0x02, (0, 2): 0x04, (1, 0): 0x08,
    (1, 1): 0x10, (1, 2): 0x20, (0, 3): 0x40, (1, 3): 0x80,
}


class Canvas:
    def __init__(self, cols, rows):
        self.cols, self.rows = cols, rows
        self.w, self.h = cols * 2, rows * 4
        self.dots = {}

    def set(self, x, y, color):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < self.w and 0 <= y < self.h:
            self.dots[(x, y)] = color

    def erase(self, x, y):
        self.dots.pop((int(round(x)), int(round(y))), None)

    def line(self, x0, y0, x1, y1, c0, c1=None):
        c1 = c1 or c0
        n = max(1, int(max(abs(x1 - x0), abs(y1 - y0))))
        for i in range(n + 1):
            t = i / n
            self.set(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, lerp(c0, c1, t))

    def cells(self):
        """-> rows x cols grid of (char, colour) or None."""
        grid = [[None] * self.cols for _ in range(self.rows)]
        acc = {}
        for (x, y), c in self.dots.items():
            key = (x // 2, y // 4)
            m, r, g, b, n = acc.get(key, (0, 0, 0, 0, 0))
            acc[key] = (m | _BITS[(x % 2, y % 4)], r + c[0], g + c[1], b + c[2], n + 1)
        for (cx, cy), (m, r, g, b, n) in acc.items():
            grid[cy][cx] = (chr(0x2800 + m), (r // n, g // n, b // n))
        return grid


def serialize(row):
    parts, last = [], None
    for cell in row:
        if cell is None:
            parts.append(" ")
            continue
        ch, col = cell
        if col != last:
            parts.append(rgb(col))
            last = col
        parts.append(ch)
    parts.append(RESET)
    return "".join(parts)


# =============================================================================
#  1) RING LOADER + HOURGLASS + TITLE + PROGRESS BAR
# =============================================================================
RING_COLS, RING_ROWS = 20, 10
GAP_DEG = 4.5


def _build_ring_dots():
    c = RING_COLS - 0.5  # 19.5
    dots = []
    for py in range(RING_ROWS * 4):
        for px in range(RING_COLS * 2):
            dx, dy = px - c, py - c
            if not (15.6 <= math.hypot(dx, dy) <= 19.6):
                continue
            phi = math.degrees(math.atan2(dx, -dy)) % 360  # 0 = top, clockwise
            if (min(phi, 360 - phi) < GAP_DEG or abs(phi - 90) < GAP_DEG
                    or abs(phi - 270) < GAP_DEG):
                continue  # the three small gaps (12, 3 and 9 o'clock)
            dots.append((px, py, phi))
    return dots


RING_DOTS = _build_ring_dots()

HOURGLASS = [
    ["▀▀▀▀▀▀", " ╲▓▓╱ ", "  ╲╱  ", "  ╱╲  ", " ╱  ╲ ", "▄▄▄▄▄▄"],
    ["▀▀▀▀▀▀", " ╲▒▒╱ ", "  ╲╱  ", "  ╱╲  ", " ╱▒▒╲ ", "▄▄▄▄▄▄"],
    ["▀▀▀▀▀▀", " ╲  ╱ ", "  ╲╱  ", "  ╱╲  ", " ╱▓▓╲ ", "▄▄▄▄▄▄"],
    ["▄▄▄▄▄▄", " ╲▓▓╱ ", "  ╲╱  ", "  ╱╲  ", " ╱  ╲ ", "▀▀▀▀▀▀"],
]
FINAL_HOURGLASS = 1


def ring_color(phi):
    if phi < 180:   # right half -> blue
        return lerp((90, 185, 255), (10, 80, 210), phi / 180)
    return lerp((255, 150, 10), (255, 218, 80), (phi - 180) / 180)  # left half -> gold


def ring_rows(fill, glow, hg):
    cv = Canvas(RING_COLS, RING_ROWS)
    for px, py, phi in RING_DOTS:
        if phi > fill * 360:
            if (px + py) % 3 == 0:
                cv.set(px, py, TRACK)  # faint track before the ring is drawn
            continue
        col = ring_color(phi)
        if glow is not None:
            d = (glow - phi) % 360
            if d < 90:
                col = lerp(col, (255, 255, 255), (1 - d / 90) ** 2 * 0.8)
        cv.set(px, py, col)
    grid = cv.cells()
    for i, text in enumerate(HOURGLASS[hg]):
        for j, ch in enumerate(text):
            if ch != " ":
                grid[2 + i][7 + j] = (ch, AMBER if ch in "▓▒" else GOLD)
    return [serialize(r) for r in grid]


TITLE = "PROJECT IS LOADING..."


def title_line(k):
    cells = []
    for i, ch in enumerate(TITLE):
        if i < 7:
            col = lerp((255, 226, 95), (255, 150, 20), i / 6)
        else:
            col = lerp((70, 165, 255), (205, 232, 255), (i - 7) / (len(TITLE) - 8))
        cells.append(BOLD + rgb(col) + (ch if i < k else " ") + RESET)
    return " ".join(cells)


BAR_INNER = 46


def bar_lines(pct):
    n = BAR_INNER
    full, rem = divmod(int(n * 8 * pct / 100), 8)
    cells = []
    for i in range(n):
        if i < full or (i == full and rem):
            base = lerp((255, 224, 95), (255, 135, 10), i / (n - 1))
            if (i // 2) % 2:
                base = lerp(base, (0, 0, 0), 0.16)  # subtle stripes like the image
            ch = "█" if i < full else "▏▎▍▌▋▊▉"[rem - 1]
            cells.append(rgb(base) + ch)
        else:
            cells.append(rgb(TRACK) + "░")
    mid = paint("│", BORDER) + "".join(cells) + RESET + paint("│", BLUE)
    return [
        gradient("╭" + "─" * n + "╮", BORDER, BLUE),
        mid,
        gradient("╰" + "─" * n + "╯", BORDER, BLUE),
    ]


HEADER_H = 1 + RING_ROWS + 1 + 1 + 1 + 3


def header_frame(fill, glow, hg, title_k, pct):
    rows = [""]
    rows += [center(r) for r in ring_rows(fill, glow, hg)]
    rows += ["", center(title_line(title_k)), ""]
    rows += [center(r) for r in bar_lines(pct)]
    return rows


def animate_header():
    region = Region(HEADER_H)
    frame = 0
    # act 1 - the ring draws itself
    steps = 28
    for i in range(steps + 1):
        region.draw(header_frame(i / steps, None, (frame // 5) % 4, 0, 0))
        frame += 1
        pause(0.03)
    # act 2 - the title is typed while the ring glows
    for k in range(len(TITLE) + 1):
        region.draw(header_frame(1, (frame * 17) % 360, (frame // 5) % 4, k, 0))
        frame += 1
        pause(0.035)
    # act 3 - progress bar fills
    steps = 44
    for i in range(steps + 1):
        pct = LOAD_PERCENT * i / steps
        region.draw(header_frame(1, (frame * 17) % 360, (frame // 5) % 4, len(TITLE), pct))
        frame += 1
        pause(0.035)
    # settle on the final look (same as the image)
    region.draw(header_frame(1, None, FINAL_HOURGLASS, len(TITLE), LOAD_PERCENT))


# =============================================================================
#  2) THE EYE  (procedurally drawn in braille, opens like a real eye)
# =============================================================================
EYE_COLS, EYE_ROWS = 44, 11


def eye_canvas(openness):
    k = max(0.05, min(1.0, openness))
    cv = Canvas(EYE_COLS, EYE_ROWS)
    cx, cy, a = 43.5, 25.0, 39.0
    up, lo, skew = 17.0 * k, 10.5 * k, 0.10
    icx, icy, ir, pr = cx - 3, cy + 1, 13.5, 5.2
    rng = random.Random(11)

    # golden / blue sparkles
    for _ in range(46):
        base = rng.choice([(255, 190, 60), (210, 140, 40), (70, 140, 235)])
        cv.set(rng.uniform(0, cv.w), rng.uniform(0, cv.h),
               lerp((0, 0, 0), base, rng.uniform(0.25, 0.7)))
    # energy streaks (blue left, gold right)
    cv.line(2, 24, 16, 36, (60, 130, 255), (10, 40, 120))
    cv.line(6, 18, 13, 26, (70, 150, 255), (15, 50, 140))
    cv.line(0, 30, 8, 38, (40, 100, 220), (10, 30, 100))
    cv.line(80, 28, 87, 38, (255, 190, 60), (120, 70, 10))
    cv.line(74, 14, 86, 24, (255, 170, 40), (110, 60, 10))

    def lids(x):
        u = (x - cx) / a
        if abs(u) >= 1:
            return None
        s = 1 - u * u
        off = skew * (x - cx)
        return cy - up * s ** 0.85 + off, cy + lo * s + off, u

    # eyeball: iris, rays, pupil, sclera
    for x in range(cv.w):
        r = lids(x)
        if r is None:
            continue
        yu, yl, _ = r
        for y in range(math.ceil(yu + 1.5), math.floor(yl - 0.5) + 1):
            dx, dy = x - icx, y - icy
            rr = math.hypot(dx, dy)
            if rr <= ir:
                if rr < pr:
                    cv.erase(x, y)  # pupil stays dark
                    continue
                if rr > ir - 1.6:
                    cv.set(x, y, (150, 85, 15))  # dark rim of the iris
                    continue
                ray = math.sin(math.atan2(dy, dx) * 20 + rr * 0.45)
                if ray > -0.45 or rr < pr + 2.2:
                    col = lerp((255, 215, 90), (235, 125, 15), (rr - pr) / (ir - pr))
                    if ray > 0.6:
                        col = lerp(col, (255, 245, 190), 0.45)
                    cv.set(x, y, col)
            elif (x + 2 * y) % 3 == 0:
                f = min(1.0, min(y - yu, yl - y) / 7)
                cv.set(x, y, lerp((60, 52, 45), (165, 150, 128), f))

    # eyelids, crease and lashes
    for x in range(int(cx - a), int(cx + a) + 1):
        r = lids(x)
        if r is None:
            continue
        yu, yl, u = r
        f = 1 - abs(u) ** 2.2
        cv.set(x, yu, lerp((120, 70, 15), (255, 215, 85), f))
        cv.set(x, yu - 1, lerp((90, 50, 10), (255, 190, 60), f))
        cv.set(x, yl, lerp((100, 60, 15), (215, 140, 40), f))
        if x % 2 == 0:
            cv.set(x, yu - 5 * k - 1, lerp((50, 30, 5), (150, 95, 25), f))
        if x % 3 == 0:
            cv.set(x, yl + 2, lerp((40, 25, 5), (120, 75, 20), f))
    for x in range(int(cx - a) + 3, int(cx + a) - 1, 3):
        r = lids(x)
        if r is None:
            continue
        yu, _, u = r
        length = (5.5 + 3.5 * math.sin(x * 1.3) ** 2) * (1 - abs(u) ** 3 * 0.6) * (0.35 + 0.65 * k)
        dxl, dyl = 0.25 + 0.6 * u, -1.0
        norm = math.hypot(dxl, dyl)
        cv.line(x, yu - 1, x + dxl / norm * length, yu - 1 + dyl / norm * length,
                (235, 175, 55), (80, 45, 8))

    # little light reflection on the iris
    if k > 0.6:
        hx, hy = icx + 5.5, icy - 6
        for ox in (0, 1):
            for oy in (0, 1):
                cv.set(hx + ox, hy + oy, (255, 248, 225))
    return cv


def eye_frame(openness):
    grid = eye_canvas(openness).cells()
    n = len(grid)
    edge = lerp(BORDER, (0, 0, 0), 0.3)
    rows = []
    for i, row in enumerate(grid):
        if i == 0:
            left = " " * 4 + paint("╲", edge) + " " * 8
            right = " " * 9 + paint("╱", edge)
        elif i == n - 1:
            left = " " * 4 + paint("╱", edge) + " " * 8
            right = " " * 9 + paint("╲", edge)
        else:
            left = " " * 5 + paint("│", edge) + " " * 7
            right = " " * 8 + paint("│", edge)
        rows.append(left + serialize(row) + right)
    return rows


def animate_eye():
    region = Region(EYE_ROWS)
    for o in (0.0, 0.10, 0.28, 0.52, 0.78, 1.0):  # the eye opens
        region.draw(eye_frame(o))
        pause(0.08)
    pause(0.3)
    for o in (0.45, 0.08, 0.45, 1.0):              # one blink
        region.draw(eye_frame(o))
        pause(0.06)
    region.draw(eye_frame(1.0))


# =============================================================================
#  3) "ALL EYES ON YOU"  (block letters, metallic gradient + shine sweep)
# =============================================================================
FONT = {
    "A": ("▄▀█", "█▀█"), "L": ("█  ", "█▄▄"), "E": ("█▀▀", "██▄"),
    "Y": ("█▄█", " █ "), "S": ("█▀▀", "▄▄█"), "O": ("█▀█", "█▄█"),
    "N": ("█▄ █", "█ ▀█"), "U": ("█ █", "█▄█"), " ": (" ", " "),
}
HEADLINE_GROUPS = [
    ("ALL EYES", (255, 236, 140), (205, 135, 20)),   # gold
    ("ON YOU", (244, 248, 255), (105, 145, 215)),    # silver-blue
]


def headline_rows():
    r0, r1 = [], []
    for gi, (text, c0, c1) in enumerate(HEADLINE_GROUPS):
        top, bottom = "", ""
        for ci, ch in enumerate(text):
            a, b = FONT[ch]
            top += (" " if ci else "") + a
            bottom += (" " if ci else "") + b
        for i, (x, y) in enumerate(zip(top, bottom)):
            c = lerp(c0, c1, i / (len(top) - 1))
            r0.append((x, c))
            r1.append((y, lerp(c, (0, 0, 0), 0.28)))
        if gi == 0:
            for _ in range(3):
                r0.append((" ", None))
                r1.append((" ", None))
    return r0, r1


def animate_headline():
    r0, r1 = headline_rows()
    total = len(r0)
    pad = " " * ((WIDTH - total) // 2)
    region = Region(2)

    def frame(k, shine=None):
        lines = []
        for row in (r0, r1):
            s = []
            for i, (ch, col) in enumerate(row[:k]):
                if col is None or ch == " ":
                    s.append(" ")
                    continue
                if shine is not None and abs(i - shine) < 5:
                    col = lerp(col, (255, 255, 255), (1 - abs(i - shine) / 5) * 0.85)
                s.append(BOLD + rgb(col) + ch)
            lines.append(pad + "".join(s) + RESET)
        return lines

    for k in range(0, total + 1, 2):
        region.draw(frame(k))
        pause(0.018)
    region.draw(frame(total))
    for s in range(-5, total + 6, 2):               # shine sweeps over the letters
        region.draw(frame(total, s))
        pause(0.012)
    region.draw(frame(total))


def divider_line(span):
    total = 62
    c = (total - 1) / 2
    chars = []
    for i in range(total):
        d = abs(i - c)
        if d > span:
            chars.append(" ")
            continue
        base = lerp(GOLD, BLUE, i / (total - 1))
        chars.append(rgb(lerp((0, 0, 0), base, (1 - (d / c) ** 2) ** 0.9)) + "━")
    return center("".join(chars) + RESET)


def animate_divider():
    region = Region(1)
    for span in range(0, 33, 2):
        region.draw([divider_line(span)])
        pause(0.015)


# =============================================================================
#  4) PROJECT INFORMATION PANEL
# =============================================================================
BW = 67                                  # box width
INNER = BW - 2
PADL = " " * ((WIDTH - BW) // 2)
ICON_W, LABEL_W = 3, 14
VALUE_W = INNER - (1 + ICON_W + 2 + LABEL_W + 2) - 1

ENTRIES = [
    ("❏", "PROJECT NAME", [PROJECT_NAME]),
    ("</>", "VERSION", [PROJECT_VERSION]),
    ("☺", "DEVELOPER", [DEVELOPER]),
    ("◎", "ROLE", [ROLE]),
    ("▦", "CREATED ON", [CREATED_ON]),
    ("≣", "DESCRIPTION", DESCRIPTION),
    ("⚙", "TECHNOLOGIES", [TECHNOLOGIES]),
]


def colorize_value(text):
    return "".join((rgb(MUTED) if ch == "|" else rgb(WHITE)) + ch for ch in text) + RESET


def box_top():
    title = " ".join("PROJECT INFORMATION")
    tab_w = len(title) + 2
    side = (BW - 4 - tab_w) // 2
    line1 = PADL + " " * (1 + side) + paint("╭" + "─" * tab_w + "╮", BORDER)
    line2 = (PADL + paint("╭" + "─" * side + "╯", BORDER)
             + paint(" " + title + " ", GOLD, True)
             + paint("╰" + "─" * side + "╮", BORDER))
    return [line1, line2]


def box_bottom():
    return PADL + paint("╰" + "─" * INNER + "╯", BORDER)


def box_separator():
    return (PADL + paint("│", BORDER) + " " + rgb(SEPARATOR) + "─" * (INNER - 2) + RESET
            + " " + paint("│", BORDER))


def entry_frame(icon, label, vlines, k):
    rows, left = [], k
    for i, value in enumerate(vlines):
        shown = value[:max(0, left)]
        left -= len(value)
        ic = paint(icon.ljust(ICON_W), GOLD, True) if i == 0 else " " * ICON_W
        lb = paint(label.ljust(LABEL_W), MUTED) if i == 0 else " " * LABEL_W
        body = (" " + ic + "  " + lb + "  " + colorize_value(shown)
                + " " * (VALUE_W - len(shown)) + " ")
        rows.append(PADL + paint("│", BORDER) + body + paint("│", BORDER))
    return rows


def animate_box():
    for line in box_top():
        out(line + "\n")
        flush()
    pause(0.15)
    for idx, (icon, label, vlines) in enumerate(ENTRIES):
        region = Region(len(vlines))
        total = sum(len(v) for v in vlines)
        for k in range(0, total + 1, 2):             # values are "typed"
            region.draw(entry_frame(icon, label, vlines, k))
            pause(0.012)
        region.draw(entry_frame(icon, label, vlines, total))
        if idx < len(ENTRIES) - 1:
            out(box_separator() + "\n")
        pause(0.07)
    out(box_bottom() + "\n")
    flush()


# =============================================================================
#  0) BOOT SEQUENCE  (typing effect + status checks + loading bar)
# =============================================================================
def type_text(text, speed=0.012):
    for ch in text:
        out(ch)
        pause(speed)
    out("\n")
    flush()


def boot_sequence():
    clear_screen()
    inner = 66
    out("\n")
    out(center(paint("╔" + "═" * inner + "╗", BLUE)) + "\n")
    out(center(paint("║", BLUE) + " " * inner + paint("║", BLUE)) + "\n")
    out(center(paint("║", BLUE) + paint("R I T U   R A J".center(inner), WHITE, True)
               + paint("║", BLUE)) + "\n")
    out(center(paint("║", BLUE) + paint(ROLE.center(inner), MUTED) + paint("║", BLUE)) + "\n")
    out(center(paint("║", BLUE) + " " * inner + paint("║", BLUE)) + "\n")
    out(center(paint("╚" + "═" * inner + "╝", BLUE)) + "\n\n")
    pause(0.3)

    type_text("  " + paint("WELCOME DEVELOPER", GOLD, True), 0.02)
    type_text("  " + paint("Code • Learn • Build • Improve • Repeat", MUTED), 0.012)
    out("\n")
    type_text("  " + paint("INITIALIZING PROJECT ENVIRONMENT...", BLUE, True), 0.015)
    out("\n")

    steps = [
        ("Starting Python runtime...", "Python runtime"),
        ("Loading data processing modules...", "Data processing"),
        ("Preparing machine learning environment...", "Machine learning"),
        ("Initializing AI components...", "Artificial intelligence"),
        ("Checking project configuration...", "Project configuration"),
    ]
    for doing, done in steps:
        out("\r  " + paint("›", GOLD) + " " + paint(doing, WHITE) + "\033[K")
        pause(0.22)
        out("\r  " + paint("✓", GREEN) + " " + paint(done.ljust(46), WHITE)
            + paint("[ OK ]", GREEN) + "\033[K\n")
    out("\n")

    type_text("  " + paint("BUILDING PROJECT ENVIRONMENT", GOLD), 0.012)
    width = 42
    for i in range(width + 1):
        filled = "".join(rgb(lerp(GOLD, AMBER, j / (width - 1))) + "█" for j in range(i))
        out("\r  " + paint("[", BORDER) + filled + paint("░" * (width - i), TRACK)
            + paint("]", BLUE) + " " + paint(f"{int(i / width * 100):3d}%", WHITE) + "\033[K")
        pause(0.02)
    out("\n")
    pause(0.5)


# =============================================================================
#  MAIN
# =============================================================================
def splash():
    clear_screen()
    animate_header()      # ring + hourglass, title, progress bar
    animate_eye()         # the eye opens
    out("\n")
    animate_headline()    # ALL EYES ON YOU
    animate_divider()
    out("\n")
    animate_box()         # PROJECT INFORMATION


def main():
    global SPEED
    args = sys.argv[1:]
    if "--fast" in args:
        SPEED = 0
    setup_terminal()
    columns = shutil.get_terminal_size((WIDTH, 40)).columns
    try:
        out("\033[?25l")  # hide cursor while animating
        if columns < WIDTH:
            out(paint(f"Tip: widen your terminal to at least {WIDTH} columns "
                      f"(now {columns}) for the best look.\n", AMBER))
            pause(1.8)
        if SPEED > 0 and "--no-boot" not in args:
            boot_sequence()
        splash()
    except KeyboardInterrupt:
        pass
    finally:
        out(RESET + "\033[?25h\n")
        flush()


if __name__ == "__main__":
    main()


Choose = input("please choose one unit from (ft / cm) : ")
Age = int(input("Enter your Age : "))
Height = float(input("enter your height in ft : "))
Picture = input("Do you want photo (Yes/No) : ")
Height_cm = 0
Total_price = 0
if Choose == "ft":
    Height_cm = (Height* 30.48)
else :
    pass

if Height_cm >120:
    print("You can ride.")
    if Age <12:
        Total_price += 5
    elif 12 <=Age <18:
        Total_price += 7
    elif 18 <= Age < 45:
        Total_price += 12
    else:
        Total_price +=0


if Picture == "Yes"or "yes" or "y" or"Y":
    Total_price += 3
else:
    pass

print(f"Height = {Height_cm}cm \nYour total price for a ride is : ${Total_price}")

