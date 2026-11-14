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

    function closeFlyout() {
        flyout.classList.remove("open");
        flyout.setAttribute("aria-hidden", "true");
        flyoutVideo.pause();
    }

    const videos = { "mcp-square": "../media/MCPFlow.mp4?v=2", "jwt-square": "../media/JWTTokenToAPIM.mp4", "angular-square": "../media/AngularEntraAuth.mp4", "tiers-square": "../media/SubscriptionTiersAPIM.mp4" };
    Object.keys(videos).forEach(function (id) {
        const el = document.getElementById(id);
        if (el) el.addEventListener("click", e => { e.preventDefault(); openFlyout(videos[id]); });
    });

    document.getElementById("flyout-fs").addEventListener("click", () => {
        if (flyoutVideo.requestFullscreen) flyoutVideo.requestFullscreen();
        else if (flyoutVideo.webkitEnterFullscreen) flyoutVideo.webkitEnterFullscreen();
    });

    document.getElementById("flyout-close").addEventListener("click", closeFlyout);
    document.addEventListener("keydown", e => { if (e.key === "Escape") closeFlyout(); });
})();
