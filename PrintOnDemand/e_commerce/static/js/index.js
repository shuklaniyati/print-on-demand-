// Mobile sidebar toggle (home page)
const menuToggle = document.getElementById('menu-toggle');
const homeSidebar = document.getElementById('home-sidebar');

if (menuToggle && homeSidebar) {
    menuToggle.addEventListener('click', () => {
        const isOpen = homeSidebar.classList.toggle('is-open');
        menuToggle.setAttribute('aria-expanded', String(isOpen));
        menuToggle.setAttribute('aria-label', isOpen ? 'Close navigation' : 'Open navigation');
    });

    document.addEventListener('click', (event) => {
        if (
            homeSidebar.classList.contains('is-open') &&
            !homeSidebar.contains(event.target) &&
            !menuToggle.contains(event.target)
        ) {
            homeSidebar.classList.remove('is-open');
            menuToggle.setAttribute('aria-expanded', 'false');
            menuToggle.setAttribute('aria-label', 'Open navigation');
        }
    });
}

// Navbar shadow on scroll
const navbar = document.querySelector('.navbar');

if (navbar) {
    window.addEventListener('scroll', () => {
        navbar.classList.toggle('fixed-navbar', window.scrollY > 0);
    });
}

// Highlight active sidebar link from current path
const sidebarLinks = document.querySelectorAll('.sidebar-nav-item');

if (sidebarLinks.length) {
    const path = window.location.pathname;
    sidebarLinks.forEach((link) => {
        if (link.pathname === path) {
            link.classList.add('is-active');
        }
    });
}
