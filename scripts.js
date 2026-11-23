// Shared page scripts. Safe to load on any page: each feature only runs if its elements exist.

// Video flyout: squares with a data-video attribute open it.
(function () {
    const flyout = document.getElementById("flyout");
    if (!flyout) return;
    const flyoutVideo = document.getElementById("flyout-video");

    function openFlyout(src) {
        if (!flyoutVideo.currentSrc.endsWith(src.split("?")[0])) {
            flyoutVideo.src = src;
            flyoutVideo.load();
        }
        flyout.classList.add("open");
        flyout.setAttribute("aria-hidden", "false");
        flyoutVideo.play().catch(() => {});
    }

    function enterFullscreen() {
        // Full-screen the whole flyout so the title and buttons stay visible.
        if (flyout.requestFullscreen) flyout.requestFullscreen().catch(() => {});
        else if (flyout.webkitRequestFullscreen) flyout.webkitRequestFullscreen();
        else if (flyoutVideo.webkitEnterFullscreen) flyoutVideo.webkitEnterFullscreen();
    }

    function isFullscreen() {
        return !!(document.fullscreenElement || document.webkitFullscreenElement || flyoutVideo.webkitDisplayingFullscreen);
    }

    function exitFullscreen() {
        if (document.fullscreenElement && document.exitFullscreen) document.exitFullscreen().catch(() => {});
        else if (document.webkitFullscreenElement && document.webkitExitFullscreen) document.webkitExitFullscreen();
        else if (flyoutVideo.webkitDisplayingFullscreen && flyoutVideo.webkitExitFullscreen) flyoutVideo.webkitExitFullscreen();
    }

    // Close action: in full screen, return to the normal-size flyout; otherwise close it.
    function dismissFlyout() {
        if (isFullscreen()) exitFullscreen();
        else closeFlyout();
    }

    function closeFlyout() {
        flyout.classList.remove("open");
        flyout.setAttribute("aria-hidden", "true");
        flyoutVideo.pause();
    }

    const videos = { "mi-square": "manim/media/videos/Allow-APIM-Access-To-Azure-Resources-Using-Managed-Identities/480p15/Allow-APIM-Access-To-Azure-Resources-Using-Managed-Identities.mp4", "mcp-square": "manim/media/videos/Use-Claude-MCP-Connectors-With-APIs/480p15/Use-Claude-MCP-Connectors-With-APIs.mp4", "foundry-square": "manim/media/videos/Use-An-Azure-Web-App-To-Call-Foundry-Agents-Via-Azure-APIM/480p15/Use-An-Azure-Web-App-To-Call-Foundry-Agents-Via-Azure-APIM.mp4", "jwt-square": "manim/media/videos/Authorise-Claude-To-Use-APIs-Inside-Azure-APIM/480p15/Authorise-Claude-To-Use-APIs-Inside-Azure-APIM.mp4", "angular-square": "manim/media/videos/Authorise-Azure-Hosted-Angular-SPA-With-Microsoft-Entra-ID/480p15/Authorise-Azure-Hosted-Angular-SPA-With-Microsoft-Entra-ID.mp4", "tiers-square": "manim/media/videos/Manage-Tiered-Subscriptions-With-Azure-APIM/480p15/Manage-Tiered-Subscriptions-With-Azure-APIM.mp4", "toolbox-square": "manim/media/videos/Streamline-Microsoft-Foundry-Architecture-With-Toolboxes/480p15/Streamline-Microsoft-Foundry-Architecture-With-Toolboxes.mp4", "passkey-square": "manim/media/videos/Sign-In-With-Passkeys-On-An-ASP-NET-Core-Web-Site/480p15/Sign-In-With-Passkeys-On-An-ASP-NET-Core-Web-Site.mp4", "apim-query-square": "manim/media/videos/Query-APIM-Traffic-With-Claude-Code-And-Azure-MCP-Server/480p15/Query-APIM-Traffic-With-Claude-Code-And-Azure-MCP-Server.mp4" };
    Object.keys(videos).forEach(function (id) {
        const el = document.getElementById(id);
        if (!el) return;
        // The video title is the h3 containing the link.
        const h3 = el.closest("h3");
        const title = h3 ? h3.textContent.trim() : "";
        if (title) { el.title = title; el.setAttribute("aria-label", title); }
        el.addEventListener("click", e => {
            e.preventDefault();
            flyout.setAttribute("aria-label", title);
            flyoutVideo.title = title;
            openFlyout(videos[id]);
        });
    });

    // The MP4 icon next to a title opens the same video as the title link.
    document.querySelectorAll("[data-video-for]").forEach(function (icon) {
        icon.addEventListener("click", e => {
            e.preventDefault();
            const titleLink = document.getElementById(icon.dataset.videoFor);
            if (titleLink) titleLink.click();
        });
    });

    document.getElementById("flyout-fs").addEventListener("click", enterFullscreen);

    document.getElementById("flyout-close").addEventListener("click", dismissFlyout);
    document.addEventListener("keydown", e => { if (e.key === "Escape") dismissFlyout(); });
})();

// Topic tabs: show only the receipes whose h3 has the chosen data-tab value.
(function () {
    const tabs = document.getElementById("az-tabs");
    const panel = document.getElementById("recipes-panel");
    if (!tabs || !panel) return;

    // A receipe is an h3 title plus the elements after it (its note) up to the next h3.
    const items = Array.from(panel.querySelectorAll("h3")).map(function (h3) {
        const nodes = [h3];
        for (let n = h3.nextElementSibling; n && n.tagName !== "H3"; n = n.nextElementSibling) nodes.push(n);
        return { nodes: nodes, letter: h3.dataset.tab || "" };
    });

    const tabDefs = [["foundry", "Foundry"], ["apim", "API Management"], ["other", "Other"]];
    const letters = tabDefs.map(function (t) { return t[0]; });
    const buttons = {};

    function makeTab(key, label, count) {
        const b = document.createElement("button");
        b.type = "button";
        b.id = "az-" + key;
        b.textContent = label;
        b.setAttribute("role", "tab");
        b.setAttribute("aria-controls", "recipes-panel");
        b.setAttribute("aria-selected", "false");
        b.tabIndex = -1;
        b.title = count + (count === 1 ? " receipe" : " receipes");
        if (count === 0) { b.disabled = true; b.setAttribute("aria-disabled", "true"); }
        b.addEventListener("click", function () { select(key, false); });
        buttons[key] = b;
        tabs.appendChild(b);
    }

    tabDefs.forEach(function (t) { const l = t[0]; makeTab(l, t[1], items.filter(function (i) { return i.letter === l; }).length); });
    // Start on the first letter (alphabetically) that has a receipe.
    const firstKey = letters.filter(function (l) { return !buttons[l].disabled; })[0];

    function select(key, focus) {
        if (!buttons[key] || buttons[key].disabled) key = firstKey;
        Object.keys(buttons).forEach(function (k) {
            const on = k === key;
            buttons[k].setAttribute("aria-selected", on ? "true" : "false");
            buttons[k].tabIndex = on ? 0 : -1;
        });
        items.forEach(function (i) {
            const show = i.letter === key;
            i.nodes.forEach(function (n) { n.hidden = !show; });
        });
        panel.setAttribute("aria-labelledby", "az-" + key);
        buttons[key].scrollIntoView({ block: "nearest", inline: "nearest" });
        if (focus) buttons[key].focus();
        if (history.replaceState) history.replaceState(null, "", "#" + key);
    }

    // Keyboard navigation: left/right (and Home/End) move between the enabled tabs.
    tabs.addEventListener("keydown", function (e) {
        const enabled = Object.keys(buttons).filter(function (k) { return !buttons[k].disabled; });
        const current = Object.keys(buttons).filter(function (k) { return buttons[k] === document.activeElement; })[0];
        let i = enabled.indexOf(current);
        if (i < 0) return;
        if (e.key === "ArrowRight") i = (i + 1) % enabled.length;
        else if (e.key === "ArrowLeft") i = (i - 1 + enabled.length) % enabled.length;
        else if (e.key === "Home") i = 0;
        else if (e.key === "End") i = enabled.length - 1;
        else return;
        e.preventDefault();
        select(enabled[i], true);
    });

    // Deep link: index.html#M opens the M tab; the browser back/forward and edited hash also work.
    function fromHash() { select((location.hash || "").replace("#", "").toLowerCase(), false); }
    window.addEventListener("hashchange", fromHash);
    fromHash();
})();
