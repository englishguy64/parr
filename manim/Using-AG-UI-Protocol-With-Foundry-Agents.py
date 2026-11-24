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
ERR_C = "#b42318"

config.background_color = BG
Text.set_default(font="Arial", color=INK)

WEB_C = BURGUNDY
REST_C = "#0f766e"
AGUI_C = "#6d4c9f"
FOUNDRY_C = GOLD
AGENT1_C = "#a33a5c"
AGENT2_C = SLATE
AGENT3_C = "#9a3412"


def packet(label, color):
    box = RoundedRectangle(width=max(0.5, 0.11 * len(label) + 0.25), height=0.32, corner_radius=0.08,
                           color=color, fill_color=color, fill_opacity=1, stroke_width=1)
    txt = Text(label, font_size=12, color=WHITE).move_to(box)
    return VGroup(box, txt)


def component(title, sub, color, width, height, center):
    box = RoundedRectangle(width=width, height=height, corner_radius=0.12, color=color,
                           fill_color=color, fill_opacity=0.14, stroke_width=3).move_to(center)
    ttl = Text(title, font_size=17, color=color).move_to(box.get_top() + DOWN * 0.3)
    lines = VGroup(*[Text(s, font_size=13, color=INK) for s in sub]).arrange(DOWN, buff=0.1)
    lines.move_to(box.get_center() + DOWN * 0.2)
    return VGroup(box, ttl, lines)


def card(text, color, y):
    box = RoundedRectangle(width=3.5, height=0.5, corner_radius=0.1, color=color,
                           fill_color=WHITE, fill_opacity=1, stroke_width=2).move_to([-3.6, y, 0])
    txt = Text(text, font_size=13, color=INK).move_to(box)
    return VGroup(box, txt)


class AGUIWithFoundryAgents(Scene):
    def construct(self):
        title = Text("Using AG-UI protocol with Foundry Agents", font_size=28,
                     color=BURGUNDY).to_edge(UP, buff=0.25)
        self.add(title)

        # ---------- user ----------
        head = Circle(radius=0.17, color=INK, stroke_width=3)
        body = Arc(radius=0.32, start_angle=0, angle=PI, color=INK, stroke_width=3).shift(DOWN * 0.5)
        user = VGroup(head, body, Text("User", font_size=16).shift(DOWN * 0.8)).move_to([-6.7, 0.2, 0])

        # ---------- web app with its use cases ----------
        wbox = RoundedRectangle(width=4.0, height=4.6, corner_radius=0.2, color=WEB_C, stroke_width=3,
                                fill_color=WEB_C, fill_opacity=0.06).move_to([-3.6, 0.2, 0])
        w_title = Text("Web App (front end)", font_size=18, color=WEB_C).move_to(wbox.get_top() + DOWN * 0.3)
        rest_lbl = Text("REST use cases", font_size=13, color=REST_C).move_to([-3.6, 1.85, 0])
        agui_lbl = Text("AG-UI use cases", font_size=13, color=AGUI_C).move_to([-3.6, 0.35, 0])
        c_order = card("Look up an order status", REST_C, 1.45)
        c_class = card("Classify a support ticket", REST_C, 0.9)
        c_chat = card("Stream a chat answer", AGUI_C, -0.1)
        c_prog = card("Show live agent progress", AGUI_C, -0.7)
        c_hitl = card("Approve a refund (human in the loop)", AGUI_C, -1.3)
        web = VGroup(wbox, w_title, rest_lbl, agui_lbl, c_order, c_class, c_chat, c_prog, c_hitl)

        # ---------- backend APIs ----------
        bbox = RoundedRectangle(width=2.0, height=4.6, corner_radius=0.2, color=LINE, stroke_width=2,
                                fill_color=LINE, fill_opacity=0.08).move_to([0.2, 0.2, 0])
        b_lbl = Text("Backend APIs", font_size=15, color=MUTED).move_to(bbox.get_top() + DOWN * 0.3)
        rest_api = component("REST API", ["JSON"], REST_C, 1.7, 1.0, [0.2, 1.1, 0])
        agui_api = component("AG-UI API", ["SSE events"], AGUI_C, 1.7, 1.0, [0.2, -0.75, 0])
        backend = VGroup(bbox, b_lbl, rest_api, agui_api)

        # ---------- Foundry ----------
        fbox = RoundedRectangle(width=3.3, height=4.6, corner_radius=0.2, color=FOUNDRY_C, stroke_width=3,
                                fill_color=FOUNDRY_C, fill_opacity=0.08).move_to([4.85, 0.2, 0])
        f_title = Text("Microsoft Foundry", font_size=18, color=FOUNDRY_C).move_to(fbox.get_top() + DOWN * 0.3)
        agent1 = component("Order Agent", ["Prompt Agent", "Order status, tickets"], AGENT1_C,
                           2.8, 1.05, [4.85, 1.3, 0])
        agent2 = component("Research Agent", ["Prompt Agent", "Chat and tool calls"], AGENT2_C,
                           2.8, 1.05, [4.85, 0.05, 0])
        agent3 = component("Refund Agent", ["Prompt Agent", "Proposes a refund"], AGENT3_C,
                           2.8, 1.05, [4.85, -1.2, 0])
        foundry = VGroup(fbox, f_title, agent1, agent2, agent3)

        # ---------- connections (dashed idle lines) ----------
        def dline(a, b):
            return DashedLine(a, b, color=LINE, stroke_width=1.5)

        l_user = dline(user.get_right() + RIGHT * 0.1, wbox.get_left())
        # card -> API (start at card, end at API)
        lc_order = dline(c_order[0].get_right(), rest_api[0].get_left())
        lc_class = dline(c_class[0].get_right(), rest_api[0].get_left())
        lc_chat = dline(c_chat[0].get_right(), agui_api[0].get_left())
        lc_prog = dline(c_prog[0].get_right(), agui_api[0].get_left())
        lc_hitl = dline(c_hitl[0].get_right(), agui_api[0].get_left())
        # API -> agent (start at API, end at agent)
        la_order = dline(rest_api[0].get_right(), agent1[0].get_left())
        la_chat = dline(agui_api[0].get_right(), agent2[0].get_left())
        la_hitl = dline(agui_api[0].get_right(), agent3[0].get_left())
        links = VGroup(l_user, lc_order, lc_class, lc_chat, lc_prog, lc_hitl, la_order, la_chat, la_hitl)

        status = Text("A web app with REST and AG-UI use cases, calling Foundry agents through its own Backend APIs",
                      font_size=20).to_edge(DOWN, buff=0.25)
        self.add(status)

        def say(msg, color=INK):
            status.become(Text(msg, font_size=22, color=color).to_edge(DOWN, buff=0.25))

        self.play(FadeIn(user), FadeIn(web), run_time=1.2)
        self.play(FadeIn(backend), FadeIn(foundry), run_time=1)
        self.play(Create(links), run_time=1.2)
        self.wait(0.5)

        def hl(mob, color=HILITE):
            r = SurroundingRectangle(mob, color=color, buff=0.06, stroke_width=3)
            self.play(Create(r), run_time=0.35)
            return r

        def lit(line, color):
            return line.animate.set_color(color).set_stroke(width=3)

        def unlit(line):
            return line.animate.set_color(LINE).set_stroke(width=1.5)

        def travel(pkt, pts, t=0.7):
            for p in pts:
                self.play(pkt.animate.move_to(p), run_time=t)

        def ends(line, reverse=False):
            return (line.get_end(), line.get_start()) if reverse else (line.get_start(), line.get_end())

        # ---------- REST: one request, one response ----------
        def rest_call(c, lc, la, agent, ag_color, label, back, msgs, full=True):
            say(msgs[0], REST_C)
            r_c = hl(c)
            q = packet(label, REST_C).move_to(lc.get_start())
            self.play(FadeIn(q), lit(lc, REST_C), run_time=0.3)
            travel(q, [lc.get_end()])
            r_api = hl(rest_api, REST_C)
            say(msgs[1], REST_C)
            self.play(lit(la, REST_C), q.animate.move_to(la.get_start()), run_time=0.3)
            travel(q, [la.get_end()])
            r_ag = hl(agent, ag_color)
            self.play(FadeOut(q), run_time=0.2)
            say(msgs[2], OK_C)
            self.wait(0.6)
            a = packet(back, OK_C).move_to(la.get_end())
            self.play(FadeIn(a), run_time=0.2)
            travel(a, [la.get_start()])
            self.play(unlit(la), a.animate.move_to(lc.get_end()), run_time=0.3)
            travel(a, [lc.get_start()])
            self.play(FadeOut(a), unlit(lc), FadeOut(r_api), FadeOut(r_ag), FadeOut(r_c), run_time=0.4)

        say("The user opens the web app, which offers REST and AG-UI use cases", WEB_C)
        req = packet("HTTPS", WEB_C).move_to(l_user.get_start())
        self.play(FadeIn(req), lit(l_user, WEB_C), run_time=0.3)
        self.play(req.animate.move_to(l_user.get_end()), run_time=1.0)
        r_web = hl(wbox, WEB_C)
        self.play(FadeOut(req), unlit(l_user), run_time=0.3)

        say("REST: ask once, wait, receive one complete response", REST_C)
        self.wait(1.0)

        rest_call(c_order, lc_order, la_order, agent1, AGENT1_C, "GET /orders/1042", "shipped",
                  ["1. Look up an order: the Web App sends a JSON request",
                   "2. The REST API calls the Foundry agent directly",
                   "3. One complete answer returns to the Web App"])
        rest_call(c_class, lc_class, la_order, agent1, AGENT1_C, "POST /tickets", "billing",
                  ["4. Classify a ticket: another simple request and response",
                   "5. Same REST API, same agent, no streaming needed",
                   "6. The label returns in one JSON response"])

        # ---------- AG-UI: a stream of events ----------
        say("AG-UI: ask once, then receive a live stream of events", AGUI_C)
        self.wait(1.0)

        def start_run(c, lc, la, agent, ag_color, label):
            r_c = hl(c, AGUI_C)
            q = packet(label, AGUI_C).move_to(lc.get_start())
            self.play(FadeIn(q), lit(lc, AGUI_C), run_time=0.3)
            travel(q, [lc.get_end()])
            r_api = hl(agui_api, AGUI_C)
            self.play(lit(la, AGUI_C), q.animate.move_to(la.get_start()), run_time=0.3)
            travel(q, [la.get_end()])
            r_ag = hl(agent, ag_color)
            self.play(FadeOut(q), run_time=0.2)
            return r_c, r_api, r_ag

        def stream(events, lc, la):
            for ev in events:
                col = OK_C if ev == "RUN_FINISHED" else AGUI_C
                p = packet(ev, col).move_to(la.get_end())
                self.add(p)
                travel(p, [la.get_start(), lc.get_end(), lc.get_start()], 0.5)
                self.play(FadeOut(p), run_time=0.15)

        def end_run(lc, la, rs):
            self.play(unlit(lc), unlit(la), *[FadeOut(r) for r in rs], run_time=0.4)

        # --- streaming chat ---
        say("7. Stream a chat answer: the Web App starts an AG-UI run", AGUI_C)
        rs = start_run(c_chat, lc_chat, la_chat, agent2, AGENT2_C, "run: explain topic")
        say("8. Text arrives token by token and is rendered as it is written", AGUI_C)
        stream(["RUN_STARTED", "TEXT_MESSAGE_CONTENT", "TEXT_MESSAGE_CONTENT", "RUN_FINISHED"], lc_chat, la_chat)
        end_run(lc_chat, la_chat, rs)

        # --- live progress ---
        say("9. Live agent progress: the Web App shows what the agent is doing", AGUI_C)
        rs = start_run(c_prog, lc_prog, la_chat, agent2, AGENT2_C, "run: research topic")
        say("10. Tool call and step events let the UI show each step as it happens", AGUI_C)
        stream(["STEP_STARTED", "TOOL_CALL_START", "TOOL_CALL_END", "RUN_FINISHED"], lc_prog, la_chat)
        end_run(lc_prog, la_chat, rs)

        # --- human in the loop ---
        say("11. Human in the loop: the user asks for a refund", AGUI_C)
        rs = start_run(c_hitl, lc_hitl, la_hitl, agent3, AGENT3_C, "run: refund order 1042")
        say("12. The agent proposes a tool call and pauses until a person decides", AGENT3_C)
        stream(["RUN_STARTED", "TOOL_CALL: refund 250", "RUN_FINISHED (paused)"], lc_hitl, la_hitl)
        end_run(lc_hitl, la_hitl, rs)

        dlg_box = RoundedRectangle(width=3.3, height=1.6, corner_radius=0.12, color=AGENT3_C,
                                   fill_color=WHITE, fill_opacity=1, stroke_width=3).move_to([-3.6, -0.5, 0])
        dlg_t = Text("Agent wants to refund 250", font_size=14, color=INK).move_to(dlg_box.get_top() + DOWN * 0.35)
        btn_ok = RoundedRectangle(width=1.3, height=0.45, corner_radius=0.08, color=OK_C, fill_color=OK_C,
                                  fill_opacity=1, stroke_width=1).move_to(dlg_box.get_bottom() + UP * 0.4 + LEFT * 0.8)
        btn_ok_t = Text("Approve", font_size=13, color=WHITE).move_to(btn_ok)
        btn_no = RoundedRectangle(width=1.3, height=0.45, corner_radius=0.08, color=ERR_C, fill_color=ERR_C,
                                  fill_opacity=1, stroke_width=1).move_to(dlg_box.get_bottom() + UP * 0.4 + RIGHT * 0.8)
        btn_no_t = Text("Reject", font_size=13, color=WHITE).move_to(btn_no)
        dlg = VGroup(dlg_box, dlg_t, btn_ok, btn_ok_t, btn_no, btn_no_t)

        say("13. The Web App shows an approval dialog: a human makes the decision", AGENT3_C)
        self.play(FadeIn(dlg), run_time=0.5)
        self.wait(0.8)
        click = packet("user clicks Approve", OK_C).move_to(user.get_right() + RIGHT * 0.9)
        self.play(FadeIn(click), lit(l_user, OK_C), run_time=0.3)
        self.play(click.animate.move_to(btn_ok.get_center() + UP * 0.45), run_time=1.0)
        r_btn = hl(btn_ok, HILITE)
        self.play(FadeOut(click), unlit(l_user), run_time=0.3)
        self.play(FadeOut(dlg), FadeOut(r_btn), run_time=0.4)

        say("14. The decision goes back to the same AG-UI API as a tool result and the run resumes", AGUI_C)
        rs = start_run(c_hitl, lc_hitl, la_hitl, agent3, AGENT3_C, "tool result: approved")
        say("15. The agent completes the refund and streams the outcome", OK_C)
        stream(["RUN_STARTED", "TEXT_MESSAGE_CONTENT", "RUN_FINISHED"], lc_hitl, la_hitl)
        end_run(lc_hitl, la_hitl, rs)

        # ---------- summary ----------
        self.play(FadeOut(r_web), run_time=0.3)
        say("REST: one request, one response.   AG-UI: streaming, live progress and human approval.", OK_C)
        self.wait(2.5)
        say("Direct calls to Foundry agents through Backend APIs, with no APIM in between", OK_C)
        self.wait(2.5)
