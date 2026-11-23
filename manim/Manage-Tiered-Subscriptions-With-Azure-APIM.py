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
ORANGE = "#a33a5c"

Text.set_default(font="Arial", color=INK)

OKTA_C = "#475569"
APIM_C = PURPLE
BASIC_C = TEAL
PRO_C = YELLOW
PREM_C = ORANGE
TIER_COL = {"basic": BASIC_C, "pro": PRO_C, "premium": PREM_C}
CODE_CFG = {"font": "Consolas", "font_size": 14}


def packet(label, color):
    box = RoundedRectangle(width=max(0.5, 0.1 * len(label) + 0.25), height=0.3, corner_radius=0.08,
                           color=color, fill_color=color, fill_opacity=0.95, stroke_width=1)
    return VGroup(box, Text(label, font_size=11, color=BLACK).move_to(box))


def node(title, sub, color, w, h, pos, fs=15):
    r = RoundedRectangle(width=w, height=h, corner_radius=0.12, color=color,
                         fill_color=color, fill_opacity=0.14, stroke_width=3).move_to([pos[0], pos[1], 0])
    t = Text(title, font_size=fs, color=color)
    parts = [t]
    if sub:
        parts.append(Text(sub, font_size=fs - 4, color=GRAY_B, line_spacing=0.9))
    g = VGroup(*parts).arrange(DOWN, buff=0.12).move_to(r)
    return VGroup(r, g)


def person(name, tier, pos):
    icon = VGroup(Circle(radius=0.13, color=WHITE, stroke_width=3),
                  Arc(radius=0.24, start_angle=0, angle=PI, color=WHITE, stroke_width=3).shift(DOWN * 0.36))
    lbl = Text(name, font_size=13).next_to(icon, DOWN, buff=0.12)
    tl = Text(tier, font_size=12, color=TIER_COL[tier.lower()]).next_to(lbl, DOWN, buff=0.04)
    return VGroup(icon, lbl, tl).move_to([pos[0], pos[1], 0])


def code_block(xml, width):
    c = Code(code_string=xml, language="xml", background="rectangle", formatter_style="monokai",
             paragraph_config=CODE_CFG)
    c.scale_to_fit_width(width)
    return c


class SubscriptionTiersAPIM(Scene):
    def construct(self):
        self.header = None
        self.status = None

        def next_part(text):
            if self.mobjects:
                self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.6)
            self.clear()
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

        # ======================= intro =======================
        title = Text("Manage Tiered Subscriptions With Azure APIM", font_size=34,
                     line_spacing=0.9, color=BURGUNDY)
        tiers = VGroup(*[Text(n, font_size=26, color=c) for n, c in
                         (("Basic", BASIC_C), ("Pro", PRO_C), ("Premium", PREM_C))]).arrange(RIGHT, buff=0.8)
        tiers.next_to(title, DOWN, buff=0.6)
        self.add(title)
        self.play(FadeIn(tiers, lag_ratio=0.3))
        self.wait(2)
        self.play(FadeOut(title), FadeOut(tiers))

        # ======================= part 1: identity + tier claim =======================
        next_part("1. Who is Basic, Pro or Premium?  The tier claim")

        bob = person("Bob", "Pro", (-6.1, 1.0))
        alice = person("Alice", "Basic", (-6.1, -1.2))
        okta = node("Okta", "custom claim on the\nauthorization server", OKTA_C, 2.8, 1.2, (-2.5, 0.0))
        prof = node("Okta user profile", "subscription_tier", OKTA_C, 2.5, 1.0, (1.8, 0.0))

        db_box = RoundedRectangle(width=2.5, height=2.8, corner_radius=0.12, color=GREEN,
                                  fill_color=GREEN, fill_opacity=0.12, stroke_width=3).move_to([5.7, 0.0, 0])
        db_t = Text("Subscription store", font_size=14, color=GREEN).move_to([5.7, 1.15, 0])
        db_s = Text("(Azure SQL, written by billing)", font_size=10, color=GRAY_B).move_to([5.7, 0.9, 0])
        rows = VGroup(*[Text(t, font_size=13) for t in ("alice    basic", "bob       pro", "carol    premium")])
        rows.arrange(DOWN, buff=0.22, aligned_edge=LEFT).move_to([5.7, -0.15, 0])
        db = VGroup(db_box, db_t, db_s, rows)

        self.play(FadeIn(bob), FadeIn(alice))
        self.play(FadeIn(okta))
        self.play(FadeIn(prof), FadeIn(db))
        sync = Arrow(db_box.get_left(), prof[0].get_right(), buff=0.05,
                     color=GRAY_B, stroke_width=2, max_tip_length_to_length_ratio=0.15)
        sync_l = Text("synced from billing", font_size=10, color=GRAY_B).move_to([3.75, 0.3, 0])
        self.play(Create(sync), FadeIn(sync_l))
        say("The subscription tier is persisted in a store and synced to the user's Okta profile", GREEN)
        self.wait(2.5)

        def token_card(name, tier, color):
            card = VGroup(
                RoundedRectangle(width=3.9, height=1.15, corner_radius=0.1, color=color, stroke_width=2,
                                 fill_color=BLACK, fill_opacity=1),
                Text(f"Access token (JWT) for {name.capitalize()}", font_size=12, color=color),
                Text(f"sub: {name}   aud: api://orders\nscp: orders.read   tier: {tier}", font_size=12,
                     line_spacing=0.9),
            )
            card[1].move_to(card[0].get_top() + DOWN * 0.22)
            card[2].move_to(card[0].get_center() + DOWN * 0.1)
            return card.move_to([-2.5, -1.9, 0])

        def sign_in(user, name, tier, color):
            say(f"{name.capitalize()} signs in with Okta", OKTA_C)
            hop("sign in", WHITE, user.get_right(), okta[0].get_left())
            hop("read profile", OKTA_C, okta[0].get_right(), prof[0].get_left(), 0.8)
            sub_val = Text(f"subscription_tier = {tier}", font_size=11, color=color).next_to(prof[0], DOWN, buff=0.08)
            self.play(FadeIn(sub_val))
            hop(f"tier = {tier}", color, prof[0].get_left(), okta[0].get_right(), 0.8)
            say(f"Okta maps the profile attribute to a claim in the access token: tier = {tier}", OKTA_C)
            tok = token_card(name, tier, color)
            self.play(FadeIn(tok))
            hop("token", color, okta[0].get_left(), user.get_right(), 0.9)
            self.wait(1.5)
            self.play(FadeOut(tok), FadeOut(sub_val))

        sign_in(bob, "bob", "pro", PRO_C)
        sign_in(alice, "alice", "basic", BASIC_C)

        # ======================= part 2: claim processed in APIM =======================
        next_part("2. How APIM processes the claim")

        steps = [
            ("1. validate-jwt", "Okta issuer\n+ audience", APIM_C),
            ("2. read claim", "set-variable\ntier from the JWT", APIM_C),
            ("3. choose", "branch on the\ntier variable", APIM_C),
            ("4. include-fragment", "tier-basic / pro /\npremium", APIM_C),
            ("5. Backend", "Orders API\n(only if allowed)", TEAL),
        ]
        xs = [-5.4, -2.7, 0.0, 2.7, 5.4]
        boxes = [node(t, s, c, 2.35, 1.3, (x, 0.4), fs=14) for (t, s, c), x in zip(steps, xs)]
        apim_frame = RoundedRectangle(width=13.4, height=2.2, corner_radius=0.15, color=APIM_C, stroke_width=2)
        apim_frame = DashedVMobject(apim_frame, num_dashes=90).move_to([0, 0.4, 0])
        apim_lbl = Text("Azure API Management", font_size=13, color=APIM_C).move_to([5.0, 1.4, 0])
        client = person("Client", "Pro", (-6.5, 2.0))
        self.play(FadeIn(apim_frame), FadeIn(apim_lbl), *[FadeIn(b) for b in boxes])
        self.play(FadeIn(client))
        say("Every request arrives with the JWT in the Authorization header", WHITE)
        self.wait(1)

        chips = VGroup(*[node(f"tier-{n}", None, TIER_COL[n], 1.7, 0.5, (x, -1.8), fs=14)
                         for n, x in (("basic", 0.2), ("pro", 2.5), ("premium", 4.8))])
        pk = packet("JWT  tier=pro", PRO_C).move_to([-5.4, 2.4, 0])
        self.play(FadeIn(pk))
        self.play(pk.animate.move_to(boxes[0][0].get_top() + UP * 0.25), run_time=0.9)
        say("validate-jwt checks the Okta token: issuer, audience and signature", APIM_C)
        self.play(Indicate(boxes[0][0], color=GREEN), run_time=0.8)
        self.play(pk.animate.move_to(boxes[1][0].get_top() + UP * 0.25), run_time=0.8)
        say("The tier claim is read into a variable (defaults to basic if the claim is missing)", APIM_C)
        tier_var = Text("tier = \"pro\"", font_size=14, color=PRO_C).move_to([-2.7, 1.75, 0])
        self.play(FadeIn(tier_var), Indicate(boxes[1][0], color=PRO_C), run_time=0.8)
        self.play(pk.animate.move_to(boxes[2][0].get_top() + UP * 0.25), run_time=0.8)
        say("choose compares the variable and selects exactly one policy fragment", APIM_C)
        self.play(FadeIn(chips), Indicate(boxes[2][0], color=YELLOW), run_time=0.9)
        arrows = VGroup(*[Arrow(boxes[2][0].get_bottom(), c.get_top(), buff=0.08, stroke_width=2, color=GRAY_B,
                                max_tip_length_to_length_ratio=0.12) for c in chips])
        self.play(Create(arrows))
        self.play(arrows[1].animate.set_color(PRO_C).set_stroke(width=5), chips[1][0].animate.set_fill(PRO_C, 0.5),
                  run_time=0.8)
        say("tier = pro -> the tier-pro fragment applies the Pro rate limit and quota", PRO_C)
        self.play(pk.animate.move_to(boxes[3][0].get_top() + UP * 0.25), run_time=0.8)
        self.play(Indicate(boxes[3][0], color=PRO_C), run_time=0.8)
        self.play(pk.animate.move_to(boxes[4][0].get_top() + UP * 0.25), run_time=0.8)
        self.play(Indicate(boxes[4][0], color=GREEN), FadeOut(pk), run_time=0.8)
        self.wait(1.5)

        # --- the API inbound policy XML ---
        next_part("The API inbound policy (XML)")
        xml = "\n".join([
            '<inbound>',
            '  <base />',
            '  <validate-jwt header-name="Authorization" failed-validation-httpcode="401">',
            '    <openid-config',
            '      url="https://{okta-domain}/oauth2/default/.well-known/openid-configuration" />',
            '    <audiences><audience>api://orders</audience></audiences>',
            '  </validate-jwt>',
            '  <set-variable name="sub"',
            '    value="@(context.Request.Headers.GetValueOrDefault("Authorization","").AsJwt()?.Subject)" />',
            '  <set-variable name="tier"',
            '    value="@(context.Request.Headers.GetValueOrDefault("Authorization","").AsJwt()',
            '      ?.Claims.GetValueOrDefault("tier", new string[]{"basic"}).FirstOrDefault())" />',
            '  <choose>',
            '    <when condition="@((string)context.Variables["tier"] == "premium")">',
            '      <include-fragment fragment-id="tier-premium" /></when>',
            '    <when condition="@((string)context.Variables["tier"] == "pro")">',
            '      <include-fragment fragment-id="tier-pro" /></when>',
            '    <otherwise><include-fragment fragment-id="tier-basic" /></otherwise>',
            '  </choose>',
            '</inbound>',
        ])
        code = code_block(xml, 11.5)
        if code.height > 5.0:
            code.scale_to_fit_height(5.0)
        code.move_to(DOWN * 0.1)
        self.play(FadeIn(code))
        lines = code.code_lines
        notes = [
            (2, 6, "Validate the Okta token"),
            (7, 11, "Read the user id and the tier claim"),
            (12, 18, "Choose the tier fragment (basic is the default)"),
        ]
        rect = note = None
        for a, b, text in notes:
            nr = SurroundingRectangle(VGroup(*[lines[i] for i in range(a, b + 1)]), color=YELLOW, buff=0.04,
                                      stroke_width=3)
            say(text, YELLOW)
            self.play(Create(nr) if rect is None else ReplacementTransform(rect, nr), run_time=0.6)
            rect = nr
            self.wait(3)
        self.play(FadeOut(rect))

        # ======================= part 3: products and policies =======================
        next_part("3. Products, policies and how they are assigned")
        frame = RoundedRectangle(width=13.0, height=4.7, corner_radius=0.15, color=APIM_C, stroke_width=2)
        frame = DashedVMobject(frame, num_dashes=90).move_to([0, -0.1, 0])
        fl = Text("Azure API Management", font_size=13, color=APIM_C).move_to([-5.2, -2.2, 0])
        api = node("Orders API", "one API,\npublished in 3 products", TEAL, 2.4, 1.4, (-4.9, -0.1))
        pys = [1.15, -0.1, -1.35]
        names = ["basic", "pro", "premium"]
        prods = [node(f"{n.capitalize()} product", "subscription required", TIER_COL[n], 2.7, 0.95, (-0.9, y), fs=14)
                 for n, y in zip(names, pys)]
        frags = [node(f"tier-{n}", None, TIER_COL[n], 2.3, 0.7, (4.2, y), fs=14) for n, y in zip(names, pys)]
        h1 = Text("API", font_size=12, color=GRAY_B).move_to([-4.9, 1.95, 0])
        h2 = Text("Products: packaging + subscription keys", font_size=12, color=GRAY_B).move_to([-0.9, 1.95, 0])
        h3 = Text("Policy fragments: limits", font_size=12, color=GRAY_B).move_to([4.2, 1.95, 0])
        self.play(FadeIn(frame), FadeIn(fl), FadeIn(h1), FadeIn(h2), FadeIn(h3))
        self.play(FadeIn(api))
        self.play(*[FadeIn(p) for p in prods], run_time=1.0)
        arr1 = VGroup(*[Arrow(api[0].get_right(), p[0].get_left(), buff=0.08, stroke_width=2, color=GRAY_B,
                              max_tip_length_to_length_ratio=0.1) for p in prods])
        say("The Orders API is published in three Products, one per subscription tier", WHITE)
        self.play(Create(arr1))
        self.wait(1.5)
        self.play(*[FadeIn(f) for f in frags], run_time=1.0)
        arr2 = VGroup(*[Arrow(p[0].get_right(), f[0].get_left(), buff=0.08, stroke_width=2,
                              color=TIER_COL[n], max_tip_length_to_length_ratio=0.1)
                        for p, f, n in zip(prods, frags, names)])
        say("Each Product is tied to a policy fragment that holds that tier's rate limit and quota", WHITE)
        self.play(Create(arr2))
        self.wait(2)

        claim_lbls = [Text(f"claim tier = {n}", font_size=11, color=TIER_COL[n]).next_to(f[0], DOWN, buff=0.05)
                      for f, n in zip(frags, names)]
        self.play(*[FadeIn(c) for c in claim_lbls])
        say("The tier claim in the token chooses which fragment runs for the caller", YELLOW)
        self.wait(1.5)
        for i in (0, 1, 2):
            r1 = SurroundingRectangle(VGroup(prods[i], frags[i]), color=TIER_COL[names[i]], buff=0.12, stroke_width=4)
            self.play(Create(r1), run_time=0.5)
            self.wait(0.9)
            self.play(FadeOut(r1), run_time=0.3)
        self.wait(1)

        # ======================= part 4: fragments per tier =======================
        next_part("4. A policy fragment per tier: rate limit and quota")
        specs = [("basic", 10, 1000), ("pro", 100, 50000), ("premium", 1000, 1000000)]
        summary = VGroup()
        table_hdr = VGroup(Text("Tier", font_size=15, color=GRAY_B), Text("Rate limit", font_size=15, color=GRAY_B),
                           Text("Daily quota", font_size=15, color=GRAY_B)).arrange(RIGHT, buff=0.4)
        table_hdr.move_to([4.3, 1.4, 0])
        self.play(FadeIn(table_hdr))
        rows_t = []
        prev = None
        for n, rate, quota in specs:
            xml = "\n".join([
                '<fragment>',
                f'  <!-- tier-{n} -->',
                f'  <rate-limit-by-key calls="{rate}" renewal-period="60"',
                '      counter-key="@((string)context.Variables["sub"])" />',
                f'  <quota-by-key calls="{quota}" renewal-period="86400"',
                '      counter-key="@((string)context.Variables["sub"])" />',
                '</fragment>',
            ])
            cb = code_block(xml, 7.6).move_to(LEFT * 3.0 + DOWN * 0.2)
            lbl = Text(f"Policy fragment: tier-{n}", font_size=20, color=TIER_COL[n]).next_to(cb, UP, buff=0.25)
            say(f"Claim tier = {n} -> {rate:,} calls per minute, {quota:,} calls per day", TIER_COL[n])
            if prev is None:
                self.play(FadeIn(cb), FadeIn(lbl))
            else:
                self.play(ReplacementTransform(prev[0], cb), ReplacementTransform(prev[1], lbl))
            prev = (cb, lbl)
            r = SurroundingRectangle(VGroup(cb.code_lines[2], cb.code_lines[3]), color=YELLOW, buff=0.04, stroke_width=3)
            q = SurroundingRectangle(VGroup(cb.code_lines[4], cb.code_lines[5]), color=RED, buff=0.04, stroke_width=3)
            self.play(Create(r), run_time=0.4)
            row = VGroup(Text(n.capitalize(), font_size=15, color=TIER_COL[n]),
                         Text(f"{rate:,} / min", font_size=15), Text(f"{quota:,} / day", font_size=15))
            for cell, h in zip(row, table_hdr):
                cell.move_to([h.get_center()[0], 1.4 - 0.5 * (len(rows_t) + 1), 0])
            self.play(FadeIn(row), run_time=0.4)
            rows_t.append(row)
            self.wait(1.2)
            self.play(ReplacementTransform(r, q), run_time=0.4)
            self.wait(1.2)
            self.play(FadeOut(q), run_time=0.2)
        note = Text("Counters are per user (the token's sub claim):\nrate limit exceeded -> 429 Too Many Requests\nquota exceeded -> 403 Forbidden",
                    font_size=14, color=GRAY_B, line_spacing=0.95).move_to([4.2, -1.3, 0])
        self.play(FadeIn(note))
        self.wait(3)

        # ======================= part 5: simulation =======================
        next_part("5. What users see when each tier sends 200 calls in a minute")
        count = ValueTracker(0)
        meters = []
        for n, rate, quota in specs:
            y = 1.4 - 1.5 * len(meters)
            lbl = Text(f"{n.capitalize()}  (limit {rate:,}/min)", font_size=17, color=TIER_COL[n]).move_to([-4.3, y + 0.55, 0])
            lbl.align_to([-6.6, 0, 0], LEFT)
            bg = Rectangle(width=6.0, height=0.4, color=GRAY_B, stroke_width=2).move_to([-3.6, y, 0])

            def fill(rate=rate, bg=bg, n=n):
                u = min(count.get_value() / rate, 1.0)
                col = RED if count.get_value() > rate else TIER_COL[n]
                r = Rectangle(width=max(6.0 * u, 0.001), height=0.4, stroke_width=0, fill_color=col, fill_opacity=0.9)
                return r.align_to(bg, LEFT).align_to(bg, DOWN)

            def readout(rate=rate, bg=bg):
                c = int(count.get_value())
                if c > rate:
                    return Text(f"{c} calls  ->  429 Too Many Requests", font_size=16, color=RED).next_to(bg, RIGHT, buff=0.25)
                return Text(f"{c} calls  ->  200 OK", font_size=16, color=GREEN).next_to(bg, RIGHT, buff=0.25)

            meters.append(VGroup(lbl, bg))
            self.add(lbl, bg, always_redraw(fill), always_redraw(readout))
        say("Same traffic, different outcome: the tier claim sets the limit", WHITE)
        self.wait(1)
        self.play(count.animate.set_value(200), run_time=8, rate_func=linear)
        self.wait(1)
        say("Basic is throttled after 10 calls, Pro after 100, Premium has plenty of headroom", YELLOW)
        self.wait(2.5)

        summary = Text("Identity provider -> tier claim -> APIM chooses fragment -> rate limit + quota per user",
                       font_size=18, color=GREEN).to_edge(DOWN, buff=0.7)
        self.play(FadeIn(summary))
        self.wait(3.5)
