
document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('mescia-canvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let width, height;

    // Resize handler
    function resize() {
        width = canvas.width = window.innerWidth;
        height = canvas.height = window.innerHeight;
    }
    window.addEventListener('resize', resize);
    resize();

    // Particle system for "Intricate Pattern"
    // Using a golden-ratio based Phyllotaxis pattern or similar

    class Node {
        constructor() {
            this.reset();
        }

        reset() {
            this.x = Math.random() * width;
            this.y = Math.random() * height;
            this.vx = (Math.random() - 0.5) * 0.5;
            this.vy = (Math.random() - 0.5) * 0.5;
            this.radius = Math.random() * 2 + 1;
            this.baseColor = `rgba(212, 160, 85, ${Math.random() * 0.5 + 0.1})`;
        }

        update() {
            this.x += this.vx;
            this.y += this.vy;

            if (this.x < 0 || this.x > width) this.vx *= -1;
            if (this.y < 0 || this.y > height) this.vy *= -1;
        }

        draw() {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
            ctx.fillStyle = this.baseColor;
            ctx.fill();
        }
    }

    const nodes = Array.from({ length: 100 }, () => new Node());

    // Connection Logic
    function drawConnections() {
        for (let i = 0; i < nodes.length; i++) {
            for (let j = i + 1; j < nodes.length; j++) {
                const dx = nodes[i].x - nodes[j].x;
                const dy = nodes[i].y - nodes[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < 150) {
                    ctx.beginPath();
                    ctx.moveTo(nodes[i].x, nodes[i].y);
                    ctx.lineTo(nodes[j].x, nodes[j].y);
                    const alpha = 1 - (dist / 150);
                    ctx.strokeStyle = `rgba(212, 160, 85, ${alpha * 0.2})`;
                    ctx.stroke();
                }
            }
        }
    }

    // Mouse Interaction
    let mouse = { x: null, y: null };
    window.addEventListener('mousemove', (e) => {
        mouse.x = e.clientX;
        mouse.y = e.clientY;
    });

    function animate() {
        ctx.clearRect(0, 0, width, height);

        nodes.forEach(node => {
            node.update();
            node.draw();

            // Mouse Repulsion/Attraction
            if (mouse.x) {
                const dx = node.x - mouse.x;
                const dy = node.y - mouse.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 200) {
                    const force = (200 - dist) / 200;
                    node.x += dx * force * 0.05;
                    node.y += dy * force * 0.05;
                }
            }
        });

        drawConnections();
        requestAnimationFrame(animate);
    }

    animate();
});
