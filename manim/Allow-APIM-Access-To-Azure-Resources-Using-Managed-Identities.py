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
ERR_C = "#b91c1c"

config.background_color = BG
Text.set_default(font="Arial", color=INK)

APIM_C = "#0f766e"
ENTRA_C = "#2563eb"
KV_C = GOLD
FUNC_C = "#6d4c9f"
COSMOS_C = BURGUNDY
ID_C = "#0e7490"


def packet(label, color):
    box = RoundedRectangle(width=max(0.5, 0.11 * len(label) + 0.25), height=0.32, corner_radius=0.08,
                           color=color, fill_color=color, fill_opacity=1, stroke_width=1)
    txt = Text(label, font_size=12, color=WHITE).move_to(box)
    return VGroup(box, txt)


def component(title, sub, color, width, height, center, font=17):
    box = RoundedRectangle(width=width, height=height, corner_radius=0.12, color=color,
                           fill_color=color, fill_opacity=0.14, stroke_width=3).move_to(center)
    ttl = Text(title, font_size=font, color=color).move_to(box.get_top() + DOWN * 0.27)
    lines = VGroup(*[Text(s, font_size=12, color=INK) for s in sub]).arrange(DOWN, buff=0.07)
    lines.next_to(ttl, DOWN, buff=0.1)
    return VGroup(box, ttl, lines)


def role_badge(text, color, center):
    txt = Text(text, font_size=11, color=WHITE)
    box = RoundedRectangle(width=txt.width + 0.3, height=0.3, corner_radius=0.08, color=color,
                           fill_color=color, fill_opacity=1, stroke_width=1).move_to(center)
    txt.move_to(box)
    return VGroup(box, txt)


def toggle(on):
    c = OK_C if on else LINE
    track = RoundedRectangle(width=0.5, height=0.26, corner_radius=0.13, color=c, fill_color=c,
                             fill_opacity=1, stroke_width=1)
    knob = Circle(radius=0.1, color=WHITE, fill_color=WHITE, fill_opacity=1, stroke_width=0)
    knob.move_to(track.get_right() + LEFT * 0.14 if on else track.get_left() + RIGHT * 0.14)
    return VGroup(track, knob)


class ManagedIdentityRbac(Scene):
    def construct(self):
        title = Text("Allow APIM Access to Azure Resources using Managed Identities", font_size=28,
                     color=BURGUNDY).to_edge(UP, buff=0.25)
        self.add(title)

        # ---------- components ----------
        entra = component("Microsoft Entra ID", ["Issues access tokens"], ENTRA_C, 3.0, 1.0, [0, 2.45, 0])
        apim = component("Azure API Management", ["Policy:", "authentication-managed-identity"],
                         APIM_C, 3.0, 2.2, [-5.2, 0.1, 0], font=16)
        kv = component("Azure Key Vault", ["Secrets"], KV_C, 3.2, 1.3, [4.9, 1.45, 0])
        func = component("Azure Functions", ["HTTP API"], FUNC_C, 3.2, 1.3, [4.9, -0.3, 0])
        cosmos = component("Azure Cosmos DB", ["Orders Container"], COSMOS_C, 3.2, 1.3, [4.9, -2.05, 0])
        resources = VGroup(kv, func, cosmos)

        # toggle for the system-assigned identity inside the APIM box
        tg_lbl = Text("System Assigned Identity", font_size=12, color=INK)
        tg_off = toggle(False)
        tg_row = VGroup(tg_lbl, tg_off).arrange(RIGHT, buff=0.15).move_to(apim[0].get_bottom() + UP * 0.35)

        # ---------- links ----------
        def dline(a, b):
            return DashedLine(a, b, color=LINE, stroke_width=1.5)

        l_entra = dline(apim[0].get_top() + RIGHT * 0.9, entra[0].get_left())
        l_kv = dline(apim[0].get_right() + UP * 0.5, kv[0].get_left())
        l_func = dline(apim[0].get_right(), func[0].get_left())
        l_cosmos = dline(apim[0].get_right() + DOWN * 0.5, cosmos[0].get_left())
        links = VGroup(l_entra, l_kv, l_func, l_cosmos)

        status = Text("APIM calls Azure resources without secrets, using its own identity",
                      font_size=22).to_edge(DOWN, buff=0.25)
        self.add(status)

        def say(msg, color=INK):
            status.become(Text(msg, font_size=22, color=color).to_edge(DOWN, buff=0.25))

        def lit(line, color):
            return line.animate.set_color(color).set_stroke(width=3)

        def unlit(line):
            return line.animate.set_color(LINE).set_stroke(width=1.5)

        def hl(mob, color=HILITE):
            r = SurroundingRectangle(mob, color=color, buff=0.06, stroke_width=3)
            self.play(Create(r), run_time=0.4)
            return r

        def travel(pkt, p, rt=0.9):
            self.play(pkt.animate.move_to(p), run_time=rt)

        self.play(FadeIn(entra), FadeIn(apim), run_time=1)
        self.play(FadeIn(resources), run_time=1)
        self.play(Create(links), FadeIn(tg_row), run_time=1.2)
        self.wait(0.5)

        # ---------- 1. create the system-assigned identity ----------
        say("1. Turn on the System Assigned Identity for APIM", APIM_C)
        r_tg = hl(tg_row, APIM_C)
        tg_on = toggle(True).move_to(tg_off)
        self.play(Transform(tg_off, tg_on), run_time=0.6)
        req = packet("enable identity", APIM_C).move_to(l_entra.get_start())
        self.play(FadeIn(req), lit(l_entra, APIM_C), run_time=0.3)
        travel(req, l_entra.get_end(), 1.0)
        say("2. Entra ID creates a Service Principal tied to the APIM lifecycle", ENTRA_C)
        sp = role_badge("Service Principal: apim-demo", ENTRA_C, entra[0].get_bottom() + DOWN * 0.0)
        sp.move_to(entra[0].get_center() + DOWN * 0.3)
        self.play(FadeOut(entra[2]), FadeIn(sp), FadeOut(req), run_time=0.5)
        r_e = hl(entra, ENTRA_C)
        ident = component("Managed Identity", ["Service Principal Id", "3f9c4a71-0b2e-..."], ID_C, 2.3, 1.1,
                          [-5.2, -2.45, 0], font=15)
        back = packet("Service Principal Id", OK_C).move_to(l_entra.get_end())
        self.play(FadeIn(back), lit(l_entra, OK_C), run_time=0.3)
        travel(back, l_entra.get_start(), 1.0)
        ident_tie = Line(apim[0].get_bottom(), ident[0].get_top(), color=ID_C, stroke_width=2.5)
        ident = VGroup(ident, ident_tie)[0]
        self.play(FadeOut(back), FadeIn(ident), Create(ident_tie), unlit(l_entra), FadeOut(r_e), FadeOut(r_tg), run_time=0.5)
        self.wait(0.5)

        # ---------- 2. assign built-in RBAC roles ----------
        say("3. Assign built-in RBAC roles to the Managed Identity on each Azure resource", ID_C)
        roles = {
            "kv": ("Key Vault Secrets User", KV_C, kv),
            "func": ("Website Contributor", FUNC_C, func),
            "cosmos": ("Cosmos DB Built-in Data Reader", COSMOS_C, cosmos),
        }
        badges = {}
        for key, (txt, col, res) in roles.items():
            pos = res[0].get_bottom() + UP * 0.28
            b = role_badge(txt, col, pos)
            badges[key] = b
            p = packet("role", ID_C).move_to(ident[0].get_right())
            self.play(FadeIn(p), run_time=0.2)
            self.play(p.animate.move_to(res[0].get_left() + DOWN * 0.3), run_time=0.9)
            self.play(FadeOut(p), FadeIn(b), run_time=0.4)
        self.wait(0.8)

        # ---------- access helpers ----------
        def get_token(resource_uri, color):
            say(f"APIM asks Entra ID for a token for {resource_uri}", APIM_C)
            q = packet("get token", APIM_C).move_to(l_entra.get_start())
            self.play(FadeIn(q), lit(l_entra, APIM_C), run_time=0.3)
            travel(q, l_entra.get_end(), 1.0)
            r = hl(entra, ENTRA_C)
            self.play(FadeOut(q), run_time=0.2)
            tok = packet("JWT", color).move_to(l_entra.get_end())
            self.play(FadeIn(tok), run_time=0.2)
            travel(tok, l_entra.get_start(), 1.0)
            self.play(FadeOut(tok), unlit(l_entra), FadeOut(r), run_time=0.3)

        def call(link, label, color, res, key, allowed, ok_label, bad_label="403 Forbidden",
                 msg_call="", msg_check="", msg_back=""):
            say(msg_call, color)
            q = packet(label, color).move_to(link.get_start())
            self.play(FadeIn(q), lit(link, color), run_time=0.3)
            travel(q, link.get_end(), 1.1)
            r = hl(res, color)
            say(msg_check, OK_C if allowed else ERR_C)
            rb = hl(badges[key], OK_C if allowed else ERR_C)
            self.wait(0.4)
            self.play(FadeOut(q), run_time=0.2)
            col = OK_C if allowed else ERR_C
            say(msg_back, col)
            a = packet(ok_label if allowed else bad_label, col).move_to(link.get_end())
            self.play(FadeIn(a), lit(link, col), run_time=0.3)
            travel(a, link.get_start(), 1.1)
            self.wait(0.5)
            self.play(FadeOut(a), unlit(link), FadeOut(r), FadeOut(rb), run_time=0.4)

        # ---------- 3. successful access flows ----------
        get_token("https://vault.azure.net", KV_C)
        call(l_kv, "GET /secrets/db-conn", KV_C, kv, "kv", True, "200 OK",
             msg_call="4. APIM calls Key Vault with the token: read a secret",
             msg_check="5. Key Vault checks RBAC: Secrets User allows reading secrets",
             msg_back="6. The secret value returns to APIM")

        get_token("the Functions app registration", FUNC_C)
        call(l_func, "POST /api/price", FUNC_C, func, "func", True, "200 OK",
             msg_call="7. APIM calls the Azure Function with the token",
             msg_check="8. The role assignment on the Function app grants the identity access",
             msg_back="9. The Function result returns to APIM")

        get_token("https://cosmos.azure.com", COSMOS_C)
        call(l_cosmos, "GET /orders/42", COSMOS_C, cosmos, "cosmos", True, "200 OK",
             msg_call="10. APIM calls Cosmos DB with the token: read an order",
             msg_check="11. Cosmos DB checks RBAC: Data Reader allows reads",
             msg_back="12. The order document returns to APIM")

        # ---------- 4. failures: roles lack permissions ----------
        say("Now APIM tries operations the assigned roles do not permit", ERR_C)
        self.wait(1.0)

        get_token("https://vault.azure.net", KV_C)
        call(l_kv, "PUT /secrets/db-conn", KV_C, kv, "kv", False, "",
             msg_call="13. APIM tries to write a secret to Key Vault",
             msg_check="14. Secrets User has no set permission: the write is denied",
             msg_back="15. Key Vault returns 403 Forbidden: the token is valid, the role is not enough")

        get_token("https://cosmos.azure.com", COSMOS_C)
        call(l_cosmos, "POST /orders", COSMOS_C, cosmos, "cosmos", False, "",
             msg_call="16. APIM tries to create an order in Cosmos DB",
             msg_check="17. Data Reader has no write permission: the write is denied",
             msg_back="18. Cosmos DB returns 403 Forbidden")

        # ---------- 5. fix: assign a role with enough permissions ----------
        say("19. Fix: give the Managed Identity the Cosmos DB Data Contributor role", ID_C)
        new_badge = role_badge("Cosmos DB Built-in Data Contributor", COSMOS_C,
                               cosmos[0].get_bottom() + UP * 0.28)
        p = packet("role", ID_C).move_to(ident[0].get_right())
        self.play(FadeIn(p), run_time=0.2)
        self.play(p.animate.move_to(cosmos[0].get_left() + DOWN * 0.3), run_time=0.9)
        self.play(FadeOut(p), FadeOut(badges["cosmos"]), FadeIn(new_badge), run_time=0.5)
        badges["cosmos"] = new_badge
        self.wait(0.5)

        get_token("https://cosmos.azure.com", COSMOS_C)
        call(l_cosmos, "POST /orders", COSMOS_C, cosmos, "cosmos", True, "201 Created",
             msg_call="20. APIM retries the order creation with a fresh token",
             msg_check="21. Data Contributor allows writes: access is granted",
             msg_back="22. Cosmos DB returns 201 Created")

        say("System Assigned Identity + least-privilege built-in RBAC roles: no secrets to store or rotate",
            OK_C)
        self.wait(2.5)
