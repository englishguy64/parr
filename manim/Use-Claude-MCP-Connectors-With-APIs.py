from manim import *

# ---- parr color scheme (from Source/parr/styles.css) ----
BG = "#f5f7fa"        # light page background
INK = "#222222"       # body text
MUTED = "#6b7280"     # secondary text
LINE = "#9ca3af"      # idle connection lines
BURGUNDY = "#7a1f3d"  # header colour
GOLD = "#b8860b"      # button / quote border
SLATE = "#1f2937"     # footer / h2 colour
HILITE = "#e0a100"    # highlight rectangles (brighter gold, visible on light bg)
OK_C = "#2e7d5b"      # MCP client / results

config.background_color = BG
Text.set_default(font="Arial", color=INK)

CLAUDE_C = BURGUNDY
CODEX_C = GOLD
CUSTOM_C = SLATE
ATL_C = "#a33a5c"     # lighter burgundy
MS_C = "#475569"      # lighter slate


def packet(label, color):
    box = RoundedRectangle(width=max(0.5, 0.11 * len(label) + 0.25), height=0.32, corner_radius=0.08,
                           color=color, fill_color=color, fill_opacity=1, stroke_width=1)
    txt = Text(label, font_size=12, color=WHITE).move_to(box)
    return VGroup(box, txt)


class MCPFlow(Scene):
    def construct(self):
        # title is shown immediately (no animation)
        title = Text("Use Claude MCP Connectors With APIs", font_size=34,
                     color=BURGUNDY).to_edge(UP, buff=0.25)
        self.add(title)

        # ---------- user ----------
        head = Circle(radius=0.17, color=INK, stroke_width=3)
        body = Arc(radius=0.32, start_angle=0, angle=PI, color=INK, stroke_width=3).shift(DOWN * 0.5)
        user = VGroup(head, body, Text("User", font_size=18).shift(DOWN * 0.8)).move_to(LEFT * 5.75 + UP * 2.2)
        prompt_box = RoundedRectangle(width=2.5, height=1.0, corner_radius=0.1, color=INK, stroke_width=2)
        prompt_box.move_to(LEFT * 5.75 + UP * 0.3)
        prompt_txt = Text("Create a Jira ticket for\nthe failing build and\nemail the team",
                          font_size=13, line_spacing=0.8).move_to(prompt_box)

        # ---------- chatbots ----------
        def make_bot(name, y, color):
            outer = RoundedRectangle(width=2.9, height=1.3, corner_radius=0.15, color=color,
                                     fill_color=color, fill_opacity=0.12, stroke_width=3)
            outer.move_to(LEFT * 2.6 + UP * y)
            ttl = Text(name, font_size=18, color=color).move_to(outer.get_top() + DOWN * 0.27)
            llm = RoundedRectangle(width=1.1, height=0.5, corner_radius=0.08, color=color,
                                   fill_color=color, fill_opacity=0.3)
            llm.move_to(outer.get_center() + LEFT * 0.8 + DOWN * 0.2)
            llm_t = Text("LLM", font_size=14).move_to(llm)
            cli = RoundedRectangle(width=1.3, height=0.5, corner_radius=0.08, color=OK_C,
                                   fill_color=OK_C, fill_opacity=0.3)
            cli.move_to(outer.get_center() + RIGHT * 0.75 + DOWN * 0.2)
            cli_t = Text("MCP client", font_size=13).move_to(cli)
            return VGroup(outer, ttl, llm, llm_t, cli, cli_t)

        claude = make_bot("Claude Code", 2.1, CLAUDE_C)
        codex = make_bot("Codex", 0.0, CODEX_C)
        custom = make_bot("Bespoke chatbot", -2.1, CUSTOM_C)
        bots = [claude, codex, custom]
        clients = [b[4] for b in bots]

        # ---------- MCP servers ----------
        def make_server(name, tools, y, color):
            outer = RoundedRectangle(width=2.9, height=1.8, corner_radius=0.15, color=color,
                                     fill_color=color, fill_opacity=0.12, stroke_width=3)
            outer.move_to(RIGHT * 5.2 + UP * y)
            ttl = Text(name, font_size=17, color=color).move_to(outer.get_top() + DOWN * 0.27)
            items = VGroup(*[Text(t, font_size=14) for t in tools]).arrange(DOWN, buff=0.14, aligned_edge=LEFT)
            items.move_to(outer.get_center() + DOWN * 0.22)
            return VGroup(outer, ttl, items)

        atl = make_server("Atlassian MCP server", ["create_issue", "search_jira", "update_confluence"], 1.35, ATL_C)
        ms = make_server("Microsoft MCP server", ["send_mail", "read_calendar", "search_sharepoint"], -1.35, MS_C)
        servers = [atl, ms]

        # ---------- connections ----------
        conns = {}
        for bi, cl in enumerate(clients):
            for si, sv in enumerate(servers):
                ln = DashedLine(cl.get_right(), sv[0].get_left(), color=LINE, stroke_width=1.5)
                conns[(bi, si)] = ln
        conn_group = VGroup(*conns.values())
        proto_lbl = Text("MCP (JSON-RPC over stdio / HTTP)", font_size=15, color=MUTED)
        proto_lbl.move_to(RIGHT * 1.6 + DOWN * 3.0)

        self.play(FadeIn(user), Create(prompt_box))
        self.play(*[FadeIn(b) for b in bots], run_time=1.2)
        self.play(*[FadeIn(s) for s in servers], run_time=1)
        self.play(Create(conn_group), FadeIn(proto_lbl), run_time=1.5)

        status = Text("Every chatbot embeds an MCP client that can talk to any MCP server",
                      font_size=22).to_edge(DOWN, buff=0.25)
        self.add(status)
        self.wait(1.5)

        def say(msg, color=INK):
            # step titles swap instantly (no animation)
            status.become(Text(msg, font_size=22, color=color).to_edge(DOWN, buff=0.25))

        # ---------- discovery ----------
        say("0. On startup the MCP client connects and calls tools/list", MUTED)
        pk = [packet("tools/list", OK_C).move_to(clients[0].get_right()) for _ in servers]
        self.play(*[p.animate.move_to(s[0].get_left()) for p, s in zip(pk, servers)], run_time=1)
        self.play(*[Indicate(s[2], color=HILITE) for s in servers], run_time=0.8)
        self.play(*[p.animate.move_to(clients[0].get_right()) for p in pk], run_time=0.8)
        self.play(*[FadeOut(p) for p in pk], run_time=0.3)

        # ---------- user types prompt ----------
        say("1. The user types a prompt", INK)
        self.add(prompt_txt)
        self.play(AddTextLetterByLetter(prompt_txt, time_per_char=0.04))
        self.wait(0.4)

        # prompt travels to Claude Code
        pr = packet("prompt", GOLD).move_to(prompt_box.get_right())
        self.play(FadeIn(pr))
        say("2. The prompt reaches the chatbot (Claude Code) and its LLM", CLAUDE_C)
        self.play(pr.animate.move_to(claude[2].get_top() + UP * 0.1), run_time=1.2)
        r_llm = SurroundingRectangle(claude[2], color=HILITE, buff=0.05, stroke_width=3)
        self.play(Create(r_llm), FadeOut(pr))
        think = Text("thinking...", font_size=13, color=GOLD).next_to(claude[2], DOWN, buff=0.05)
        self.play(FadeIn(think))
        self.wait(0.6)
        self.play(FadeOut(think))

        # LLM -> MCP client
        say("3. The LLM chooses a tool; the MCP client builds a tools/call request", OK_C)
        tc = packet("tools/call", OK_C).move_to(claude[2].get_right())
        self.play(FadeIn(tc))
        self.play(tc.animate.move_to(claude[4].get_left()), run_time=0.7)
        r_cli = SurroundingRectangle(claude[4], color=HILITE, buff=0.05, stroke_width=3)
        self.play(Create(r_cli), FadeOut(r_llm), FadeOut(tc))

        # client -> server
        def call_server(si, tool_idx, label, ret_label, color):
            sv = servers[si]
            ln = conns[(0, si)]
            req = packet(label, color).move_to(ln.get_start())
            self.play(FadeIn(req), ln.animate.set_color(color).set_stroke(width=3), run_time=0.3)
            self.play(req.animate.move_to(ln.get_end()), run_time=1.2)
            hl = SurroundingRectangle(sv[2][tool_idx], color=HILITE, buff=0.05, stroke_width=3)
            self.play(Create(hl), FadeOut(req), run_time=0.5)
            self.wait(0.4)
            res = packet(ret_label, OK_C).move_to(ln.get_end())
            self.play(FadeIn(res))
            self.play(res.animate.move_to(ln.get_start()), run_time=1.2)
            self.play(FadeOut(res), FadeOut(hl), ln.animate.set_color(LINE).set_stroke(width=1.5),
                      run_time=0.4)

        say("4. Request goes to the Atlassian MCP server: create_issue", ATL_C)
        call_server(0, 0, "create_issue", "PROJ-123", ATL_C)
        say("5. Then to the Microsoft MCP server: send_mail", MS_C)
        call_server(1, 0, "send_mail", "sent", MS_C)

        # client -> LLM -> user
        say("6. Tool results go back to the LLM, which writes the answer", OK_C)
        back = packet("results", OK_C).move_to(claude[4].get_left())
        self.play(FadeIn(back), FadeOut(r_cli))
        self.play(back.animate.move_to(claude[2].get_right()), run_time=0.7)
        r_llm2 = SurroundingRectangle(claude[2], color=HILITE, buff=0.05, stroke_width=3)
        self.play(Create(r_llm2), FadeOut(back))
        self.wait(0.4)

        ans_box = RoundedRectangle(width=2.5, height=1.0, corner_radius=0.1, color=OK_C, stroke_width=2)
        ans_box.move_to(LEFT * 5.75 + DOWN * 1.9)
        ans_txt = Text("Done! PROJ-123 created\nand the team was emailed.",
                       font_size=13, line_spacing=0.8, color=OK_C).move_to(ans_box)
        ans = packet("answer", OK_C).move_to(claude[2].get_top() + UP * 0.1)
        say("7. The answer is returned to the user", OK_C)
        self.play(FadeIn(ans), FadeOut(r_llm2))
        self.play(ans.animate.move_to(ans_box.get_right()), run_time=1.3)
        self.play(FadeOut(ans), Create(ans_box))
        self.play(AddTextLetterByLetter(ans_txt, time_per_char=0.04))
        self.wait(1)

        # ---------- other chatbots ----------
        say("Codex and any bespoke chatbot use the same MCP client + servers", INK)
        flashes = []
        for bi, color in ((1, CODEX_C), (2, CUSTOM_C)):
            for si in (0, 1):
                ln = conns[(bi, si)]
                p = packet("MCP", color).move_to(ln.get_start())
                flashes.append((p, ln))
        self.add(*[p for p, _ in flashes])
        self.play(*[p.animate.move_to(ln.get_end()) for p, ln in flashes], run_time=1.5)
        self.play(*[p.animate.move_to(ln.get_start()) for p, ln in flashes], run_time=1.5)
        self.play(*[FadeOut(p) for p, _ in flashes], run_time=0.3)
        say("One protocol, many clients, many servers", OK_C)
        self.wait(2)
