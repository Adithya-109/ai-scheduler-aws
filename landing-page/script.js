const textToType = "Routing dynamic payloads across the WAN since 2026. Defeating latency one AST tree at a time.";
const typingElement = document.getElementById('typing-text');
let i = 0;

function typeWriter() {
    if (i < textToType.length) {
        typingElement.innerHTML += textToType.charAt(i);
        i++;
        setTimeout(typeWriter, 50);
    }
}

// Start typing effect after a short delay
setTimeout(typeWriter, 1000);

// Theme Toggle Logic
const themeToggle = document.getElementById('theme-toggle');
let isLightMode = false;

themeToggle.addEventListener('click', () => {
    isLightMode = !isLightMode;
    if (isLightMode) {
        document.documentElement.setAttribute('data-theme', 'light');
        themeToggle.innerHTML = '🌙 DARK_MODE';
    } else {
        document.documentElement.removeAttribute('data-theme');
        themeToggle.innerHTML = '☀️ LIGHT_MODE';
    }
});
