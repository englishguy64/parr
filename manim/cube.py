import itertools
import math

import numpy as np
from manim import *

# ---- parr color scheme (Source/parr/styles.css), light background ----
config.background_color = "#f5f7fa"
INK = "#222222"
BURGUNDY = "#7a1f3d"
WHITE = INK
GRAY_B = "#6b7280"
GRAY_D = "#9ca3af"
YELLOW = "#b8860b"
GREEN = "#2e7d5b"
RED = "#b91c1c"
TEAL = "#0f766e"
BLUE = "#475569"
ORANGE = "#a33a5c"
MAROON = BURGUNDY
Text.set_default(color=INK)

SCALE = 1.2
ELEV = math.radians(20)
CENTER = np.array([-3.4, 0.3, 0.0])
SECONDS_PER_REV = 24
REVS = 2

# camera direction (unit vector pointing from the cube toward the camera)
V = np.array([0.0, -math.cos(ELEV), math.sin(ELEV)])

CORNERS = [np.array([(i & 1) * 2 - 1, ((i >> 1) & 1) * 2 - 1, ((i >> 2) & 1) * 2 - 1], dtype=float)
           for i in range(8)]

AXES = "xyz"
FACE_COLORS = [RED, MAROON, GREEN, TEAL, BLUE, ORANGE]


def build_faces():
    faces = []
    for axis in range(3):
        for sign in (1, -1):
            idx = [i for i in range(8) if CORNERS[i][axis] == sign]
            u, w = [a for a in range(3) if a != axis]
            c = sum(CORNERS[i] for i in idx) / 4
            idx.sort(key=lambda i: math.atan2(CORNERS[i][w] - c[w], CORNERS[i][u] - c[u]))
            normal = np.zeros(3)
            normal[axis] = sign
            faces.append({"name": f"{'+' if sign > 0 else '-'}{AXES[axis].upper()}",
                          "idx": idx, "normal": normal})
    return faces


FACES = build_faces()
for f, col in zip(FACES, FACE_COLORS):
    f["color"] = col


def rot(p, a):
    c, s = math.cos(a), math.sin(a)
    return np.array([p[0] * c - p[1] * s, p[0] * s + p[1] * c, p[2]])


def to_screen(p):
    return CENTER + np.array([p[0], p[2] * math.cos(ELEV) + p[1] * math.sin(ELEV), 0]) * SCALE


class Cube(Scene):
    def construct(self):
        title = Text("Spinning cube: face normal · view direction", font_size=30, color=BURGUNDY).to_edge(UP, buff=0.25)
        self.add(title)

        angle = ValueTracker(0)
        a = lambda: angle.get_value() + 0.6

        # ---------- ruler showing the size ----------
        ruler_y = CENTER[1] - 2.15
        ruler = VGroup(
            Line([CENTER[0] - SCALE, ruler_y, 0], [CENTER[0] + SCALE, ruler_y, 0], color=YELLOW),
            Line([CENTER[0] - SCALE, ruler_y - 0.1, 0], [CENTER[0] - SCALE, ruler_y + 0.1, 0], color=YELLOW),
            Line([CENTER[0] + SCALE, ruler_y - 0.1, 0], [CENTER[0] + SCALE, ruler_y + 0.1, 0], color=YELLOW),
            Text("edge length = 2 units  (corners at ±1)", font_size=16, color=YELLOW)
            .move_to([CENTER[0], ruler_y - 0.3, 0]),
        )
        facts = Text("8 corners  |  6 faces  |  5 points per face (4 corners + centre)",
                     font_size=16, color=GRAY_B).move_to([CENTER[0], ruler_y - 0.65, 0])

        # ---------- cube drawn from the angle ----------
        def cube():
            ang = a()
            pts = [rot(c, ang) for c in CORNERS]
            order = sorted(FACES, key=lambda f: sum(np.dot(rot(f["normal"], ang), V) for _ in [0]))
            g = VGroup()
            for f in order:
                n = rot(f["normal"], ang)
                front = np.dot(n, V) > 0
                poly = Polygon(*[to_screen(pts[i]) for i in f["idx"]], color=f["color"],
                               stroke_width=3 if front else 1.2,
                               fill_color=f["color"], fill_opacity=0.35 if front else 0.07)
                g.add(poly)
            return g

        def points():
            ang = a()
            g = VGroup()
            center_scr = CENTER

            def label(txt, p, color, front):
                s = to_screen(p)
                d = s - center_scr
                d = d / (np.linalg.norm(d) + 1e-6)
                t = Text(txt, font_size=14, color=color if front else GRAY_D)
                t.move_to(s + d * 0.28)
                return t

            for i, c in enumerate(CORNERS):
                p = rot(c, ang)
                front = np.dot(p, V) > 0
                g.add(Dot(to_screen(p), radius=0.05, color=WHITE if front else GRAY_D))
                g.add(label(f"V{i}", p, WHITE, front))
            for f in FACES:
                p = rot(f["normal"], ang)
                front = np.dot(p, V) > 0
                g.add(Dot(to_screen(p), radius=0.045, color=f["color"] if front else GRAY_D))
                g.add(label(f"C{f['name']}", p, f["color"], front))
            return g

        cube_mob = always_redraw(cube)
        pts_mob = always_redraw(points)

        # ---------- right-hand panel ----------
        px = -0.2
        eq = Text("n · v  =  nx·vx + ny·vy + nz·vz  =  |n||v| cos θ", font_size=22).move_to([px + 3.6, 2.5, 0])
        eq.align_to([px, 0, 0], LEFT)
        defs = Text(f"n = outward face normal    v = camera direction = ({V[0]:.2f}, {V[1]:.2f}, {V[2]:.2f})",
                    font_size=15, color=GRAY_B).next_to(eq, DOWN, buff=0.12).align_to(eq, LEFT)
        rule = Text("n · v > 0  ->  face points toward the camera (visible)", font_size=15, color=GRAY_B)
        rule.next_to(defs, DOWN, buff=0.08).align_to(eq, LEFT)

        hdr_y = 1.2
        cols = [px, px + 0.9, px + 5.1]
        hdr = VGroup(*[Text(t, font_size=15, color=GRAY_B).move_to([x, hdr_y, 0], aligned_edge=LEFT)
                       for t, x in zip(["face", "5 vertices (4 corners + centre)", "n · v"], cols)])
        rows = VGroup()
        for r, f in enumerate(FACES):
            y = hdr_y - 0.5 * (r + 1)
            vtxt = "  ".join(f"V{i}" for i in f["idx"]) + f"  C{f['name']}"

            def make_row(f=f, y=y, vtxt=vtxt):
                n = rot(f["normal"], a())
                d = float(np.dot(n, V))
                col = GREEN if d > 0 else RED
                return VGroup(
                    Text(f["name"], font_size=20, color=f["color"]).move_to([cols[0], y, 0], aligned_edge=LEFT),
                    Text(vtxt, font_size=16).move_to([cols[1], y, 0], aligned_edge=LEFT),
                    Text(f"{d + 0.0:+.2f}", font_size=22, color=col).move_to([cols[2], y, 0], aligned_edge=LEFT),
                )
            rows.add(always_redraw(make_row))

        def worked():
            ang = a()
            best = max(FACES, key=lambda f: np.dot(rot(f["normal"], ang), V))
            n = rot(best["normal"], ang)
            d = float(np.dot(n, V))
            s = (f"Most visible face ({best['name']}):  n=({n[0]:+.2f}, {n[1]:+.2f}, {n[2]:+.2f})\n"
                 f"n·v = ({n[0]:+.2f})({V[0]:+.2f}) + ({n[1]:+.2f})({V[1]:+.2f}) + ({n[2]:+.2f})({V[2]:+.2f}) = {d:+.2f}")
            return Text(s, font_size=16, color=best["color"], line_spacing=0.9).move_to(
                [px, -2.55, 0], aligned_edge=LEFT)

        worked_mob = always_redraw(worked)

        self.play(FadeIn(ruler), FadeIn(facts))
        self.add(cube_mob, pts_mob)
        self.wait(1)
        self.play(FadeIn(eq), FadeIn(defs), FadeIn(rule), FadeIn(hdr))
        self.add(rows, worked_mob)
        self.wait(1)

        # slow spin about the vertical axis
        self.play(angle.animate.set_value(TAU * REVS), run_time=SECONDS_PER_REV * REVS, rate_func=linear)
        self.wait(1)
