var w, h, canvas, ctx, particles, animationId;

var options = {
    particleColor: "white",
    lineColor: "Crimson",
    particleAmount: 60,
    defaultRadius: 2,
    variantRadius: 2,
    defaultSpeed: 1,
    variantSpeed: 2,
    linkRadius: 300
};

document.addEventListener("DOMContentLoaded", init);

function init() {
    canvas = document.getElementById("particle-canvas");
    ctx = canvas.getContext("2d");
    resizeReset();
    initialiseElements();
    startAnimation();
    highlightCurrentPage();
    window.addEventListener('resize', resizeReset);
}

function resizeReset() {
    w = canvas.width = window.innerWidth;
    h = canvas.height = window.innerHeight;
}

function initialiseElements() {
    particles = [];
    for (let i = 0; i < options.particleAmount; i++) {
        particles.push(new Particle());
    }
}

function startAnimation() {
    if (!animationId) {
        animationLoop();
    }
}

function animationLoop() {
    ctx.clearRect(0, 0, w, h);
    drawScene();
    animationId = requestAnimationFrame(animationLoop);
}

function drawScene() {
    for (let i = 0; i < particles.length; i++) {
        particles[i].update();
        particles[i].draw();
        linkPoints(particles[i], particles);
    }
}

function linkPoints(point, hubs) {
    for (let i = 0; i < hubs.length; i++) {
        const distance = checkDistance(point.x, point.y, hubs[i].x, hubs[i].y);
        const opacity = 1 - distance / options.linkRadius;
        if (opacity > 0) {
            ctx.lineWidth = 0.5;
            ctx.strokeStyle = options.lineColor;
            ctx.beginPath();
            ctx.moveTo(point.x, point.y);
            ctx.lineTo(hubs[i].x, hubs[i].y);
            ctx.closePath();
            ctx.stroke();
        }
    }
}

function checkDistance(x1, y1, x2, y2) {
    return Math.sqrt(Math.pow(x2 - x1, 2) + Math.pow(y2 - y1, 2));
}

function Particle() {
    this.x = Math.random() * w;
    this.y = Math.random() * h;
    this.color = options.particleColor;
    this.radius = options.defaultRadius + Math.random() * options.variantRadius;
    this.speed = options.defaultSpeed + Math.random() * options.variantSpeed;
    this.directionAngle = Math.floor(Math.random() * 360);
    this.vector = {
        x: Math.cos(this.directionAngle) * this.speed,
        y: Math.sin(this.directionAngle) * this.speed
    };
}

Particle.prototype.update = function () {
    this.border();
    this.x += this.vector.x;
    this.y += this.vector.y;
};

Particle.prototype.border = function () {
    if (this.x >= w || this.x <= 0) {
        this.vector.x *= -1;
    }
    if (this.y >= h || this.y <= 0) {
        this.vector.y *= -1;
    }
    if (this.x > w) this.x = w;
    if (this.y > h) this.y = h;
    if (this.x < 0) this.x = 0;
    if (this.y < 0) this.y = 0;
};

Particle.prototype.draw = function () {
    ctx.beginPath();
    ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
    ctx.closePath();
    ctx.fillStyle = this.color;
    ctx.fill();
    
};

function highlightCurrentPage() {
    const currentPage = window.location.pathname.split("/").pop();
    const links = {
        "index.html": "home-link",
        "about.html": "about-link",
        "contact.html": "contact-link"
    };
    if (links[currentPage]) {
        document.getElementById(links[currentPage]).classList.add("active");
    }
}
