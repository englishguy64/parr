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

WEB_C = BURGUNDY
APIM_C = "#0f766e"
PE_C = "#475569"
FOUNDRY_C = GOLD
AGENT1_C = "#a33a5c"
AGENT2_C = SLATE
HOSTED_C = "#6d4c9f"
VNET_C = "#475569"


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


def container_icon(color):
    # Small stack of shipping-container blocks: the usual "containerised app" symbol.
    blocks = VGroup(*[Square(side_length=0.09, color=color, fill_color=color, fill_opacity=0.9, stroke_width=0)
                      for _ in range(6)])
    blocks.arrange_in_grid(rows=2, cols=3, buff=0.025)
    frame = SurroundingRectangle(blocks, color=color, buff=0.04, stroke_width=1.5, corner_radius=0.03)
    return VGroup(frame, blocks)


def agent_box(title, sub, color, y, container=False):
    box = RoundedRectangle(width=2.7, height=0.68, corner_radius=0.1, color=color,
                           fill_color=color, fill_opacity=0.14, stroke_width=3).move_to([5.35, y, 0])
    ttl = Text(title, font_size=15, color=color).move_to(box.get_top() + DOWN * 0.2)
    txt = Text(sub, font_size=12, color=INK).move_to(box.get_bottom() + UP * 0.19)
    grp = VGroup(box, ttl, txt)
    if container:
        icon = container_icon(color).move_to(box.get_left() + RIGHT * 0.3 + UP * 0.17)
        tag = Text("container", font_size=10, color=color).move_to(box.get_right() + LEFT * 0.4 + UP * 0.17)
        grp.add(icon, tag)
    return grp


def subnet(name, cidr, x):
    box = RoundedRectangle(width=1.85, height=4.5, corner_radius=0.12, color=VNET_C, stroke_width=2,
                           fill_color=VNET_C, fill_opacity=0.05)
    box.move_to([x, -0.2, 0])
    lbl = VGroup(Text(name, font_size=14, color=VNET_C),
                 Text(cidr, font_size=14, color=INK)).arrange(DOWN, buff=0.08)
    lbl.move_to(box.get_top() + DOWN * 0.5)
    return VGroup(box, lbl)


class WebAppToFoundry(Scene):
    def construct(self):
        title = Text("Use an Azure Web App to Call Foundry Agents via Azure APIM", font_size=28,
                     color=BURGUNDY).to_edge(UP, buff=0.25)
        self.add(title)

        # ---------- user / browser ----------
        head = Circle(radius=0.17, color=INK, stroke_width=3)
        body = Arc(radius=0.32, start_angle=0, angle=PI, color=INK, stroke_width=3).shift(DOWN * 0.5)
        user = VGroup(head, body, Text("User", font_size=16).shift(DOWN * 0.8)).move_to([-6.35, -0.3, 0])

        # ---------- virtual network and subnets ----------
        vnet = RoundedRectangle(width=7.7, height=5.7, corner_radius=0.2, color=VNET_C, stroke_width=3,
                                fill_color=VNET_C, fill_opacity=0.04).move_to([-1.75, 0, 0])
        vnet_lbl = Text("Virtual Network   vnet-ai   10.0.0.0/16", font_size=15, color=VNET_C)
        vnet_lbl.move_to(vnet.get_top() + DOWN * 0.3)

        sn_web = subnet("snet-web", "10.0.1.0/24", -4.55)
        sn_apim = subnet("snet-apim", "10.0.2.0/24", -2.65)
        sn_api = subnet("snet-api", "10.0.4.0/24", -0.75)
        sn_pe = subnet("snet-pe", "10.0.3.0/24", 1.15)

        # ---------- components ----------
        web = component("Web App", ["Azure App Service", "Front end", "VNet integration"], WEB_C,
                        1.75, 1.7, [-4.55, -0.4, 0])
        apim = component("APIM", ["Developer tier", "Internal VNet mode", "10.0.2.4"], APIM_C,
                         1.75, 2.0, [-2.65, -0.45, 0])
        backend = component("Backend API", ["Azure App Service", "VNet integration"], OK_C,
                            1.75, 1.5, [-0.75, -0.4, 0])
        pe = component("Private Endpoint", ["Foundry", "10.0.3.4"], PE_C,
                       1.8, 1.4, [1.15, -0.4, 0])
        # ACR is outside the VNet: Basic tier, public endpoint, Entra ID authentication only.
        acr = component("ACR", ["Container Registry", "Entra ID auth only"], HOSTED_C,
                        1.5, 1.1, [3.0, -1.9, 0])

        # ---------- Foundry ----------
        fbox = RoundedRectangle(width=2.9, height=5.7, corner_radius=0.2, color=FOUNDRY_C, stroke_width=3,
                                fill_color=FOUNDRY_C, fill_opacity=0.08).move_to([5.35, 0, 0])
        f_title = Text("Microsoft Foundry", font_size=18, color=FOUNDRY_C).move_to(fbox.get_top() + DOWN * 0.3)
        f_sub = Text("Project: ai-agents", font_size=13, color=MUTED).next_to(f_title, DOWN, buff=0.1)
        agent1 = agent_box("Prompt Agent", "Support: answers questions", AGENT1_C, 1.51)
        agent2 = agent_box("Prompt Agent", "Research: summarises docs", AGENT2_C, 0.56)
        hosted_a = agent_box("Hosted Agent", "Order Lookup: finds order status", HOSTED_C, -0.39, container=True)
        hosted_o = agent_box("Hosted Agent", "Orchestrator: plans, delegates", HOSTED_C, -1.34, container=True)
        hosted_b = agent_box("Hosted Agent", "Policy Check: applies return rules", HOSTED_C, -2.29, container=True)
        foundry = VGroup(fbox, f_title, f_sub, agent1, agent2, hosted_a, hosted_o, hosted_b)

        # ---------- connections (dashed idle lines) ----------
        def link(a, b):
            return DashedLine(a.get_right(), b.get_left(), color=LINE, stroke_width=1.5)

        l_user = DashedLine(user.get_right() + RIGHT * 0.1, web[0].get_left(), color=LINE, stroke_width=1.5)
        l_web = link(web[0], apim[0])
        l_apim = DashedLine(apim[0].get_right(), backend[0].get_left(), color=LINE, stroke_width=1.5)
        l_be = DashedLine(backend[0].get_right(), pe[0].get_left(), color=LINE, stroke_width=1.5)
        l_a1 = DashedLine(pe[0].get_right(), agent1[0].get_left(), color=LINE, stroke_width=1.5)
        l_a2 = DashedLine(pe[0].get_right(), agent2[0].get_left(), color=LINE, stroke_width=1.5)
        l_a3 = DashedLine(pe[0].get_right(), hosted_o[0].get_left(), color=LINE, stroke_width=1.5)
        l_oa = DashedLine(hosted_o[0].get_top(), hosted_a[0].get_bottom(), color=LINE, stroke_width=1.5)
        l_ob = DashedLine(hosted_o[0].get_bottom(), hosted_b[0].get_top(), color=LINE, stroke_width=1.5)
        l_acr = DashedLine(acr[0].get_right(), [fbox.get_left()[0], -1.9, 0], color=LINE, stroke_width=1.5)
        links = VGroup(l_acr, l_user, l_web, l_apim, l_be, l_a1, l_a2, l_a3, l_oa, l_ob)

        status = Text("A front end hosted in Azure App Service calls Foundry agents through APIM",
                      font_size=22).to_edge(DOWN, buff=0.25)
        self.add(status)

        def say(msg, color=INK):
            status.become(Text(msg, font_size=22, color=color).to_edge(DOWN, buff=0.25))

        self.play(FadeIn(user), Create(vnet), FadeIn(vnet_lbl), run_time=1)
        self.play(FadeIn(sn_web), FadeIn(sn_apim), FadeIn(sn_api), FadeIn(sn_pe), run_time=1)
        self.play(FadeIn(web), FadeIn(apim), FadeIn(backend), FadeIn(pe), FadeIn(acr), run_time=1)
        self.play(FadeIn(foundry), run_time=1)
        self.play(Create(links), run_time=1.2)
        self.wait(0.5)

        def travel(pkt, points, run_time=0.9):
            for p in points:
                self.play(pkt.animate.move_to(p), run_time=run_time)

        def hl(mob, color=HILITE):
            r = SurroundingRectangle(mob, color=color, buff=0.06, stroke_width=3)
            self.play(Create(r), run_time=0.4)
            return r

        def lit(line, color):
            return line.animate.set_color(color).set_stroke(width=3)

        def unlit(line):
            return line.animate.set_color(LINE).set_stroke(width=1.5)

        # Hosted Agents are containers: Foundry signs in to ACR with Entra ID, then pulls the images.
        say("Hosted Agents are containers: Foundry signs in to ACR with Entra ID, then pulls the images", HOSTED_C)
        tok = packet("token", ERR_C if "ERR_C" in globals() else HOSTED_C).move_to(l_acr.get_end())
        self.play(FadeIn(tok), lit(l_acr, HOSTED_C), run_time=0.3)
        self.play(tok.animate.move_to(l_acr.get_start()), run_time=0.8)
        r_acr = hl(acr, HOSTED_C)
        self.play(FadeOut(tok), run_time=0.2)
        img = packet("image", HOSTED_C).move_to(l_acr.get_start())
        self.play(FadeIn(img), run_time=0.2)
        self.play(img.animate.move_to(l_acr.get_end()), run_time=0.9)
        self.play(FadeOut(img), unlit(l_acr), FadeOut(r_acr), run_time=0.3)
        self.wait(0.5)
        say("A front end hosted in Azure App Service calls Foundry agents through APIM")
        self.wait(0.3)

        # ---------- 1. user -> web app ----------
        say("1. The user opens the front end hosted in Azure App Service", WEB_C)
        req = packet("HTTPS", WEB_C).move_to(l_user.get_start())
        self.play(FadeIn(req), lit(l_user, WEB_C), run_time=0.3)
        travel(req, [l_user.get_end()], 1.1)
        r_web = hl(web)
        self.play(FadeOut(req), unlit(l_user), run_time=0.3)

        # ---------- request / response to an agent ----------
        def call_agent(agent, l_agent, color, label, back_label, step_a, step_b, step_c, step_d, step_e):
            say(step_a, WEB_C)
            q = packet(label, color).move_to(l_web.get_start())
            self.play(FadeIn(q), lit(l_web, color), run_time=0.3)
            travel(q, [l_web.get_end()], 1.0)
            r_apim = hl(apim)
            self.wait(0.3)

            say(step_b, APIM_C)
            self.play(unlit(l_web), lit(l_apim, color), q.animate.move_to(l_apim.get_start()), run_time=0.4)
            travel(q, [l_apim.get_end()], 1.0)
            r_be = hl(backend, OK_C)
            self.wait(0.3)

            say(step_c, OK_C)
            self.play(unlit(l_apim), lit(l_be, color), q.animate.move_to(l_be.get_start()), run_time=0.4)
            travel(q, [l_be.get_end()], 1.0)
            r_pe = hl(pe)

            say(step_d, PE_C)
            self.play(unlit(l_be), lit(l_agent, color), q.animate.move_to(l_agent.get_start()), run_time=0.5)
            travel(q, [l_agent.get_end()], 1.0)
            r_ag = hl(agent)
            self.play(FadeOut(q), run_time=0.2)
            self.wait(0.5)

            say(step_e, OK_C)
            a = packet(back_label, OK_C).move_to(l_agent.get_end())
            self.play(FadeIn(a), run_time=0.2)
            travel(a, [l_agent.get_start()], 1.0)
            self.play(unlit(l_agent), lit(l_be, OK_C), a.animate.move_to(l_be.get_end()), run_time=0.5)
            travel(a, [l_be.get_start()], 1.0)
            self.play(unlit(l_be), lit(l_apim, OK_C), a.animate.move_to(l_apim.get_end()), run_time=0.5)
            travel(a, [l_apim.get_start()], 1.0)
            self.play(unlit(l_apim), lit(l_web, OK_C), a.animate.move_to(l_web.get_end()), run_time=0.8)
            travel(a, [l_web.get_start()], 1.0)
            self.play(FadeOut(a), unlit(l_web), FadeOut(r_apim), FadeOut(r_be), FadeOut(r_pe), FadeOut(r_ag), run_time=0.4)

        call_agent(agent1, l_a1, AGENT1_C, "POST /support", "answer",
                   "2. Web App calls the API in APIM over the VNet (snet-web to snet-apim)",
                   "3. APIM routes the call to the Backend API (snet-api)",
                   "4. The Backend API calls Foundry through the Private Endpoint (snet-pe)",
                   "5. The Support prompt agent handles the request",
                   "6. The answer returns via the Backend and APIM to the Web App")

        call_agent(agent2, l_a2, AGENT2_C, "POST /research", "summary",
                   "7. Web App calls another API in APIM for the Research prompt agent",
                   "8. APIM routes the call to the Backend API",
                   "9. The Backend API calls Foundry through the same Private Endpoint",
                   "10. The Research prompt agent handles the request",
                   "11. The summary returns via the Backend and APIM to the Web App")

        # ---------- orchestrated call: Hosted Agent orchestrator -> two custom Hosted Agents ----------
        say("12. Web App calls APIM with a return request that needs several steps", WEB_C)
        q = packet("POST /orchestrate", HOSTED_C).move_to(l_web.get_start())
        self.play(FadeIn(q), lit(l_web, HOSTED_C), run_time=0.3)
        travel(q, [l_web.get_end()], 1.0)
        r_apim = hl(apim)
        say("13. APIM routes to the Backend API, which calls Foundry through the Private Endpoint", APIM_C)
        self.play(unlit(l_web), lit(l_apim, HOSTED_C), q.animate.move_to(l_apim.get_start()), run_time=0.4)
        travel(q, [l_apim.get_end()], 1.0)
        r_be = hl(backend, OK_C)
        self.play(unlit(l_apim), lit(l_be, HOSTED_C), q.animate.move_to(l_be.get_start()), run_time=0.4)
        travel(q, [l_be.get_end()], 1.0)
        r_pe = hl(pe)
        say("14. The orchestrator Hosted Agent receives the request and plans the steps", HOSTED_C)
        self.play(unlit(l_be), lit(l_a3, HOSTED_C), q.animate.move_to(l_a3.get_start()), run_time=0.4)
        travel(q, [l_a3.get_end()], 1.0)
        r_o = hl(hosted_o)
        self.play(FadeOut(q), unlit(l_a3), run_time=0.2)

        say("15. The orchestrator delegates to the Order Lookup and Policy Check Hosted Agents", HOSTED_C)
        qa = packet("find order", HOSTED_C).move_to(l_oa.get_start())
        qb = packet("check policy", HOSTED_C).move_to(l_ob.get_start())
        self.play(FadeIn(qa), FadeIn(qb), lit(l_oa, HOSTED_C), lit(l_ob, HOSTED_C), run_time=0.3)
        self.play(qa.animate.move_to(l_oa.get_end()), qb.animate.move_to(l_ob.get_end()), run_time=1.0)
        r_a = hl(hosted_a)
        r_b = hl(hosted_b)
        self.wait(0.5)

        say("16. Both agents return their results to the orchestrator, which combines them", OK_C)
        self.play(FadeOut(qa), FadeOut(qb), run_time=0.2)
        ra = packet("order found", OK_C).move_to(l_oa.get_end())
        rb = packet("eligible", OK_C).move_to(l_ob.get_end())
        self.play(FadeIn(ra), FadeIn(rb), run_time=0.2)
        self.play(ra.animate.move_to(l_oa.get_start()), rb.animate.move_to(l_ob.get_start()), run_time=1.0)
        self.play(FadeOut(ra), FadeOut(rb), unlit(l_oa), unlit(l_ob), FadeOut(r_a), FadeOut(r_b), run_time=0.3)

        say("17. The combined answer returns via the Backend and APIM to the Web App", OK_C)
        a = packet("combined", OK_C).move_to(l_a3.get_end())
        self.play(FadeIn(a), lit(l_a3, OK_C), run_time=0.2)
        travel(a, [l_a3.get_start()], 1.0)
        self.play(unlit(l_a3), lit(l_be, OK_C), a.animate.move_to(l_be.get_end()), run_time=0.5)
        travel(a, [l_be.get_start()], 1.0)
        self.play(unlit(l_be), lit(l_apim, OK_C), a.animate.move_to(l_apim.get_end()), run_time=0.5)
        travel(a, [l_apim.get_start()], 1.0)
        self.play(unlit(l_apim), lit(l_web, OK_C), a.animate.move_to(l_web.get_end()), run_time=0.8)
        travel(a, [l_web.get_start()], 1.0)
        self.play(FadeOut(a), unlit(l_web), FadeOut(r_apim), FadeOut(r_be), FadeOut(r_pe), FadeOut(r_o), run_time=0.4)

        # ---------- web app -> user ----------
        say("18. The Web App shows the results to the user", OK_C)
        out = packet("results", OK_C).move_to(l_user.get_end())
        self.play(FadeIn(out), lit(l_user, OK_C), run_time=0.3)
        travel(out, [l_user.get_start()], 1.1)
        self.play(FadeOut(out), unlit(l_user), FadeOut(r_web), run_time=0.4)
        say("Web App  >  APIM  >  Backend API  >  Private Endpoint  >  Foundry agents, kept on private IPs", OK_C)
        self.wait(2.5)
