import re
from manim import *

# ---- parr color scheme (from Source/parr/styles.css) ----
BG = "#f5f7fa"
INK = "#222222"
MUTED = "#6b7280"
LINE = "#9ca3af"
BURGUNDY = "#7a1f3d"
OK_C = "#2e7d5b"

config.background_color = BG
Text.set_default(font="Arial", color=INK)

SITE_C = "#7a1f3d"      # browser, the web site
API_C = "#0369a1"       # backend API
BANKID_C = "#0f766e"    # BankID service
APP_C = "#2e7d5b"       # BankID app on the phone
TEST_C = "#0369a1"
PROD_C = "#7a1f3d"
SLOW = 1.5              # slows every animation and pause
STATUS_Y = -3.0         # captions sit above the video player controls

XS = [-5.4, -2.0, 1.6, 5.0]    # BankID app, browser, backend, BankID service
TOP_Y = 1.5                    # first message
STEP_Y = 0.45                  # distance between messages


def tc(text):
    """Capitalise the first letter of each word."""
    return re.sub(r"(^|[\s(\-])([a-z])", lambda m: m.group(1) + m.group(2).upper(), text)


def actor(x, name, sub, color):
    shape = RoundedRectangle(width=2.6, height=0.7, corner_radius=0.1, color=color, fill_color=color,
                             fill_opacity=0.14, stroke_width=3).move_to([x, 2.1, 0])
    n = Text(name, font_size=13, color=color, weight=BOLD)
    s = Text(sub, font_size=10, color=MUTED)
    return VGroup(shape, VGroup(n, s).arrange(DOWN, buff=0.04).move_to(shape))


def lifeline(x):
    return DashedLine([x, 1.75, 0], [x, -2.45, 0], color=LINE, stroke_width=1.5, dash_length=0.1)


def msg(i, a, b, label, color, dashed=False):
    """Message number i (0 is the first) from actor a to actor b."""
    y = TOP_Y - STEP_Y * i
    sign = 1 if XS[b] > XS[a] else -1
    start = [XS[a] + 0.04 * sign, y, 0]
    end = [XS[b] - 0.04 * sign, y, 0]
    if dashed:
        line = DashedLine(start, end, color=color, stroke_width=2.5, dash_length=0.12)
        line.add_tip(tip_length=0.14)
    else:
        line = Arrow(start, end, buff=0, color=color, stroke_width=2.5, tip_length=0.15,
                     max_tip_length_to_length_ratio=0.3)
    text = Text(label, font_size=10, color=color).move_to([(XS[a] + XS[b]) / 2, y + 0.14, 0])
    return VGroup(line, text)


def card(title, color, x, rows, width=6.3):
    """A configuration card. rows is a list of (label, value, monospace)."""
    items = []
    for label, val, mono in rows:
        lab = Text(label, font_size=13, color=color, weight=BOLD)
        if mono:
            v = Text(val, font="Consolas", font_size=12, color=INK)
        else:
            v = Text(val, font_size=14, color=INK)
        items.append(VGroup(lab, v).arrange(DOWN, buff=0.04, aligned_edge=LEFT))
    body = VGroup(*items).arrange(DOWN, buff=0.2, aligned_edge=LEFT)
    head = Text(tc(title), font_size=18, color=color, weight=BOLD)
    height = 4.2
    frame = RoundedRectangle(width=width, height=height, corner_radius=0.15, color=color, stroke_width=3,
                             fill_color=WHITE, fill_opacity=1).move_to([x, 0.3, 0])
    head.move_to(frame.get_top() + DOWN * 0.32)
    body.next_to(head, DOWN, buff=0.22).align_to(frame, LEFT).shift(RIGHT * 0.3)
    return VGroup(frame, head, body)


class IntegrateBankID(Scene):
    def play(self, *args, **kwargs):
        kwargs["run_time"] = kwargs.get("run_time", 1.0) * SLOW
        super().play(*args, **kwargs)

    def wait(self, duration=1.0, **kwargs):
        super().wait(duration * SLOW, **kwargs)

    def construct(self):
        title = Text("Integrate BankID Into Web Sites", font_size=26,
                     color=BURGUNDY).to_edge(UP, buff=0.2)
        self.add(title)
        status = Text("BankID lets a Swedish user sign in with a phone. Two environments: test and production",
                      font_size=20).move_to([0, STATUS_Y, 0])
        self.add(status)

        def say(msg_text, color=INK):
            status.become(Text(msg_text, font_size=20, color=color).move_to([0, STATUS_Y, 0]))

        # =====================================================================
        # Part 1: the actors
        # =====================================================================
        pc_actors = [actor(XS[0], "BankID App", "On The Phone", APP_C),
                     actor(XS[1], "Browser", "Web Site", SITE_C),
                     actor(XS[2], "Backend API", "Your Server", API_C),
                     actor(XS[3], "BankID Service", "Relying Party API v6.0", BANKID_C)]
        self.play(*[FadeIn(a) for a in pc_actors], run_time=1.0)
        self.wait(2.0)
        say("The web site never talks to BankID. Only the backend API does, using a certificate", API_C)
        self.wait(3.0)
        say("The BankID app on the phone talks to the BankID service", APP_C)
        self.wait(3.0)
        self.play(*[FadeOut(a) for a in pc_actors], run_time=0.6)

        # =====================================================================
        # Why the web site needs a backend
        # =====================================================================
        say("A web site cannot call BankID safely on its own. It needs a backend API", API_C)
        why = [
            "The BankID service needs a TLS client certificate, and a web site cannot keep it secret",
            "The web site must never see the qrStartSecret that builds the QR code",
            "Only the backend sees the real end user IP, so only it can check the ip from /collect",
            "The backend API, not the web site, decides the user is signed in and starts the session",
        ]
        why_rows = VGroup(*[Text("%d.  %s" % (i + 1, r), font_size=15) for i, r in enumerate(why)])
        why_rows.arrange(DOWN, buff=0.4, aligned_edge=LEFT)
        why_frame = RoundedRectangle(width=why_rows.width + 0.8, height=why_rows.height + 1.0, corner_radius=0.15,
                                     color=API_C, stroke_width=3, fill_color=WHITE, fill_opacity=1).move_to([0, 0.2, 0])
        why_head = Text("Why The Web Site Needs A Backend API", font_size=18, color=API_C, weight=BOLD)
        why_head.move_to(why_frame.get_top() + DOWN * 0.32)
        why_rows.next_to(why_head, DOWN, buff=0.3).align_to(why_frame, LEFT).shift(RIGHT * 0.4)
        self.play(FadeIn(why_frame), FadeIn(why_head), run_time=0.8)
        for row in why_rows:
            self.play(FadeIn(row, shift=RIGHT * 0.2), run_time=0.6)
            self.wait(2.0)
        self.wait(2.0)
        self.play(FadeOut(VGroup(why_frame, why_head, why_rows)), run_time=0.8)

        # =====================================================================
        # Part 2: test and production configuration
        # =====================================================================
        say("Part 1: The same code runs in test and production. Only the configuration changes", INK)
        test_card = card("Test Configuration", TEST_C, -3.55, [
            ("Endpoint", "https://appapi2.test.bankid.com/rp/v6.0/", True),
            ("Your Certificate", "In the test Key Vault. Downloaded from BankID (FPTestcert5)", False),
            ("Trust Store", "Test BankID SSL Root CA v1 Test", True),
            ("BankID App", "Configured for test, with a Test BankID", False),
            ("Agreement", "Not needed", False),
            ("Check It Works", "Log in with a Test BankID at demo.bankid.com", False),
        ])
        prod_card = card("Production Configuration", PROD_C, 3.55, [
            ("Endpoint", "https://appapi2.bankid.com/rp/v6.0/", True),
            ("Your Certificate", "Uploaded by hand to the production Key Vault", False),
            ("Trust Store", "BankID SSL Root CA v1", True),
            ("BankID App", "The real BankID the user already has", False),
            ("Agreement", "Required, with a bank that sells BankID", False),
            ("Check It Works", "Same code, only configuration changes", False),
        ])
        self.play(FadeIn(test_card), run_time=1.0)
        say("Test: free to try. Download the test certificate and use a Test BankID in a test configured app", TEST_C)
        self.wait(6.0)
        self.play(FadeIn(prod_card), run_time=1.0)
        say("Production: a different endpoint, a different certificate and a different trust store", PROD_C)
        self.wait(6.0)
        say("The web site has a Test or Production option. The backend picks the matching certificate from Key Vault", API_C)
        self.wait(6.0)
        say("A test call sent to production never shows a login in an app configured for test", INK)
        self.wait(5.0)
        self.play(FadeOut(test_card), FadeOut(prod_card), run_time=0.8)

        # =====================================================================
        # Part 3: requirements for production
        # =====================================================================
        say("Part 2: What you need before you can go to production", PROD_C)
        reqs = [
            "Sign an agreement with a bank that sells BankID",
            "Order a relying party certificate from that bank. It is not the test certificate",
            "Upload it by hand to the production Key Vault. The backend reads it with its managed identity",
            "Install the BankID SSL root CA for production in the backend trust store",
            "Call https://appapi2.bankid.com/rp/v6.0/ using TLS 1.2 or 1.3 with the certificate",
            "Send the real end user IP in every order and check it matches the ip in /collect",
            "Keep qrStartSecret in the backend and call /collect every 2 seconds",
            "Renew the certificate before it expires",
        ]
        rows = VGroup(*[Text("%d.  %s" % (i + 1, r), font_size=15) for i, r in enumerate(reqs)])
        rows.arrange(DOWN, buff=0.3, aligned_edge=LEFT)
        frame = RoundedRectangle(width=rows.width + 0.8, height=rows.height + 1.0, corner_radius=0.15,
                                 color=PROD_C, stroke_width=3, fill_color=WHITE, fill_opacity=1).move_to([0, 0.1, 0])
        head = Text("Requirements For Production", font_size=18, color=PROD_C, weight=BOLD)
        head.move_to(frame.get_top() + DOWN * 0.32)
        rows.next_to(head, DOWN, buff=0.25).align_to(frame, LEFT).shift(RIGHT * 0.4)
        self.play(FadeIn(frame), FadeIn(head), run_time=0.8)
        for i, row in enumerate(rows):
            self.play(FadeIn(row, shift=RIGHT * 0.2), run_time=0.6)
            self.wait(1.6)
        self.wait(3.0)
        self.play(FadeOut(VGroup(frame, head, rows)), run_time=0.8)

        # =====================================================================
        # Part 4: sign in from a PC, scanning a QR code
        # =====================================================================
        def build_flow(actors_group, flow_title):
            lines = [lifeline(x) for x in XS]
            self.play(*[FadeIn(a) for a in actors_group], *[FadeIn(l) for l in lines], run_time=1.0)
            return lines

        say("Part 3: Sign in from a PC. The user scans an animated QR code with the phone", SITE_C)
        pc_actors = [actor(XS[0], "BankID App", "On The Phone", APP_C),
                     actor(XS[1], "Browser", "Web Site On The PC", SITE_C),
                     actor(XS[2], "Backend API", "Your Server", API_C),
                     actor(XS[3], "BankID Service", "Relying Party API v6.0", BANKID_C)]
        lines = build_flow(pc_actors, "pc")
        self.wait(2.0)

        steps = [
            (1, 2, "POST /api/bankid/start", SITE_C, False,
             "The web site asks the backend to start a sign in. The backend is the only part that calls BankID", SITE_C),
            (2, 3, "POST /auth with endUserIp", API_C, False,
             "The backend calls /auth with the end user IP. The TLS client certificate identifies your company", API_C),
            (3, 2, "orderRef, qrStartToken, qrStartSecret", BANKID_C, True,
             "BankID returns an order. The qrStartSecret never leaves the backend", BANKID_C),
            (2, 1, "orderRef and QR data", API_C, True,
             "Every second the backend builds new QR data: bankid.token.time.HMAC. the web site draws the QR code", API_C),
            (1, 0, "Scans the animated QR code", SITE_C, True,
             "The user scans the animated QR code with the BankID app on the phone", APP_C),
            (0, 3, "User approves with PIN or biometrics", APP_C, False,
             "The user approves in the BankID app. The app talks directly to the BankID service", APP_C),
            (2, 3, "POST /collect every 2 seconds", API_C, False,
             "Meanwhile the backend calls /collect every 2 seconds. The status stays pending until the user is done", API_C),
            (3, 2, "complete: Personal Number (YYYYMMDDNNNN)", BANKID_C, True,
             "Complete: the backend gets the Personal Number (YYYYMMDDNNNN) and name, and checks the ip is the one it saw", BANKID_C),
            (2, 1, "Session cookie: signed in", API_C, True,
             "The backend starts its own session. The web site shows the user as signed in", OK_C),
        ]
        shown = []
        for i, (a, b, label, color, dashed, caption, ccolor) in enumerate(steps):
            say(caption, ccolor)
            m = msg(i, a, b, label, color, dashed)
            self.play(FadeIn(m), run_time=0.8)
            shown.append(m)
            self.wait(2.6)
        self.wait(2.0)
        self.play(*[FadeOut(x) for x in shown], *[FadeOut(a) for a in pc_actors], *[FadeOut(l) for l in lines],
                  run_time=0.8)

        # =====================================================================
        # Part 5: sign in on the phone, same device
        # =====================================================================
        say("Part 4: Sign in on the phone. The website and the BankID app are on the same device", SITE_C)
        mob_actors = [actor(XS[0], "BankID App", "On The Same Phone", APP_C),
                      actor(XS[1], "Browser", "Web Site On The Phone", SITE_C),
                      actor(XS[2], "Backend API", "Your Server", API_C),
                      actor(XS[3], "BankID Service", "Relying Party API v6.0", BANKID_C)]
        lines = build_flow(mob_actors, "mobile")
        phone = DashedVMobject(RoundedRectangle(width=6.3, height=5.3, corner_radius=0.2, color=SITE_C,
                                                stroke_width=2).move_to([(XS[0] + XS[1]) / 2, 0.0, 0]), num_dashes=60)
        phone_lbl = Text("Same Phone", font_size=12, color=SITE_C, weight=BOLD).move_to([(XS[0] + XS[1]) / 2, 2.65, 0])
        self.play(FadeIn(phone), FadeIn(phone_lbl), run_time=0.8)
        self.wait(2.0)

        steps = [
            (1, 2, "POST /api/bankid/start", SITE_C, False,
             "The web site asks the backend to start a sign in. No QR code is needed on the same device", SITE_C),
            (2, 3, "POST /auth with endUserIp, returnUrl", API_C, False,
             "The backend calls /auth with the end user IP and a returnUrl for coming back to the site", API_C),
            (3, 2, "orderRef, autoStartToken", BANKID_C, True,
             "BankID returns an orderRef and an autoStartToken", BANKID_C),
            (2, 1, "orderRef, autoStartToken", API_C, True,
             "The backend passes the autoStartToken on to the web site", API_C),
            (1, 0, "Open app.bankid.com/?autostarttoken=...", SITE_C, False,
             "The web site opens the BankID app with a link containing the autoStartToken", SITE_C),
            (0, 3, "User approves, app returns to site", APP_C, False,
             "The user approves in the BankID app, which then returns to the website using the returnUrl", APP_C),
            (2, 3, "POST /collect every 2 seconds", API_C, False,
             "The backend calls /collect every 2 seconds, exactly as on the PC", API_C),
            (3, 2, "complete: Personal Number (YYYYMMDDNNNN)", BANKID_C, True,
             "Complete: the backend checks the ip matches the browser. This protects against session fixation", BANKID_C),
            (2, 1, "Session cookie: signed in", API_C, True,
             "The backend starts its session and the web site shows the user as signed in", OK_C),
        ]
        shown = []
        for i, (a, b, label, color, dashed, caption, ccolor) in enumerate(steps):
            say(caption, ccolor)
            m = msg(i, a, b, label, color, dashed)
            self.play(FadeIn(m), run_time=0.8)
            shown.append(m)
            self.wait(2.6)
        self.wait(2.0)

        say("Tip: on a phone also offer a QR code, and on a PC also offer Open BankID on this device", OK_C)
        self.wait(6.0)
