/* ═══════════════════════════════════════════════════
   MHT-CET College Compass — Dashboard Logic
   Server-backed wishlist • Recommendation engine
   ═══════════════════════════════════════════════════ */

// ─── State ──────────────────────────────────────────
let allColleges = [];
let currentRecommendations = [];
let userWishlist = []; // Server-backed

// ─── Init ───────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    loadDropdowns();
    loadStats();
    setupNavigation();
    setupGauge();
    setupTFWS();
    setupFilterTabs();
    setupCompare();
    loadWishlistFromServer();
    setup3DTilt();
    setupDotMatrix();
});

// ─── Navigation ─────────────────────────────────────
function setupNavigation() {
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => switchView(btn.dataset.view));
    });
}

function switchView(name) {
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    const btn = document.querySelector(`[data-view="${name}"]`);
    if (btn) btn.classList.add('active');

    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    const view = document.getElementById(`view-${name}`);
    if (view) view.classList.add('active');

    if (name === 'wishlist') renderWishlist();
}

// ─── Dropdowns ──────────────────────────────────────
async function loadDropdowns() {
    try {
        const [brRes, ciRes, coRes] = await Promise.all([
            fetch('/api/branches'), fetch('/api/cities'), fetch('/api/colleges')
        ]);

        if (brRes.status === 401) {
            window.location.href = '/login';
            return;
        }

        const brData = await brRes.json();
        const ciData = await ciRes.json();
        const coData = await coRes.json();

        const brSel = document.getElementById('branch');
        brData.branches.forEach(b => {
            const o = document.createElement('option');
            o.value = b; o.textContent = b;
            brSel.appendChild(o);
        });

        const ciSel = document.getElementById('city');
        ciData.cities.forEach(c => {
            const o = document.createElement('option');
            o.value = c; o.textContent = c;
            ciSel.appendChild(o);
        });

        allColleges = coData.colleges;
    } catch (e) {
        console.error('Dropdown load failed:', e);
    }
}

async function loadStats() {
    try {
        const res = await fetch('/api/stats');
        if (res.status === 401) return;
        const s = await res.json();
        document.getElementById('hero-records').textContent = s.total_records.toLocaleString() + '+';
        document.getElementById('hero-colleges').textContent = s.total_colleges.toLocaleString() + '+';
    } catch (e) {}
}

// ─── Circular Gauge ─────────────────────────────────
function setupGauge() {
    const slider = document.getElementById('percentile-slider');
    const number = document.getElementById('percentile');
    const gaugeFill = document.getElementById('gauge-fill');

    function updateGauge(val) {
        // Arc spans 270deg (3/4 of circle)
        // Total circumference = 2 * PI * 85 = 534.07
        // 270deg arc length = 534.07 * 0.75 = 400.55
        const maxArc = 400.55;
        const arcLength = (val / 100) * maxArc;
        const gap = 534.07 - arcLength;
        gaugeFill.setAttribute('stroke-dasharray', `${arcLength} ${gap}`);
    }

    slider.addEventListener('input', () => {
        number.value = slider.value;
        updateGauge(parseFloat(slider.value));
    });

    number.addEventListener('input', () => {
        let v = parseFloat(number.value) || 0;
        v = Math.max(0, Math.min(100, v));
        slider.value = v;
        updateGauge(v);
    });

    // Initial gauge render
    updateGauge(parseFloat(number.value));
}

// ─── TFWS Toggle ────────────────────────────────────
function setupTFWS() {
    const toggle = document.getElementById('tfws-toggle');
    const hidden = document.getElementById('tfws');
    const btns = toggle.querySelectorAll('.tfws-btn');

    toggle.dataset.active = 'no';

    btns.forEach(btn => {
        btn.addEventListener('click', () => {
            btns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const val = btn.dataset.value;
            hidden.value = val;
            toggle.dataset.active = val;
        });
    });
}

// ─── Recommendations ────────────────────────────────
async function getRecommendations() {
    const submitBtn = document.getElementById('submit-btn');
    const loading = document.getElementById('loading-state');
    const results = document.getElementById('results-section');

    submitBtn.disabled = true;
    loading.style.display = 'block';
    results.style.display = 'none';

    const payload = {
        percentile: parseFloat(document.getElementById('percentile').value),
        category: document.getElementById('category').value,
        branch: document.getElementById('branch').value,
        city: document.getElementById('city').value,
        tfws: document.getElementById('tfws').value === 'yes',
        college_type: document.getElementById('college-type').value
    };

    try {
        const res = await fetch('/api/recommend', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (res.status === 401) { window.location.href = '/login'; return; }

        const data = await res.json();
        if (data.error) { alert('Error: ' + data.error); return; }

        currentRecommendations = data.recommendations;
        renderResults(data);
    } catch (e) {
        alert('Request failed. Is the server running?');
        console.error(e);
    } finally {
        submitBtn.disabled = false;
        loading.style.display = 'none';
    }
}

// ─── Render Results ─────────────────────────────────
function renderResults(data) {
    const results = document.getElementById('results-section');
    results.style.display = 'block';

    document.getElementById('stat-filtered').textContent = data.stats.total_candidates_filtered;
    document.getElementById('stat-safe').textContent = data.stats.tier_counts.Safe || 0;
    document.getElementById('stat-moderate').textContent = data.stats.tier_counts.Moderate || 0;
    document.getElementById('stat-dream').textContent = data.stats.tier_counts.Dream || 0;

    // Set readout timestamp
    const timeEl = document.getElementById('readout-time');
    if (timeEl) {
        const now = new Date();
        timeEl.textContent = now.toLocaleTimeString('en-US', { hour12: false }) + '.' + String(now.getMilliseconds()).padStart(3, '0');
    }

    renderCards(data.recommendations, 'all');
    results.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function wishlistKey(rec) {
    return `${rec.college_name}__${rec.branch_group}__${rec.category}`;
}

function renderCards(recs, filter) {
    const grid = document.getElementById('rec-grid');
    grid.innerHTML = '';

    const list = filter === 'all' ? recs : recs.filter(r => r.tier === filter);

    if (!list.length) {
        grid.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-3);font-family:JetBrains Mono,monospace;font-size:0.8rem;letter-spacing:0.05em">NO ' + (filter === 'all' ? '' : filter.toUpperCase() + ' ') + 'RESULTS FOUND // ADJUST PARAMETERS</div>';
        return;
    }

    list.forEach((rec, i) => {
        const wished = userWishlist.some(w =>
            w.college_name === rec.college_name &&
            w.branch_group === rec.branch_group &&
            w.category === rec.category
        );

        // Calculate SVG ring values
        const radius = 20;
        const circumference = 2 * Math.PI * radius;
        const pct = rec.probability_pct / 100;
        const offset = circumference * (1 - pct);

        const el = document.createElement('div');
        el.className = `holo-card tier-${rec.tier}`;
        el.style.animationDelay = `${i * 0.07}s`;

        el.innerHTML = `
            <div class="holo-rank">
                <span class="holo-rank-num">${rec.rank}</span>
                <span class="holo-rank-label">RANK</span>
            </div>
            <div class="holo-info">
                <div class="holo-name" title="${rec.college_name}">${rec.college_name}</div>
                <div class="holo-meta">
                    <span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>${rec.branch_group}</span>
                    <span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>${rec.city}</span>
                    <span>${rec.category}</span>
                    <span>Cutoff: ${rec.cutoff_score.toFixed(2)}%</span>
                </div>
            </div>
            <div class="holo-prob">
                <div class="prob-ring-wrap">
                    <svg class="prob-ring-svg" viewBox="0 0 48 48">
                        <circle class="prob-ring-track" cx="24" cy="24" r="${radius}"/>
                        <circle class="prob-ring-fill" cx="24" cy="24" r="${radius}"
                            stroke-dasharray="${circumference}" stroke-dashoffset="${offset}"/>
                    </svg>
                    <span class="prob-ring-val">${rec.probability_pct}%</span>
                </div>
                <span class="prob-ring-lbl">CHANCE</span>
            </div>
            <div class="holo-actions">
                <span class="tier-neon tier-${rec.tier}">${rec.tier.toUpperCase()}</span>
                <button class="heart-btn ${wished ? 'active' : ''}" onclick="toggleWishlist(this, ${JSON.stringify(rec).replace(/"/g, '&quot;')})">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="${wished ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
                </button>
            </div>
        `;
        grid.appendChild(el);
    });

    // Reinit 3D tilt for new cards
    setup3DTilt();
}

// ─── Filter Tabs ────────────────────────────────────
function setupFilterTabs() {
    document.querySelectorAll('.filter-pill').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.filter-pill').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            renderCards(currentRecommendations, tab.dataset.filter);
        });
    });
}

// ─── Wishlist (Server-Backed) ───────────────────────
async function loadWishlistFromServer() {
    try {
        const res = await fetch('/api/wishlist');
        if (res.status === 401) return;
        const data = await res.json();
        userWishlist = data.wishlist || [];
        updateWishlistBadge();
    } catch (e) {
        console.error('Failed to load wishlist:', e);
        userWishlist = [];
    }
}

function updateWishlistBadge() {
    const c = userWishlist.length;
    const badge = document.getElementById('wishlist-count');
    badge.style.display = c > 0 ? 'inline' : 'none';
    badge.textContent = c;
}

async function toggleWishlist(btn, rec) {
    const existing = userWishlist.find(w =>
        w.college_name === rec.college_name &&
        w.branch_group === rec.branch_group &&
        w.category === rec.category
    );

    if (existing) {
        // Remove
        try {
            await fetch(`/api/wishlist/${existing.id}`, { method: 'DELETE' });
            userWishlist = userWishlist.filter(w => w.id !== existing.id);
            btn.classList.remove('active');
            btn.querySelector('svg').setAttribute('fill', 'none');
        } catch (e) { console.error(e); }
    } else {
        // Add
        try {
            const res = await fetch('/api/wishlist', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(rec)
            });
            // Reload wishlist to get the new ID
            await loadWishlistFromServer();
            btn.classList.add('active');
            btn.querySelector('svg').setAttribute('fill', 'currentColor');
        } catch (e) { console.error(e); }
    }
    updateWishlistBadge();
}

async function removeFromWishlist(id) {
    try {
        await fetch(`/api/wishlist/${id}`, { method: 'DELETE' });
        userWishlist = userWishlist.filter(w => w.id !== id);
        updateWishlistBadge();
        renderWishlist();

        // Re-render rec cards if visible
        if (currentRecommendations.length) {
            const f = document.querySelector('.filter-pill.active');
            renderCards(currentRecommendations, f ? f.dataset.filter : 'all');
        }
    } catch (e) {
        console.error('Failed to remove from wishlist:', e);
    }
}

function renderWishlist() {
    const grid = document.getElementById('wishlist-grid');
    const empty = document.getElementById('wishlist-empty');
    const hint = document.getElementById('wishlist-hint');

    updateWishlistBadge();

    if (!userWishlist.length) {
        grid.innerHTML = '';
        grid.style.display = 'none';
        empty.style.display = 'block';
        hint.textContent = 'Bookmark colleges from recommendations';
        return;
    }

    empty.style.display = 'none';
    grid.style.display = 'flex';
    hint.textContent = `${userWishlist.length} college(s) saved`;

    grid.innerHTML = userWishlist.map((item, i) => `
        <div class="wishlist-card" style="animation-delay:${i * 0.05}s">
            <div class="wl-info">
                <h3>${item.college_name}</h3>
                <div class="meta">
                    <span>${item.branch_group || ''}</span>
                    <span>${item.city || ''}</span>
                    <span>${item.category || ''}</span>
                    ${item.tier ? `<span class="tier-badge tier-${item.tier}">${item.tier} ${item.probability_pct || ''}%</span>` : ''}
                </div>
            </div>
            <div class="wl-actions">
                <span style="color:var(--text-3);font-size:.8rem">Cutoff: ${item.cutoff_score ? parseFloat(item.cutoff_score).toFixed(2) + '%' : '—'}</span>
                <button class="btn-remove" onclick="removeFromWishlist(${item.id})">Remove</button>
            </div>
        </div>
    `).join('');
}

// ─── Compare ────────────────────────────────────────
let selectedC1 = '', selectedC2 = '';

function setupCompare() {
    setupSearchInput('compare-c1', 'dropdown-c1', n => { selectedC1 = n; checkCompareBtn(); });
    setupSearchInput('compare-c2', 'dropdown-c2', n => { selectedC2 = n; checkCompareBtn(); });

    document.getElementById('compare-btn').addEventListener('click', async () => {
        if (selectedC1 && selectedC2) await runComparison(selectedC1, selectedC2);
    });
}

function checkCompareBtn() {
    document.getElementById('compare-btn').disabled = !(selectedC1 && selectedC2 && selectedC1 !== selectedC2);
}

function setupSearchInput(inputId, dropdownId, setFn) {
    const input = document.getElementById(inputId);
    const dd = document.getElementById(dropdownId);

    input.addEventListener('input', () => {
        const q = input.value.toLowerCase().trim();
        if (q.length < 2) { dd.classList.remove('open'); return; }

        const matches = allColleges.filter(c => c.name.toLowerCase().includes(q)).slice(0, 12);
        if (!matches.length) { dd.classList.remove('open'); return; }

        dd.innerHTML = matches.map(c =>
            `<div class="search-dropdown-item" data-name="${c.name.replace(/"/g, '&quot;')}">${c.name}<span class="city-tag">${c.city}</span></div>`
        ).join('');

        dd.querySelectorAll('.search-dropdown-item').forEach(item => {
            item.addEventListener('click', () => {
                input.value = item.dataset.name;
                setFn(item.dataset.name);
                dd.classList.remove('open');
            });
        });
        dd.classList.add('open');
    });

    input.addEventListener('blur', () => setTimeout(() => dd.classList.remove('open'), 200));
    input.addEventListener('focus', () => { if (input.value.length >= 2) input.dispatchEvent(new Event('input')); });
}

async function runComparison(c1, c2) {
    const loading = document.getElementById('compare-loading');
    const results = document.getElementById('compare-results');
    loading.style.display = 'block';
    results.style.display = 'none';

    try {
        const res = await fetch(`/api/compare?c1=${encodeURIComponent(c1)}&c2=${encodeURIComponent(c2)}`);
        if (res.status === 401) { window.location.href = '/login'; return; }
        const data = await res.json();
        if (data.error) { alert(data.error); return; }
        renderComparison(data);
    } catch (e) {
        alert('Comparison failed');
        console.error(e);
    } finally {
        loading.style.display = 'none';
    }
}

function renderComparison(data) {
    const results = document.getElementById('compare-results');
    results.style.display = 'block';

    document.getElementById('compare-header').innerHTML = `
        <div class="cmp-college-card c1-accent">
            <h3>${data.college1.name}</h3>
            <div class="meta">${data.college1.city} &bull; ${data.college1.total_branches} Branches</div>
        </div>
        <div class="cmp-college-card c2-accent">
            <h3>${data.college2.name}</h3>
            <div class="meta">${data.college2.city} &bull; ${data.college2.total_branches} Branches</div>
        </div>
    `;

    const thead = document.getElementById('compare-thead');
    const tbody = document.getElementById('compare-tbody');

    thead.innerHTML = '<tr><th>Branch</th><th>Category</th><th style="color:var(--accent)">College 1</th><th style="color:var(--gold)">College 2</th><th>Diff</th></tr>';

    if (!data.comparison.length) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:24px;color:var(--text-3)">No common branches found</td></tr>';
    } else {
        tbody.innerHTML = data.comparison.map(row => {
            let cls = 'diff-neutral', txt = '—';
            if (row.difference !== null) {
                if (row.difference > 0) { cls = 'diff-negative'; txt = '+' + row.difference.toFixed(2); }
                else if (row.difference < 0) { cls = 'diff-positive'; txt = row.difference.toFixed(2); }
                else txt = '0.00';
            }
            return `<tr>
                <td>${row.branch_group}</td><td>${row.category}</td>
                <td>${row.college1_score !== null ? row.college1_score.toFixed(2) + '%' : '—'}</td>
                <td>${row.college2_score !== null ? row.college2_score.toFixed(2) + '%' : '—'}</td>
                <td class="${cls}">${txt}</td>
            </tr>`;
        }).join('');
    }

    document.getElementById('compare-summary').innerHTML = `
        <div class="summary-card"><h4>Common Branches</h4><div class="value">${data.common_branches.length}</div></div>
        <div class="summary-card"><h4>Only in College 1</h4><div class="value" style="color:var(--accent)">${data.only_in_college1.length}</div></div>
        <div class="summary-card"><h4>Only in College 2</h4><div class="value" style="color:var(--gold)">${data.only_in_college2.length}</div></div>
    `;

    results.scrollIntoView({ behavior: 'smooth' });
}

// ─── 3D Tilt Effect on Holo Cards ───────────────────
function setup3DTilt() {
    document.querySelectorAll('.holo-card').forEach(card => {
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;

            const rotateX = ((y - centerY) / centerY) * -3;
            const rotateY = ((x - centerX) / centerX) * 3;

            card.style.transform = `perspective(600px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateX(4px)`;

            // Dynamic highlight
            const highlight = card.querySelector('::after') || card;
            card.style.background = `radial-gradient(circle at ${x}px ${y}px, rgba(255,107,53,0.03), rgba(10,10,18,0.8) 50%)`;
        });

        card.addEventListener('mouseleave', () => {
            card.style.transform = '';
            card.style.background = '';
        });
    });
}

// ─── Interactive Dot Matrix Canvas ──────────────────
function setupDotMatrix() {
    const canvas = document.getElementById('cmd-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const container = canvas.parentElement;

    let width, height;
    let dots = [];
    const spacing = 22; // Distance between dots
    const baseRadius = 1;
    const hoverRadius = 3.5;
    const hoverDistance = 120; // Magnetic field radius

    let mouse = { x: -1000, y: -1000 };

    function resize() {
        width = container.clientWidth;
        height = container.clientHeight;
        canvas.width = width;
        canvas.height = height;
        initDots();
    }

    function initDots() {
        dots = [];
        const cols = Math.ceil(width / spacing);
        const rows = Math.ceil(height / spacing);

        for (let i = 0; i <= cols; i++) {
            for (let j = 0; j <= rows; j++) {
                dots.push({
                    baseX: i * spacing,
                    baseY: j * spacing,
                    x: i * spacing,
                    y: j * spacing,
                });
            }
        }
    }

    function draw() {
        ctx.clearRect(0, 0, width, height);
        ctx.fillStyle = '#FF6B35'; // orange accent

        dots.forEach(dot => {
            const dx = mouse.x - dot.baseX;
            const dy = mouse.y - dot.baseY;
            const dist = Math.sqrt(dx * dx + dy * dy);

            let radius = baseRadius;
            let targetX = dot.baseX;
            let targetY = dot.baseY;

            if (dist < hoverDistance) {
                // Magnetic pull + grow
                const force = (hoverDistance - dist) / hoverDistance;
                radius = baseRadius + (hoverRadius - baseRadius) * Math.pow(force, 1.5);
                
                // Pull towards cursor slightly
                const pullStr = 0.15;
                targetX = dot.baseX + dx * force * pullStr;
                targetY = dot.baseY + dy * force * pullStr;
                
                ctx.globalAlpha = 0.15 + 0.85 * force;
            } else {
                ctx.globalAlpha = 0.15;
            }

            // Interpolate position for smooth easing
            dot.x += (targetX - dot.x) * 0.15;
            dot.y += (targetY - dot.y) * 0.15;

            ctx.beginPath();
            ctx.arc(dot.x, dot.y, radius, 0, Math.PI * 2);
            ctx.fill();
        });

        requestAnimationFrame(draw);
    }

    container.addEventListener('mousemove', (e) => {
        const rect = canvas.getBoundingClientRect();
        mouse.x = e.clientX - rect.left;
        mouse.y = e.clientY - rect.top;
    });

    container.addEventListener('mouseleave', () => {
        mouse.x = -1000;
        mouse.y = -1000;
    });

    window.addEventListener('resize', resize);
    
    // Init
    resize();
    draw();
}
