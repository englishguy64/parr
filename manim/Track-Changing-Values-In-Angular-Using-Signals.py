import re
from manim import *

# ---- parr color scheme (from Source/parr/styles.css) ----
BG = "#f5f7fa"
INK = "#222222"
MUTED = "#6b7280"
LINE = "#9ca3af"
BURGUNDY = "#7a1f3d"
GOLD = "#b8860b"
OK_C = "#2e7d5b"

config.background_color = BG
Text.set_default(font="Arial", color=INK)

SPA_C = "#7a1f3d"       # Angular SPA and its components
SIGNAL_C = "#0369a1"    # writable signal
COMPUTED_C = "#0f766e"  # computed signal
EFFECT_C = "#b8860b"    # effect
DIRTY_C = "#d97706"     # marked dirty
SLOW = 1.6              # slows every animation and pause
STATUS_Y = -3.0         # captions sit above the video player controls

PRICE = 19


def tc(text):
    """Capitalise the first letter of each word."""
    return re.sub(r"(^|[\s(\-])([a-z])", lambda m: m.group(1) + m.group(2).upper(), text)


def panel(title, sub, color, center, width, height):
    frame = RoundedRectangle(width=width, height=height, corner_radius=0.15, color=color, stroke_width=3,
                             fill_color=color, fill_opacity=0.06).move_to(center)
    head = Text(tc(title), font_size=17, color=color, weight=BOLD).move_to(frame.get_top() + DOWN * 0.3)
    if not sub:
        return VGroup(frame, head)
    sub_t = Text(sub, font_size=11, color=MUTED).next_to(head, DOWN, buff=0.05)
    return VGroup(frame, head, sub_t)


def component(title, code, center, width, height):
    """An Angular component box: name and the signal it reads in its template."""
    shape = RoundedRectangle(width=width, height=height, corner_radius=0.1, color=SPA_C, stroke_width=3,
                             fill_color=WHITE, fill_opacity=1).move_to(center)
    head = Text(title, font_size=13, color=SPA_C, weight=BOLD).move_to(shape.get_top() + DOWN * 0.25)
    parts = [shape, head]
    if code:
        c = Text(code, font="Consolas", font_size=10, color=MUTED)
        if c.width > width - 0.3:
            c.scale_to_fit_width(width - 0.3)
        parts.append(c.next_to(head, DOWN, buff=0.08))
    return VGroup(*parts)


def node(title, code, color, center, width=2.6, height=1.2):
    """A signal, computed or effect in the store, with its current value as the last line."""
    shape = RoundedRectangle(width=width, height=height, corner_radius=0.1, color=color, fill_color=color,
                             fill_opacity=0.12, stroke_width=3).move_to(center)
    t = Text(title, font_size=14, color=color, weight=BOLD)
    c = Text(code, font="Consolas", font_size=9, color=MUTED)
    if c.width > width - 0.2:
        c.scale_to_fit_width(width - 0.2)
    group = VGroup(t, c).arrange(DOWN, buff=0.07).move_to(shape.get_center() + UP * 0.17)
    return VGroup(shape, group)


def value(label, center, color, size=13):
    return Text(label, font_size=size, color=color, weight=BOLD).move_to(center)


def arrow(a, b, color=LINE):
    return Arrow(a, b, buff=0, color=color, stroke_width=2.5, tip_length=0.15, max_tip_length_to_length_ratio=0.3)


def token(label, color, width=1.2):
    shape = RoundedRectangle(width=width, height=0.28, corner_radius=0.07, color=color, fill_color=WHITE,
                             fill_opacity=1, stroke_width=2)
    return VGroup(shape, Text(label, font_size=9, color=color).move_to(shape))


class TrackChangingValues(Scene):
    def play(self, *args, **kwargs):
        kwargs["run_time"] = kwargs.get("run_time", 1.0) * SLOW
        super().play(*args, **kwargs)

    def wait(self, duration=1.0, **kwargs):
        super().wait(duration * SLOW, **kwargs)

    def construct(self):
        title = Text("Track Changing Values In Angular Using Signals", font_size=28, color=BURGUNDY).to_edge(UP, buff=0.2)
        self.add(title)
        status = Text("An Angular SPA with three components that share one signal store", font_size=20)
        status.move_to([0, STATUS_Y, 0])
        self.add(status)

        def say(msg, color=INK):
            status.become(Text(msg, font_size=20, color=color).move_to([0, STATUS_Y, 0]))

        # =====================================================================
        # The SPA and its components
        # =====================================================================
        spa = panel("Angular SPA", "Standalone Components, OnPush", SPA_C, [0, 0.2, 0], 14.0, 5.5)
        comps = panel("Components", "", SPA_C, [-3.4, -0.1, 0], 6.6, 4.6)
        header = component("HeaderComponent", "{{ store.count() }}", [-3.4, 1.25, 0], 6.0, 0.8)
        badge = value("Cart: 0", [-1.3, 1.25, 0], SPA_C)
        products = component("ProductListComponent", "", [-4.95, -0.55, 0], 2.9, 2.5)
        cart = component("ShoppingBasketComponent", "{{ store.count() }} {{ store.total() }}", [-1.85, -0.55, 0], 2.9, 2.5)

        book_row = value("Book  19", [-5.4, -0.45, 0], INK, 12)
        pen_row = value("Pen  7", [-5.4, -1.15, 0], INK, 12)
        btn_book = VGroup(RoundedRectangle(width=0.7, height=0.3, corner_radius=0.08, color=SPA_C,
                                           fill_color=SPA_C, fill_opacity=0.15, stroke_width=2),
                          Text("Add", font_size=11, color=SPA_C)).move_to([-4.0, -0.45, 0])
        btn_book[1].move_to(btn_book[0])
        btn_pen = btn_book.copy().move_to([-4.0, -1.15, 0])
        no_render = value("Not Re-Rendered", [-4.95, -1.6, 0], MUTED, 12).set_opacity(0)

        cart_items = value("Items: 0", [-1.85, -0.45, 0], INK, 14)
        cart_total = value("Total: 0", [-1.85, -1.05, 0], INK, 14)

        # =====================================================================
        # The store
        # =====================================================================
        store = panel("ShoppingBasketService", "", SIGNAL_C, [3.7, -0.1, 0], 6.2, 4.6)
        items_n = node("items", "items = signal<Item[]>([])", SIGNAL_C, [3.7, 1.05, 0])
        count_n = node("count", "count = computed(() => items().length)", COMPUTED_C, [2.1, -0.45, 0], 2.9)
        total_n = node("total", "total = computed(() => items().reduce(...))", COMPUTED_C, [5.3, -0.45, 0], 2.9)
        effect_n = node("effect", "effect(() => localStorage.setItem(total()))", EFFECT_C, [3.7, -1.7, 0], 3.0, 1.0)
        items_v = value("[ ]", items_n[0].get_center() + DOWN * 0.3, SIGNAL_C)
        count_v = value("0", count_n[0].get_center() + DOWN * 0.38, COMPUTED_C)
        total_v = value("0", total_n[0].get_center() + DOWN * 0.38, COMPUTED_C)
        effect_v = value("Saved: 0", effect_n[0].get_center() + DOWN * 0.28, EFFECT_C, 12)

        dep1 = arrow(items_n[0].get_bottom() + LEFT * 0.7, count_n[0].get_top() + RIGHT * 0.5, LINE)
        dep2 = arrow(items_n[0].get_bottom() + RIGHT * 0.7, total_n[0].get_top() + LEFT * 0.5, LINE)
        dep3 = arrow(total_n[0].get_bottom() + LEFT * 0.7, effect_n[0].get_top() + RIGHT * 0.8, LINE)

        # reads: components to the store
        read_header = DashedLine([-0.1, 1.25, 0], [0.6, 1.25, 0], color=SIGNAL_C, stroke_width=2.5)
        read_header.add_tip(tip_length=0.12)
        read_cart = DashedLine([-0.4, -0.55, 0], [0.6, -0.55, 0], color=SIGNAL_C, stroke_width=2.5)
        read_cart.add_tip(tip_length=0.12)

        self.play(FadeIn(spa), run_time=0.8)
        self.play(FadeIn(comps), FadeIn(store), run_time=1.0)
        self.play(FadeIn(header), FadeIn(badge), FadeIn(products), FadeIn(cart), run_time=1.0)
        self.add(no_render)
        self.play(FadeIn(book_row), FadeIn(pen_row), FadeIn(btn_book), FadeIn(btn_pen),
                  FadeIn(cart_items), FadeIn(cart_total), run_time=0.8)
        say("Three components: a header with a cart badge, a product list and the cart", SPA_C)
        self.wait(3.0)

        # =====================================================================
        # signal()
        # =====================================================================
        say("signal(): the store holds the cart in a writable signal. It is a value that tells Angular who reads it", SIGNAL_C)
        self.play(FadeIn(items_n), FadeIn(items_v), run_time=1.0)
        self.wait(3.0)

        # =====================================================================
        # computed()
        # =====================================================================
        say("computed(): count and total are derived from items. They are read-only and cached until items changes", COMPUTED_C)
        self.play(FadeIn(count_n), FadeIn(total_n), FadeIn(count_v), FadeIn(total_v),
                  FadeIn(dep1), FadeIn(dep2), run_time=1.0)
        self.wait(3.0)

        # =====================================================================
        # effect()
        # =====================================================================
        say("effect(): runs a side effect, here saving the total to local storage, whenever a signal it reads changes", EFFECT_C)
        self.play(FadeIn(effect_n), FadeIn(effect_v), FadeIn(dep3), run_time=1.0)
        self.wait(3.0)

        # =====================================================================
        # components read signals
        # =====================================================================
        say("Components read signals by calling them in the template. Angular records each reader", SIGNAL_C)
        self.play(FadeIn(read_header), FadeIn(read_cart), run_time=0.8)
        self.wait(3.0)

        # =====================================================================
        # Click: add a book
        # =====================================================================
        def add_book(n):
            say("The user clicks Add. The component calls store.add(), which calls items.update()", SPA_C)
            self.play(Indicate(btn_book[0], color=SPA_C, scale_factor=1.15), run_time=0.8)
            tok = token("store.add(book)", SPA_C, 1.3).move_to(btn_book.get_center())
            self.play(FadeIn(tok), run_time=0.3)
            self.play(tok.animate.move_to(items_n[0].get_left() + LEFT * 0.5 + DOWN * 0.1), run_time=1.4)
            self.play(FadeOut(tok), run_time=0.3)
            self.play(Transform(items_v, value("[ " + ", ".join(["Book"] * n) + " ]",
                                               items_n[0].get_center() + DOWN * 0.3, SIGNAL_C)), run_time=0.8)
            self.wait(1.0)

            say("items changed, so its dependants are marked dirty. Nothing is recalculated yet", DIRTY_C)
            self.play(count_n[0].animate.set_stroke(DIRTY_C), total_n[0].animate.set_stroke(DIRTY_C),
                      effect_n[0].animate.set_stroke(DIRTY_C), items_n[0].animate.set_stroke(DIRTY_C),
                      run_time=0.8)
            self.wait(2.0)

            say("Angular refreshes only the views that read them: the badge and the cart. The product list is skipped", OK_C)
            self.play(Transform(count_v, value(str(n), count_n[0].get_center() + DOWN * 0.38, COMPUTED_C)),
                      Transform(total_v, value(str(n * PRICE), total_n[0].get_center() + DOWN * 0.38, COMPUTED_C)),
                      count_n[0].animate.set_stroke(COMPUTED_C), total_n[0].animate.set_stroke(COMPUTED_C),
                      items_n[0].animate.set_stroke(SIGNAL_C), run_time=1.0)
            self.play(Transform(badge, value("Cart: %d" % n, badge.get_center(), SPA_C)),
                      Transform(cart_items, value("Items: %d" % n, cart_items.get_center(), INK, 14)),
                      Transform(cart_total, value("Total: %d" % (n * PRICE), cart_total.get_center(), INK, 14)),
                      Indicate(header[0], color=OK_C, scale_factor=1.03),
                      Indicate(cart[0], color=OK_C, scale_factor=1.04), run_time=1.2)
            self.play(no_render.animate.set_opacity(1), run_time=0.6)
            self.wait(1.5)

            say("The effect runs once, after the change, and saves the new total", EFFECT_C)
            self.play(effect_n[0].animate.set_stroke(EFFECT_C), run_time=0.5)
            self.play(Transform(effect_v, value("Saved: %d" % (n * PRICE), effect_n[0].get_center() + DOWN * 0.28,
                                                EFFECT_C, 12)),
                      Indicate(effect_n[0], color=EFFECT_C, scale_factor=1.06), run_time=1.0)
            self.wait(2.0)

        add_book(1)
        self.play(no_render.animate.set_opacity(0), run_time=0.4)
        add_book(2)

        # =====================================================================
        # Summary
        # =====================================================================
        say("Signals give fine-grained updates: change a value, and only the code that reads it reacts", OK_C)
        self.wait(5.0)
