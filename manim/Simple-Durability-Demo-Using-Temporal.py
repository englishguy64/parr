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
BAD_C = "#9f1239"

config.background_color = BG
Text.set_default(font="Arial", color=INK)

TEMPORAL_C = "#6d4c9f"
WORKFLOW_C = "#7a1f3d"
ACTIVITY_C = "#0369a1"
QUEUE_C = "#b45309"
SLOW = 1.8  # slows every animation and pause
STATUS_Y = -3.0  # captions sit above the video player controls


def tc(text):
    """Capitalise the first letter of each word."""
    return re.sub(r"(^|[\s(\-])([a-z])", lambda m: m.group(1) + m.group(2).upper(), text)


def box(title, color, width, center, height=0.7, font_size=14, subtitle=None):
    shape = RoundedRectangle(width=width, height=height, corner_radius=0.1, color=color,
                             fill_color=color, fill_opacity=0.14, stroke_width=3).move_to(center)
    if subtitle:
        t = Text(tc(title), font_size=font_size, color=color)
        s = Text(tc(subtitle), font_size=11, color=MUTED)
        label = VGroup(t, s).arrange(DOWN, buff=0.05).move_to(shape)
    else:
        label = Text(tc(title), font_size=font_size, color=color).move_to(shape)
    return VGroup(shape, label)


def chip(label, color, center, width=2.4, height=0.4, font_size=13):
    shape = RoundedRectangle(width=width, height=height, corner_radius=0.08, color=color,
                             fill_color=WHITE, fill_opacity=1, stroke_width=2).move_to(center)
    return VGroup(shape, Text(tc(label), font_size=font_size, color=INK).move_to(shape))


def arrow(a, b, color=LINE):
    return Arrow(a, b, buff=0, color=color, stroke_width=2.5, tip_length=0.15,
                 max_tip_length_to_length_ratio=0.3)


def code_panel(heading, color, lines, center, width, font_size=11):
    """A white panel with a heading and monospace code lines. Returns (panel, line_mobjects)."""
    char_w = Text("x" * 20, font="Consolas", font_size=font_size).width / 20
    rows = VGroup(*[Text(l.strip() or " ", font="Consolas", font_size=font_size, color=INK) for l in lines])
    rows.arrange(DOWN, buff=0.08, aligned_edge=LEFT)
    for row, l in zip(rows, lines):
        row.shift(RIGHT * char_w * (len(l) - len(l.lstrip())))
    if rows.width > width - 0.5:
        rows.scale_to_fit_width(width - 0.5)
    head = Text(tc(heading), font_size=14, color=color, weight=BOLD)
    height = rows.height + head.height + 0.75
    frame = RoundedRectangle(width=width, height=height, corner_radius=0.12, color=color, stroke_width=3,
                             fill_color=WHITE, fill_opacity=1).move_to(center)
    head.move_to(frame.get_top() + DOWN * 0.3)
    rows.next_to(head, DOWN, buff=0.22).shift(RIGHT * (frame.get_left()[0] + 0.25 - rows.get_left()[0] + char_w * 0))
    return VGroup(frame, head, rows), list(rows)


class DurableTemporal(Scene):
    def play(self, *args, **kwargs):
        kwargs["run_time"] = kwargs.get("run_time", 1.0) * SLOW
        super().play(*args, **kwargs)

    def wait(self, duration=1.0, **kwargs):
        super().wait(duration * SLOW, **kwargs)

    def construct(self):
        title = Text("Simple Durability Demo Using Temporal", font_size=28, color=BURGUNDY).to_edge(UP, buff=0.2)
        self.add(title)
        status = Text("Temporal runs your code as a Durable Workflow", font_size=20).move_to([0, STATUS_Y, 0])
        self.add(status)

        def say(msg, color=INK):
            status.become(Text(msg, font_size=20, color=color).move_to([0, STATUS_Y, 0]))

        # =====================================================================
        # Overview diagram
        # =====================================================================
        client = box("Client", MUTED, 1.5, [-6.0, 1.05, 0], height=0.8, subtitle="Your App")

        svc_frame = RoundedRectangle(width=4.4, height=3.0, corner_radius=0.15, color=TEMPORAL_C, stroke_width=3,
                                     fill_color=TEMPORAL_C, fill_opacity=0.07).move_to([-1.9, 1.05, 0])
        svc_title = Text("Temporal Service", font_size=16, color=TEMPORAL_C, weight=BOLD).move_to([-1.9, 2.28, 0])
        frontend = chip("Frontend", TEMPORAL_C, [-1.9, 1.8, 0])
        history = chip("History Service", TEMPORAL_C, [-1.9, 1.25, 0])
        matching = chip("Matching Service", TEMPORAL_C, [-1.9, 0.7, 0])
        database = chip("Database", GOLD, [-1.9, 0.15, 0])
        service = VGroup(svc_frame, svc_title, frontend, history, matching, database)

        queue = box("Task Queue", QUEUE_C, 1.5, [1.55, 1.05, 0], height=0.8)

        wk_frame = RoundedRectangle(width=3.8, height=3.0, corner_radius=0.15, color=TEMPORAL_C, stroke_width=3,
                                    fill_color=WHITE, fill_opacity=0.9).move_to([5.0, 1.05, 0])
        wk_title = Text("Worker (Your Process)", font_size=16, color=TEMPORAL_C, weight=BOLD).move_to([5.0, 2.28, 0])
        wf = box("Workflow", WORKFLOW_C, 3.2, [5.0, 1.65, 0], height=0.7, subtitle="Durable And Deterministic")
        acts = [chip("Reserve Stock", ACTIVITY_C, [5.0, 0.9, 0], width=3.2),
                chip("Charge Card", ACTIVITY_C, [5.0, 0.45, 0], width=3.2),
                chip("Ship Order", ACTIVITY_C, [5.0, 0.0, 0], width=3.2)]
        act_label = Text("Activities", font_size=11, color=MUTED).move_to([5.0, -0.28, 0])
        worker = VGroup(wk_frame, wk_title, wf, *acts, act_label)

        a_start = arrow([-5.25, 1.05, 0], [-4.1, 1.05, 0])
        start_lbl = Text("Start", font_size=11, color=MUTED).move_to([-4.68, 1.3, 0])
        a_queue = arrow([0.3, 1.05, 0], [0.8, 1.05, 0], QUEUE_C)
        a_poll = arrow([3.1, 1.05, 0], [2.3, 1.05, 0], QUEUE_C)
        polls = Text("Polls", font_size=11, color=QUEUE_C).move_to([2.7, 1.3, 0])
        overview = VGroup(client, service, queue, worker, a_start, start_lbl, a_queue, a_poll, polls)

        self.play(FadeIn(client), FadeIn(service), run_time=1.0)
        self.play(FadeIn(queue), FadeIn(a_start), FadeIn(start_lbl), FadeIn(a_queue), run_time=0.8)
        self.play(FadeIn(worker), FadeIn(a_poll), FadeIn(polls), run_time=1.0)
        say("Three Parts: Your Client, The Temporal Service And Your Workers")
        self.wait(2.5)

        # =====================================================================
        # Inside the Temporal Service
        # =====================================================================
        say("First, What Is A Client?", MUTED)
        self.wait(1.5)
        self.play(FadeOut(overview), run_time=0.8)

        what_head = Text("What Is A Client?", font_size=20, color=MUTED, weight=BOLD).move_to([0, 2.65, 0])
        customer = box("Customer", MUTED, 1.6, [-6.0, 1.4, 0], height=0.7, subtitle="Places An Order")
        api_frame = RoundedRectangle(width=4.2, height=1.9, corner_radius=0.14, color=INK, stroke_width=3,
                                     fill_color=WHITE, fill_opacity=1).move_to([-2.2, 1.4, 0])
        api_title = Text("Your Web API", font_size=15, color=INK, weight=BOLD).move_to([-2.2, 2.1, 0])
        api_sub = Text("Receives POST /orders", font_size=11, color=MUTED).move_to([-2.2, 1.78, 0])
        client_chip = box("Temporal Client", TEMPORAL_C, 3.2, [-2.2, 1.0, 0], height=0.6,
                          subtitle="SDK Library Inside Your App")
        svc_box = box("Temporal Service", TEMPORAL_C, 2.8, [4.6, 1.4, 0], height=0.8)
        c_a1 = arrow([-5.15, 1.4, 0], [-4.3, 1.4, 0])
        c_a2 = arrow([-0.1, 1.0, 0], [3.2, 1.0, 0], TEMPORAL_C)
        c_l2 = Text("Start OrderWorkflow", font_size=12, color=TEMPORAL_C).move_to([1.55, 1.3, 0])
        what_group = VGroup(customer, api_frame, api_title, api_sub, client_chip, svc_box, c_a1, c_a2, c_l2)

        what_lines = ["A Client Is Not A Separate Server Or Product",
                      "It Is The Temporal SDK Used Inside Your Own App, Such As A Web API Or Console App",
                      "Your App Receives An Order, The Client Asks The Service To Start OrderWorkflow",
                      "It Gets A Handle Back, So It Can Wait For The Result, Check Status, Signal Or Query",
                      "The Client Never Runs The Workflow, A Worker Does That"]
        what_rows = VGroup(*[Text("- " + x, font_size=14, color=INK) for x in what_lines]).arrange(
            DOWN, buff=0.17, aligned_edge=LEFT).move_to([0, -1.0, 0]).align_to([-6.6, 0, 0], LEFT)

        self.play(FadeIn(what_head), FadeIn(customer), run_time=0.8)
        self.play(FadeIn(api_frame), FadeIn(api_title), FadeIn(api_sub), FadeIn(c_a1), run_time=1.0)
        say("A Customer Places An Order With Your Web API", MUTED)
        self.wait(2.5)
        self.play(FadeIn(client_chip), run_time=1.0)
        say("Inside Your API, The Temporal Client Is Just Code From The Temporal SDK", TEMPORAL_C)
        self.wait(3.0)
        self.play(FadeIn(svc_box), FadeIn(c_a2), FadeIn(c_l2), run_time=1.0)
        say("It Calls The Temporal Service To Start The Workflow", BURGUNDY)
        self.wait(3.0)
        for r in what_rows:
            self.play(FadeIn(r, shift=RIGHT * 0.2), run_time=0.8)
            self.wait(1.8)
        self.wait(3.0)
        self.play(FadeOut(VGroup(what_head, what_group, what_rows)), run_time=1.0)

        # =====================================================================
        # What is the Temporal Service: self-hosted or Temporal Cloud
        # =====================================================================
        say("Next, What Is The Temporal Service?", TEMPORAL_C)
        self.wait(1.5)
        ts_head = Text("What Is The Temporal Service?", font_size=20, color=TEMPORAL_C, weight=BOLD)
        ts_head.move_to([0, 2.65, 0])
        ts_def = VGroup(
            Text("The Engine That Remembers Every Workflow: It Stores State And Event History", font_size=15),
            Text("And Hands Tasks To Workers. It Never Runs Your Code.", font_size=15)
        ).arrange(DOWN, buff=0.08).move_to([0, 2.0, 0])
        self.play(FadeIn(ts_head), FadeIn(ts_def), run_time=1.0)
        say("The Service Is Where Workflow State Lives, Your Workers Stay In Your Own Environment", TEMPORAL_C)
        self.wait(4.0)

        def option_card(name, sub, color, cx, bullets):
            shape = RoundedRectangle(width=6.6, height=2.95, corner_radius=0.14, color=color, stroke_width=3,
                                     fill_color=color, fill_opacity=0.08).move_to([cx, 0.2, 0])
            head = Text(name, font_size=22, color=color, weight=BOLD).move_to([cx, 1.3, 0])
            subt = Text(sub, font_size=13, color=MUTED).next_to(head, DOWN, buff=0.06)
            rows = [Text("- " + b, font_size=13, color=INK) for b in bullets]
            VGroup(*rows).arrange(DOWN, buff=0.14, aligned_edge=LEFT).move_to([cx, -0.3, 0]).align_to(
                [cx - 3.1, 0, 0], LEFT)
            return VGroup(shape, head, subt), rows

        sh_card, sh_rows = option_card(
            "Self-Hosted", "Option 1: You Run The Service", BURGUNDY, -3.55,
            ["Open Source And Free To Use", "Run It On Your Own Servers Or Kubernetes",
             "You Run The Database: Cassandra, PostgreSQL Or MySQL",
             "You Own Upgrades, Scaling, Backups And Security",
             "Local Dev Server: One Command, Good For Learning"])
        tc_card, tc_rows = option_card(
            "Temporal Cloud", "Option 2: Temporal Runs The Service", TEMPORAL_C, 3.55,
            ["A Managed Service, You Pay For What You Use", "Create A Namespace, Then Connect Over TLS",
             "Sign In With An API Key Or A Client Certificate",
             "Temporal Handles Upgrades, Scaling And Backups",
             "Your Workers Still Run In Your Own Environment"])

        say("Option 1: Self-Hosted, You Run The Service Yourself", BURGUNDY)
        self.play(FadeIn(sh_card), run_time=0.9)
        for r in sh_rows:
            self.play(FadeIn(r, shift=RIGHT * 0.2), run_time=0.7)
            self.wait(1.3)
        self.wait(1.0)
        say("Option 2: Temporal Cloud, Temporal Runs The Service For You", TEMPORAL_C)
        self.play(FadeIn(tc_card), run_time=0.9)
        for r in tc_rows:
            self.play(FadeIn(r, shift=RIGHT * 0.2), run_time=0.7)
            self.wait(1.3)
        self.wait(1.0)

        yc = box("Your Clients And Workers", MUTED, 3.2, [-4.2, -2.05, 0], height=0.55, font_size=13)
        ys = box("Temporal Service", TEMPORAL_C, 2.8, [3.2, -2.05, 0], height=0.55, font_size=13)
        y_arrow = arrow([-2.55, -2.05, 0], [1.75, -2.05, 0], TEMPORAL_C)
        y_lbl = Text("Self-Hosted Or Cloud: Same SDK Code", font_size=12, color=TEMPORAL_C).move_to([-0.4, -1.78, 0])
        say("Your Code Is The Same Either Way, Only Address, Namespace And Authentication Change", BURGUNDY)
        self.play(FadeIn(VGroup(yc, ys, y_arrow, y_lbl)), run_time=1.2)
        self.wait(6.0)
        self.play(FadeOut(VGroup(ts_head, ts_def, sh_card, tc_card, *sh_rows, *tc_rows, yc, ys, y_arrow, y_lbl)),
                  run_time=1.0)

        say("Next, What Is Inside The Temporal Service?", TEMPORAL_C)
        self.wait(1.5)

        heading = Text("Inside The Temporal Service", font_size=20, color=TEMPORAL_C, weight=BOLD)
        heading.move_to([0, 2.65, 0])
        c2 = box("Client", MUTED, 1.4, [-6.2, 1.9, 0], height=0.7, subtitle="Your App")
        comp_defs = [
            ("Frontend", TEMPORAL_C, 1.9, ["Clients And Workers Call It Over gRPC",
                                           "It Checks Each Request, Applies Rate Limits And Routes It"]),
            ("History Service", TEMPORAL_C, 0.8, ["Owns Every Workflow: Its State And Its Event History",
                                                   "It Decides When The Next Workflow Task Is Needed"]),
            ("Matching Service", QUEUE_C, -0.3, ["Manages The Task Queues And Holds Tasks Until A Worker Asks",
                                                  "Workers Poll It, It Matches A Task To A Waiting Worker"]),
            ("Database", GOLD, -1.4, ["Durable Storage: Cassandra, PostgreSQL Or MySQL",
                                      "The Event History Lives Here, So Nothing Is Ever Lost"]),
        ]
        comps, explains = [], []
        for name, col, y, lines in comp_defs:
            comps.append(chip(name, col, [-3.0, y, 0], width=2.6, height=0.55, font_size=15))
            explains.append(VGroup(*[Text(l, font_size=14, color=INK) for l in lines]).arrange(
                DOWN, buff=0.08, aligned_edge=LEFT).move_to([2.2, y, 0]).align_to([-1.2, 0, 0], LEFT))
        v_arrows = [arrow([-3.0, 1.9 - 0.3, 0], [-3.0, 0.8 + 0.3, 0]),
                    arrow([-3.0, 0.8 - 0.3, 0], [-3.0, -0.3 + 0.3, 0]),
                    arrow([-3.0, -0.3 - 0.3, 0], [-3.0, -1.4 + 0.3, 0])]
        c_arrow = arrow([-5.5, 1.9, 0], [-4.3, 1.9, 0])

        self.play(FadeIn(heading), FadeIn(c2), run_time=0.8)
        for i, (comp, ex) in enumerate(zip(comps, explains)):
            say(["Frontend: Receives Every Call", "History Service: Keeps Each Workflow's Record",
                 "Matching Service: Hands Work To Workers", "Database: Makes It All Durable"][i],
                comp_defs[i][1])
            extras = [FadeIn(c_arrow)] if i == 0 else [FadeIn(v_arrows[i - 1])]
            self.play(FadeIn(comp), *extras, FadeIn(ex, shift=RIGHT * 0.2), run_time=1.0)
            self.wait(3.0)

        say("Following A Start Workflow Request Through The Service", BURGUNDY)
        self.wait(1.0)
        req = Dot(c2[0].get_center(), radius=0.1, color=BURGUNDY)
        self.play(FadeIn(req), run_time=0.4)
        self.play(req.animate.move_to(comps[0][0].get_left() + RIGHT * 0.2), run_time=1.0)
        say("1  The Frontend Receives The Start Request", TEMPORAL_C)
        self.wait(2.0)
        self.play(req.animate.move_to(comps[1][0].get_left() + RIGHT * 0.2), run_time=1.0)
        say("2  History Service Creates The Workflow And Records WorkflowExecutionStarted", TEMPORAL_C)
        self.wait(2.0)
        self.play(req.animate.move_to(comps[3][0].get_left() + RIGHT * 0.2), run_time=1.0)
        say("3  The Event Is Written To The Database", GOLD)
        self.wait(2.0)
        self.play(req.animate.move_to(comps[2][0].get_left() + RIGHT * 0.2), run_time=1.0)
        say("4  Matching Service Puts A Workflow Task On The Task Queue For A Worker", QUEUE_C)
        self.wait(2.5)
        self.play(FadeOut(req), run_time=0.4)

        self.play(FadeOut(VGroup(heading, c2, c_arrow, *comps, *explains, *v_arrows)), run_time=1.0)

        # =====================================================================
        # Clients and Workers
        # =====================================================================
        say("Next: What Is The Difference Between A Client And A Worker?", BURGUNDY)
        self.wait(1.5)
        cw_head = Text("Clients And Workers", font_size=20, color=TEMPORAL_C, weight=BOLD).move_to([0, 2.65, 0])
        self.play(FadeIn(cw_head), run_time=0.8)

        def info_card(name, sub, color, cx, bullets):
            shape = RoundedRectangle(width=6.6, height=3.3, corner_radius=0.14, color=color, stroke_width=3,
                                     fill_color=color, fill_opacity=0.08).move_to([cx, 0.75, 0])
            head = Text(name, font_size=22, color=color, weight=BOLD).move_to([cx, 2.1, 0])
            subt = Text(sub, font_size=13, color=MUTED).next_to(head, DOWN, buff=0.06)
            rows = [Text("- " + b, font_size=14, color=INK) for b in bullets]
            VGroup(*rows).arrange(DOWN, buff=0.17, aligned_edge=LEFT).move_to([cx, 0.45, 0]).align_to(
                [cx - 3.1, 0, 0], LEFT)
            return VGroup(shape, head, subt), rows

        client_card, client_rows = info_card(
            "Client", "Asks For Work To Be Done", MUTED, -3.55,
            ["Any App That Needs A Workflow Run", "For Example A Web API, A Console App Or A Scheduler",
             "Starts A Workflow, Sends It Signals, Asks It Queries",
             "Does Not Run Workflow Or Activity Code", "Short-Lived: It Asks, Then Moves On"])
        worker_card, worker_rows = info_card(
            "Worker", "Does The Work", TEMPORAL_C, 3.55,
            ["A Long-Running Process That You Host", "For Example A Container In Azure Or Kubernetes",
             "Runs Your Workflow And Activity Code", "Polls One Task Queue For Work",
             "Run Several To Scale Out Or To Survive A Failure"])

        say("Client: The App That Asks For A Workflow To Be Started", MUTED)
        self.play(FadeIn(client_card), run_time=0.9)
        for r in client_rows:
            self.play(FadeIn(r, shift=RIGHT * 0.2), run_time=0.7)
            self.wait(1.2)
        self.wait(1.0)
        say("Worker: The Process That Actually Runs Your Code", TEMPORAL_C)
        self.play(FadeIn(worker_card), run_time=0.9)
        for r in worker_rows:
            self.play(FadeIn(r, shift=RIGHT * 0.2), run_time=0.7)
            self.wait(1.2)
        self.wait(1.0)

        mc = box("Client", MUTED, 1.5, [-4.2, -1.9, 0], height=0.55, font_size=13)
        ms = box("Temporal Service", TEMPORAL_C, 2.6, [0, -1.9, 0], height=0.55, font_size=13)
        mw = box("Worker", TEMPORAL_C, 1.5, [4.2, -1.9, 0], height=0.55, font_size=13)
        m_a1 = arrow([-3.45, -1.9, 0], [-1.3, -1.9, 0])
        m_a2 = arrow([3.45, -1.9, 0], [1.3, -1.9, 0], QUEUE_C)
        m_l1 = Text("Starts", font_size=11, color=MUTED).move_to([-2.4, -1.62, 0])
        m_l2 = Text("Polls", font_size=11, color=QUEUE_C).move_to([2.4, -1.62, 0])
        say("Both Connect Out To The Temporal Service, It Never Calls Into Your Apps", BURGUNDY)
        self.play(FadeIn(VGroup(mc, ms, mw, m_a1, m_a2, m_l1, m_l2)), run_time=1.2)
        self.wait(5.0)
        self.play(FadeOut(VGroup(cw_head, client_card, worker_card, *client_rows, *worker_rows,
                                 mc, ms, mw, m_a1, m_a2, m_l1, m_l2)), run_time=1.0)

        # =====================================================================
        # Client, Worker and Workflow code
        # =====================================================================
        say("Now A Detailed Example In Code: An Order Workflow", BURGUNDY)
        self.wait(1.5)

        client_panel, client_lines = code_panel(
            "Client Code: Starts The Workflow", MUTED,
            ['client = await Client.connect("localhost:7233")',
             "handle = await client.start_workflow(",
             "    OrderWorkflow.run, order,",
             '    id="order-1001",',
             '    task_queue="orders")',
             "result = await handle.result()"],
            [-3.55, 1.5, 0], 6.6)
        worker_panel, worker_lines = code_panel(
            "Worker Code: Registers Workflow And Activities", TEMPORAL_C,
            ['worker = Worker(client, task_queue="orders",',
             "    workflows=[OrderWorkflow],",
             "    activities=[reserve_stock, charge_card, ship_order])",
             "await worker.run()"],
            [-3.55, -0.85, 0], 6.6)
        wf_panel, wf_lines = code_panel(
            "Workflow Code: The Orchestration", WORKFLOW_C,
            ["@workflow.defn",
             "class OrderWorkflow:",
             "    @workflow.run",
             "    async def run(self, order):",
             "        opts = dict(start_to_close_timeout=timedelta(seconds=30))",
             "        await workflow.execute_activity(reserve_stock, order, **opts)",
             "        await workflow.execute_activity(charge_card, order, **opts)",
             "        await workflow.execute_activity(ship_order, order, **opts)",
             '        return "Shipped"'],
            [3.5, 0.7, 0], 6.9)

        def mark(lines, color):
            rect = SurroundingRectangle(VGroup(*lines), color=color, buff=0.05, stroke_width=2.5,
                                        fill_color=color, fill_opacity=0.15)
            return rect

        self.play(FadeIn(client_panel), run_time=1.0)
        say("Client: Starts The Workflow With A Unique Id And A Task Queue Name", MUTED)
        m = mark(client_lines[1:5], BURGUNDY)
        self.play(FadeIn(m), run_time=0.8)
        self.wait(3.5)
        say("The Id Identifies The Run. The Task Queue Says Which Workers Should Run It", BURGUNDY)
        self.wait(3.0)
        self.play(FadeOut(m), run_time=0.5)

        self.play(FadeIn(worker_panel), run_time=1.0)
        say("Worker: Listens To The Same Task Queue And Registers Workflow And Activity Code", TEMPORAL_C)
        m = mark(worker_lines[0:3], TEMPORAL_C)
        self.play(FadeIn(m), run_time=0.8)
        self.wait(4.0)
        self.play(FadeOut(m), run_time=0.5)

        self.play(FadeIn(wf_panel), run_time=1.0)
        say("Workflow: Plain Code That Calls Activities One After Another", WORKFLOW_C)
        m = mark(wf_lines[5:8], WORKFLOW_C)
        self.play(FadeIn(m), run_time=0.8)
        self.wait(3.5)
        say("Each Activity Call Becomes Events In The History: Scheduled, Started, Completed", GOLD)
        self.wait(4.0)
        self.play(FadeOut(m), run_time=0.5)
        m = mark(wf_lines[4:5], ACTIVITY_C)
        self.play(FadeIn(m), run_time=0.8)
        say("Timeouts And Retries Are Set On Activities, They Are Not Written Into The Workflow", ACTIVITY_C)
        self.wait(4.5)
        self.play(FadeOut(m), run_time=0.5)
        m = mark(wf_lines[0:4], TEMPORAL_C)
        self.play(FadeIn(m), run_time=0.8)
        say("The Workflow Itself Must Be Deterministic: No Random Numbers, Clocks Or Network Calls", BAD_C)
        self.wait(4.5)
        self.play(FadeOut(m), run_time=0.5)
        self.wait(1.0)

        self.play(FadeOut(VGroup(client_panel, worker_panel, wf_panel)), run_time=1.0)

        # =====================================================================
        # Run it on the overview diagram, then fail and recover
        # =====================================================================
        say("Now Watch That Workflow Run, Fail And Recover", BURGUNDY)
        self.play(FadeIn(overview), run_time=1.0)
        self.wait(1.5)

        def principle(msg, color, *targets):
            say(msg, color)
            self.play(*[Indicate(t, color=color, scale_factor=1.06) for t in targets], run_time=1.2)
            self.wait(2.0)

        principle("Workflow: Durable Code That Orchestrates The Steps", WORKFLOW_C, wf)
        principle("Activities: The Real Work, Retried Automatically When They Fail", ACTIVITY_C, *acts)
        principle("Worker: Your Own Process That Runs Workflow And Activity Code", TEMPORAL_C, wk_frame)
        principle("Task Queue: Workers Pull Work, The Service Never Pushes", QUEUE_C, queue, polls)
        principle("Event History: Every Step Is Saved, It Is The Source Of Truth", GOLD, history, database)

        log_title = Text("Event History", font_size=14, color=MUTED, weight=BOLD).move_to([-4.3, -0.95, 0])
        log_names = ["WorkflowExecutionStarted", "ActivityTaskCompleted: ReserveStock",
                     "ActivityTaskCompleted: ChargeCard", "ActivityTaskCompleted: ShipOrder",
                     "WorkflowExecutionCompleted"]
        log_rows = []
        for i, name in enumerate(log_names):
            t = Text(name, font_size=13, color=INK)
            t.move_to([-4.3, -1.35 - i * 0.3, 0]).align_to([-6.8, 0, 0], LEFT)
            log_rows.append(t)

        self.play(FadeIn(log_title), run_time=0.5)
        dot = Dot(client[0].get_center(), radius=0.1, color=BURGUNDY)
        self.play(FadeIn(dot), run_time=0.4)

        def to(p, rt=0.9):
            self.play(dot.animate.move_to(p), run_time=rt)

        def record(i):
            self.play(FadeIn(log_rows[i], shift=RIGHT * 0.2),
                      Indicate(history[0], color=GOLD, scale_factor=1.05), run_time=0.8)

        wf_pt = wf[0].get_bottom() + UP * 0.05

        def run_activity(k):
            to(wf_pt, 0.7)
            to(acts[k][0].get_left() + RIGHT * 0.12, 0.8)
            self.play(Indicate(acts[k][0], color=OK_C, scale_factor=1.06), run_time=0.7)
            to(wf_pt, 0.7)

        say("The Client Starts The Workflow: The Service Records The Start", BURGUNDY)
        to(history[0].get_center())
        record(0)
        say("A Workflow Task Is Placed On The Task Queue", QUEUE_C)
        to(queue[0].get_center())
        to(wf_pt)
        say("A Worker Polls The Queue And Runs The Workflow Code", WORKFLOW_C)
        self.wait(1.0)

        say("The Workflow Schedules Activity One: Reserve Stock", ACTIVITY_C)
        run_activity(0)
        record(1)
        say("The Workflow Schedules Activity Two: Charge Card", ACTIVITY_C)
        run_activity(1)
        record(2)
        say("Each Result Is Saved To The Event History Before The Next Step", OK_C)
        self.wait(1.5)

        # ---------- failure ----------
        say("Now The Worker Crashes Part Way Through The Workflow", BAD_C)
        cross = Cross(Square(side_length=0.9), stroke_color=BAD_C, stroke_width=7).move_to(wk_frame)
        self.play(FadeIn(cross, scale=1.4), wk_frame.animate.set_stroke(BAD_C), FadeOut(dot), run_time=0.9)
        self.wait(1.5)

        card = RoundedRectangle(width=6.3, height=1.85, corner_radius=0.12, color=TEMPORAL_C, stroke_width=3,
                                fill_color=WHITE, fill_opacity=1).move_to([3.5, -1.8, 0])
        card_title = Text("How Temporal Recovers From A Failure", font_size=14, color=TEMPORAL_C, weight=BOLD)
        card_title.move_to([3.5, -1.02, 0])
        steps = ["1  The Worker Dies And The Task Times Out",
                 "2  The Temporal Service Still Holds The Full History",
                 "3  The Workflow Task Returns To The Task Queue",
                 "4  Any Healthy Worker Polls The Queue And Takes It",
                 "5  It Replays The History, Finished Steps Are Not Run Again",
                 "6  The Workflow Resumes At Ship Order, Where It Left Off"]
        step_rows = VGroup(*[Text(x, font_size=12, color=INK) for x in steps]).arrange(
            DOWN, buff=0.05, aligned_edge=LEFT)
        step_rows.move_to([3.5, -1.95, 0])
        say("Temporal Never Loses Its Place, The History Is Kept Outside The Worker", TEMPORAL_C)
        self.play(FadeIn(card), FadeIn(card_title), run_time=0.8)
        for r in step_rows:
            self.play(FadeIn(r, shift=RIGHT * 0.2), run_time=0.8)
            self.wait(1.0)
        self.wait(1.5)

        # ---------- recovery by replay ----------
        say("A New Worker Replays The History, Results Come From The Log", TEMPORAL_C)
        self.play(FadeOut(cross), wk_frame.animate.set_stroke(TEMPORAL_C), run_time=0.8)
        replay = Dot(history[0].get_center(), radius=0.1, color=GOLD)
        self.play(FadeIn(replay), run_time=0.4)
        for i in range(3):
            self.play(Indicate(log_rows[i], color=GOLD, scale_factor=1.06),
                      replay.animate.move_to(log_rows[i].get_right() + RIGHT * 0.25), run_time=1.0)
        self.play(replay.animate.move_to(wf_pt), run_time=1.2)
        say("Reserve Stock And Charge Card Are Skipped, Nothing Is Charged Twice", GOLD)
        self.wait(2.0)

        dot = replay
        say("The Workflow Carries On From Ship Order", OK_C)
        run_activity(2)
        record(3)
        record(4)
        self.play(FadeOut(dot), FadeIn(Text("Done", font_size=14, color=OK_C, weight=BOLD)
                                       .next_to(log_rows[4], RIGHT, buff=0.3)), run_time=0.6)
        self.wait(2.0)

        # =====================================================================
        # More principles
        # =====================================================================
        say("More Temporal Principles", BURGUNDY)
        self.play(*[FadeOut(m) for m in self.mobjects if m not in (title, status)], run_time=1.0)

        cards = [
            ("Workflows", WORKFLOW_C, ["Code That Runs Durably", "For Seconds Or Years"]),
            ("Activities", ACTIVITY_C, ["Side Effects With Timeouts", "And Retry Policies"]),
            ("Determinism", TEMPORAL_C, ["Workflow Code Must Repeat", "Exactly When Replayed"]),
            ("Task Queues", QUEUE_C, ["Workers Pull Work", "And Scale Independently"]),
            ("Signals", OK_C, ["Send Data Into", "A Running Workflow"]),
            ("Queries", "#0e7490", ["Read The Current State", "Without Changing It"]),
            ("Timers", GOLD, ["Durable Sleep That", "Survives Restarts"]),
            ("Versioning", BAD_C, ["Patching Keeps Running", "Workflows Safe On Deploy"]),
        ]
        grid = VGroup()
        for n, (name, col, lines) in enumerate(cards):
            cx = -5.2 + (n % 4) * 3.47
            cy = 1.5 - (n // 4) * 2.25
            shape = RoundedRectangle(width=3.2, height=1.95, corner_radius=0.12, color=col, stroke_width=3,
                                     fill_color=col, fill_opacity=0.1).move_to([cx, cy, 0])
            head = Text(name, font_size=19, color=col, weight=BOLD).move_to([cx, cy + 0.5, 0])
            body = VGroup(*[Text(l, font_size=13, color=INK) for l in lines]).arrange(DOWN, buff=0.1).move_to(
                [cx, cy - 0.2, 0])
            grid.add(VGroup(shape, head, body))
        self.play(LaggedStart(*[FadeIn(c, shift=UP * 0.2) for c in grid], lag_ratio=0.35), run_time=4.0)
        self.wait(3.0)
        say("Durable Execution: Write Normal Code, Temporal Makes It Survive Failure", BURGUNDY)
        self.wait(4.0)
