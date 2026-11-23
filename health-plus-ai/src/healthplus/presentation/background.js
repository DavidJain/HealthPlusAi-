// HealthPlus AI — living background + small interactive touches.
//
// Streamlit reruns the script on every interaction and re-sends this code,
// so everything here is guarded to boot exactly once per page load. The
// canvas is attached to <body>, outside React's tree, so reruns never
// remove it.
(function () {
  if (window.__hpBooted) return;
  window.__hpBooted = true;

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ── Particle network ───────────────────────────────────────────────
  var canvas = document.createElement("canvas");
  canvas.id = "hp-plexus";
  canvas.setAttribute("aria-hidden", "true");
  document.body.prepend(canvas);
  var ctx = canvas.getContext("2d");

  var W = 0, H = 0, DPR = 1, nodes = [], stars = [];
  var mouse = { x: -9999, y: -9999 };
  var LINK = 150;

  // cyan → violet → magenta, picked by horizontal position
  function colorAt(x, a) {
    var t = Math.max(0, Math.min(1, x / W));
    var r, g, b;
    if (t < 0.5) { var k = t / 0.5; r = 34 + (139 - 34) * k; g = 211 + (92 - 211) * k; b = 238 + (246 - 238) * k; }
    else { var k2 = (t - 0.5) / 0.5; r = 139 + (224 - 139) * k2; g = 92 + (64 - 92) * k2; b = 246 + (251 - 246) * k2; }
    return "rgba(" + (r | 0) + "," + (g | 0) + "," + (b | 0) + "," + a + ")";
  }

  function resize() {
    DPR = Math.min(window.devicePixelRatio || 1, 1.5);
    W = window.innerWidth; H = window.innerHeight;
    canvas.width = W * DPR; canvas.height = H * DPR;
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    var count = Math.min(120, Math.max(40, Math.round((W * H) / 13000)));
    LINK = W < 640 ? 110 : 150;
    nodes = [];
    for (var i = 0; i < count; i++) {
      nodes.push({
        x: Math.random() * W, y: Math.random() * H,
        vx: (Math.random() - 0.5) * 0.35, vy: (Math.random() - 0.5) * 0.35,
        r: Math.random() * 1.6 + 0.6
      });
    }
    stars = [];
    for (var j = 0; j < Math.round(count * 1.4); j++) {
      stars.push({ x: Math.random() * W, y: Math.random() * H, r: Math.random() * 1.1 + 0.2, p: Math.random() * Math.PI * 2 });
    }
  }

  function frame(t) {
    ctx.clearRect(0, 0, W, H);

    // twinkling star dust
    for (var s = 0; s < stars.length; s++) {
      var st = stars[s];
      var a = 0.25 + 0.35 * Math.sin(t * 0.0012 + st.p);
      ctx.fillStyle = "rgba(220,225,255," + Math.max(0.05, a) + ")";
      ctx.fillRect(st.x, st.y, st.r, st.r);
    }

    // move nodes; gentle pull toward the pointer
    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      var dxm = mouse.x - n.x, dym = mouse.y - n.y, dm = Math.sqrt(dxm * dxm + dym * dym);
      if (dm < 220 && dm > 1) { n.vx += (dxm / dm) * 0.012; n.vy += (dym / dm) * 0.012; }
      n.vx *= 0.995; n.vy *= 0.995;
      var sp = Math.sqrt(n.vx * n.vx + n.vy * n.vy);
      if (sp < 0.08) { n.vx += (Math.random() - 0.5) * 0.05; n.vy += (Math.random() - 0.5) * 0.05; }
      if (sp > 1.2) { n.vx *= 0.9; n.vy *= 0.9; }
      n.x += n.vx; n.y += n.vy;
      if (n.x < -20) n.x = W + 20; else if (n.x > W + 20) n.x = -20;
      if (n.y < -20) n.y = H + 20; else if (n.y > H + 20) n.y = -20;
    }

    // links
    ctx.lineWidth = 0.8;
    for (var p = 0; p < nodes.length; p++) {
      var A = nodes[p];
      for (var q = p + 1; q < nodes.length; q++) {
        var B = nodes[q];
        var dx = A.x - B.x, dy = A.y - B.y;
        if (dx > LINK || dx < -LINK || dy > LINK || dy < -LINK) continue;
        var d = Math.sqrt(dx * dx + dy * dy);
        if (d < LINK) {
          ctx.strokeStyle = colorAt((A.x + B.x) / 2, (1 - d / LINK) * 0.42);
          ctx.beginPath(); ctx.moveTo(A.x, A.y); ctx.lineTo(B.x, B.y); ctx.stroke();
        }
      }
      // pointer links
      var mx = A.x - mouse.x, my = A.y - mouse.y, md = Math.sqrt(mx * mx + my * my);
      if (md < 200) {
        ctx.strokeStyle = colorAt(A.x, (1 - md / 200) * 0.6);
        ctx.beginPath(); ctx.moveTo(A.x, A.y); ctx.lineTo(mouse.x, mouse.y); ctx.stroke();
      }
    }

    // glowing nodes
    for (var k = 0; k < nodes.length; k++) {
      var N = nodes[k];
      ctx.fillStyle = colorAt(N.x, 0.9);
      ctx.shadowColor = colorAt(N.x, 1);
      ctx.shadowBlur = 10;
      ctx.beginPath(); ctx.arc(N.x, N.y, N.r, 0, Math.PI * 2); ctx.fill();
    }
    ctx.shadowBlur = 0;

    if (!reduceMotion) requestAnimationFrame(frame);
  }

  resize();
  var rt;
  window.addEventListener("resize", function () { clearTimeout(rt); rt = setTimeout(resize, 150); });
  window.addEventListener("pointermove", function (e) { mouse.x = e.clientX; mouse.y = e.clientY; }, { passive: true });
  window.addEventListener("pointerleave", function () { mouse.x = mouse.y = -9999; });
  requestAnimationFrame(frame);

  // ── Spotlight that follows the pointer across starter cards ────────
  document.addEventListener("pointermove", function (e) {
    var btn = e.target.closest && e.target.closest(".st-key-hp-suggest button");
    if (!btn) return;
    var r = btn.getBoundingClientRect();
    btn.style.setProperty("--mx", (e.clientX - r.left) + "px");
    btn.style.setProperty("--my", (e.clientY - r.top) + "px");
  }, { passive: true });

  // ── Count-up numbers (once per value, not on every rerun) ──────────
  var counted = {};
  function countUp(el) {
    var to = parseInt(el.getAttribute("data-count"), 10);
    var key = el.getAttribute("data-key") + ":" + to;
    if (isNaN(to) || el.__hpDone) return;
    el.__hpDone = true;
    if (counted[key] || reduceMotion) { el.textContent = to.toLocaleString(); counted[key] = true; return; }
    counted[key] = true;
    var start = performance.now(), dur = 1400;
    (function tick(now) {
      var p = Math.min(1, (now - start) / dur);
      var eased = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(to * eased).toLocaleString();
      if (p < 1) requestAnimationFrame(tick);
    })(start);
  }
  function scan() { document.querySelectorAll("[data-count]").forEach(countUp); }
  new MutationObserver(scan).observe(document.body, { childList: true, subtree: true });
  scan();
})();
