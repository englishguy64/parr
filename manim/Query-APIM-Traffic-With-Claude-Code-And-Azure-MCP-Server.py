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
AZ_C = "#0f6cbd"      # Azure blue
LA_C = "#475569"      # Log Analytics slate
MONO = "Consolas"

KQL = (
    "ApiManagementGatewayLogs\n"
    "| where TimeGenerated > ago(7d)\n"
    "| summarize total = count(),\n"
    "            throttled = countif(ResponseCode == 429)\n"
    "            by day = bin(TimeGenerated, 1d)\n"
    "| extend pct429 = round(100.0 * throttled / total, 2)\n"
    "| order by day asc"
)

# example numbers for the animation only
RESULTS = [("Mon", 0.4), ("Tue", 0.6), ("Wed", 0.5), ("Thu", 6.8),
           ("Fri", 1.2), ("Sat", 0.2), ("Sun", 0.1)]


def packet(label, color):
    box = RoundedRectangle(width=max(0.5, 0.11 * len(label) + 0.25), height=0.32, corner_radius=0.08,
                           color=color, fill_color=color, fill_opacity=1, stroke_width=1)
    txt = Text(label, font_size=12, color=WHITE).move_to(box)
    return VGroup(box, txt)


def dark_panel(width, height, center):
    return RoundedRectangle(width=width, height=height, corner_radius=0.12, color=SLATE,
                            fill_color=SLATE, fill_opacity=1, stroke_width=2).move_to(center)


class QueryAPIMTraffic(Scene):
    def construct(self):
        # title is shown immediately (no animation)
        title = Text("Query APIM Traffic With Claude Code And Azure MCP Server", font_size=32,
                     color=BURGUNDY).to_edge(UP, buff=0.25)
        self.add(title)

        status = Text("", font_size=22).to_edge(DOWN, buff=0.25)
        self.add(status)

        def say(msg, color=INK):
            # step titles swap instantly (no animation)
            status.become(Text(msg, font_size=22, color=color).to_edge(DOWN, buff=0.25))

        # ---------- the platform engineer ----------
        head = Circle(radius=0.17, color=INK, stroke_width=3)
        body = Arc(radius=0.32, start_angle=0, angle=PI, color=INK, stroke_width=3).shift(DOWN * 0.5)
        role = Text("Azure APIM\nPlatform Engineer", font_size=15, line_spacing=0.8).shift(DOWN * 0.98)
        user = VGroup(head, body, role).move_to(LEFT * 5.55 + UP * 1.85)
        prompt_box = RoundedRectangle(width=2.5, height=0.9, corner_radius=0.1, color=INK, stroke_width=2)
        prompt_box.move_to(LEFT * 5.55 + DOWN * 0.15)
        prompt_txt = Text("What % of our APIM requests\nwere 429s each day last week?",
                          font_size=12, line_spacing=0.8).move_to(prompt_box)

        # ---------- Claude Code ----------
        cc_outer = RoundedRectangle(width=3.0, height=1.5, corner_radius=0.15, color=CLAUDE_C,
                                    fill_color=CLAUDE_C, fill_opacity=0.12, stroke_width=3)
        cc_outer.move_to(LEFT * 2.3 + UP * 1.7)
        cc_ttl = Text("Claude Code", font_size=18, color=CLAUDE_C).move_to(cc_outer.get_top() + DOWN * 0.27)
        llm = RoundedRectangle(width=1.1, height=0.5, corner_radius=0.08, color=CLAUDE_C,
                               fill_color=CLAUDE_C, fill_opacity=0.3)
        llm.move_to(cc_outer.get_center() + LEFT * 0.8 + DOWN * 0.2)
        llm_t = Text("LLM", font_size=14).move_to(llm)
        cli = RoundedRectangle(width=1.3, height=0.5, corner_radius=0.08, color=OK_C,
                               fill_color=OK_C, fill_opacity=0.3)
        cli.move_to(cc_outer.get_center() + RIGHT * 0.75 + DOWN * 0.2)
        cli_t = Text("MCP client", font_size=13).move_to(cli)
        claude = VGroup(cc_outer, cc_ttl, llm, llm_t, cli, cli_t)

        # ---------- Azure MCP Server ----------
        mcp_outer = RoundedRectangle(width=3.0, height=1.6, corner_radius=0.15, color=AZ_C,
                                     fill_color=AZ_C, fill_opacity=0.12, stroke_width=3)
        mcp_outer.move_to(RIGHT * 1.9 + UP * 1.7)
        mcp_ttl = Text("Azure MCP Server", font_size=17, color=AZ_C).move_to(mcp_outer.get_top() + DOWN * 0.27)
        mcp_items = VGroup(*[Text(t, font_size=12, font=MONO) for t in
                             ["monitor_workspace_log_query", "monitor_table_list", "group_list"]]
                           ).arrange(DOWN, buff=0.12, aligned_edge=LEFT)
        mcp_items.move_to(mcp_outer.get_center() + DOWN * 0.22)
        mcp = VGroup(mcp_outer, mcp_ttl, mcp_items)

        # ---------- Log Analytics ----------
        la_outer = RoundedRectangle(width=2.3, height=1.6, corner_radius=0.15, color=LA_C,
                                    fill_color=LA_C, fill_opacity=0.12, stroke_width=3)
        la_outer.move_to(RIGHT * 5.75 + UP * 1.7)
        la_ttl = Text("Log Analytics\nworkspace", font_size=15, color=LA_C, line_spacing=0.8
                      ).move_to(la_outer.get_top() + DOWN * 0.47)
        la_tbl = Text("ApiManagementGatewayLogs", font_size=9, font=MONO).move_to(la_outer.get_center() + DOWN * 0.45)
        la = VGroup(la_outer, la_ttl, la_tbl)

        # ---------- connections ----------
        ln_cc_mcp = DashedLine(cli.get_right(), mcp_outer.get_left(), color=LINE, stroke_width=1.5)
        ln_mcp_la = DashedLine(mcp_outer.get_right(), la_outer.get_left(), color=LINE, stroke_width=1.5)

        panel_c = RIGHT * 0.95 + DOWN * 1.2   # shared area for the KQL / terminal / results panels

        def kql_text(panel):
            t = Text(KQL, font_size=14, font=MONO, color=WHITE, line_spacing=0.75,
                     t2c={"where": HILITE, "summarize": HILITE, "extend": HILITE, "order by": HILITE,
                          "ago": "#7fd1ae", "count()": "#7fd1ae", "countif": "#7fd1ae",
                          "bin": "#7fd1ae", "round": "#7fd1ae"})
            t.move_to(panel.get_center() + DOWN * 0.2)
            return t

        # =====================================================
        # PART 1 - BEFORE the MCP server: the engineer writes KQL by hand
        # =====================================================
        say("1. Before MCP: the engineer wants to know what % of requests were 429s", INK)
        # the question box pops out of the engineer
        prompt_group = VGroup(prompt_box, prompt_txt)
        prompt_group.save_state()
        prompt_group.scale(0.05).move_to(user.get_center())
        self.play(FadeIn(user), FadeIn(la))
        self.add(prompt_group)
        self.play(Restore(prompt_group), run_time=1.3)
        self.wait(0.6)
        prompt_proto = prompt_group.copy()   # kept so the box can reappear after the MCP server is connected

        say("2. They have to write the KQL query themselves in the Log Analytics editor", LA_C)
        kql_panel = dark_panel(8.6, 2.75, panel_c)
        kql_hdr = Text("Log Analytics > Logs   (engineer types the KQL)", font_size=13, color=HILITE, font=MONO)
        kql_hdr.move_to(kql_panel.get_top() + DOWN * 0.25)
        kql_txt = kql_text(kql_panel)
        self.play(FadeIn(kql_panel), FadeIn(kql_hdr))
        self.add(kql_txt)
        self.play(AddTextLetterByLetter(kql_txt, time_per_char=0.012), run_time=3)
        self.wait(1)
        # the question box disappears once the KQL query is on screen
        self.play(FadeOut(prompt_group), run_time=0.5)

        say("3. Then run it directly against the Log Analytics workspace", LA_C)
        # the KQL query box itself travels into Log Analytics (no dotted line)
        kql_box = VGroup(kql_panel, kql_hdr, kql_txt)
        self.play(kql_box.animate.scale(0.2).move_to(la_outer.get_center() + DOWN * 0.1), run_time=1.6)
        hl_la = SurroundingRectangle(la_tbl, color=HILITE, buff=0.06, stroke_width=3)
        self.play(Create(hl_la), FadeOut(kql_box), run_time=0.5)
        self.wait(0.4)
        rows0 = packet("7 rows", OK_C).move_to(la_outer.get_left())
        self.play(FadeIn(rows0))
        self.play(rows0.animate.move_to(user.get_right() + RIGHT * 0.1), FadeOut(hl_la), run_time=1.5)
        self.play(FadeOut(rows0))
        pain = Text("Works, but you need to know KQL, the table names and the portal",
                    font_size=17, color=MUTED).move_to(panel_c)
        self.play(FadeIn(pain))
        self.wait(2)
        self.play(FadeOut(pain))

        # =====================================================
        # PART 2 - connect Claude Code to the Azure MCP server with /mcp
        # =====================================================
        say("4. Now the engineer connects Claude Code to the Azure MCP Server", AZ_C)
        self.play(FadeIn(claude), FadeIn(mcp), run_time=1.2)
        self.play(Create(ln_cc_mcp), Create(ln_mcp_la), run_time=0.8)
        self.wait(0.6)

        say("5. The engineer configures MCP in Claude Code by typing /mcp", OK_C)
        # a box "Engineer configures MCP" comes out of the engineer and connects to Claude Code
        cfg_rect = RoundedRectangle(width=2.7, height=0.6, corner_radius=0.1, color=AZ_C,
                                    fill_color=AZ_C, fill_opacity=0.15, stroke_width=2.5)
        cfg_txt = Text("Engineer configures MCP", font_size=14, color=AZ_C).move_to(cfg_rect)
        cfg_box = VGroup(cfg_rect, cfg_txt)
        cfg_pos = LEFT * 2.3 + UP * 0.5
        cfg_box.move_to(cfg_pos)
        cfg_box.save_state()
        cfg_box.scale(0.05).move_to(user.get_center())
        self.add(cfg_box)
        self.play(Restore(cfg_box), run_time=1.3)
        cfg_link = Line(cfg_rect.get_top(), cc_outer.get_bottom(), color=AZ_C, stroke_width=3)
        r_mcp_client = SurroundingRectangle(cli, color=HILITE, buff=0.05, stroke_width=3)
        self.play(Create(cfg_link), Create(r_mcp_client), run_time=0.6)
        term = dark_panel(8.6, 2.75, panel_c)
        add_cmd =Text("$ claude mcp add azure -- npx -y @azure/mcp@latest server start",
                       font_size=13, font=MONO, color="#c9d1d9")
        slash = Text("> /mcp", font_size=18, font=MONO, color=WHITE)
        hdr = Text("Manage MCP servers", font_size=14, font=MONO, color="#c9d1d9")
        row = Text("> azure     connected", font_size=16, font=MONO, color=WHITE,
                   t2c={"connected": "#5fd3a0"})
        tools_row = Text("   1 server, tools: monitor_workspace_log_query, ...", font_size=12,
                         font=MONO, color="#8b949e")
        lines = VGroup(add_cmd, slash, hdr, row, tools_row).arrange(DOWN, buff=0.22, aligned_edge=LEFT)
        lines.move_to(term.get_center())
        lines.align_to(term, LEFT).shift(RIGHT * 0.35)
        self.play(FadeIn(term))
        self.add(add_cmd)
        self.play(AddTextLetterByLetter(add_cmd, time_per_char=0.03), run_time=2)
        self.add(slash)
        self.play(AddTextLetterByLetter(slash, time_per_char=0.12))
        self.wait(0.4)
        self.play(FadeIn(hdr), run_time=0.5)
        self.play(FadeIn(row), run_time=0.5)
        self.play(FadeIn(tools_row), run_time=0.5)

        say("6. The MCP client connects and discovers the tools of the server (tools/list)", OK_C)
        ping = packet("tools/list", OK_C).move_to(cli.get_right())
        self.play(FadeIn(ping), ln_cc_mcp.animate.set_color(OK_C).set_stroke(width=3), run_time=0.4)
        self.play(ping.animate.move_to(mcp_outer.get_left()), run_time=1)
        self.play(Indicate(mcp_items, color=HILITE), run_time=0.8)
        self.play(ping.animate.move_to(cli.get_right()), run_time=0.8)
        self.play(FadeOut(ping), run_time=0.3)
        self.wait(0.8)
        self.play(FadeOut(term), FadeOut(lines), FadeOut(r_mcp_client), FadeOut(cfg_link), FadeOut(cfg_box))

        # =====================================================
        # PART 3 - AFTER the connection: ask in plain English
        # =====================================================
        say("7. After connecting: ask the same question in plain English, no KQL needed", GOLD)
        # the question box reappears (from the engineer) now that Claude Code is connected ...
        q_box = prompt_proto.copy()
        q_box.set_z_index(5)
        q_box.save_state()
        q_box.scale(0.05).move_to(user.get_center())
        self.add(q_box)
        self.play(Restore(q_box), run_time=1.2)
        self.wait(0.5)
        # ... and is sent forward into the Claude Code box
        self.play(q_box.animate.scale(0.3).move_to(llm.get_center()), run_time=1.5)
        r_llm = SurroundingRectangle(llm, color=HILITE, buff=0.05, stroke_width=3)
        self.play(Create(r_llm), FadeOut(q_box), run_time=0.4)

        say("8. Claude Code writes the KQL for you", CLAUDE_C)
        gen_panel = dark_panel(8.6, 2.75, panel_c)
        gen_hdr = Text("Claude Code writes the KQL", font_size=13, color=HILITE, font=MONO)
        gen_hdr.move_to(gen_panel.get_top() + DOWN * 0.25)
        gen_txt = kql_text(gen_panel)
        self.play(FadeIn(gen_panel), FadeIn(gen_hdr))
        self.add(gen_txt)
        self.play(AddTextLetterByLetter(gen_txt, time_per_char=0.006), run_time=1.5)
        self.wait(1.2)
        self.play(FadeOut(gen_panel), FadeOut(gen_hdr), FadeOut(gen_txt))

        say("9. The MCP client sends tools/call to the Azure MCP Server", OK_C)
        tc = packet("tools/call", OK_C).move_to(llm.get_right())
        self.play(FadeIn(tc))
        self.play(tc.animate.move_to(cli.get_left()), run_time=0.6)
        r_cli = SurroundingRectangle(cli, color=HILITE, buff=0.05, stroke_width=3)
        self.play(Create(r_cli), FadeOut(r_llm), FadeOut(tc))

        req = packet("KQL query", AZ_C).move_to(cli.get_right())
        self.play(FadeIn(req), ln_cc_mcp.animate.set_color(AZ_C).set_stroke(width=3), run_time=0.3)
        self.play(req.animate.move_to(mcp_outer.get_left()), run_time=1)
        hl_tool = SurroundingRectangle(mcp_items[0], color=HILITE, buff=0.05, stroke_width=3)
        self.play(Create(hl_tool), FadeOut(req), run_time=0.5)

        say("10. The server runs the KQL against the APIM gateway logs", AZ_C)
        q2 = packet("KQL", AZ_C).move_to(mcp_outer.get_right())
        self.play(FadeIn(q2), ln_mcp_la.animate.set_color(AZ_C).set_stroke(width=3), run_time=0.3)
        self.play(q2.animate.move_to(la_outer.get_left()), run_time=1)
        hl_la2 = SurroundingRectangle(la_tbl, color=HILITE, buff=0.06, stroke_width=3)
        self.play(Create(hl_la2), FadeOut(q2), run_time=0.5)
        self.wait(0.5)

        say("11. Rows come back through the MCP server to Claude Code", OK_C)
        rows = packet("7 rows", OK_C).move_to(la_outer.get_left())
        self.play(FadeIn(rows))
        self.play(rows.animate.move_to(mcp_outer.get_right()), FadeOut(hl_la2), run_time=0.9)
        self.play(rows.animate.move_to(mcp_outer.get_left()), FadeOut(hl_tool), run_time=0.5)
        self.play(rows.animate.move_to(cli.get_right()), run_time=0.9)
        self.play(rows.animate.move_to(llm.get_right()), FadeOut(r_cli), run_time=0.6)
        r_llm2 = SurroundingRectangle(llm, color=HILITE, buff=0.05, stroke_width=3)
        self.play(Create(r_llm2), FadeOut(rows))
        self.play(ln_cc_mcp.animate.set_color(OK_C).set_stroke(width=2),
                  ln_mcp_la.animate.set_color(OK_C).set_stroke(width=2), run_time=0.3)

        # ---------- answer: table with a bar per day ----------
        say("12. Claude Code answers the engineer: % of requests throttled (429) per day", OK_C)
        ans = packet("answer", OK_C).move_to(llm.get_top() + UP * 0.1)
        self.play(FadeIn(ans), FadeOut(r_llm2))
        self.play(ans.animate.move_to(user.get_right() + DOWN * 0.3), run_time=1.3)
        self.play(FadeOut(ans))

        res_panel = dark_panel(8.6, 2.75, panel_c)
        res_hdr = Text("429 rate by day, last 7 days   (example data)", font_size=13, font=MONO,
                       color=HILITE).move_to(res_panel.get_top() + DOWN * 0.25)
        row_txts = VGroup(*[Text(f"{d}  {p:4.1f}%", font_size=14, font=MONO, color=WHITE)
                            for d, p in RESULTS]).arrange(DOWN, buff=0.07, aligned_edge=LEFT)
        row_txts.move_to(res_panel.get_left() + RIGHT * 1.2 + DOWN * 0.2)
        bars = VGroup()
        for t, (d, p) in zip(row_txts, RESULTS):
            colr = HILITE if p == max(v for _, v in RESULTS) else OK_C
            bar = Rectangle(width=max(0.05, p * 0.4), height=0.16, color=colr, fill_color=colr,
                            fill_opacity=1, stroke_width=0)
            bar.move_to(t.get_right() + RIGHT * 0.25, aligned_edge=LEFT)
            bars.add(bar)
        note = Text("Thursday spike:\n6.8% of requests\nwere throttled (429)", font_size=14, color=HILITE,
                    line_spacing=0.8)
        note.move_to(bars[3].get_right() + RIGHT * 0.3, aligned_edge=LEFT)
        self.play(FadeIn(res_panel), FadeIn(res_hdr))
        self.play(FadeIn(row_txts), run_time=0.6)
        self.play(*[GrowFromEdge(b, LEFT) for b in bars], run_time=1.2)
        self.play(Indicate(bars[3], color=HILITE), FadeIn(note), run_time=1)
        self.wait(1.5)

        say("Before: write the KQL yourself.  After: ask in plain English, the Azure MCP Server runs it", OK_C)
        self.wait(3)
