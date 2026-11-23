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
TEAL = "#0f766e"
BLUE = "#475569"

Text.set_default(font="Arial", color=INK)

SERVER_C = BURGUNDY
BROWSER_C = BLUE
PRIV_C = RED
PUB_C = GREEN
MONO = "Consolas"

USER_POS = (-5.9, 0.9)
BROWSER_POS = (-2.4, 1.0)
AUTH_POS = (-2.4, -1.5)
SERVER_POS = (4.5, 1.0)
STORE_POS = (4.5, -1.5)


def packet(label, color):
    box = RoundedRectangle(width=max(0.5, 0.1 * len(label) + 0.25), height=0.3, corner_radius=0.08,
                           color=color, fill_color=color, fill_opacity=0.95, stroke_width=1)
    return VGroup(box, Text(label, font_size=11, color=BLACK).move_to(box))


def node(title, sub, color, w, h, pos, fs=15):
    r = RoundedRectangle(width=w, height=h, corner_radius=0.12, color=color,
                         fill_color=color, fill_opacity=0.14, stroke_width=3).move_to([pos[0], pos[1], 0])
    parts = [Text(title, font_size=fs, color=color)]
    if sub:
        parts.append(Text(sub, font_size=fs - 4, color=GRAY_B, line_spacing=0.9))
    g = VGroup(*parts).arrange(DOWN, buff=0.1).move_to(r)
    return VGroup(r, g)


def person(name, pos):
    icon = VGroup(Circle(radius=0.16, color=INK, stroke_width=3),
                  Arc(radius=0.3, start_angle=0, angle=PI, color=INK, stroke_width=3).shift(DOWN * 0.42))
    lbl = Text(name, font_size=14).next_to(icon, DOWN, buff=0.14)
    return VGroup(icon, lbl).move_to([pos[0], pos[1], 0])


def key_icon(color, scale=1.0):
    ring = Circle(radius=0.11, color=color, stroke_width=3)
    shaft = Line([0.11, 0, 0], [0.55, 0, 0], color=color, stroke_width=3)
    t1 = Line([0.42, 0, 0], [0.42, -0.12, 0], color=color, stroke_width=3)
    t2 = Line([0.52, 0, 0], [0.52, -0.09, 0], color=color, stroke_width=3)
    return VGroup(ring, shaft, t1, t2).scale(scale)


def labelled_key(color, label, scale=1.0, fs=11):
    k = key_icon(color, scale)
    t = Text(label, font_size=fs, color=color).next_to(k, DOWN, buff=0.06)
    return VGroup(k, t)


def info_card(title, lines, color, w, pos, fs=10):
    head = Text(title, font_size=fs + 1, color=color)
    body = VGroup(*[Text(l, font_size=fs, font=MONO) for l in lines]).arrange(DOWN, buff=0.09,
                                                                             aligned_edge=LEFT)
    inner = VGroup(head, body).arrange(DOWN, buff=0.14, aligned_edge=LEFT)
    box = RoundedRectangle(width=w, height=inner.height + 0.3, corner_radius=0.1, color=color,
                           stroke_width=2, fill_color=BLACK, fill_opacity=1)
    inner.move_to(box)
    return VGroup(box, inner).move_to([pos[0], pos[1], 0])


class PasskeySignIn(Scene):
    def construct(self):
        self.header = None
        self.status = None
        self.card = None

        def next_part(text):
            if self.mobjects:
                self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.6)
            self.clear()
            self.card = None
            self.header = Text(text, font_size=28, color=BURGUNDY).to_edge(UP, buff=0.25)
            self.status = Text("", font_size=19).to_edge(DOWN, buff=0.2)
            self.add(self.status, self.header)

        def say(msg, color=WHITE):
            self.status.become(Text(msg, font_size=19, color=color).to_edge(DOWN, buff=0.2))

        def hop(label, color, a, b, t=0.9, keep=False):
            p = packet(label, color).move_to(a)
            self.play(FadeIn(p), run_time=0.2)
            self.play(p.animate.move_to(b), run_time=t)
            if not keep:
                self.play(FadeOut(p), run_time=0.2)
            return p

        def show_card(new):
            anims = [FadeIn(new)]
            if self.card is not None:
                anims.append(FadeOut(self.card))
            self.play(*anims, run_time=0.6)
            self.card = new

        def clear_card():
            if self.card is not None:
                self.play(FadeOut(self.card), run_time=0.4)
                self.card = None

        def build_site(with_auth_slot=True):
            user = person("User", USER_POS)
            browser = node("Browser", "WebAuthn API", BROWSER_C, 2.7, 1.3, BROWSER_POS, fs=15)
            server = node("ASP.NET Core web site", ".NET 10 SDK + ASP.NET Core Identity", SERVER_C, 4.6, 1.3,
                          SERVER_POS, fs=15)
            store = node("AspNetUserPasskeys", None, GREEN, 4.6, 1.5, STORE_POS, fs=14)
            hdr = Text("credentialId   publicKey   signCount  user", font_size=10, font=MONO, color=GRAY_B)
            hdr.move_to([STORE_POS[0], STORE_POS[1] + 0.2, 0])
            store.add(hdr)
            self.play(FadeIn(user), FadeIn(browser), run_time=0.7)
            self.play(FadeIn(server), FadeIn(store), run_time=0.7)
            return user, browser, server, store

        # ======================= intro =======================
        title = Text("Sign In With Passkeys On An\nASP.NET Core Web Site", font_size=34,
                     line_spacing=0.9, color=BURGUNDY)
        sub = VGroup(Text("WebAuthn", font_size=24, color=BROWSER_C),
                     Text("FIDO2", font_size=24, color=YELLOW),
                     Text(".NET 10", font_size=24, color=SERVER_C)).arrange(RIGHT, buff=0.8)
        sub.next_to(title, DOWN, buff=0.6)
        self.add(title)
        self.play(FadeIn(sub, lag_ratio=0.3))
        self.wait(2)
        self.play(FadeOut(title), FadeOut(sub))

        # ======================= part 1: create a passkey =======================
        next_part("1. Create a passkey")
        user, browser, server, store = build_site()
        auth = node("Authenticator", "FIDO2 / CTAP2", YELLOW, 2.7, 1.3, AUTH_POS, fs=15)
        self.play(FadeIn(auth))

        say("The user chooses Create passkey on the web site", WHITE)
        hop("Create passkey", WHITE, user[0].get_right() + RIGHT * 0.1, browser[0].get_left(), 1.0)

        say("The site sends a challenge, its domain (rp.id) and the user id", SERVER_C)
        hop("GET options", BROWSER_C, browser[0].get_right(), server[0].get_left(), 0.9)
        show_card(info_card("PublicKeyCredentialCreationOptions", [
            "challenge : random, single use",
            "rp.id     : example.com",
            "user.id   : opaque user handle",
        ], SERVER_C, 3.3, (0.55, -0.4)))
        hop("challenge", SERVER_C, server[0].get_left(), browser[0].get_right(), 0.9)

        say("WebAuthn: navigator.credentials.create() hands the request to the authenticator", BROWSER_C)
        hop("credentials.create()", BROWSER_C, browser[0].get_bottom(), auth[0].get_top(), 0.9)

        say("The user proves presence: touch, PIN, fingerprint or face", YELLOW)
        uv = Text("touch / PIN / biometric", font_size=12, color=YELLOW).next_to(auth[0], LEFT, buff=0.25)
        self.play(FadeIn(uv), Indicate(auth[0], color=YELLOW), run_time=1.0)

        say("The authenticator creates a key pair for this site only", PRIV_C)
        priv = labelled_key(PRIV_C, "private key", 1.0).move_to([AUTH_POS[0] - 0.8, -2.65, 0])
        pub = labelled_key(PUB_C, "public key", 1.0).move_to([AUTH_POS[0] + 0.8, -2.65, 0])
        self.play(FadeIn(priv, shift=UP * 0.15), FadeIn(pub, shift=UP * 0.15), run_time=0.9)
        say("The private key never leaves the authenticator", PRIV_C)
        self.play(Indicate(priv, color=PRIV_C, scale_factor=1.3), run_time=1.2)
        self.play(FadeOut(uv))

        say("Only the public key and an attestation are sent back", GREEN)
        pub_copy = pub.copy()
        self.play(pub_copy.animate.move_to(auth[0].get_top() + UP * 0.2), run_time=0.6)
        self.play(FadeOut(pub_copy), run_time=0.2)
        hop("public key + attestation", GREEN, auth[0].get_top(), browser[0].get_bottom(), 0.9)
        hop("POST attestation", BROWSER_C, browser[0].get_right(), server[0].get_left(), 0.9)

        say("The site checks the challenge, origin and attestation", SERVER_C)
        show_card(info_card("ASP.NET Core Identity verifies", [
            "[x] challenge matches",
            "[x] origin = https://example.com",
            "[x] attestation is valid",
        ], SERVER_C, 3.3, (0.55, -0.4)))
        self.play(Indicate(server[0], color=SERVER_C), run_time=0.9)

        say("The PUBLIC key is stored against the user in AspNetUserPasskeys", GREEN)
        pk = labelled_key(PUB_C, "public", 0.9).move_to(server[0].get_bottom() + DOWN * 0.05)
        self.play(FadeIn(pk))
        self.play(pk.animate.move_to([STORE_POS[0], STORE_POS[1] + 0.2, 0]).scale(0.6), run_time=0.9)
        row = Text("7f3a91..    ES256 key       0      bob", font_size=10, font=MONO)
        row.move_to([STORE_POS[0], STORE_POS[1] - 0.2, 0])
        self.play(FadeOut(pk), FadeIn(row))
        hop("passkey created", GREEN, server[0].get_left(), browser[0].get_right(), 0.9)
        self.wait(2.5)

        # ======================= part 2: where the keys are stored =======================
        next_part("2. Where are the keys stored?")
        opts = [
            ("FIDO2 security\nkey", "USB / NFC / BLE", YELLOW, "hardware bound\nnot exportable", -5.6),
            ("TPM 2.0", "Windows Hello", TEAL, "hardware bound\nbacked by the PC", -2.8),
            ("Secure Enclave", "iPhone, iPad, Mac\nTouch ID / Face ID", BLUE, "hardware bound,\nmay sync via iCloud", 0.0),
            ("Android\nKeystore", "phone or tablet", GREEN, "hardware bound,\nmay sync via Google", 2.8),
            ("Password\nmanager", "1Password, Bitwarden,\nDashlane", BURGUNDY, "synced across\nyour devices", 5.6),
        ]
        tag = Text("PRIVATE key: held by the user's authenticator", font_size=16, color=PRIV_C).move_to([0, 2.8, 0])
        self.play(FadeIn(tag))
        devs = []
        for t, s, c, note, x in opts:
            n = node(t, s, c, 2.55, 1.7, (x, 1.45), fs=14)
            k = labelled_key(PRIV_C, "private", 0.8).move_to([x, 0.15, 0])
            nt = Text(note, font_size=11, color=GRAY_B, line_spacing=0.9).move_to([x, -0.6, 0])
            devs.append((n, k, nt, x))
            self.play(FadeIn(n), FadeIn(k, shift=UP * 0.1), FadeIn(nt), run_time=0.5)
        say("Any of these can hold the private key. The site cannot tell which, nor read the key", PRIV_C)
        self.wait(2.5)

        srv = node("ASP.NET Core Identity", "AspNetUserPasskeys: credentialId + PUBLIC key + signCount", SERVER_C,
                   8.4, 1.0, (0, -2.5), fs=14)
        self.play(FadeIn(srv))
        pubs = VGroup(*[labelled_key(PUB_C, "public", 0.7).move_to([x, -0.3, 0]) for *_, x in devs])
        self.play(FadeIn(pubs))
        self.play(*[p.animate.move_to([x * 0.7, -1.7, 0]) for p, (*_, x) in zip(pubs, devs)], run_time=1.4)
        say("Only PUBLIC keys reach the server: a stolen database cannot be used to sign in", PUB_C)
        self.wait(3.5)

        # ======================= part 3: log in with different methods =======================
        next_part("3. Log in with different methods")
        user, browser, server, store = build_site()
        row = Text("7f3a91..    ES256 key       0      bob", font_size=10, font=MONO)
        row.move_to([STORE_POS[0], STORE_POS[1] - 0.2, 0])
        self.play(FadeIn(row))

        methods = [
            ("FIDO2 security key", "USB / NFC, CTAP2", YELLOW, "Touch the key (and PIN if asked)",
             "CTAP2 getAssertion", "inside the key's secure element"),
            ("Windows Hello", "TPM 2.0 chip", TEAL, "Face, fingerprint or Windows Hello PIN",
             "platform API call", "inside the TPM chip"),
            ("Phone via QR code", "cross-device (hybrid)", BLUE, "Scan the QR code, approve on the phone",
             "Bluetooth + cloud relay", "inside the phone's secure hardware"),
            ("Synced passkey", "password manager / iCloud / Google", BURGUNDY, "Autofill, then biometric or master key",
             "browser autofill", "using the synced private key"),
        ]
        counter = None
        for idx, (mt, ms, mc, uv_msg, link, where) in enumerate(methods):
            first = idx == 0
            new_counter = Text(f"Method {idx + 1} of {len(methods)}", font_size=14, color=GRAY_B).to_edge(
                UP, buff=0.85)
            anims = [FadeIn(new_counter)] + ([FadeOut(counter)] if counter else [])
            self.play(*anims, run_time=0.4)
            counter = new_counter

            auth = node(mt, ms, mc, 2.9, 1.3, AUTH_POS, fs=15)
            priv = labelled_key(PRIV_C, "private key", 0.8).next_to(auth[0], LEFT, buff=0.35)
            self.play(FadeIn(auth), FadeIn(priv), run_time=0.7)
            say(f"The user chooses to sign in with: {mt}", mc)
            self.wait(0.6 if not first else 1.2)

            hop("Sign in with passkey", WHITE, user[0].get_right() + RIGHT * 0.1, browser[0].get_left(), 0.9)
            hop("GET options", BROWSER_C, browser[0].get_right(), server[0].get_left(), 0.8)
            if first:
                say("The site issues a NEW random challenge for every sign in", SERVER_C)
                show_card(info_card("PublicKeyCredentialRequestOptions", [
                    "challenge : new random bytes",
                    "rpId      : example.com",
                    "allowCredentials : empty",
                ], SERVER_C, 3.3, (0.55, -0.4)))
            hop("challenge", SERVER_C, server[0].get_left(), browser[0].get_right(), 0.8)

            say("navigator.credentials.get() via " + link, BROWSER_C)
            hop("credentials.get()", BROWSER_C, browser[0].get_bottom(), auth[0].get_top(), 0.9)

            say("User verification: " + uv_msg, YELLOW)
            uv = Text("verify user", font_size=12, color=YELLOW).next_to(auth[0], RIGHT, buff=0.25)
            self.play(FadeIn(uv), Indicate(auth[0], color=YELLOW), run_time=1.0)

            say("The challenge is signed " + where + ". The private key does not leave.", PRIV_C)
            self.play(Indicate(priv, color=PRIV_C, scale_factor=1.35), run_time=1.1)
            self.play(FadeOut(uv), run_time=0.2)
            hop("signature", GREEN, auth[0].get_top(), browser[0].get_bottom(), 0.9)
            hop("POST assertion", BROWSER_C, browser[0].get_right(), server[0].get_left(), 0.9)

            say("The server finds the PUBLIC key by credentialId and verifies the signature", SERVER_C)
            self.play(Indicate(row, color=GREEN, scale_factor=1.15), run_time=0.9)
            if first:
                show_card(info_card("ASP.NET Core Identity verifies", [
                    "[x] signature valid (public key)",
                    "[x] challenge and origin match",
                    "[x] signCount has increased",
                ], SERVER_C, 3.3, (0.55, -0.4)))
            self.play(Indicate(server[0], color=SERVER_C), run_time=0.8)
            new_row = Text(f"7f3a91..    ES256 key       {idx + 1}      bob", font_size=10, font=MONO)
            new_row.move_to(row)
            self.play(Transform(row, new_row), run_time=0.4)

            say("Signed in: the server issues the normal authentication cookie", GREEN)
            hop("auth cookie", GREEN, server[0].get_left(), browser[0].get_right(), 0.9)
            ok = Text("Signed in as bob", font_size=18, color=GREEN).next_to(browser[0], UP, buff=0.3)
            self.play(FadeIn(ok), run_time=0.4)
            self.wait(1.5)
            self.play(FadeOut(ok), FadeOut(auth), FadeOut(priv), run_time=0.5)
            if first:
                clear_card()

        say("Same protocol every time: only the authenticator and how the user is verified change", GREEN)
        self.wait(3)

        # ======================= summary =======================
        next_part("Summary")
        pts = VGroup(
            Text("Create: the authenticator makes a key pair, the site stores the public key", font_size=19,
                 color=GREEN),
            Text("Private keys live in FIDO2 keys, TPMs, Secure Enclave, Android or password managers",
                 font_size=19, color=PRIV_C),
            Text("Log in: the site sends a challenge and the authenticator signs it", font_size=19,
                 color=BROWSER_C),
            Text("ASP.NET Core Identity on .NET 10 verifies it against AspNetUserPasskeys", font_size=19,
                 color=SERVER_C),
            Text("Signatures are bound to the site's domain, so passkeys resist phishing", font_size=19,
                 color=YELLOW),
        ).arrange(DOWN, buff=0.45, aligned_edge=LEFT).move_to([0, 0.2, 0])
        self.play(FadeIn(pts, lag_ratio=0.3), run_time=2.5)
        self.wait(5)
