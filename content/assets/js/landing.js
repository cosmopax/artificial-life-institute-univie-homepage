document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('mescia-canvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let width = 0;
    let height = 0;
    let dpr = 1;

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const config = {
        count: reducedMotion ? 70 : 120,
        maxDist: 150,
        repelDist: reducedMotion ? 140 : 200,
        speed: reducedMotion ? 0.25 : 0.45
    };

    const maxDistSq = config.maxDist * config.maxDist;
    const repelDistSq = config.repelDist * config.repelDist;
    const cellSize = config.maxDist;
    const grid = new Map();
    const neighborOffsets = [-1, 0, 1];

    function resize() {
        width = window.innerWidth;
        height = window.innerHeight;
        dpr = Math.min(window.devicePixelRatio || 1, 2);
        canvas.width = Math.round(width * dpr);
        canvas.height = Math.round(height * dpr);
        canvas.style.width = `${width}px`;
        canvas.style.height = `${height}px`;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    window.addEventListener('resize', resize);
    resize();

    class Node {
        constructor(index) {
            this.index = index;
            this.reset();
        }

        reset() {
            this.x = Math.random() * width;
            this.y = Math.random() * height;
            this.vx = (Math.random() - 0.5) * config.speed;
            this.vy = (Math.random() - 0.5) * config.speed;
            this.radius = Math.random() * 2 + 0.8;
            this.baseColor = `rgba(212, 160, 85, ${Math.random() * 0.5 + 0.12})`;
        }

        update() {
            this.x += this.vx;
            this.y += this.vy;

            if (this.x < 0 || this.x > width) {
                this.vx *= -1;
                this.x = Math.max(0, Math.min(width, this.x));
            }
            if (this.y < 0 || this.y > height) {
                this.vy *= -1;
                this.y = Math.max(0, Math.min(height, this.y));
            }
        }

        draw() {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
            ctx.fillStyle = this.baseColor;
            ctx.fill();
        }
    }

    const nodes = Array.from({ length: config.count }, (_, index) => new Node(index));

    function gridKey(x, y) {
        return `${x},${y}`;
    }

    function populateGrid() {
        grid.clear();
        for (const node of nodes) {
            const cellX = Math.floor(node.x / cellSize);
            const cellY = Math.floor(node.y / cellSize);
            const key = gridKey(cellX, cellY);
            let bucket = grid.get(key);
            if (!bucket) {
                bucket = [];
                grid.set(key, bucket);
            }
            bucket.push(node);
        }
    }

    function drawConnections() {
        populateGrid();
        ctx.lineWidth = 1;

        for (const node of nodes) {
            const cellX = Math.floor(node.x / cellSize);
            const cellY = Math.floor(node.y / cellSize);

            for (const xOffset of neighborOffsets) {
                for (const yOffset of neighborOffsets) {
                    const bucket = grid.get(gridKey(cellX + xOffset, cellY + yOffset));
                    if (!bucket) continue;

                    for (const other of bucket) {
                        if (other.index <= node.index) continue;
                        const dx = node.x - other.x;
                        const dy = node.y - other.y;
                        const distSq = dx * dx + dy * dy;
                        if (distSq < maxDistSq) {
                            const dist = Math.sqrt(distSq);
                            const alpha = 1 - dist / config.maxDist;
                            ctx.beginPath();
                            ctx.moveTo(node.x, node.y);
                            ctx.lineTo(other.x, other.y);
                            ctx.strokeStyle = `rgba(212, 160, 85, ${alpha * 0.2})`;
                            ctx.stroke();
                        }
                    }
                }
            }
        }
    }

    const mouse = { x: 0, y: 0, active: false };
    window.addEventListener('mousemove', (event) => {
        mouse.x = event.clientX;
        mouse.y = event.clientY;
        mouse.active = true;
    });
    window.addEventListener('mouseout', (event) => {
        if (!event.relatedTarget) {
            mouse.active = false;
        }
    });

    let animationId = null;

    function animate() {
        if (document.hidden) {
            animationId = null;
            return;
        }

        ctx.clearRect(0, 0, width, height);

        for (const node of nodes) {
            node.update();

            if (mouse.active) {
                const dx = node.x - mouse.x;
                const dy = node.y - mouse.y;
                const distSq = dx * dx + dy * dy;

                if (distSq < repelDistSq) {
                    const dist = Math.sqrt(distSq) || 1;
                    const force = (config.repelDist - dist) / config.repelDist;
                    const push = force * 2.5;
                    node.x += (dx / dist) * push;
                    node.y += (dy / dist) * push;
                }
            }

            node.draw();
        }

        drawConnections();
        animationId = requestAnimationFrame(animate);
    }

    document.addEventListener('visibilitychange', () => {
        if (!document.hidden && animationId === null) {
            animationId = requestAnimationFrame(animate);
        }
    });

    animationId = requestAnimationFrame(animate);
});
