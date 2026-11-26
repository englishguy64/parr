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

    const videos = { "a2ui-square": "manim/media/videos/Receive-A2UI-Components-Into-Angular-Website-From-Foundry-Agents/480p15/Receive-A2UI-Components-Into-Angular-Website-From-Foundry-Agents.mp4", "temporal-square": "manim/media/videos/Protect-Long-And-Multi-Step-Processes-Using-Temporal-Durability-Execution/480p15/Protect-Long-And-Multi-Step-Processes-Using-Temporal-Durability-Execution.mp4", "agui-square": "manim/media/videos/Using-AG-UI-Protocol-With-Foundry-Agents/480p15/Using-AG-UI-Protocol-With-Foundry-Agents.mp4", "services-square": "manim/media/videos/Using-Foundry-Services-And-Guardrails/480p15/Using-Foundry-Services-And-Guardrails.mp4", "mi-square": "manim/media/videos/Allow-APIM-Access-To-Azure-Resources-Using-Managed-Identities/480p15/Allow-APIM-Access-To-Azure-Resources-Using-Managed-Identities.mp4", "mcp-square": "manim/media/videos/Use-Claude-MCP-Connectors-With-APIs/480p15/Use-Claude-MCP-Connectors-With-APIs.mp4", "foundry-square": "manim/media/videos/Use-An-Azure-Web-App-To-Call-Foundry-Agents-Via-Azure-APIM/480p15/Use-An-Azure-Web-App-To-Call-Foundry-Agents-Via-Azure-APIM.mp4", "jwt-square": "manim/media/videos/Authorise-Claude-To-Use-APIs-Inside-Azure-APIM/480p15/Authorise-Claude-To-Use-APIs-Inside-Azure-APIM.mp4", "angular-square": "manim/media/videos/Authorise-Azure-Hosted-Angular-SPA-With-Microsoft-Entra-ID/480p15/Authorise-Azure-Hosted-Angular-SPA-With-Microsoft-Entra-ID.mp4", "tiers-square": "manim/media/videos/Manage-Tiered-Subscriptions-With-Azure-APIM/480p15/Manage-Tiered-Subscriptions-With-Azure-APIM.mp4", "toolbox-square": "manim/media/videos/Streamline-Microsoft-Foundry-Architecture-With-Toolboxes/480p15/Streamline-Microsoft-Foundry-Architecture-With-Toolboxes.mp4", "passkey-square": "manim/media/videos/Sign-In-With-Passkeys-On-An-ASP-NET-Core-Web-Site/480p15/Sign-In-With-Passkeys-On-An-ASP-NET-Core-Web-Site.mp4", "apim-query-square": "manim/media/videos/Query-APIM-Traffic-With-Claude-Code-And-Azure-MCP-Server/480p15/Query-APIM-Traffic-With-Claude-Code-And-Azure-MCP-Server.mp4" };
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
