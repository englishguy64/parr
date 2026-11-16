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
RED_C = "#a33a5c"
PURPLE = BURGUNDY
TEAL = "#0f766e"
BLUE = "#475569"
BLUE_C = "#475569"
ORANGE = BURGUNDY

Text.set_default(font="Arial", color=INK)

ANG_C = RED_C
AZ_C = BLUE
ENTRA_C = "#2684FF"
APIM_C = PURPLE
ID_C = YELLOW
AT_C = GREEN


def packet(label, color):
    box = RoundedRectangle(width=max(0.5, 0.1 * len(label) + 0.25), height=0.3, corner_radius=0.08,
                           color=color, fill_color=color, fill_opacity=0.95, stroke_width=1)
    txt = Text(label, font_size=11, color=BLACK).move_to(box)
    return VGroup(box, txt)


def tick(pos):
    p = np.array(pos)
    return VGroup(Line(p + [-0.07, 0.0, 0], p + [-0.02, -0.06, 0], color=GREEN, stroke_width=3),
                  Line(p + [-0.02, -0.06, 0], p + [0.08, 0.07, 0], color=GREEN, stroke_width=3))


def card(w, h, color, center, fill=0.12, dashed=False):
    r = RoundedRectangle(width=w, height=h, corner_radius=0.12, color=color,
                         fill_color=color, fill_opacity=fill, stroke_width=3)
    if dashed:
        r = DashedVMobject(r, num_dashes=60)
    return r.move_to([center[0], center[1], 0])


class AngularEntraAuth(Scene):
    def construct(self):
        title = Text("Authorise Azure Hosted Angular SPA With Microsoft Entra ID", font_size=30,
                     color=BURGUNDY).to_edge(UP, buff=0.25)
        self.add(title)

        status = Text("", font_size=20).to_edge(DOWN, buff=0.2)
        self.add(status)

        def say(msg, color=WHITE):
            status.become(Text(msg, font_size=20, color=color).to_edge(DOWN, buff=0.2))

        def travel(pkt, pts, t=0.7):
            for pt in pts:
                self.play(pkt.animate.move_to(pt), run_time=t)

        # ---------------- Angular app hosted in Azure ----------------
        host = card(4.6, 3.6, AZ_C, [-4.6, 0.5], fill=0.06, dashed=True)
        host_lbl = Text("Azure Static Web Apps", font_size=14, color=AZ_C).move_to([-4.6, 2.1, 0])
        app_t = Text("Angular SPA", font_size=18, color=ANG_C).move_to([-4.6, 1.72, 0])
        chip = VGroup(card(3.0, 0.3, ANG_C, [-4.6, 1.38], fill=0.25),
                      Text("@azure/msal-angular  (MSAL)", font_size=12).move_to([-4.6, 1.38, 0]))
        btn = VGroup(card(1.4, 0.38, ANG_C, [-4.6, 0.88], fill=0.5), Text("Sign in", font_size=15).move_to([-4.6, 0.88, 0]))
        banner = Text("", font_size=14).move_to([-4.6, 0.33, 0])
        mem = card(3.9, 0.95, GRAY_B, [-4.6, -0.65], fill=0.05, dashed=True)
        mem_t = Text("In-memory token cache", font_size=12, color=GRAY_B).move_to([-4.6, -0.38, 0])

        user = VGroup(Circle(radius=0.15, color=WHITE, stroke_width=3),
                      Arc(radius=0.28, start_angle=0, angle=PI, color=WHITE, stroke_width=3).shift(DOWN * 0.42),
                      Text("User", font_size=14).shift(DOWN * 0.7)).move_to([-5.6, -2.3, 0])

        self.play(Create(host), FadeIn(host_lbl), FadeIn(app_t), FadeIn(chip), FadeIn(btn),
                  FadeIn(mem), FadeIn(mem_t), FadeIn(user))
        self.add(banner)
        say("An Angular SPA hosted in Azure, using MSAL Angular for sign-in", WHITE)
        self.wait(2)

        # ---------------- Entra + app registration ----------------
        entra = card(3.4, 2.9, ENTRA_C, [0.8, 1.2], fill=0.08)
        entra_t = Text("Microsoft Entra ID", font_size=18, color=ENTRA_C).move_to([0.8, 2.4, 0])
        reg = card(3.1, 1.95, GRAY_B, [0.8, 1.25], fill=0.1)
        reg_lines = VGroup(
            Text("App registration: orders-spa", font_size=13, color=YELLOW),
            Text("Client ID: 1111-2222-3333", font_size=12),
            Text("Redirect URI:", font_size=12),
            Text("https://orders.azurestaticapps.net", font_size=11, color=GRAY_B),
            Text("API scope:", font_size=12),
            Text("api://orders/orders.read", font_size=11, color=GRAY_B),
        ).arrange(DOWN, buff=0.07, aligned_edge=LEFT).move_to(reg)
        self.play(FadeIn(entra), FadeIn(entra_t))
        self.play(FadeIn(reg), FadeIn(reg_lines))
        say("The app is registered in Entra ID: client ID, redirect URI and the API scope it may request", ENTRA_C)
        self.wait(2.5)

        # ---------------- MSAL config card ----------------
        cfg = card(4.6, 1.9, ANG_C, [0.8, -1.9], fill=0.1)
        cfg_lines = VGroup(
            Text("MSAL configuration in the Angular SPA", font_size=13, color=ANG_C),
            Text("clientId: 1111-2222-3333", font_size=12),
            Text("authority: login.microsoftonline.com/<tenant-id>", font_size=12),
            Text("redirectUri: https://orders.azurestaticapps.net", font_size=12),
            Text("scopes: api://orders/orders.read", font_size=12),
            Text("cacheLocation: memoryStorage", font_size=12, color=GREEN),
        ).arrange(DOWN, buff=0.07, aligned_edge=LEFT).move_to(cfg)
        self.play(FadeIn(cfg), FadeIn(cfg_lines))
        say("MSAL Angular is configured with the same values (library: @azure/msal-angular + msal-browser)", ANG_C)
        self.wait(3)
        self.play(FadeOut(cfg), FadeOut(cfg_lines))

        # lanes between Angular and Entra
        req_a, req_e = np.array([-2.3, 1.0, 0]), np.array([-0.9, 1.0, 0])
        res_e, res_a = np.array([-0.9, 0.6, 0]), np.array([-2.3, 0.6, 0])

        # ---------------- login popup ----------------
        popup = card(4.4, 1.95, WHITE, [0.8, -1.9], fill=0.08)
        pop_t = Text("Microsoft sign in", font_size=14).move_to([0.8, -1.1, 0])
        f1 = RoundedRectangle(width=3.6, height=0.34, corner_radius=0.05, color=GRAY_B, stroke_width=2).move_to([0.8, -1.5, 0])
        f2 = RoundedRectangle(width=3.6, height=0.34, corner_radius=0.05, color=GRAY_B, stroke_width=2).move_to([0.8, -1.95, 0])

        def start_login():
            self.play(Indicate(btn), run_time=0.6)
            pk = packet("authorize + PKCE", YELLOW).move_to(req_a)
            say("User clicks Sign in: MSAL redirects the browser to Entra (authorization code flow + PKCE)", YELLOW)
            self.play(FadeIn(pk))
            travel(pk, [req_e], 0.9)
            self.play(FadeOut(pk), FadeIn(popup), FadeIn(pop_t), FadeIn(f1), FadeIn(f2))

        def type_creds(email, pw):
            e = Text(email, font_size=13).move_to(f1.get_left() + RIGHT * 0.1, aligned_edge=LEFT)
            p = Text(pw, font_size=13).move_to(f2.get_left() + RIGHT * 0.1, aligned_edge=LEFT)
            self.play(AddTextLetterByLetter(e, time_per_char=0.05))
            self.play(AddTextLetterByLetter(p, time_per_char=0.05))
            return VGroup(e, p)

        def set_banner(msg, color):
            new = Text(msg, font_size=14, color=color).move_to([-4.6, 0.33, 0])
            self.play(Transform(banner, new), run_time=0.3)

        # ----- attempt 1: failure -----
        start_login()
        say("Entra shows its own sign-in page - the app never sees the password", ENTRA_C)
        creds = type_creds("alice@contoso.com", "••••••")
        msg = Text("Incorrect password", font_size=13, color=RED).move_to([0.8, -2.5, 0]) \
            if False else Text("Incorrect password / sign-in cancelled", font_size=13, color=RED).move_to([0.8, -2.42, 0])
        self.play(FadeIn(msg), popup.animate.set_stroke(RED))
        self.wait(1)
        say("FAILED: Entra redirects back to the Angular SPA with an error (error=access_denied)", RED)
        pk = packet("redirect: error", RED).move_to(res_e)
        self.play(FadeOut(popup), FadeOut(pop_t), FadeOut(f1), FadeOut(f2), FadeOut(creds), FadeOut(msg), FadeIn(pk))
        travel(pk, [res_a], 0.9)
        set_banner("Sign-in failed - no tokens issued", RED)
        self.play(FadeOut(pk))
        self.wait(2)
        popup.set_stroke(WHITE)

        # ----- attempt 2: success -----
        set_banner("", WHITE)
        start_login()
        creds = type_creds("alice@contoso.com", "••••••••••")
        ok = Text("Signed in (MFA satisfied)", font_size=13, color=GREEN).move_to([0.8, -2.42, 0])
        self.play(FadeIn(ok), popup.animate.set_stroke(GREEN))
        self.wait(1)
        say("SUCCESS: Entra redirects back to the redirect URI with a one-time authorization code", GREEN)
        pk = packet("redirect: auth code", GREEN).move_to(res_e)
        self.play(FadeOut(popup), FadeOut(pop_t), FadeOut(f1), FadeOut(f2), FadeOut(creds), FadeOut(ok), FadeIn(pk))
        travel(pk, [res_a], 0.9)
        self.play(FadeOut(pk))
        self.wait(0.5)

        # ---------------- token exchange ----------------
        say("MSAL swaps the code (+ PKCE verifier) at Entra's token endpoint", YELLOW)
        pk = packet("code + PKCE verifier", YELLOW).move_to(req_a)
        self.play(FadeIn(pk))
        travel(pk, [req_e], 0.9)
        self.play(Indicate(reg, color=GREEN), run_time=0.8)
        self.play(FadeOut(pk))
        idp = packet("ID token", ID_C).move_to(res_e + UP * 0.2)
        atp = packet("Access token", AT_C).move_to(res_e + DOWN * 0.2)
        say("Entra returns an ID token (who signed in) AND an access token (what API it may call)", GREEN)
        self.play(FadeIn(idp), FadeIn(atp))
        self.play(idp.animate.move_to(res_a + UP * 0.2), atp.animate.move_to(res_a + DOWN * 0.2), run_time=1.0)

        tok_card = card(5.6, 1.9, GRAY_B, [1.4, -1.9], fill=0.08)
        tok_lines = VGroup(
            Text("ID token - for the Angular SPA", font_size=13, color=ID_C),
            Text("Says who signed in (name, email). Never sent to the API.", font_size=12),
            Text("Access token - for the API", font_size=13, color=AT_C),
            Text("aud: api://orders   scp: orders.read   exp: 1 hour", font_size=12),
            Text("Not a swap: both come back from the same code exchange", font_size=11, color=GRAY_B),
        ).arrange(DOWN, buff=0.08, aligned_edge=LEFT).move_to(tok_card)
        self.play(FadeIn(tok_card), FadeIn(tok_lines))
        self.wait(4)
        self.play(FadeOut(tok_card), FadeOut(tok_lines))

        # ---------------- memory storage ----------------
        say("MSAL keeps the tokens in memory (cacheLocation: memoryStorage), not in browser storage", AT_C)
        id_m = packet("ID token", ID_C).move_to([-5.45, -0.72, 0])
        at_m = packet("Access token", AT_C).move_to([-3.85, -0.72, 0])
        self.play(Transform(idp, id_m), Transform(atp, at_m), run_time=1.2)
        mem_note = Text("Lost on page refresh; harder for scripts to steal", font_size=11, color=GRAY_B)
        mem_note.move_to([-4.6, -1.38, 0])
        set_banner("Signed in as alice@contoso.com", GREEN)
        self.play(FadeIn(mem_note))
        self.wait(2.5)

        # ---------------- APIM ----------------
        apim = card(2.8, 2.9, APIM_C, [5.4, 1.2], fill=0.1)
        apim_t = Text("Azure API Management", font_size=14, color=APIM_C).move_to([5.4, 2.4, 0])
        vj = card(2.5, 1.9, APIM_C, [5.4, 1.2], fill=0.15)
        vj_t = Text("validate-jwt", font_size=13, color=APIM_C).move_to([5.4, 2.0, 0])
        checks = ["Signature valid", "Issuer trusted", "Audience api://orders", "Not expired", "Scope orders.read"]
        row_y = [1.7 - 0.28 * i for i in range(len(checks))]
        rows = VGroup(*[Text(c, font_size=11).move_to([4.5, y, 0], aligned_edge=LEFT) for c, y in zip(checks, row_y)])
        self.play(FadeIn(apim), FadeIn(apim_t), FadeIn(vj), FadeIn(vj_t), FadeIn(rows))
        say("Angular's MsalInterceptor reads the access token from memory and attaches it to API calls", AT_C)
        self.wait(2)

        call = packet("GET /orders  Bearer <access token>", AT_C).move_to([-3.85, -0.72, 0])
        self.play(FadeIn(call))
        say("The access token is forwarded to Azure APIM as a Bearer token for validation", AT_C)
        travel(call, [[-3.85, -0.72, 0], [5.4, -0.72, 0], [5.4, -0.2, 0]], 1.0)
        self.play(FadeOut(call))
        for i, y in enumerate(row_y):
            m = tick([4.3, y, 0])
            self.play(Create(m), rows[i].animate.set_color(GREEN), run_time=0.35)
        ok_pk = packet("HTTP 200 OK", GREEN).move_to([5.4, -0.2, 0])
        self.play(FadeIn(ok_pk))
        travel(ok_pk, [[5.4, -0.72, 0], [-3.85, -0.72, 0]], 1.0)
        set_banner("Orders loaded (HTTP 200)", GREEN)
        self.play(FadeOut(ok_pk))
        say("Valid token -> APIM allows the call. Missing, expired or wrong-audience token -> 401", GREEN)
        self.wait(3)
