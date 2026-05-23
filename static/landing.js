/* ═══════════════════════════════════════════════════
   College Compass — Landing Page Interactions
   Particle canvas • Cursor glow • Scroll reveals
   Counter animation • Nav scroll effect
   ═══════════════════════════════════════════════════ */

// ─── Cursor Glow ────────────────────────────────────
const cursorGlow = document.getElementById('cursor-glow');
let mouseX = 0, mouseY = 0, glowX = 0, glowY = 0;

document.addEventListener('mousemove', e => {
    mouseX = e.clientX;
    mouseY = e.clientY;
});

function updateCursorGlow() {
    glowX += (mouseX - glowX) * 0.08;
    glowY += (mouseY - glowY) * 0.08;
    cursorGlow.style.left = glowX + 'px';
    cursorGlow.style.top = glowY + 'px';
    requestAnimationFrame(updateCursorGlow);
}
updateCursorGlow();


// ─── Particle Canvas System ─────────────────────────
const canvas = document.getElementById('particle-canvas');
const ctx = canvas.getContext('2d');
let particles = [];
let particleMouseX = 0, particleMouseY = 0;

function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
}
resizeCanvas();
window.addEventListener('resize', resizeCanvas);

document.addEventListener('mousemove', e => {
    particleMouseX = e.clientX;
    particleMouseY = e.clientY;
});

class Particle {
    constructor() {
        this.reset();
    }

    reset() {
        this.x = Math.random() * canvas.width;
        this.y = Math.random() * canvas.height;
        this.size = Math.random() * 2 + 0.5;
        this.speedX = (Math.random() - 0.5) * 0.4;
        this.speedY = (Math.random() - 0.5) * 0.4;
        this.opacity = Math.random() * 0.5 + 0.1;
        this.color = Math.random() > 0.7 ? '#FF6B35' : '#ffffff';
        this.pulseSpeed = Math.random() * 0.02 + 0.005;
        this.pulseOffset = Math.random() * Math.PI * 2;
    }

    update(time) {
        this.x += this.speedX;
        this.y += this.speedY;

        // Mouse repulsion
        const dx = this.x - particleMouseX;
        const dy = this.y - particleMouseY;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 150) {
            const force = (150 - dist) / 150;
            this.x += (dx / dist) * force * 1.5;
            this.y += (dy / dist) * force * 1.5;
        }

        // Wrap around
        if (this.x < -10) this.x = canvas.width + 10;
        if (this.x > canvas.width + 10) this.x = -10;
        if (this.y < -10) this.y = canvas.height + 10;
        if (this.y > canvas.height + 10) this.y = -10;

        // Pulse
        this.currentOpacity = this.opacity * (0.5 + 0.5 * Math.sin(time * this.pulseSpeed + this.pulseOffset));
    }

    draw() {
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        ctx.fillStyle = this.color;
        ctx.globalAlpha = this.currentOpacity;
        ctx.fill();
        ctx.globalAlpha = 1;
    }
}

// Create particles
const PARTICLE_COUNT = Math.min(100, Math.floor((window.innerWidth * window.innerHeight) / 15000));
for (let i = 0; i < PARTICLE_COUNT; i++) {
    particles.push(new Particle());
}

function drawConnections(time) {
    const maxDist = 120;
    for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
            const dx = particles[i].x - particles[j].x;
            const dy = particles[i].y - particles[j].y;
            const dist = Math.sqrt(dx * dx + dy * dy);

            if (dist < maxDist) {
                const alpha = (1 - dist / maxDist) * 0.12;
                ctx.beginPath();
                ctx.moveTo(particles[i].x, particles[i].y);
                ctx.lineTo(particles[j].x, particles[j].y);
                ctx.strokeStyle = `rgba(255, 107, 53, ${alpha})`;
                ctx.lineWidth = 0.5;
                ctx.stroke();
            }
        }
    }

    // Mouse connections
    for (let i = 0; i < particles.length; i++) {
        const dx = particles[i].x - particleMouseX;
        const dy = particles[i].y - particleMouseY;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < 200) {
            const alpha = (1 - dist / 200) * 0.2;
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particleMouseX, particleMouseY);
            ctx.strokeStyle = `rgba(255, 107, 53, ${alpha})`;
            ctx.lineWidth = 0.8;
            ctx.stroke();
        }
    }
}

let animTime = 0;
function animateParticles() {
    animTime++;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    particles.forEach(p => {
        p.update(animTime);
        p.draw();
    });

    drawConnections(animTime);

    requestAnimationFrame(animateParticles);
}
animateParticles();


// ─── Nav Scroll Effect ──────────────────────────────
const nav = document.getElementById('landing-nav');
let lastScroll = 0;

window.addEventListener('scroll', () => {
    const y = window.scrollY;
    nav.classList.toggle('scrolled', y > 50);

    // Fade scroll indicator
    const indicator = document.getElementById('scroll-indicator');
    if (indicator) {
        indicator.style.opacity = Math.max(0, 1 - y / 300);
    }
    lastScroll = y;
});


// ─── Scroll Reveal (IntersectionObserver) ───────────
const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('revealed');
            revealObserver.unobserve(entry.target);
        }
    });
}, {
    threshold: 0.15,
    rootMargin: '0px 0px -40px 0px'
});

document.querySelectorAll('.reveal-up').forEach(el => {
    revealObserver.observe(el);
});


// ─── Counter Animation ──────────────────────────────
function animateCounter(element, target, duration = 2000) {
    const start = 0;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);

        // Ease out cubic
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = Math.floor(eased * target);

        element.textContent = current.toLocaleString() + (target >= 100 ? '+' : '%');

        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    requestAnimationFrame(update);
}

// Observe stats section
const statsSection = document.getElementById('hero-stats');
if (statsSection) {
    const statsObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const counters = entry.target.querySelectorAll('.stat-number');
                counters.forEach(counter => {
                    const target = parseInt(counter.dataset.target);
                    animateCounter(counter, target);
                });
                statsObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.5 });
    statsObserver.observe(statsSection);
}


// ─── Smooth anchor scrolling ────────────────────────
document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
        e.preventDefault();
        const target = document.querySelector(a.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });
});


// ─── Magnetic button effect ─────────────────────────
document.querySelectorAll('.btn-primary, .nav-cta').forEach(btn => {
    btn.addEventListener('mousemove', e => {
        const rect = btn.getBoundingClientRect();
        const x = e.clientX - rect.left - rect.width / 2;
        const y = e.clientY - rect.top - rect.height / 2;
        btn.style.transform = `translate(${x * 0.15}px, ${y * 0.15 - 2}px)`;
    });

    btn.addEventListener('mouseleave', () => {
        btn.style.transform = '';
    });
});
