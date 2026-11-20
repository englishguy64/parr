from manim import *

# ---- parr color scheme (from Source/parr/styles.css) ----
BG = "#f5f7fa"
INK = "#222222"
MUTED = "#6b7280"
LINE = "#9ca3af"
BURGUNDY = "#7a1f3d"
GOLD = "#b8860b"
SLATE = "#1f2937"
HILITE = "#e0a100"
OK_C = "#2e7d5b"

config.background_color = BG
Text.set_default(font="Arial", color=INK)

APIM_C = "#0f766e"
FOUNDRY_C = GOLD
PROJECT_C = "#475569"
AGENT_C = "#a33a5c"
HOSTED_C = "#6d4c9f"
WORKFLOW_C = "#b45309"
TOOLBOX_C = "#1d4ed8"
EXT_C = SLATE
DEPLOY_C = "#0369a1"
GOV_C = "#9f1239"


def packet(label, color):
    box = RoundedRectangle(width=max(0.5, 0.11 * len(label) + 0.25), height=0.32, corner_radius=0.08,
                           color=color, fill_color=color, fill_opacity=1, stroke_width=1)
    txt = Text(label, font_size=12, color=WHITE).move_to(box)
    return VGroup(box, txt)


def small_box(title, color, width, center, container=False, height=0.55):
    box = RoundedRectangle(width=width, height=height, corner_radius=0.1, color=color,
                           fill_color=color, fill_opacity=0.14, stroke_width=3).move_to(center)
    ttl = Text(title, font_size=15, color=color).move_to(box)
    grp = VGroup(box, ttl)
    if container:
        blocks = VGroup(*[Square(side_length=0.07, color=color, fill_color=color, fill_opacity=0.9,
                                 stroke_width=0) for _ in range(6)])
        blocks.arrange_in_grid(rows=2, cols=3, buff=0.02)
        frame = SurroundingRectangle(blocks, color=color, buff=0.035, stroke_width=1.5, corner_radius=0.03)
        icon = VGroup(frame, blocks).move_to(box.get_left() + RIGHT * 0.28)
        ttl.shift(RIGHT * 0.15)
        grp.add(icon)
    return grp


def chip(label, color, center, width=1.8, font_size=12):
    box = RoundedRectangle(width=width, height=0.34, corner_radius=0.08, color=color,
                           fill_color=WHITE, fill_opacity=1, stroke_width=2).move_to(center)
    txt = Text(label, font_size=font_size, color=INK).move_to(box)
    return VGroup(box, txt)


def chapter_pill(n, name, color):
    box = RoundedRectangle(width=3.0, height=0.45, corner_radius=0.22, color=color,
                           fill_color=color, fill_opacity=1, stroke_width=0)
    txt = Text(f"{n}   {name}", font_size=18, color=WHITE).move_to(box)
    return VGroup(box, txt).move_to([0, 3.05, 0])


class SharedToolboxes(Scene):
    def construct(self):
        title = Text("Streamline Microsoft Foundry Architecture With Toolboxes", font_size=26,
                     color=BURGUNDY).to_edge(UP, buff=0.25)
        self.add(title)

        status = Text("A toolbox is defined once and shared by every agent that needs its tools",
                      font_size=22).to_edge(DOWN, buff=0.25)
        self.add(status)

        def say(msg, color=INK):
            status.become(Text(msg, font_size=22, color=color).to_edge(DOWN, buff=0.25))

        # ---------- APIM ----------
        apim_box = RoundedRectangle(width=1.7, height=1.5, corner_radius=0.12, color=APIM_C, stroke_width=3,
                                    fill_color=APIM_C, fill_opacity=0.14).move_to([-5.8, 1.1, 0])
        apim_t = Text("APIM", font_size=17, color=APIM_C).move_to(apim_box.get_top() + DOWN * 0.3)
        apim_s = VGroup(*[Text(s, font_size=12) for s in ["API gateway", "Managed identity", "Entra token"]])
        apim_s.arrange(DOWN, buff=0.1).move_to(apim_box.get_center() + DOWN * 0.2)
        apim = VGroup(apim_box, apim_t, apim_s)

        # ---------- Deploy (outside the instance) ----------
        dbox = RoundedRectangle(width=2.3, height=2.2, corner_radius=0.12, color=DEPLOY_C, stroke_width=3,
                                fill_color=DEPLOY_C, fill_opacity=0.08).move_to([-5.8, -1.5, 0])
        d_title = Text("Deploy", font_size=17, color=DEPLOY_C).move_to(dbox.get_top() + DOWN * 0.28)
        d_vs = small_box("Foundry Toolkit", DEPLOY_C, 1.95, [-5.8, -1.2, 0], height=0.75)
        d_vs[1].become(VGroup(Text("Foundry Toolkit", font_size=13, color=DEPLOY_C),
                              Text("for VS Code", font_size=13, color=DEPLOY_C)).arrange(DOWN, buff=0.05)
                       .move_to(d_vs[0]))
        d_azd = small_box("AZD", DEPLOY_C, 1.95, [-5.8, -2.1, 0], height=0.55)
        deploy = VGroup(dbox, d_title, d_vs, d_azd)

        # ---------- Foundry instance ----------
        fbox = RoundedRectangle(width=7.4, height=5.3, corner_radius=0.2, color=FOUNDRY_C, stroke_width=3,
                                fill_color=FOUNDRY_C, fill_opacity=0.08).move_to([-0.3, -0.1, 0])
        f_title = Text("Microsoft Foundry instance", font_size=18, color=FOUNDRY_C)
        f_title.move_to(fbox.get_top() + DOWN * 0.3)
        f_sub = Text("Azure resource: models, identity, networking, connections",
                     font_size=12, color=MUTED).next_to(f_title, DOWN, buff=0.08)
        models = chip("Model deployments", FOUNDRY_C, [-0.3, 1.35, 0], width=2.6)
        foundry = VGroup(fbox, f_title, f_sub, models)

        pbox = RoundedRectangle(width=6.9, height=3.75, corner_radius=0.15, color=PROJECT_C, stroke_width=2,
                                fill_color=PROJECT_C, fill_opacity=0.05).move_to([-0.3, -0.75, 0])
        p_lbl = Text("Project", font_size=14, color=PROJECT_C).move_to(pbox.get_top() + DOWN * 0.22)
        project = VGroup(pbox, p_lbl)

        # ---------- agent types ----------
        a_lbl = Text("Agent types", font_size=12, color=MUTED).move_to([-2.5, 0.78, 0])
        agent_p = small_box("Prompt Agent", AGENT_C, 2.1, [-2.5, 0.3, 0])
        agent_w = small_box("Workflow Agent", WORKFLOW_C, 2.1, [-2.5, -0.45, 0])
        agent_h = small_box("Hosted Agent", HOSTED_C, 2.1, [-2.5, -1.2, 0], container=True)
        agents = VGroup(a_lbl, agent_p, agent_w, agent_h)

        # ---------- toolbox ----------
        tbox = RoundedRectangle(width=2.3, height=2.6, corner_radius=0.12, color=TOOLBOX_C, stroke_width=3,
                                fill_color=TOOLBOX_C, fill_opacity=0.12).move_to([1.2, -0.5, 0])
        t_title = Text("Toolbox", font_size=17, color=TOOLBOX_C).move_to(tbox.get_top() + DOWN * 0.25)
        t_name = Text("support-tools", font_size=12, color=INK).next_to(t_title, DOWN, buff=0.06)
        version = Text("version 1 (default)", font_size=12, color=OK_C).next_to(t_name, DOWN, buff=0.08)
        endpoint = Text("one MCP endpoint", font_size=12, color=TOOLBOX_C).move_to(tbox.get_bottom() + UP * 0.22)
        toolbox = VGroup(tbox, t_title, t_name, version, endpoint)

        # ---------- external tools list (outside the instance) ----------
        xbox = RoundedRectangle(width=2.6, height=4.3, corner_radius=0.12, color=EXT_C, stroke_width=3,
                                fill_color=EXT_C, fill_opacity=0.06).move_to([5.5, -0.2, 0])
        x_title = Text("Tools and services", font_size=15, color=EXT_C).move_to(xbox.get_top() + DOWN * 0.28)
        x_sub = Text("hosted outside Foundry", font_size=11, color=MUTED).next_to(x_title, DOWN, buff=0.06)
        names = ["MCP", "OpenAPI", "A2A", "Skills", "Agents (A2A)", "Other"]
        chips = {}
        for i, n in enumerate(names):
            chips[n] = chip(n, EXT_C, [5.5, 0.85 - i * 0.55, 0], width=2.0)
        ext = VGroup(xbox, x_title, x_sub, *chips.values())

        # ---------- links ----------
        def dline(a, b):
            return DashedLine(a, b, color=LINE, stroke_width=1.5)

        l_p = dline(apim_box.get_right(), agent_p[0].get_left())
        l_w = dline(apim_box.get_right(), agent_w[0].get_left())
        l_h = dline(apim_box.get_right(), agent_h[0].get_left())
        l_tp = dline(agent_p[0].get_right(), tbox.get_left())
        l_tw = dline(agent_w[0].get_right(), tbox.get_left())
        l_th = dline(agent_h[0].get_right(), tbox.get_left())
        l_x = dline(tbox.get_right(), xbox.get_left())
        l_d = dline(dbox.get_right(), [fbox.get_left()[0], -1.5, 0])
        links = VGroup(l_p, l_w, l_h, l_tp, l_tw, l_th, l_x, l_d)

        def lit(line, color):
            return line.animate.set_color(color).set_stroke(width=3)

        def unlit(line):
            return line.animate.set_color(LINE).set_stroke(width=1.5)

        def hl(mob, color=HILITE):
            r = SurroundingRectangle(mob, color=color, buff=0.06, stroke_width=3)
            self.play(Create(r), run_time=0.4)
            return r

        def travel(pkt, p, run_time=1.0):
            self.play(pkt.animate.move_to(p), run_time=run_time)

        # ---------- intro: the picture ----------
        say("The Foundry instance is the Azure resource. Work happens inside a project", FOUNDRY_C)
        self.play(FadeIn(apim), FadeIn(foundry), run_time=1)
        self.play(FadeIn(project), run_time=0.8)
        self.wait(0.3)
        say("A project holds agents of different types, and the toolbox they share", AGENT_C)
        self.play(FadeIn(agents), FadeIn(toolbox), run_time=1)
        self.wait(0.3)
        say("The toolbox calls tools and services hosted outside the instance", EXT_C)
        self.play(FadeIn(ext), run_time=1)
        say("You deploy to the instance with Foundry Toolkit for VS Code or AZD", DEPLOY_C)
        self.play(FadeIn(deploy), run_time=1)
        self.play(Create(links), run_time=1.2)
        self.wait(0.6)

        pill = chapter_pill(1, "Build", DEPLOY_C)

        # ===================== 1. BUILD =====================
        self.play(FadeIn(pill), run_time=0.5)
        say("Build: create the toolbox from Foundry Toolkit for VS Code or the AZD CLI", DEPLOY_C)
        r_dep = hl(deploy, DEPLOY_C)
        pk = packet("create toolbox", DEPLOY_C).move_to(l_d.get_start())
        self.play(FadeIn(pk), lit(l_d, DEPLOY_C), run_time=0.3)
        travel(pk, l_d.get_end())
        self.play(pk.animate.move_to(tbox.get_left() + LEFT * 0.7), run_time=0.8)
        r_tb = hl(tbox, TOOLBOX_C)
        self.play(FadeOut(pk), unlit(l_d), FadeOut(r_dep), run_time=0.3)

        say("Build: choose the tools, then publish version 1 as the default", TOOLBOX_C)
        reg = []
        for n in names:
            p = packet("add", TOOLBOX_C).move_to(l_x.get_start())
            reg.append(p)
        self.play(lit(l_x, TOOLBOX_C), run_time=0.3)
        for n, p in zip(names, reg):
            self.play(FadeIn(p), run_time=0.1)
            self.play(p.animate.move_to(l_x.get_end()), run_time=0.35)
            self.play(p.animate.move_to(chips[n][0].get_left() + LEFT * 0.3), FadeOut(p), run_time=0.2)
            self.play(chips[n][0].animate.set_stroke(color=TOOLBOX_C, width=3), run_time=0.15)
        self.play(unlit(l_x), FadeOut(r_tb), run_time=0.3)
        self.wait(0.4)

        # ===================== 2. DISCOVER =====================
        pill2 = chapter_pill(2, "Discover", AGENT_C)
        self.play(ReplacementTransform(pill, pill2), run_time=0.5)
        pill = pill2
        say("Discover: an agent asks the toolbox which tools fit the task", AGENT_C)
        r_ap = hl(agent_p, AGENT_C)
        pk = packet("tool_search", TOOLBOX_C).move_to(l_tp.get_start())
        self.play(FadeIn(pk), lit(l_tp, TOOLBOX_C), run_time=0.3)
        travel(pk, l_tp.get_end())
        r_tb = hl(tbox, TOOLBOX_C)
        self.play(FadeOut(pk), run_time=0.2)

        say("Discover: the toolbox returns only the matching tools, found at runtime", TOOLBOX_C)
        self.play(unlit(l_tp), lit(l_x, TOOLBOX_C), run_time=0.3)
        marks = [hl(chips[n], HILITE) for n in ("MCP", "OpenAPI")]
        back = packet("2 tools found", OK_C).move_to(l_tp.get_end())
        self.play(FadeIn(back), run_time=0.2)
        self.play(lit(l_tp, OK_C), back.animate.move_to(l_tp.get_start()), run_time=1.0)
        self.play(FadeOut(back), unlit(l_tp), unlit(l_x), FadeOut(r_tb), FadeOut(r_ap),
                  *[FadeOut(m) for m in marks], run_time=0.4)
        self.wait(0.4)

        # ===================== 3. CONSUME =====================
        pill3 = chapter_pill(3, "Consume", OK_C)
        self.play(ReplacementTransform(pill, pill3), run_time=0.5)
        pill = pill3
        say("Consume: APIM calls the Foundry instance and routes to a Prompt Agent", APIM_C)
        q = packet("POST /support", AGENT_C).move_to(apim_box.get_center() + LEFT * 0.0)
        self.play(FadeIn(q), run_time=0.3)
        r_apim = hl(apim)
        self.play(q.animate.move_to(l_p.get_start()), lit(l_p, AGENT_C), run_time=0.5)
        travel(q, l_p.get_end())
        r_ap = hl(agent_p, AGENT_C)
        self.play(FadeOut(q), unlit(l_p), run_time=0.2)

        say("Consume: the agent calls the tool through the shared toolbox endpoint", TOOLBOX_C)
        tq = packet("call_tool", TOOLBOX_C).move_to(l_tp.get_start())
        self.play(FadeIn(tq), lit(l_tp, TOOLBOX_C), run_time=0.3)
        travel(tq, l_tp.get_end())
        r_tb = hl(tbox, TOOLBOX_C)
        self.play(unlit(l_tp), lit(l_x, TOOLBOX_C), tq.animate.move_to(l_x.get_start()), run_time=0.4)
        travel(tq, l_x.get_end())
        r_c = hl(chips["MCP"], HILITE)
        self.wait(0.3)
        res = packet("tool result", OK_C).move_to(l_x.get_end())
        self.play(FadeOut(tq), FadeIn(res), run_time=0.2)
        travel(res, l_x.get_start())
        self.play(unlit(l_x), lit(l_tp, OK_C), res.animate.move_to(l_tp.get_end()), run_time=0.4)
        travel(res, l_tp.get_start())
        self.play(FadeOut(res), unlit(l_tp), FadeOut(r_tb), FadeOut(r_c), run_time=0.3)

        say("Consume: the answer returns through APIM to the caller", OK_C)
        a = packet("answer", OK_C).move_to(l_p.get_end())
        self.play(FadeIn(a), lit(l_p, OK_C), run_time=0.2)
        travel(a, l_p.get_start())
        self.play(FadeOut(a), unlit(l_p), FadeOut(r_ap), FadeOut(r_apim), run_time=0.4)

        say("Consume: a Hosted Agent uses the very same toolbox, here for an OpenAPI tool", HOSTED_C)
        q = packet("POST /orchestrate", HOSTED_C).move_to(apim_box.get_center())
        self.play(FadeIn(q), run_time=0.3)
        r_apim = hl(apim)
        self.play(q.animate.move_to(l_h.get_start()), lit(l_h, HOSTED_C), run_time=0.5)
        travel(q, l_h.get_end())
        r_ah = hl(agent_h, HOSTED_C)
        self.play(FadeOut(q), unlit(l_h), run_time=0.2)
        tq = packet("call_tool", TOOLBOX_C).move_to(l_th.get_start())
        self.play(FadeIn(tq), lit(l_th, TOOLBOX_C), run_time=0.3)
        travel(tq, l_th.get_end())
        r_tb = hl(tbox, TOOLBOX_C)
        self.play(unlit(l_th), lit(l_x, TOOLBOX_C), tq.animate.move_to(l_x.get_start()), run_time=0.4)
        travel(tq, l_x.get_end())
        r_c = hl(chips["OpenAPI"], HILITE)
        self.play(FadeOut(tq), unlit(l_x), FadeOut(r_c), FadeOut(r_tb), FadeOut(r_ah), FadeOut(r_apim),
                  run_time=0.4)
        self.wait(0.4)

        # ===================== 4. GOVERNANCE =====================
        pill4 = chapter_pill(4, "Governance", GOV_C)
        self.play(ReplacementTransform(pill, pill4), run_time=0.5)
        pill = pill4
        say("Governance: the toolbox centralises authentication and policy for every tool", GOV_C)
        g1 = chip("Entra ID auth", GOV_C, [1.2, -0.2, 0], width=1.9)
        g2 = chip("OAuth passthrough", GOV_C, [1.2, -0.62, 0], width=1.9)
        g3 = chip("Guardrails", GOV_C, [1.2, -1.04, 0], width=1.9)
        r_tb = hl(tbox, GOV_C)
        for g in (g1, g2, g3):
            self.play(FadeIn(g), run_time=0.45)
        self.wait(0.5)

        say("Governance: agents hold no per-tool credentials, so tools can change safely", GOV_C)
        self.play(Indicate(agent_p, color=GOV_C), Indicate(agent_w, color=GOV_C), Indicate(agent_h, color=GOV_C),
                  run_time=1.5)

        say("Governance: promote version 2, and every agent uses it with no redeploy", OK_C)
        new_version = Text("version 2 (default)", font_size=12, color=OK_C).move_to(version)
        self.play(Transform(version, new_version), run_time=0.8)
        flash = SurroundingRectangle(tbox, color=OK_C, buff=0.08, stroke_width=4)
        self.play(Create(flash), run_time=0.4)
        self.play(FadeOut(flash), FadeOut(r_tb), run_time=0.4)
        self.wait(0.5)

        say("Build once, discover at runtime, consume anywhere, with governance built in", OK_C)
        self.wait(2.5)
