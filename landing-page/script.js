// Theme toggle. Light is the default (matches data-theme in index.html).
const themeToggle = document.getElementById('theme-toggle');
let isLightMode = true;

themeToggle.addEventListener('click', () => {
    isLightMode = !isLightMode;
    document.documentElement.setAttribute('data-theme', isLightMode ? 'light' : 'dark');
    themeToggle.textContent = isLightMode ? 'Dark mode' : 'Light mode';
});
