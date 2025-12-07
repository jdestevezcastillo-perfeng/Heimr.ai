// ===== Heimr Website Interactivity =====

document.addEventListener('DOMContentLoaded', () => {
    initCopyButton();
    initMobileNav();
    initScrollEffects();
});

// ===== Copy to Clipboard =====
function initCopyButton() {
    const copyBtn = document.querySelector('.copy-btn');
    if (!copyBtn) return;

    copyBtn.addEventListener('click', async () => {
        const textToCopy = copyBtn.dataset.copy;
        const copyText = copyBtn.querySelector('.copy-text');

        try {
            await navigator.clipboard.writeText(textToCopy);
            copyBtn.classList.add('copied');
            copyText.textContent = 'Copied!';

            setTimeout(() => {
                copyBtn.classList.remove('copied');
                copyText.textContent = 'Copy';
            }, 2000);
        } catch (err) {
            // Fallback for older browsers
            const textarea = document.createElement('textarea');
            textarea.value = textToCopy;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);

            copyBtn.classList.add('copied');
            copyText.textContent = 'Copied!';

            setTimeout(() => {
                copyBtn.classList.remove('copied');
                copyText.textContent = 'Copy';
            }, 2000);
        }
    });
}

// ===== Mobile Navigation Toggle =====
function initMobileNav() {
    const toggle = document.querySelector('.nav-toggle');
    const navLinks = document.querySelector('.nav-links');

    if (!toggle || !navLinks) return;

    toggle.addEventListener('click', () => {
        navLinks.classList.toggle('active');
        toggle.classList.toggle('active');
    });

    // Close menu when clicking a link
    navLinks.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', () => {
            navLinks.classList.remove('active');
            toggle.classList.remove('active');
        });
    });
}

// ===== Scroll Effects =====
function initScrollEffects() {
    const header = document.querySelector('.header');
    let lastScroll = 0;

    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;

        // Add shadow on scroll
        if (currentScroll > 50) {
            header.style.boxShadow = '0 4px 30px rgba(0, 0, 0, 0.3)';
        } else {
            header.style.boxShadow = 'none';
        }

        lastScroll = currentScroll;
    });

    // Intersection Observer for fade-in animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    // Observe feature cards
    document.querySelectorAll('.feature-card').forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = `opacity 0.6s ease ${index * 0.1}s, transform 0.6s ease ${index * 0.1}s`;
        observer.observe(card);
    });
}
