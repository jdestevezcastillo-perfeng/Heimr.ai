// Copyright (c) 2025 Juan Estevez Castillo
// Licensed under AGPL v3. Commercial licenses available.
// See LICENSE or https://www.gnu.org/licenses/agpl-3.0.html
// Countdown Timer Script
function updateCountdown() {
    // Target: December 7, 2025 at 1:00 PM CET
    const targetDate = new Date('2025-12-07T13:00:00+01:00');
    const now = new Date();
    const diff = targetDate - now;
    
    if (diff <= 0) {
        // Countdown ended
        document.getElementById('days').textContent = '00';
        document.getElementById('hours').textContent = '00';
        document.getElementById('minutes').textContent = '00';
        document.getElementById('seconds').textContent = '00';
        
        // Change message
        document.querySelector('.release-date').innerHTML = '🎉 <strong>LIVE NOW!</strong> 🎉';
        return;
    }
    
    // Calculate time units
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((diff % (1000 * 60)) / 1000);
    
    // Update DOM with leading zeros
    document.getElementById('days').textContent = String(days).padStart(2, '0');
    document.getElementById('hours').textContent = String(hours).padStart(2, '0');
    document.getElementById('minutes').textContent = String(minutes).padStart(2, '0');
    document.getElementById('seconds').textContent = String(seconds).padStart(2, '0');
}

// Update countdown every second
updateCountdown();
setInterval(updateCountdown, 1000);

// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Add scanline effect on page load
window.addEventListener('load', () => {
    document.body.style.animation = 'none';
    setTimeout(() => {
        document.body.style.animation = '';
    }, 10);
});

// Glitch text effect for hero title
const glitchText = document.querySelector('.glitch');
if (glitchText) {
    setInterval(() => {
        if (Math.random() > 0.95) {
            glitchText.style.textShadow = `
                ${Math.random() * 10 - 5}px ${Math.random() * 10 - 5}px 0 #ff00ff,
                ${Math.random() * 10 - 5}px ${Math.random() * 10 - 5}px 0 #00ffff
            `;
            setTimeout(() => {
                glitchText.style.textShadow = '0 0 30px var(--color-cyan)';
            }, 100);
        }
    }, 200);
}
