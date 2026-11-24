// AG-UI client for the three use cases. No library and no build step: an AG-UI run is one POST whose response is a stream
// of Server-Sent Events, each "data: {json}" with a "type" such as RUN_STARTED or TEXT_MESSAGE_CONTENT.
//
//   request   POST {backend}/agui/<use case>   {threadId, runId, messages, ...}   Accept: text/event-stream
//   response  RUN_STARTED, TEXT_MESSAGE_START/CONTENT/END, TOOL_CALL_START/ARGS/END, RUN_FINISHED (or RUN_ERROR)
//
// Human in the loop: the run can finish with outcome.type "interrupt". The page asks a person, then starts a new run on the
// same thread whose body carries a "resume" entry with the decision.
(async function () {
    const $ = (id) => document.getElementById(id);

    const cases = {
        chat: {
            path: "/agui/chat",
            about: "The Support agent answers and the text arrives word by word, so the page can show it while it is still being written.",
            example: "In two sentences, what is the AG-UI protocol?",
            steps: false,
        },
        progress: {
            path: "/agui/progress",
            about: "The Research agent works on a longer task. The page shows each stage of the run and every event, so the user is never staring at a spinner.",
            example: "Correct my grammar and explain each fix: me and him goes to the shop yesterday and buyed three apple.",
            steps: true,
        },
        approval: {
            path: "/agui/approval",
            about: "The Support agent drafts a reply to a customer. Before anything is sent, the run pauses and a person approves or rejects the action.",
            example: "A customer asks where order ORD-1001 is and whether they can return it. Draft a short reply.",
            steps: false,
        },
    };

    // Per use case: its own thread, the messages sent so far, and what is shown.
    const state = {};
    function fresh() { return { threadId: crypto.randomUUID(), history: [], turns: [], events: [], pending: null }; }
    for (const k of Object.keys(cases)) state[k] = fresh();

    let current = "chat";
    let running = false;
    let abort = null;
    let runStart = 0;
    let timer = null;
    let eventCount = 0;
    let charCount = 0;

    const cfg = await fetch("config.json").then(r => r.json()).catch(() => ({ backendUrl: "http://localhost:5100" }));
    const backend = cfg.backendUrl.replace(/\/$/, "");

    // ---------- rendering ----------
    function renderTurns() {
        const box = $("response");
        box.textContent = "";
        const s = state[current];
        if (!s.turns.length) { box.textContent = "The answer appears here."; return; }
        for (const t of s.turns) {
            const div = document.createElement("div");
            div.className = "turn";
            const who = document.createElement("span");
            who.className = "who";
            who.textContent = t.who + ": ";
            const text = document.createElement("span");
            text.textContent = t.text;
            if (t.live) text.className = "caret";
            div.append(who, text);
            box.append(div);
        }
    }

    function renderEvents() {
        const list = $("events");
        list.textContent = "";
        for (const e of state[current].events) list.append(eventRow(e));
        list.scrollTop = list.scrollHeight;
    }

    function eventRow(e) {
        const li = document.createElement("li");
        const t = document.createElement("span"); t.className = "t"; t.textContent = e.ms + " ms";
        const type = document.createElement("span"); type.className = "type " + e.kind; type.textContent = e.type;
        const d = document.createElement("span"); d.className = "detail"; d.textContent = e.detail;
        li.append(t, type, d);
        return li;
    }

    function setStatus(text, isError) {
        $("status").textContent = text || "";
        $("status").className = "status" + (isError ? " error" : "");
    }

    function renderApproval() {
        const p = state[current].pending;
        $("approval").hidden = !p;
        if (p) $("approval-tool").textContent = p.toolName || "tool";
    }

    function setSteps(stage) {
        const items = [...$("steps").children];
        const order = ["started", "writing", "finished"];
        items.forEach((li) => {
            const i = order.indexOf(li.dataset.step);
            li.className = stage === null ? "" : i < stage ? "done" : i === stage ? "active" : "";
        });
        if (stage === 3) items.forEach((li) => li.className = "done");
    }

    function setMeter() {
        $("meter-events").textContent = eventCount + " events";
        $("meter-chars").textContent = charCount + " characters";
        $("meter-time").textContent = ((performance.now() - runStart) / 1000).toFixed(1) + " s";
    }

    function setRunning(on) {
        running = on;
        $("send").disabled = on;
        $("stop").hidden = !on;
        $("reset").disabled = on;
        document.querySelectorAll(".tab").forEach(b => b.disabled = on);
        $("approve").disabled = on;
        $("reject").disabled = on;
        if (on) { runStart = performance.now(); timer = setInterval(setMeter, 100); }
        else { clearInterval(timer); setMeter(); }
    }

    function selectCase(name) {
        current = name;
        document.querySelectorAll(".tab").forEach(b => {
            const on = b.dataset.case === name;
            b.classList.toggle("active", on);
            b.setAttribute("aria-selected", on);
        });
        $("about").textContent = cases[name].about;
        $("message").value = cases[name].example;
        $("steps-box").hidden = !cases[name].steps;
        $("message-label").textContent = name === "approval" ? "Customer message" : "Message";
        setSteps(null);
        setStatus("");
        renderTurns();
        renderEvents();
        renderApproval();
    }

    // ---------- AG-UI ----------
    function logEvent(ev) {
        const s = state[current];
        let kind = "text", detail = "";
        switch (ev.type) {
            case "RUN_STARTED": kind = "run"; detail = "run " + short(ev.runId); break;
            case "RUN_FINISHED": kind = "fin"; detail = ev.outcome?.type === "interrupt" ? "outcome: interrupt (waiting for a person)" : "outcome: " + (ev.outcome?.type || "success"); break;
            case "RUN_ERROR": kind = "err"; detail = ev.message || ""; break;
            case "TEXT_MESSAGE_START": detail = "message " + short(ev.messageId) + ", role " + ev.role; break;
            case "TEXT_MESSAGE_CONTENT": detail = JSON.stringify(ev.delta); break;
            case "TEXT_MESSAGE_END": detail = "message " + short(ev.messageId); break;
            case "TOOL_CALL_START": kind = "tool"; detail = ev.toolCallName; break;
            case "TOOL_CALL_ARGS": kind = "tool"; detail = ev.delta; break;
            case "TOOL_CALL_END": kind = "tool"; detail = "call " + short(ev.toolCallId); break;
            default: detail = "";
        }
        const entry = { ms: Math.round(performance.now() - runStart), type: ev.type, kind, detail };
        s.events.push(entry);
        eventCount++;
        if (state[current] === s) {
            const list = $("events");
            list.append(eventRow(entry));
            list.scrollTop = list.scrollHeight;
        }
    }
    const short = (id) => (id || "").slice(-6);

    function handle(ev, s, turnRef) {
        logEvent(ev);
        switch (ev.type) {
            case "RUN_STARTED":
                setSteps(0);
                break;
            case "TEXT_MESSAGE_START":
                turnRef.turn = { who: "Agent", text: "", live: true, id: ev.messageId };
                s.turns.push(turnRef.turn);
                setSteps(1);
                renderTurns();
                break;
            case "TEXT_MESSAGE_CONTENT":
                if (turnRef.turn) { turnRef.turn.text += ev.delta; charCount += ev.delta.length; renderTurns(); }
                break;
            case "TEXT_MESSAGE_END":
                if (turnRef.turn) {
                    turnRef.turn.live = false;
                    if (current !== "approval") s.history.push({ id: ev.messageId, role: "assistant", content: turnRef.turn.text });
                    turnRef.turn = null;
                    renderTurns();
                }
                break;
            case "TOOL_CALL_START":
                s.pendingTool = ev.toolCallName;
                break;
            case "RUN_FINISHED":
                if (ev.outcome?.type === "interrupt" && ev.outcome.interrupts?.length) {
                    s.pending = { interruptId: ev.outcome.interrupts[0].id, toolName: s.pendingTool };
                    setSteps(2);
                    $("steps").lastElementChild.textContent = "Paused: waiting for a person";
                    setStatus("Waiting for your decision");
                } else {
                    $("steps").lastElementChild.textContent = "Run finished";
                    setSteps(3);
                    setStatus("Done");
                }
                renderApproval();
                break;
            case "RUN_ERROR":
                setStatus(ev.message || "The run failed.", true);
                break;
        }
    }

    async function run(body) {
        const s = state[current];
        const turnRef = { turn: null };
        eventCount = 0; charCount = 0;
        s.events = []; renderEvents();
        abort = new AbortController();
        setRunning(true);
        setStatus("Running...");
        try {
            const res = await fetch(backend + cases[current].path, {
                method: "POST",
                headers: { "Content-Type": "application/json", "Accept": "text/event-stream" },
                body: JSON.stringify(body),
                signal: abort.signal,
            });
            if (!res.ok) throw new Error("The backend answered " + res.status + ".");

            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";
            for (;;) {
                const { value, done } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                // An SSE event ends with a blank line. Comment lines (": keepalive") start with a colon and are ignored.
                let idx;
                while ((idx = buffer.search(/\r?\n\r?\n/)) >= 0) {
                    const block = buffer.slice(0, idx);
                    buffer = buffer.slice(idx).replace(/^\r?\n\r?\n/, "");
                    const data = block.split(/\r?\n/).filter(l => l.startsWith("data:")).map(l => l.slice(5).trimStart()).join("\n");
                    if (data) handle(JSON.parse(data), s, turnRef);
                }
            }
        } catch (e) {
            if (e.name === "AbortError") setStatus("Stopped.");
            else setStatus(e.message || "The call failed. Is the backend running?", true);
        } finally {
            if (turnRef.turn) { turnRef.turn.live = false; renderTurns(); }
            setRunning(false);
        }
    }

    // ---------- events from the page ----------
    $("run-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const text = $("message").value.trim();
        if (!text || running) return;
        const s = state[current];
        s.pending = null; renderApproval();
        s.turns.push({ who: "You", text });
        s.history.push({ id: crypto.randomUUID(), role: "user", content: text });
        renderTurns();
        // The full conversation goes with every run: an AG-UI client owns the history.
        await run({ threadId: s.threadId, runId: crypto.randomUUID(), messages: s.history, state: {}, tools: [], context: [], forwardedProps: {} });
    });

    async function decide(approved) {
        const s = state[current];
        if (!s.pending || running) return;
        const interruptId = s.pending.interruptId;
        s.pending = null; renderApproval();
        s.turns.push({ who: "You", text: approved ? "Approved" : "Rejected" });
        renderTurns();
        // Resume: a new run on the same thread. It carries only the decision for the interrupt.
        await run({
            threadId: s.threadId, runId: crypto.randomUUID(), messages: [],
            resume: [{ interruptId, status: "resolved", payload: { approved } }],
        });
    }
    $("approve").addEventListener("click", () => decide(true));
    $("reject").addEventListener("click", () => decide(false));
    $("stop").addEventListener("click", () => abort && abort.abort());
    $("reset").addEventListener("click", () => { state[current] = fresh(); selectCase(current); });
    document.querySelectorAll(".tab").forEach(b => b.addEventListener("click", () => { if (!running) selectCase(b.dataset.case); }));

    selectCase("chat");
})();
