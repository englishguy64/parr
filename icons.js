// Open header icon links in a separate popup window on larger screens.
// On phones and tablets (narrow viewports) or if the popup is blocked, fall back to the normal new-tab behaviour.
document.querySelectorAll('.header-links .icons a').forEach(function (link) {
    link.addEventListener('click', function (e) {
        if (window.innerWidth < 900 || !/^https?:/.test(link.getAttribute('href'))) return;
        var win = window.open(link.href, '_blank', 'noopener,width=1100,height=800');
        if (win) e.preventDefault();
    });
});
