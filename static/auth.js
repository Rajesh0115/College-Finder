/* ═══════════════════════════════════════════════════
   College Compass — Auth Page Logic
   Form handling • Error display • Particle bg
   ═══════════════════════════════════════════════════ */

// ─── Simple particle background (lighter version) ───
const canvas = document.getElementById('particle-canvas');
if (canvas) {
    const ctx = canvas.getContext('2d');
    let particles = [];

    function resize() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener('resize', resize);

    class Dot {
        constructor() {
            this.x = Math.random() * canvas.width;
            this.y = Math.random() * canvas.height;
            this.size = Math.random() * 1.5 + 0.3;
            this.sx = (Math.random() - 0.5) * 0.3;
            this.sy = (Math.random() - 0.5) * 0.3;
            this.opacity = Math.random() * 0.3 + 0.05;
            this.color = Math.random() > 0.8 ? '#FF6B35' : '#ffffff';
        }
        update() {
            this.x += this.sx;
            this.y += this.sy;
            if (this.x < 0) this.x = canvas.width;
            if (this.x > canvas.width) this.x = 0;
            if (this.y < 0) this.y = canvas.height;
            if (this.y > canvas.height) this.y = 0;
        }
        draw() {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
            ctx.fillStyle = this.color;
            ctx.globalAlpha = this.opacity;
            ctx.fill();
            ctx.globalAlpha = 1;
        }
    }

    const count = Math.min(50, Math.floor((window.innerWidth * window.innerHeight) / 25000));
    for (let i = 0; i < count; i++) particles.push(new Dot());

    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        particles.forEach(p => { p.update(); p.draw(); });

        // Draw connections
        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const dx = particles[i].x - particles[j].x;
                const dy = particles[i].y - particles[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 100) {
                    ctx.beginPath();
                    ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(particles[j].x, particles[j].y);
                    ctx.strokeStyle = `rgba(255,107,53,${(1 - dist / 100) * 0.08})`;
                    ctx.lineWidth = 0.4;
                    ctx.stroke();
                }
            }
        }
        requestAnimationFrame(animate);
    }
    animate();
}


// ─── Error Display ──────────────────────────────────
function showError(msg) {
    const el = document.getElementById('auth-error');
    const txt = document.getElementById('error-text');
    if (el && txt) {
        txt.textContent = msg;
        el.style.display = 'flex';
        // Re-trigger animation
        el.style.animation = 'none';
        el.offsetHeight;
        el.style.animation = '';
    }
}

function hideError() {
    const el = document.getElementById('auth-error');
    if (el) el.style.display = 'none';
}


// ─── Auth Form Handler ──────────────────────────────
async function handleAuth(url, data) {
    const btn = document.getElementById('auth-btn');
    const btnText = btn.querySelector('.auth-btn-text');
    const loader = document.getElementById('btn-loader');

    hideError();
    btn.disabled = true;
    btnText.style.display = 'none';
    loader.style.display = 'block';

    try {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await res.json();

        if (result.success && result.redirect) {
            // Success — redirect with a small delay for feel
            btnText.textContent = '✓ Success!';
            btnText.style.display = 'block';
            loader.style.display = 'none';
            setTimeout(() => {
                window.location.href = result.redirect;
            }, 400);
        } else {
            showError(result.error || 'Something went wrong');
            btn.disabled = false;
            btnText.style.display = 'block';
            loader.style.display = 'none';
        }
    } catch (e) {
        showError('Connection failed. Is the server running?');
        btn.disabled = false;
        btnText.style.display = 'block';
        loader.style.display = 'none';
    }
}
