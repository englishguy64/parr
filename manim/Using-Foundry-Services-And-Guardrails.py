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

FOUNDRY_C = GOLD
GUARD_C = "#9f1239"
PARTNER_C = "#1f2937"
AGENT_C = "#a33a5c"
WORKFLOW_C = "#b45309"
HOSTED_C = "#6d4c9f"
MODEL_C = "#0369a1"
TOOL_C = "#1d4ed8"
KNOW_C = "#0f766e"
DOC_C = "#b45309"
TRANS_C = "#7c3aed"
SPEECH_C = "#be185d"
LANG_C = "#0e7490"
MEM_C = "#475569"

AGENT_X, BAND_X, SERVICE_X = -4.5, -0.6, 4.4


def box(title, color, width, center, height=0.7, font_size=15, subtitle=None):
    shape = RoundedRectangle(width=width, height=height, corner_radius=0.1, color=color,
                             fill_color=color, fill_opacity=0.14, stroke_width=3).move_to(center)
    if subtitle:
        t = Text(title, font_size=font_size, color=color)
        s = Text(subtitle, font_size=11, color=MUTED)
        label = VGroup(t, s).arrange(DOWN, buff=0.05).move_to(shape)
    else:
        label = Text(title, font_size=font_size, color=color).move_to(shape)
    return VGroup(shape, label)


def chip(label, color, center, width=2.1):
    shape = RoundedRectangle(width=width, height=0.34, corner_radius=0.08, color=color,
                             fill_color=WHITE, fill_opacity=1, stroke_width=2).move_to(center)
    return VGroup(shape, Text(label, font_size=12, color=INK).move_to(shape))


def route(points):
    path = VMobject()
    path.set_points_as_corners([np.array(p) for p in points])
    return path


class FoundryAgentsGuardrails(Scene):
    def construct(self):
        title = Text("Using Foundry Services and Guardrails", font_size=26,
                     color=BURGUNDY).to_edge(UP, buff=0.25)
        self.add(title)

        status = Text("Every agent runs inside one Foundry resource", font_size=22).to_edge(DOWN, buff=0.25)
        self.add(status)

        def say(msg, color=INK):
            status.become(Text(msg, font_size=22, color=color).to_edge(DOWN, buff=0.25))

        # ---------- Foundry: the single main symbol ----------
        f_box = RoundedRectangle(width=12.4, height=5.9, corner_radius=0.25, color=FOUNDRY_C, stroke_width=4,
                                 fill_color=FOUNDRY_C, fill_opacity=0.07).move_to([0, -0.15, 0])
        f_title = Text("Microsoft Foundry", font_size=24, color=FOUNDRY_C, weight=BOLD)
        f_title.move_to(f_box.get_top() + DOWN * 0.3)
        foundry = VGroup(f_box, f_title)

        # ---------- agents ----------
        agents = {
            "support": box("Support Agent", AGENT_C, 2.7, [AGENT_X, 1.65, 0], height=0.85, subtitle="Prompt agent"),
            "onboard": box("Onboarding Agent", WORKFLOW_C, 2.7, [AGENT_X, 0.5, 0], height=0.85,
                           subtitle="Workflow agent"),
            "research": box("Research Agent", HOSTED_C, 2.7, [AGENT_X, -0.65, 0], height=0.85,
                            subtitle="Hosted agent"),
            "voice": box("Voice Agent", SPEECH_C, 2.7, [AGENT_X, -1.8, 0], height=0.85, subtitle="Prompt agent"),
        }

        # ---------- guardrails band ----------
        band = RoundedRectangle(width=2.6, height=4.3, corner_radius=0.15, color=GUARD_C, stroke_width=3,
                                fill_color=GUARD_C, fill_opacity=0.10).move_to([BAND_X, -0.15, 0])
        g_title = Text("Guardrails", font_size=17, color=GUARD_C).move_to(band.get_top() + DOWN * 0.28)
        guard_names = ["Content Safety", "Custom Blocklists", "Prompt Shields", "Groundedness", "PII Detection",
                       "Protected Material", "3rd-Party Security"]
        guards = {n: chip(n, PARTNER_C if n == "3rd-Party Security" else GUARD_C, [BAND_X, 1.25 - i * 0.52, 0])
                  for i, n in enumerate(guard_names)}
        shield = VGroup(
            Polygon([-0.17, 0.17, 0], [0.17, 0.17, 0], [0.17, -0.02, 0], [0, -0.2, 0], [-0.17, -0.02, 0],
                    color=GUARD_C, fill_color=GUARD_C, fill_opacity=1, stroke_width=1)
        ).next_to(g_title, LEFT, buff=0.1)
        guardrails = VGroup(band, g_title, shield, *guards.values())

        # ---------- services ----------
        svc_defs = [
            ("models", "Models", MODEL_C, "Model deployments"),
            ("trans", "Translator", TRANS_C, "Text and document translation"),
            ("doc", "Document Intelligence", DOC_C, "Prebuilt and custom analyzers"),
            ("speech", "Speech", SPEECH_C, "Speech to text, text to speech"),
            ("lang", "Language", LANG_C, "Entities, sentiment, summaries"),
            ("know", "Knowledge", KNOW_C, "Foundry IQ and search"),
            ("tools", "Toolbox", TOOL_C, "One MCP endpoint"),
            ("memory", "Memory", MEM_C, "Long term agent memory"),
        ]
        svc = {k: box(t, c, 3.1, [SERVICE_X, 1.8 - i * 0.56, 0], height=0.5, font_size=14, subtitle=sub)
               for i, (k, t, c, sub) in enumerate(svc_defs)}

        # Document Intelligence prebuilt analyzers, shown while the Onboarding Agent uses it
        prebuilt = [("Invoice", "prebuilt-invoice"), ("Receipt", "prebuilt-receipt"),
                    ("ID document", "prebuilt-idDocument"), ("Business card", "prebuilt-businessCard"),
                    ("Tax form (W-2)", "prebuilt-tax.us.w2"), ("Layout and Read", "prebuilt-layout")]
        p_box = RoundedRectangle(width=3.5, height=4.6, corner_radius=0.12, color=DOC_C, stroke_width=3,
                                 fill_color=WHITE, fill_opacity=1).move_to([SERVICE_X, -0.1, 0])
        p_title = Text("Document Intelligence", font_size=15, color=DOC_C).move_to(p_box.get_top() + DOWN * 0.3)
        p_sub = Text("Prebuilt analyzers", font_size=12, color=MUTED).next_to(p_title, DOWN, buff=0.06)
        p_rows = VGroup(*[
            VGroup(Text(n, font_size=14, color=DOC_C),
                   Text(m, font_size=11, color=MUTED)).arrange(DOWN, buff=0.04, aligned_edge=LEFT)
            for n, m in prebuilt]).arrange(DOWN, buff=0.22, aligned_edge=LEFT)
        p_rows.move_to(p_box.get_center() + DOWN * 0.3).align_to(p_box, LEFT).shift(RIGHT * 0.35)
        panel = VGroup(p_box, p_title, p_sub, p_rows)

        # Third-party security integration examples, shown while the Voice Agent is inspected
        partners = [("Palo Alto Networks", "Prisma AIRS"), ("Zenity", "Agent security partner")]
        steps = ["Enabled under Guardrails, Integrations tab", "Bring your own license (BYOL)",
                 "Endpoint and API key held in Key Vault", "Prompts and responses go to the partner",
                 "Same region as the partner endpoint"]
        t_box = RoundedRectangle(width=3.5, height=4.6, corner_radius=0.12, color=PARTNER_C, stroke_width=3,
                                 fill_color=WHITE, fill_opacity=1).move_to([SERVICE_X, -0.1, 0])
        t_title = Text("3rd-Party Security", font_size=15, color=PARTNER_C).move_to(t_box.get_top() + DOWN * 0.3)
        t_sub = Text("Partner integrations", font_size=12, color=MUTED).next_to(t_title, DOWN, buff=0.06)
        t_partners = VGroup(*[
            VGroup(Text(n, font_size=14, color=PARTNER_C),
                   Text(m, font_size=11, color=MUTED)).arrange(DOWN, buff=0.04, aligned_edge=LEFT)
            for n, m in partners]).arrange(DOWN, buff=0.2, aligned_edge=LEFT)
        t_steps = VGroup(*[Text("- " + x, font_size=11, color=INK) for x in steps]).arrange(
            DOWN, buff=0.16, aligned_edge=LEFT)
        t_body = VGroup(t_partners, t_steps).arrange(DOWN, buff=0.35, aligned_edge=LEFT)
        t_body.move_to(t_box.get_center() + DOWN * 0.3).align_to(t_box, LEFT).shift(RIGHT * 0.3)
        partner_panel = VGroup(t_box, t_title, t_sub, t_body)

        # ---------- build ----------
        self.play(FadeIn(foundry), run_time=1.0)
        self.play(*[FadeIn(a, shift=RIGHT * 0.2) for a in agents.values()], run_time=1.2)
        say("Several agents, each of a different type")
        self.wait(0.8)
        self.play(*[FadeIn(s, shift=LEFT * 0.2) for s in svc.values()], run_time=1.2)
        say("Agents use different Foundry services and tools", MODEL_C)
        self.wait(0.8)
        self.play(FadeIn(guardrails), run_time=1.2)
        say("Guardrails sit between every agent and every service", GUARD_C)
        self.wait(1.0)

        # ---------- wiring ----------
        def agent_pt(k):
            return agents[k][0].get_right()

        def svc_pt(k):
            return svc[k][0].get_left()

        wires = []
        visible = []
        for a_key, s_key in [("support", "trans"), ("onboard", "doc"), ("research", "lang"), ("voice", "speech")]:
            a, s = agent_pt(a_key), svc_pt(s_key)
            b_l = np.array([band.get_left()[0], a[1], 0])
            b_r = np.array([band.get_right()[0], s[1], 0])
            wires.append(route([a, b_l, b_r, s]))
            visible.append(Line(a, b_l, color=LINE, stroke_width=2))
            visible.append(Line(b_r, s, color=LINE, stroke_width=2))
        self.play(*[Create(v) for v in visible], run_time=1.0)

        def flow(wire, color, guard_name, text, text_color):
            dot = Dot(wire.get_start(), radius=0.09, color=color)
            self.play(FadeIn(dot), run_time=0.2)
            mid = wire.point_from_proportion(0.38)
            first = route([wire.get_start(), [band.get_left()[0], wire.get_start()[1], 0]])
            self.play(MoveAlongPath(dot, first), run_time=0.7)
            say(text, text_color)
            self.play(guards[guard_name][0].animate.set_fill(GUARD_C, opacity=0.35), run_time=0.25)
            self.play(guards[guard_name][0].animate.set_fill(WHITE, opacity=1), run_time=0.25)
            rest = route([[band.get_left()[0], wire.get_start()[1], 0], [band.get_right()[0], wire.get_end()[1], 0],
                          wire.get_end()])
            self.play(MoveAlongPath(dot, rest), run_time=1.0)
            self.play(Indicate(dot, color=color), run_time=0.4)
            self.play(FadeOut(dot), run_time=0.2)

        flow(wires[0], AGENT_C, "Custom Blocklists", "Support Agent calls Translator, custom blocklist screens banned terms",
             TRANS_C)

        right_lines = [visible[i] for i in range(1, len(visible), 2)]

        def show_panel(pnl, text, color, hold=3.0):
            self.play(*[FadeOut(o) for o in svc.values()], *[FadeOut(l) for l in right_lines],
                      FadeIn(pnl), run_time=0.8)
            say(text, color)
            self.wait(hold)
            self.play(FadeOut(pnl), *[FadeIn(o) for o in svc.values()], *[FadeIn(l) for l in right_lines],
                      run_time=0.8)

        flow(wires[1], WORKFLOW_C, "PII Detection", "Onboarding Agent reads documents with Document Intelligence",
             DOC_C)
        show_panel(panel, "Prebuilt analyzers: invoices, receipts, IDs, cards, tax forms and layout", DOC_C)

        flow(wires[2], HOSTED_C, "Groundedness", "Research Agent analyses text with Language, checked for groundedness",
             LANG_C)
        flow(wires[3], SPEECH_C, "3rd-Party Security", "Voice Agent uses Speech, third-party security integration inspects",
             PARTNER_C)
        show_panel(partner_panel, "Third-party security: Prisma AIRS and Zenity, bring your own license",
                   PARTNER_C, hold=4.0)

        # ---------- all agents share the model ----------
        model_wire = route([[AGENT_X, 1.65 + 0.425, 0], [AGENT_X, 2.2, 0], [SERVICE_X, 2.2, 0],
                            [SERVICE_X, 1.8 + 0.25, 0]])
        model_wire.set_stroke(color=MODEL_C, width=2)
        self.play(Create(model_wire), run_time=0.9)
        say("All agents reason with the same model deployments", MODEL_C)
        self.wait(1.2)

        # ---------- blocked request ----------
        say("An unsafe request is stopped at the Guardrails", GUARD_C)
        bad = Dot(wires[3].get_start(), radius=0.1, color=GUARD_C)
        self.play(FadeIn(bad), run_time=0.2)
        self.play(bad.animate.move_to([band.get_left()[0], wires[3].get_start()[1], 0]), run_time=0.8)
        cross = Cross(Square(side_length=0.3), stroke_color=GUARD_C, stroke_width=6).move_to(bad)
        self.play(guards["Prompt Shields"][0].animate.set_fill(GUARD_C, opacity=0.6), FadeIn(cross, scale=1.5),
                  run_time=0.4)
        blocked = Text("Blocked: prompt injection", font_size=14, color=GUARD_C).next_to(cross, DOWN, buff=0.15)
        self.play(FadeIn(blocked), run_time=0.4)
        self.wait(1.5)
        self.play(FadeOut(bad), FadeOut(cross), FadeOut(blocked),
                  guards["Prompt Shields"][0].animate.set_fill(WHITE, opacity=1), run_time=0.6)

        say("One Foundry: many agents, shared services, enforced Guardrails", BURGUNDY)
        self.wait(2.0)
