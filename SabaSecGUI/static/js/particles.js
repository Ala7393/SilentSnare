// particles.js – optimised network-particle animation
// Fixes: batched draw calls, no per-line strokeStyle, squared-distance, 30fps cap, mobile reduction

(function () {
    function initParticles(canvasId, opts) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        const ctx = canvas.getContext('2d');

        // Detect low-power device (mobile / small screen)
        const isMobile = window.innerWidth < 900 ||
            /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent);

        const cfg = Object.assign({
            count:       55,
            speed:       0.35,
            dotRadius:   2,
            dotColor:    'rgba(255,215,0,',
            lineColor:   '255,215,0',
            maxDist:     130,
            dotOpacity:  0.55,
            lineOpacity: 0.12,
        }, opts || {});

        // Reduce load on mobile
        if (isMobile) {
            cfg.count    = Math.max(8, Math.floor(cfg.count * 0.35));
            cfg.maxDist  = Math.floor(cfg.maxDist * 0.7);
            cfg.speed    = cfg.speed * 0.6;
        }

        const maxDistSq = cfg.maxDist * cfg.maxDist; // avoid sqrt every frame

        let W, H, particles = [];
        let lastFrame = 0;
        const FPS_CAP = isMobile ? 24 : 40; // hard cap — 24fps mobile, 40fps desktop
        const FRAME_MS = 1000 / FPS_CAP;

        function resize() {
            W = canvas.width  = canvas.offsetWidth;
            H = canvas.height = canvas.offsetHeight;
        }

        function Particle() {
            this.x  = Math.random() * W;
            this.y  = Math.random() * H;
            this.vx = (Math.random() - 0.5) * cfg.speed;
            this.vy = (Math.random() - 0.5) * cfg.speed;
            this.r  = cfg.dotRadius + Math.random() * 0.6;
        }

        function init() {
            resize();
            particles = Array.from({ length: cfg.count }, () => new Particle());
        }

        function draw() {
            ctx.clearRect(0, 0, W, H);

            // ── Lines: ONE beginPath + ONE stroke for ALL lines ──────────
            // Use globalAlpha for fade instead of per-line strokeStyle
            ctx.beginPath();
            ctx.strokeStyle = 'rgb(' + cfg.lineColor + ')';
            ctx.lineWidth = 0.6;

            const len = particles.length;
            for (let i = 0; i < len; i++) {
                for (let j = i + 1; j < len; j++) {
                    const dx = particles[i].x - particles[j].x;
                    const dy = particles[i].y - particles[j].y;
                    const dSq = dx * dx + dy * dy; // no sqrt!
                    if (dSq < maxDistSq) {
                        ctx.moveTo(particles[i].x, particles[i].y);
                        ctx.lineTo(particles[j].x, particles[j].y);
                    }
                }
            }
            ctx.globalAlpha = cfg.lineOpacity;
            ctx.stroke();

            // ── Dots: ONE beginPath + ONE fill for ALL dots ──────────────
            ctx.globalAlpha = cfg.dotOpacity;
            ctx.fillStyle = cfg.dotColor + '1)';
            ctx.beginPath();
            for (const p of particles) {
                ctx.moveTo(p.x + p.r, p.y);
                ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
            }
            ctx.fill();

            ctx.globalAlpha = 1; // reset
        }

        function update() {
            for (const p of particles) {
                p.x += p.vx;
                p.y += p.vy;
                if (p.x < -10)      p.x = W + 10;
                else if (p.x > W + 10) p.x = -10;
                if (p.y < -10)      p.y = H + 10;
                else if (p.y > H + 10) p.y = -10;
            }
        }

        let rafId;
        function loop(ts) {
            rafId = requestAnimationFrame(loop);
            if (ts - lastFrame < FRAME_MS) return; // skip frame — enforce fps cap
            lastFrame = ts;
            update();
            draw();
        }

        // Pause when tab is not visible — saves CPU entirely
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                cancelAnimationFrame(rafId);
            } else {
                lastFrame = 0;
                rafId = requestAnimationFrame(loop);
            }
        });

        init();
        rafId = requestAnimationFrame(loop);

        const ro = new ResizeObserver(() => resize());
        ro.observe(canvas);

        return { stop: () => cancelAnimationFrame(rafId) };
    }

    window.initParticles = initParticles;
})();
