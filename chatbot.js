// Particle animation script
var w, h, loopId, id, canvas, ctx, particles;

var options = {
    particleColor: "white",
    lineColor: "Fuchsia",
    particleAmount: 60,
    defaultRadius: 2,
    variantRadius: 2,
    defaultSpeed: 1,
    variantSpeed: 2,
    linkRadius: 300
};

var rgb = options.lineColor.match(/\d+/g);

document.addEventListener("DOMContentLoaded", init);

function init() {
    canvas = document.getElementById("particle-canvas");
    ctx = canvas.getContext("2d");
    resizeReset();
    initialiseElements();
    startAnimation();
}

function resizeReset() {
    w = canvas.width = window.innerWidth;
    h = canvas.height = window.innerHeight;
}

function initialiseElements() {
    particles = [];
    for (var i = 0; i < options.particleAmount; i++) {
        particles.push(new Particle());
    }
}

function startAnimation() {
    loopId = requestAnimationFrame(animationLoop);
}

function animationLoop() {
    ctx.clearRect(0, 0, w, h);
    drawScene();

    id = requestAnimationFrame(animationLoop);
}

function drawScene() {
    drawLine();
    drawParticle();
}

function drawParticle() {
    for (var i = 0; i < particles.length; i++) {
        particles[i].update();
        particles[i].draw();
    }
}

function drawLine() {
   for (var i = 0; i < particles.length; i++) {
      linkPoints(particles[i], particles);
    }
    
}

 function linkPoints(point, hubs) {
     for (var i = 0; i < hubs.length; i++) {
       var distance = checkDistance(point.x, point.y, hubs[i].x, hubs[i].y);
      var opacity = 1 - distance / options.linkRadius;
        if (opacity > 0) {
        ctx.lineWidth = 0.5;
        ctx.strokeStyle = options.lineColor; // Use lineColor from options object
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

Particle = function () {
    var _this = this;

    _this.x = Math.random() * w;
    _this.y = Math.random() * h;
    _this.color = options.particleColor;
    _this.radius = options.defaultRadius + Math.random() * options.variantRadius;
    _this.speed = options.defaultSpeed + Math.random() * options.variantSpeed;
    _this.directionAngle = Math.floor(Math.random() * 360);
    _this.vector = {
        x: Math.cos(_this.directionAngle) * _this.speed,
        y: Math.sin(_this.directionAngle) * _this.speed
    }

    _this.update = function () {
        _this.border();
        _this.x += _this.vector.x;
        _this.y += _this.vector.y;
    }

    _this.border = function () {
        if (_this.x >= w || _this.x <= 0) {
            _this.vector.x *= -1;
        }
        if (_this.y >= h || _this.y <= 0) {
            _this.vector.y *= -1;
        }
        if (_this.x > w) _this.x = w;
        if (_this.y > h) _this.y = h;
        if (_this.x < 0) _this.x = 0;
        if (_this.y < 0) _this.y = 0;
    }

    _this.draw = function() {
        ctx.beginPath();
        ctx.arc(_this.x, _this.y, _this.radius, 0, Math.PI * 2);
        ctx.closePath();
        ctx.fillStyle = _this.color;
        ctx.fill();
    }
}

const socket = new WebSocket("ws://localhost:8765");

socket.addEventListener("open", () => {
    console.log("WebSocket connection established");
});

socket.addEventListener("error", (event) => {
    console.error("WebSocket error:", event);
});

socket.addEventListener("close", () => {
    console.log("WebSocket connection closed");
});

socket.addEventListener('message', (event) => {
    const response = JSON.parse(event.data);
    console.log('Message from server:', response);

    if (response.response) {
        updateConversationBox('Dave', response.response || 'No response available');
    }
});

const sendButton = document.getElementById('send-message');
const messageInput = document.getElementById('user-input');
const conversationBox = document.getElementById('conversation-box');

function updateConversationBox(speaker, text) {
    const messageElement = document.createElement('p');
    messageElement.textContent = `--- ${speaker}: ${text}`;
    conversationBox.appendChild(messageElement);
}

function sendMessage() {
    const message = messageInput.value;
    if (message && socket.readyState === WebSocket.OPEN) {
        updateConversationBox('USER', message);
        socket.send(JSON.stringify({ input: message }));
        messageInput.value = '';
    }
}

sendButton.addEventListener('click', () => {
    sendMessage();
});

messageInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
        event.preventDefault();
        sendMessage();
    }
});
