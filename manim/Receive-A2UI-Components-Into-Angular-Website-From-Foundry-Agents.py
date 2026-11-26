import re
from manim import *

# ---- parr color scheme (from Source/parr/styles.css) ----
BG = "#f5f7fa"
INK = "#222222"
MUTED = "#6b7280"
LINE = "#9ca3af"
BURGUNDY = "#7a1f3d"
GOLD = "#b8860b"
OK_C = "#2e7d5b"

config.background_color = BG
Text.set_default(font="Arial", color=INK)

SITE_C = "#7a1f3d"      # Angular website
API_C = "#0369a1"       # C# Backend API
FOUNDRY_C = "#b8860b"   # Foundry and its agents
A2UI_C = "#0f766e"      # A2UI messages
SLOW = 1.6              # slows every animation and pause
STATUS_Y = -3.0         # captions sit above the video player controls

LANE1, LANE2 = 1.0, -0.7    # response lane, streaming lane


def tc(text):
    """Capitalise the first letter of each word."""
    return re.sub(r"(^|[\s(\-])([a-z])", lambda m: m.group(1) + m.group(2).upper(), text)


def panel(title, sub, color, center, width, height, fill=0.07):
    """A rounded panel with a heading at the top."""
    frame = RoundedRectangle(width=width, height=height, corner_radius=0.15, color=color, stroke_width=3,
                             fill_color=color, fill_opacity=fill).move_to(center)
    head = Text(tc(title), font_size=17, color=color, weight=BOLD).move_to(frame.get_top() + DOWN * 0.32)
    parts = [frame, head]
    if sub:
        parts.append(Text(tc(sub), font_size=11, color=MUTED).next_to(head, DOWN, buff=0.06))
    return VGroup(*parts)


def box(title, sub, color, center, width, height):
    shape = RoundedRectangle(width=width, height=height, corner_radius=0.1, color=color, fill_color=color,
                             fill_opacity=0.14, stroke_width=3).move_to(center)
    t = Text(tc(title), font_size=15, color=color, weight=BOLD)
    s = Text(sub, font_size=11, color=MUTED)
    return VGroup(shape, VGroup(t, s).arrange(DOWN, buff=0.05).move_to(shape))


def agent_box(line1, line2, name, color, center):
    """Foundry agent symbol: what the agent returns and over which protocol, then its name."""
    shape = RoundedRectangle(width=3.1, height=1.3, corner_radius=0.1, color=color, fill_color=color,
                             fill_opacity=0.14, stroke_width=3).move_to(center)
    a = Text(line1, font_size=13, color=color, weight=BOLD)
    b = Text(line2, font_size=13, color=color, weight=BOLD)
    n = Text(name, font_size=11, color=MUTED)
    return VGroup(shape, VGroup(a, b, n).arrange(DOWN, buff=0.07).move_to(shape))


def arrow(a, b, color=LINE):
    return Arrow(a, b, buff=0, color=color, stroke_width=2.5, tip_length=0.15, max_tip_length_to_length_ratio=0.3)


def safe_text(s, **kw):
    """Text() fails on blank strings, so a blank becomes an invisible letter that keeps the height."""
    if s.strip():
        return Text(s, **kw)
    height = Text("Ag", **kw).height
    return Rectangle(width=0.02, height=height, stroke_width=0, fill_opacity=0)


def token(label, color, width=1.0):
    shape = RoundedRectangle(width=width, height=0.28, corner_radius=0.07, color=color, fill_color=WHITE,
                             fill_opacity=1, stroke_width=2)
    return VGroup(shape, Text(label, font_size=9, color=color).move_to(shape))


def code_panel(heading, color, lines, center, width, font_size=12, highlight=None):
    """White panel with monospace code. Leading spaces are kept. Returns (panel, line_mobjects)."""
    char_w = Text("x" * 20, font="Consolas", font_size=font_size).width / 20
    rows = VGroup(*[safe_text(l.strip(), font="Consolas", font_size=font_size, color=INK) for l in lines])
    rows.arrange(DOWN, buff=0.07, aligned_edge=LEFT)
    for row, l in zip(rows, lines):
        row.shift(RIGHT * char_w * (len(l) - len(l.lstrip())))
    head = Text(tc(heading), font_size=14, color=color, weight=BOLD)
    height = rows.height + head.height + 0.75
    frame = RoundedRectangle(width=width, height=height, corner_radius=0.12, color=color, stroke_width=3,
                             fill_color=WHITE, fill_opacity=1).move_to(center)
    head.move_to(frame.get_top() + DOWN * 0.3)
    rows.next_to(head, DOWN, buff=0.2).shift(RIGHT * (frame.get_left()[0] + 0.25 - rows.get_left()[0]))
    return VGroup(frame, head, rows), list(rows)


class ReceiveA2UI(Scene):
    def play(self, *args, **kwargs):
        kwargs["run_time"] = kwargs.get("run_time", 1.0) * SLOW
        super().play(*args, **kwargs)

    def wait(self, duration=1.0, **kwargs):
        super().wait(duration * SLOW, **kwargs)

    def construct(self):
        title = Text("Receive A2UI Components Into Angular Website From Foundry Agents", font_size=26,
                     color=BURGUNDY).to_edge(UP, buff=0.2)
        if title.width > 12.6:
            title.scale_to_fit_width(12.6)
        self.add(title)
        status = Text("A simple flow: Angular website, C# Backend API and two Foundry agents",
                      font_size=20).move_to([0, STATUS_Y, 0])
        self.add(status)

        def say(msg, color=INK):
            status.become(Text(msg, font_size=20, color=color).move_to([0, STATUS_Y, 0]))

        # =====================================================================
        # The three parts
        # =====================================================================
        site = panel("Angular Website", "A2UI Renderer", SITE_C, [-5.2, 0.4, 0], 3.0, 3.0)
        api = panel("C# Backend API", "ASP.NET, .NET 10", API_C, [-0.4, 0.3, 0], 3.0, 3.2)
        foundry = panel("Microsoft Foundry", "Two Hosted Agents, C#", FOUNDRY_C, [5.3, 0.4, 0], 3.4, 3.9)
        agent1 = agent_box("Agent returns data", "via Responses protocol", "a2ui-response", FOUNDRY_C, [5.3, LANE1, 0])
        agent2 = agent_box("Agent returns data", "via AG-UI protocol", "a2ui-stream", FOUNDRY_C, [5.3, LANE2, 0])

        # the mini surface inside the website: a card with a heading and lines of text
        card = RoundedRectangle(width=2.5, height=1.55, corner_radius=0.08, color=LINE, stroke_width=2,
                                fill_color=WHITE, fill_opacity=1).move_to([-5.2, -0.3, 0])
        card_head = Rectangle(width=1.5, height=0.14, stroke_width=0, fill_color=INK, fill_opacity=0.8)
        card_head.move_to(card.get_top() + DOWN * 0.25 + LEFT * 0.4)
        bars = [Rectangle(width=2.1 - 0.15 * (i % 2) * 3, height=0.1, stroke_width=0, fill_color=A2UI_C,
                          fill_opacity=0.55).move_to(card.get_top() + DOWN * (0.55 + i * 0.22)).align_to(card, LEFT).shift(RIGHT * 0.2)
                for i in range(4)]
        status_bar = Rectangle(width=0.9, height=0.08, stroke_width=0, fill_color=MUTED, fill_opacity=0.6)
        status_bar.move_to(card.get_bottom() + UP * 0.18).align_to(card, LEFT).shift(RIGHT * 0.2)
        surface = VGroup(card, card_head, *bars, status_bar)

        translator1 = box("Responses To A2UI", "Translator", A2UI_C, [-0.4, 0.5, 0], 2.6, 0.8)
        translator2 = box("AG-UI To A2UI", "Translator", A2UI_C, [-0.4, -0.7, 0], 2.6, 0.8)

        self.play(FadeIn(site), FadeIn(api), run_time=1.0)
        self.play(FadeIn(foundry), FadeIn(agent1), FadeIn(agent2), run_time=1.0)
        say("Angular renders A2UI components, the C# Backend API talks to the Foundry agents", INK)
        self.wait(3.0)
        self.play(FadeIn(translator1), FadeIn(translator2), run_time=0.8)
        say("The Backend API has two translators, one per protocol, each producing A2UI components", A2UI_C)
        self.wait(3.0)

        # lane geometry
        def lane_pts(lane):
            return {"site": [-3.7, lane, 0], "api_l": [-1.9, lane, 0], "api_r": [1.1, lane, 0], "ag_l": [3.9, lane, 0]}

        # =====================================================================
        # Flow 1: Response
        # =====================================================================
        say("Flow 1: The agent that returns data via the Responses protocol. The user asks a question", SITE_C)
        L = lane_pts(LANE1)
        req1 = arrow([-3.7, LANE1 + 0.12, 0], [-1.9, LANE1 + 0.12, 0], SITE_C)
        req1_lbl = Text("POST prompt", font_size=10, color=SITE_C).move_to([-2.8, LANE1 + 0.38, 0])
        self.play(FadeIn(req1), FadeIn(req1_lbl), run_time=0.8)
        prompt_tok = token("prompt", SITE_C, 0.8).move_to([-3.7, LANE1 + 0.12, 0])
        self.play(FadeIn(prompt_tok), run_time=0.3)
        self.play(prompt_tok.animate.move_to([-0.4, LANE1 + 0.12, 0]), run_time=1.2)
        self.wait(1.0)

        say("The Backend API calls the agent and receives the answer via the Responses protocol", API_C)
        call1 = arrow([1.1, LANE1 + 0.12, 0], [3.75, LANE1 + 0.12, 0], API_C)
        call1_lbl = Text("Responses protocol", font_size=10, color=API_C).move_to([2.5, LANE1 + 0.38, 0])
        self.play(FadeIn(call1), FadeIn(call1_lbl), run_time=0.8)
        self.play(prompt_tok.animate.move_to([5.3, LANE1 + 0.12, 0]), run_time=1.4)
        self.wait(1.0)

        say("The agent answers once, with one complete block of text", FOUNDRY_C)
        text_tok = token("complete text", FOUNDRY_C, 1.3).move_to([5.3, LANE1 - 0.12, 0])
        back1 = arrow([3.75, LANE1 - 0.12, 0], [1.1, LANE1 - 0.12, 0], FOUNDRY_C)
        self.play(FadeOut(prompt_tok), FadeIn(text_tok), FadeIn(back1), run_time=0.8)
        self.play(text_tok.animate.move_to([0.4, LANE1 - 0.12, 0]).scale(0.85), run_time=1.5)
        self.wait(1.0)

        say("The Responses translator turns the text into three A2UI messages", A2UI_C)
        self.play(text_tok.animate.move_to(translator1.get_center()), run_time=0.8)
        self.play(FadeOut(text_tok), Indicate(translator1[0], color=A2UI_C, scale_factor=1.08), run_time=1.0)
        msgs = [token(n, A2UI_C, 1.25) for n in ("createSurface", "updateComponents", "updateDataModel")]
        msg_array = VGroup(*msgs).arrange(DOWN, buff=0.06).move_to([2.4, -0.2, 0])
        self.play(FadeIn(msg_array, shift=DOWN * 0.1), run_time=1.0)
        self.wait(2.0)

        say("One JSON array holding all three messages goes back to the website", A2UI_C)
        ret1 = arrow([-1.9, LANE1 - 0.12, 0], [-3.7, LANE1 - 0.12, 0], A2UI_C)
        self.play(FadeIn(ret1), run_time=0.6)
        self.play(msg_array.animate.move_to([-4.2, LANE1 - 0.12, 0]).scale(0.7), run_time=1.6)
        self.play(FadeOut(msg_array), FadeIn(surface), run_time=1.0)
        say("The Angular A2UI renderer builds the card: heading, answer text and status", SITE_C)
        self.wait(4.0)

        self.play(FadeOut(VGroup(req1, req1_lbl, call1, call1_lbl, back1, ret1)), run_time=0.8)

        # =====================================================================
        # Flow 2: Streaming
        # =====================================================================
        say("Flow 2: The agent that returns data via the AG-UI protocol", SITE_C)
        self.play(FadeOut(surface), run_time=0.8)
        self.wait(1.5)
        req2 = arrow([-3.7, LANE2 + 0.12, 0], [-1.9, LANE2 + 0.12, 0], SITE_C)
        call2 = arrow([1.1, LANE2 + 0.12, 0], [3.75, LANE2 + 0.12, 0], API_C)
        back2 = arrow([3.75, LANE2 - 0.12, 0], [1.1, LANE2 - 0.12, 0], FOUNDRY_C)
        ret2 = arrow([-1.9, LANE2 - 0.12, 0], [-3.7, LANE2 - 0.12, 0], A2UI_C)
        ag_lbl = VGroup(Text("A2UI messages", font_size=10, color=A2UI_C).move_to([-2.8, LANE2 - 0.38, 0]),
                        Text("AG-UI protocol", font_size=10, color=FOUNDRY_C).move_to([2.5, LANE2 - 0.38, 0]))
        self.play(FadeIn(req2), FadeIn(call2), FadeIn(back2), FadeIn(ret2), FadeIn(ag_lbl), run_time=1.0)

        say("The AG-UI translator starts with the surface and its components, sent once", A2UI_C)
        first = [token("createSurface", A2UI_C, 1.25), token("updateComponents", A2UI_C, 1.25)]
        for m in first:
            m.move_to(translator2.get_center())
        self.play(FadeIn(first[0]), run_time=0.4)
        self.play(first[0].animate.move_to([-4.2, LANE2 - 0.12, 0]).scale(0.7), run_time=1.2)
        self.play(FadeIn(first[1]), run_time=0.4)
        self.play(first[1].animate.move_to([-4.2, LANE2 - 0.12, 0]).scale(0.7), run_time=1.2)
        self.play(FadeOut(first[0]), FadeOut(first[1]), FadeIn(card), FadeIn(card_head), FadeIn(status_bar), run_time=0.8)
        self.wait(2.0)

        say("The agent now sends AG-UI text events as it is written, small pieces called deltas", FOUNDRY_C)
        self.wait(2.5)
        words = ["Start", "with", "a", "calm", "walk."]
        for i, w in enumerate(words):
            delta = token(w, FOUNDRY_C, 0.75).move_to([5.3, LANE2 - 0.12, 0])
            self.play(FadeIn(delta), run_time=0.25)
            self.play(delta.animate.move_to([0.8, LANE2 - 0.12, 0]), run_time=0.7)
            self.play(delta.animate.move_to(translator2.get_center()), run_time=0.4)
            self.play(FadeOut(delta), Indicate(translator2[0], color=A2UI_C, scale_factor=1.05), run_time=0.4)
            msg = token("updateDataModel", A2UI_C, 1.25).move_to(translator2.get_center())
            self.play(FadeIn(msg), run_time=0.2)
            self.play(msg.animate.move_to([-4.2, LANE2 - 0.12, 0]).scale(0.7), run_time=0.8)
            self.play(FadeOut(msg), FadeIn(bars[min(i, 3)]) if i < 4 else Indicate(bars[3], color=A2UI_C), run_time=0.4)
            if i == 0:
                say("The AG-UI translator turns each text delta into one A2UI updateDataModel message", A2UI_C)
        self.wait(2.0)
        say("The answer grows on screen while the agent is still writing: AG-UI carries the text, A2UI describes the UI", SITE_C)
        self.wait(4.0)

        self.play(FadeOut(VGroup(req2, call2, back2, ret2, ag_lbl, surface, translator1, translator2)), run_time=1.0)
        self.play(FadeOut(VGroup(site, api, foundry, agent1, agent2)), run_time=1.0)

        # =====================================================================
        # The detailed A2UI payload
        # =====================================================================
        say("Now the detailed A2UI payload that goes back to the Angular website", A2UI_C)
        self.wait(2.0)

        JSON_C = [-3.45, 0.1, 0]   # left panel centre
        W_LEFT = 6.8

        # ---- message 1: createSurface ----
        m1, m1_lines = code_panel("Message 1: createSurface", A2UI_C, [
            "{",
            '  "version": "v0.9",',
            '  "createSurface": {',
            '    "surfaceId": "stream-1",',
            '    "catalogId": "https://a2ui.org/.../basic/catalog.json"',
            "  }",
            "}"], JSON_C, W_LEFT)
        right_empty = RoundedRectangle(width=5.9, height=4.6, corner_radius=0.12, color=LINE, stroke_width=3,
                                       fill_opacity=0).move_to([3.7, 0.1, 0])
        right_lbl = Text("Surface: stream-1 (empty)", font_size=14, color=MUTED).move_to(right_empty)
        self.play(FadeIn(m1), FadeIn(right_empty), FadeIn(right_lbl), run_time=1.0)
        say("createSurface: makes an empty surface and names the catalog of components it may use", A2UI_C)
        hl = SurroundingRectangle(VGroup(*m1_lines[3:5]), color=A2UI_C, buff=0.05, fill_color=A2UI_C, fill_opacity=0.12)
        self.play(FadeIn(hl), run_time=0.6)
        self.wait(6.0)
        self.play(FadeOut(hl), run_time=0.4)

        # ---- message 2: updateComponents ----
        m2a, m2a_lines = code_panel("Message 2: updateComponents (layout)", A2UI_C, [
            "{ \"version\": \"v0.9\",",
            "  \"updateComponents\": {",
            "    \"surfaceId\": \"stream-1\",",
            "    \"components\": [",
            "      { \"id\": \"root\", \"component\": \"Column\",",
            "        \"children\": [\"card\"] },",
            "      { \"id\": \"card\", \"component\": \"Card\",",
            "        \"child\": \"body\" },",
            "      { \"id\": \"body\", \"component\": \"Column\",",
            "        \"children\": [\"heading\", \"agent\", \"answer\",",
            "                     \"divider\", \"status\"] },",
            "      ..."], JSON_C, W_LEFT)
        self.play(FadeOut(m1), run_time=0.6)
        self.play(FadeIn(m2a), run_time=0.8)
        say("updateComponents: a flat list. Components point to their children by id", A2UI_C)
        self.wait(2.0)

        # component tree rows (right side)
        tree_defs = [
            (0, "Column", "root", SITE_C), (1, "Card", "card", SITE_C), (2, "Column", "body", SITE_C),
            (3, "Text h3", "heading", A2UI_C), (3, "Text caption", "agent", A2UI_C),
            (3, "Text body  ← /answer", "answer", A2UI_C), (3, "Divider", "divider", A2UI_C),
            (3, "Text caption  ← /status", "status", A2UI_C)]
        tree_rows = []
        for i, (indent, kind, cid, col) in enumerate(tree_defs):
            t = Text(f"{kind}    id: {cid}", font_size=13, color=col)
            t.move_to([1.1 + indent * 0.45, 2.0 - i * 0.48, 0]).align_to([1.1 + indent * 0.45, 0, 0], LEFT)
            tree_rows.append(t)
        tree_box = RoundedRectangle(width=5.9, height=4.6, corner_radius=0.12, color=A2UI_C, stroke_width=3,
                                    fill_opacity=0).move_to([3.7, 0.1, 0])
        tree_title = Text("Component Tree The Renderer Builds", font_size=14, color=A2UI_C, weight=BOLD).move_to([3.7, 2.15, 0])
        # shift tree rows down a little under the title
        for r in tree_rows:
            r.shift(DOWN * 0.45)
        self.play(FadeOut(right_empty), FadeOut(right_lbl), FadeIn(tree_box), FadeIn(tree_title), run_time=0.6)
        for r in tree_rows[:3]:
            self.play(FadeIn(r, shift=RIGHT * 0.2), run_time=0.7)
        self.wait(2.5)

        m2b, m2b_lines = code_panel("Message 2: updateComponents (text)", A2UI_C, [
            "      { \"id\": \"heading\", \"component\": \"Text\",",
            "        \"variant\": \"h3\", \"text\": \"Streamed answer\" },",
            "      { \"id\": \"answer\", \"component\": \"Text\",",
            "        \"variant\": \"body\",",
            "        \"text\": { \"path\": \"/answer\" } },",
            "      { \"id\": \"status\", \"component\": \"Text\",",
            "        \"variant\": \"caption\",",
            "        \"text\": { \"path\": \"/status\" } },",
            "      ... agent, divider",
            "    ]",
            "  }",
            "}"], JSON_C, W_LEFT)
        self.play(FadeOut(m2a), run_time=0.6)
        self.play(FadeIn(m2b), run_time=0.8)
        for r in tree_rows[3:]:
            self.play(FadeIn(r, shift=RIGHT * 0.2), run_time=0.6)
        say("A path such as /answer binds a component to data: when the data changes, the text redraws", A2UI_C)
        hl = SurroundingRectangle(VGroup(*m2b_lines[4:5]), color=GOLD, buff=0.05, fill_color=GOLD, fill_opacity=0.15)
        self.play(FadeIn(hl), run_time=0.6)
        self.wait(7.0)
        self.play(FadeOut(hl), run_time=0.4)

        # ---- message 3: updateDataModel, repeated as the answer grows ----
        def data_lines(value):
            return ["{ \"version\": \"v0.9\",",
                    "  \"updateDataModel\": {",
                    "    \"surfaceId\": \"stream-1\",",
                    "    \"path\": \"/answer\",",
                    f"    \"value\": \"{value}\"",
                    "  }",
                    "}"]

        def preview(answer_text, status_text):
            card_f = RoundedRectangle(width=5.4, height=2.5, corner_radius=0.1, color=LINE, stroke_width=2,
                                      fill_color=WHITE, fill_opacity=1).move_to([3.7, 1.15, 0])
            h = Text("Streamed answer from the Streaming agent", font_size=15, weight=BOLD).move_to(
                card_f.get_top() + DOWN * 0.35).align_to(card_f, LEFT).shift(RIGHT * 0.25)
            a = Text("Foundry agent: a2ui-stream", font_size=10, color=MUTED).next_to(h, DOWN, buff=0.12).align_to(h, LEFT)
            ans = safe_text(answer_text, font_size=15).next_to(a, DOWN, buff=0.2).align_to(h, LEFT)
            div = Line(card_f.get_left() + RIGHT * 0.25 + DOWN * 0.45, card_f.get_right() + LEFT * 0.25 + DOWN * 0.45,
                       color=LINE, stroke_width=1.5).shift(DOWN * 0.0)
            div.move_to(card_f.get_bottom() + UP * 0.6)
            st = Text(status_text, font_size=10, color=MUTED).move_to(card_f.get_bottom() + UP * 0.3).align_to(h, LEFT)
            return VGroup(card_f, h, a, ans, div, st)

        def model_box(answer_text, status_text):
            f = RoundedRectangle(width=5.4, height=1.55, corner_radius=0.1, color=GOLD, stroke_width=2.5,
                                 fill_color=GOLD, fill_opacity=0.08).move_to([3.7, -1.6, 0])
            t = Text("Data Model (/)", font_size=12, color=GOLD, weight=BOLD).move_to(f.get_top() + DOWN * 0.25).align_to(f, LEFT).shift(RIGHT * 0.25)
            l1 = Text(f"answer:  \"{answer_text}\"", font="Consolas", font_size=12).next_to(t, DOWN, buff=0.2).align_to(t, LEFT)
            l2 = Text(f"status:  \"{status_text}\"", font="Consolas", font_size=12).next_to(l1, DOWN, buff=0.12).align_to(t, LEFT)
            return VGroup(f, t, l1, l2)

        m3, _ = code_panel("Message 3: updateDataModel", A2UI_C, data_lines(""), JSON_C, W_LEFT)
        pv = preview("", "Streaming...")
        mb = model_box("", "Streaming...")
        self.play(FadeOut(m2b), *[FadeOut(r) for r in tree_rows], FadeOut(tree_box), FadeOut(tree_title), run_time=0.8)
        self.play(FadeIn(m3), FadeIn(pv), FadeIn(mb), run_time=1.0)
        say("updateDataModel: sets the data. The card is already on screen, only its text changes", A2UI_C)
        self.wait(4.0)

        steps = ["Start", "Start with a", "Start with a calm walk."]
        say("Each AG-UI text delta sends one more updateDataModel to the /answer path", A2UI_C)
        for value in steps:
            new_m3, _ = code_panel("Message 3: updateDataModel", A2UI_C, data_lines(value), JSON_C, W_LEFT)
            new_pv = preview(value, "Streaming...")
            new_mb = model_box(value, "Streaming...")
            self.play(Transform(m3, new_m3), Transform(pv, new_pv), Transform(mb, new_mb), run_time=0.8)
            self.wait(2.2)

        done_m = ["{ \"version\": \"v0.9\",", "  \"updateDataModel\": {", "    \"surfaceId\": \"stream-1\",",
                  "    \"path\": \"/status\",", "    \"value\": \"Complete in 2.3 s\"", "  }", "}"]
        new_m3, _ = code_panel("Message 4: updateDataModel", A2UI_C, done_m, JSON_C, W_LEFT)
        new_pv = preview("Start with a calm walk.", "Complete in 2.3 s")
        new_mb = model_box("Start with a calm walk.", "Complete in 2.3 s")
        say("A last updateDataModel to the /status path marks the answer as complete", OK_C)
        self.play(Transform(m3, new_m3), Transform(pv, new_pv), Transform(mb, new_mb), run_time=0.8)
        self.wait(5.0)
        say("A2UI: the agent side describes the UI as data, the Angular website renders it as components", BURGUNDY)
        self.wait(6.0)
