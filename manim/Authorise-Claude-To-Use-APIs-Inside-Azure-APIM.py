import numpy as np
from manim import *

# ---- parr color scheme (Source/parr/styles.css), light background ----
config.background_color = "#f5f7fa"
INK = "#222222"
BURGUNDY = "#7a1f3d"
WHITE = INK
BLACK = "#ffffff"
GRAY_B = "#6b7280"
GRAY_D = "#9ca3af"
YELLOW = "#b8860b"
GREEN = "#2e7d5b"
RED = "#b91c1c"
PURPLE = BURGUNDY
TEAL = "#0f766e"
BLUE = "#475569"
BLUE_C = "#a33a5c"
ORANGE = BURGUNDY

CLAUDE_C = ORANGE
VNET_C = BLUE
APIM_C = "#2684FF"
POLICY_C = PURPLE
HEADER_C = RED
PAYLOAD_C = BLUE_C
SIG_C = GREEN

Text.set_default(font="Arial", color=INK)

INSTANCE_URL = "https://claude-demo-apim.azure-api.net/orders/v1"


def packet(label, color):
    box = RoundedRectangle(width=max(0.5, 0.11 * len(label) + 0.25), height=0.32, corner_radius=0.08,
                           color=color, fill_color=color, fill_opacity=0.9, stroke_width=1)
    txt = Text(label, font_size=12, color=BLACK).move_to(box)
    return VGroup(box, txt)


def tick(pos):
    p = np.array(pos)
    return VGroup(Line(p + [-0.08, 0.0, 0], p + [-0.02, -0.07, 0], color=GREEN, stroke_width=3),
                  Line(p + [-0.02, -0.07, 0], p + [0.09, 0.08, 0], color=GREEN, stroke_width=3))


def cross(pos):
    p = np.array(pos)
    return VGroup(Line(p + [-0.08, -0.08, 0], p + [0.08, 0.08, 0], color=RED, stroke_width=3),
                  Line(p + [-0.08, 0.08, 0], p + [0.08, -0.08, 0], color=RED, stroke_width=3))


class JWTTokenToAPIM(Scene):
    def construct(self):
        # ======================= Part 1: the token in English =======================
        title = Text("Authorise Claude To Use APIs Inside Azure APIM", font_size=32, color=BURGUNDY).to_edge(UP, buff=0.3)
        self.add(title)

        h_raw = Text("eyJhbGciOiJSUzI1NiJ9", font_size=20, color=HEADER_C)
        p_raw = Text("eyJpc3MiOiJsb2dpbi4uLiJ9", font_size=20, color=PAYLOAD_C)
        s_raw = Text("SflKxwRJSMeKKF2QT4fw", font_size=20, color=SIG_C)
        d1, d2 = Text(".", font_size=20), Text(".", font_size=20)
        token = VGroup(h_raw, d1, p_raw, d2, s_raw).arrange(RIGHT, buff=0.08).move_to(UP * 2.0)
        tok_lbl = Text("What the token looks like on the wire (three parts)", font_size=18, color=GRAY_B)
        tok_lbl.next_to(token, UP, buff=0.2)
        self.play(FadeIn(tok_lbl), Write(token), run_time=1.5)

        def card(name, color, lines, part):
            head = Text(name, font_size=20, color=color)
            body = Text("\n".join(lines), font_size=16, line_spacing=0.9)
            g = VGroup(head, body).arrange(DOWN, buff=0.15, aligned_edge=LEFT)
            box = SurroundingRectangle(g, color=color, buff=0.18, corner_radius=0.1)
            g = VGroup(box, g)
            g.move_to([part.get_center()[0], -0.6, 0])
            return g

        c_head = card("HEADER", HEADER_C, ["How it is signed:", "Algorithm: RS256", "Type: JWT"], h_raw)
        c_pay = card("PAYLOAD (the claims)", PAYLOAD_C,
                     ["Issuer: login.contoso-idp.example", "Subject: claude-agent",
                      "Audience: api://orders", "Scope: orders.read", "Expires: in 1 hour"], p_raw)
        c_sig = card("SIGNATURE", SIG_C, ["The issuer's digital seal.", "Proves the token was", "not changed."], s_raw)
        c_head.set_x(max(c_head.get_x(), -4.7))
        c_sig.set_x(min(c_sig.get_x(), 4.7))
        for c, raw, col in ((c_head, h_raw, HEADER_C), (c_pay, p_raw, PAYLOAD_C), (c_sig, s_raw, SIG_C)):
            arr = Arrow(raw.get_bottom(), c.get_top(), buff=0.1, color=col, stroke_width=3)
            self.play(Create(arr), FadeIn(c), run_time=1.2)
            self.wait(0.8)
        note = Text("Plain English: \"Contoso's login server says claude-agent may read orders for the next hour.\"",
                    font_size=18, color=YELLOW).to_edge(DOWN, buff=0.5)
        self.play(FadeIn(note))
        self.wait(3)
        self.play(*[FadeOut(m) for m in self.mobjects])

        # ======================= Part 2: architecture =======================
        title = Text("Authorise Claude To Use APIs Inside Azure APIM", font_size=32, color=BURGUNDY).to_edge(UP, buff=0.25)
        self.add(title)

        claude = VGroup(
            RoundedRectangle(width=2.2, height=1.2, corner_radius=0.15, color=CLAUDE_C,
                             fill_color=CLAUDE_C, fill_opacity=0.2, stroke_width=3),
            Text("Claude", font_size=26, color=CLAUDE_C),
        ).move_to(LEFT * 5.4 + UP * 0.3)
        sub_claude = Text("(client with a JWT)", font_size=13, color=GRAY_B).next_to(claude, UP, buff=0.1)
        url_lbl = Text("POST\nclaude-demo-apim\n.azure-api.net/orders/v1", font_size=12, line_spacing=0.9)
        url_lbl.move_to(LEFT * 4.9 + DOWN * 1.1)
        auth_lbl = Text("Authorization:\nBearer <JWT>", font_size=12, color=YELLOW, line_spacing=0.9)
        auth_lbl.next_to(url_lbl, DOWN, buff=0.15)
        inet = Text("Public internet", font_size=13, color=GRAY_B).move_to(LEFT * 3.4 + DOWN * 0.15)

        vnet = RoundedRectangle(width=9.3, height=5.4, corner_radius=0.2, color=VNET_C, stroke_width=3)
        vnet = DashedVMobject(vnet, num_dashes=90).move_to(RIGHT * 2.25 + DOWN * 0.0)
        vnet_lbl = Text("Private VNET  10.0.0.0/16", font_size=16, color=VNET_C).move_to(RIGHT * 0.2 + UP * 2.4)

        endpoint = VGroup(Circle(radius=0.17, color=GREEN, fill_color=GREEN, fill_opacity=0.5),
                          Text("Public API endpoint", font_size=12, color=GREEN).shift(UP * 0.4))
        endpoint.move_to(LEFT * 2.4 + UP * 0.3)

        apim = RoundedRectangle(width=3.6, height=3.3, corner_radius=0.15, color=APIM_C,
                                fill_color=APIM_C, fill_opacity=0.12, stroke_width=3).move_to(RIGHT * 0.9 + UP * 0.05)
        apim_t = Text("Azure API Management", font_size=15, color=APIM_C).move_to(apim.get_top() + DOWN * 0.22)

        policy = RoundedRectangle(width=3.2, height=2.4, corner_radius=0.1, color=POLICY_C,
                                  fill_color=POLICY_C, fill_opacity=0.15, stroke_width=3)
        policy.move_to(RIGHT * 0.9 + DOWN * 0.2)
        pol_t = Text("Fragment", font_size=16, color=POLICY_C).move_to(policy.get_top() + DOWN * 0.2)
        pol_s = Text("validate-jwt", font_size=12, color=GRAY_B).next_to(pol_t, DOWN, buff=0.05)

        checks = ["Signature is valid", "Issuer is trusted", "Audience matches API",
                  "Token not expired", "Scope: orders.read"]
        row_y = [policy.get_top()[1] - 0.85 - 0.3 * i for i in range(len(checks))]
        rows = VGroup(*[Text(c, font_size=13).move_to([-0.25, y, 0], aligned_edge=LEFT)
                        for c, y in zip(checks, row_y)])
        mark_x = -0.45

        backend = VGroup(
            RoundedRectangle(width=2.2, height=1.2, corner_radius=0.12, color=TEAL,
                             fill_color=TEAL, fill_opacity=0.2, stroke_width=3),
            Text("Orders API\n(private backend)", font_size=15, line_spacing=0.9),
        ).move_to(RIGHT * 5.2 + UP * 0.3)

        self.play(FadeIn(claude), FadeIn(sub_claude))
        self.play(Create(vnet), FadeIn(vnet_lbl), run_time=1.5)
        self.play(FadeIn(apim), FadeIn(apim_t), FadeIn(policy), FadeIn(pol_t), FadeIn(pol_s), FadeIn(rows))
        self.play(FadeIn(backend), FadeIn(endpoint), FadeIn(inet))
        self.play(FadeIn(url_lbl), FadeIn(auth_lbl))

        status = Text("APIM sits inside a private VNET; only its API endpoint is public", font_size=22)
        status.to_edge(DOWN, buff=0.25)
        self.add(status)
        self.wait(2)

        def say(msg, color=WHITE):
            status.become(Text(msg, font_size=22, color=color).to_edge(DOWN, buff=0.25))

        # key points along the request path
        p_claude = claude.get_right() + RIGHT * 0.1
        p_endpoint = endpoint[0].get_center()
        p_policy_in = policy.get_left() + LEFT * 0.05
        p_apim_out = apim.get_right() + RIGHT * 0.05
        p_backend_in = backend.get_left()

        def travel(pkt, pts, t=0.7):
            for pt in pts:
                self.play(pkt.animate.move_to(pt), run_time=t)

        def run_case(label, color, fail_idx, status_msgs):
            marks = VGroup()
            pkt = packet(label, color).move_to(p_claude)
            say(status_msgs[0], YELLOW)
            self.play(FadeIn(pkt))
            travel(pkt, [p_endpoint, p_policy_in])
            say(status_msgs[1], POLICY_C)
            self.play(FadeOut(pkt), policy.animate.set_stroke(YELLOW), run_time=0.3)
            ok = True
            for i, y in enumerate(row_y):
                if fail_idx == i:
                    m = cross([mark_x, y, 0])
                    ok = False
                    self.play(Create(m), rows[i].animate.set_color(RED), run_time=0.5)
                    marks.add(m)
                    break
                m = tick([mark_x, y, 0])
                marks.add(m)
                self.play(Create(m), rows[i].animate.set_color(GREEN), run_time=0.5)
            col = GREEN if ok else RED
            self.play(policy.animate.set_stroke(col).set_fill(col, opacity=0.2), run_time=0.4)
            self.wait(0.4)

            if ok:
                say(status_msgs[2], GREEN)
                fwd = packet("request", GREEN).move_to(p_policy_in + RIGHT * 0.1)
                self.play(FadeIn(fwd))
                travel(fwd, [p_apim_out, p_backend_in])
                self.play(backend[0].animate.set_stroke(YELLOW), run_time=0.3)
                data = packet("order data", TEAL).move_to(p_backend_in)
                self.play(FadeOut(fwd), FadeIn(data))
                travel(data, [p_apim_out, p_policy_in + RIGHT * 0.1], t=0.7)
                self.play(backend[0].animate.set_stroke(TEAL), run_time=0.2)
                code = packet("HTTP 200 OK", GREEN)
                code.move_to(data)
                self.play(Transform(data, code))
            else:
                say(status_msgs[2], RED)
                code = packet("HTTP 401 Unauthorized", RED).move_to(p_policy_in)
                data = code
                self.play(FadeIn(data))
                bk = Text("backend never called", font_size=12, color=RED).next_to(backend, DOWN, buff=0.1)
                self.play(FadeIn(bk))
            travel(data, [p_endpoint, p_claude], t=0.9)
            stamp_col = GREEN if ok else RED
            stamp = Text("HTTP 200 OK" if ok else "HTTP 401 Unauthorized", font_size=22, color=stamp_col)
            stamp.next_to(claude, DOWN, buff=1.9).shift(RIGHT * 0.2)
            self.play(FadeOut(data), FadeIn(stamp))
            self.wait(2)
            cleanup = [stamp, marks]
            if not ok:
                cleanup.append(bk)
            self.play(*[FadeOut(m) for m in cleanup],
                      *[r.animate.set_color(WHITE) for r in rows],
                      policy.animate.set_stroke(POLICY_C).set_fill(POLICY_C, opacity=0.15),
                      run_time=0.6)

        run_case("JWT (valid)", YELLOW, None,
                 ["1. Claude sends the request with its JWT to the public API endpoint",
                  "2. The Fragment checks the token inside APIM",
                  "3. All checks pass -> APIM calls the private backend"])
        run_case("JWT (expired)", YELLOW, 3,
                 ["Now Claude sends an expired JWT",
                  "The Fragment checks the token inside APIM",
                  "Token expired -> APIM rejects it with 401 Unauthorized"])

        say("Only the API is public - APIM and the backend stay inside the private VNET", GREEN)
        self.wait(3)

        # ======================= Part 3: the policy fragment XML =======================
        self.play(*[FadeOut(m) for m in self.mobjects])
        title3 = Text("Azure API Management Policy Fragment (XML): validate-jwt", font_size=32, color=BURGUNDY).to_edge(UP, buff=0.3)
        self.add(title3)

        cfg = {"font": "Consolas", "font_size": 14}

        # 3a: the API policy pulls the fragment in
        inc_lbl = Text("1. The API's inbound policy includes the fragment", font_size=20, color=YELLOW)
        inc = Code(code_string='<inbound>\n    <base />\n    <include-fragment fragment-id="validate-jwt" />\n</inbound>',
                   language="xml", background="rectangle", formatter_style="monokai", paragraph_config=cfg)
        inc.scale(1.6).move_to(DOWN * 0.2)
        inc_lbl.next_to(inc, UP, buff=0.4)
        self.play(FadeIn(inc_lbl), FadeIn(inc))
        self.wait(3)
        self.play(FadeOut(inc_lbl), FadeOut(inc))

        # 3b: the fragment itself, one check at a time
        xml = "\n".join([
            '<fragment>',
            '  <validate-jwt header-name="Authorization"',
            '                require-scheme="Bearer"',
            '                require-expiration-time="true"',
            '                require-signed-tokens="true"',
            '                failed-validation-httpcode="401"',
            '                failed-validation-error-message="Unauthorized">',
            '    <openid-config',
            '      url="https://login.contoso-idp.example/.well-known/openid-configuration" />',
            '    <audiences>',
            '      <audience>api://orders</audience>',
            '    </audiences>',
            '    <issuers>',
            '      <issuer>https://login.contoso-idp.example/</issuer>',
            '    </issuers>',
            '    <required-claims>',
            '      <claim name="scp" match="any">',
            '        <value>orders.read</value>',
            '      </claim>',
            '    </required-claims>',
            '  </validate-jwt>',
            '</fragment>',
        ])
        code = Code(code_string=xml, language="xml", background="rectangle", formatter_style="monokai",
                    paragraph_config=cfg)
        code.scale_to_fit_width(8.8)
        code.scale_to_fit_height(min(code.height, 5.3))
        code.move_to(LEFT * 2.5 + DOWN * 0.3)
        lbl = Text("2. The fragment: what APIM checks", font_size=20, color=YELLOW)
        lbl.next_to(code, UP, buff=0.15)
        self.play(FadeIn(lbl), FadeIn(code))
        self.wait(1)

        lines = code.code_lines
        steps = [
            (1, 2, "Check 1: Read the token from the\nAuthorization header (Bearer scheme)"),
            (3, 4, "Check 2: The token must be signed\nand carry an expiry time"),
            (7, 8, "Check 3: Fetch the issuer's public keys\nto verify the signature"),
            (9, 11, "Check 4: Audience must be api://orders"),
            (12, 14, "Check 5: Issuer must be\nlogin.contoso-idp.example"),
            (15, 19, "Check 6: Scope (scp) must include\norders.read"),
            (5, 6, "If any check fails:\nreturn HTTP 401 Unauthorized"),
        ]
        rect = None
        note = None
        for a, b, text in steps:
            new_rect = SurroundingRectangle(VGroup(*[lines[i] for i in range(a, b + 1)]),
                                            color=YELLOW if a != 5 else RED, buff=0.04, stroke_width=3)
            new_note = Text(text, font_size=18, line_spacing=0.9,
                            color=WHITE if a != 5 else RED).move_to(RIGHT * 4.85 + UP * 0.3)
            if rect is None:
                self.play(Create(new_rect), FadeIn(new_note))
            else:
                self.play(ReplacementTransform(rect, new_rect), FadeOut(note), FadeIn(new_note))
            rect, note = new_rect, new_note
            self.wait(2.2)
        self.play(FadeOut(rect), FadeOut(note))
        end = Text("All checks pass:\nrequest goes to the backend\n\nAny check fails:\nHTTP 401 Unauthorized",
                   font_size=18, line_spacing=0.9, color=GREEN).move_to(RIGHT * 4.85 + UP * 0.3)
        self.play(FadeIn(end))
        self.wait(3)
