(function () {
  // 动画 iframe 按容器宽度等比缩放（composition 设计尺寸 1280x720）
  function fitAnims() {
    document.querySelectorAll(".anim-embed").forEach(function (wrap) {
      var iframe = wrap.querySelector("iframe");
      if (!iframe) return;
      var scale = wrap.clientWidth / 1280;
      iframe.style.transform = "scale(" + scale + ")";
      wrap.style.height = Math.round(720 * scale) + "px";
    });
  }
  window.addEventListener("resize", fitAnims);
  fitAnims();

  // 代码块复制按钮
  document.querySelectorAll(".codehilite").forEach(function (block) {
    var btn = document.createElement("button");
    btn.className = "copy-btn";
    btn.textContent = "复制";
    btn.addEventListener("click", function () {
      var code = block.querySelector("pre").innerText;
      navigator.clipboard.writeText(code).then(function () {
        btn.textContent = "已复制";
        setTimeout(function () { btn.textContent = "复制"; }, 1400);
      });
    });
    block.appendChild(btn);
  });

  // 目录 scroll-spy
  var tocLinks = Array.prototype.slice.call(document.querySelectorAll("[data-toc-link]"));
  if (tocLinks.length) {
    var map = new Map();
    tocLinks.forEach(function (a) {
      var id = decodeURIComponent(a.getAttribute("href").slice(1));
      var el = document.getElementById(id);
      if (el) map.set(el, a);
    });
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            tocLinks.forEach(function (a) { a.classList.remove("toc-active"); });
            var link = map.get(entry.target);
            if (link) link.classList.add("toc-active");
          }
        });
      },
      { rootMargin: "-80px 0px -70% 0px" }
    );
    map.forEach(function (_, el) { observer.observe(el); });
  }

  // 顶部导航高亮当前章
  var path = location.pathname;
  document.querySelectorAll(".site-nav a, .mobile-nav-panel a").forEach(function (a) {
    var href = a.getAttribute("href");
    if (href && path.endsWith(href.split("/").pop())) a.classList.add("active");
  });

  // ---- 交互组件 ----
  function fmtBytes(bytes) {
    var gb = bytes / 1073741824;
    if (gb >= 1) return gb.toFixed(gb >= 100 ? 0 : 1) + " GB";
    var mb = bytes / 1048576;
    if (mb >= 1) return mb.toFixed(mb >= 100 ? 0 : 1) + " MB";
    return (bytes / 1024).toFixed(0) + " KB";
  }

  // KV Cache 显存计算器（d_head 按 128 计）
  var kvCalc = document.getElementById("kv-calc");
  if (kvCalc) {
    var D_HEAD = 128;
    var kvRead = function () {
      var p = {};
      kvCalc.querySelectorAll("[data-p]").forEach(function (el) {
        var v = parseFloat(el.value);
        if (el.dataset.log) v = 128 * Math.pow(2, v);
        p[el.dataset.p] = v;
      });
      return p;
    };
    var kvUpdate = function () {
      var p = kvRead();
      var total = 2 * p.seq * p.batch * p.layers * (p.kvheads * D_HEAD) * p.dtype;
      var perTok = 2 * p.kvheads * D_HEAD * p.dtype * p.layers;
      kvCalc.querySelector('[data-o="seq"]').textContent = p.seq.toLocaleString();
      kvCalc.querySelector('[data-o="batch"]').textContent = p.batch;
      kvCalc.querySelector('[data-o="layers"]').textContent = p.layers;
      kvCalc.querySelector('[data-o="kvheads"]').textContent = p.kvheads;
      kvCalc.querySelector('[data-o="total"]').textContent = fmtBytes(total);
      kvCalc.querySelector('[data-o="pertok"]').textContent = fmtBytes(perTok);
      var ratio = total / (14 * 1073741824);
      kvCalc.querySelector('[data-o="vs"]').textContent =
        ratio < 0.1 ? "可忽略" : ratio.toFixed(ratio >= 10 ? 0 : 1) + "×";
    };
    kvCalc.querySelectorAll("[data-p]").forEach(function (el) {
      el.addEventListener("input", kvUpdate);
    });
    kvUpdate();
  }

  // 量化粒度 8×8 网格（同色区域共享一个 scale）
  var GC = ["#bfdbfe", "#fcd34d", "#86efac", "#c4b5fd"];
  var BC = ["#bfdbfe", "#93c5fd", "#60a5fa", "#3b82f6", "#2563eb", "#1d4ed8", "#1e40af", "#172554"];
  document.querySelectorAll("[data-grid8]").forEach(function (el) {
    var mode = el.dataset.grid8;
    var html = "";
    for (var r = 0; r < 64; r++) {
      var c;
      if (mode === "tensor") c = BC[2];
      else if (mode === "channel") c = BC[r >> 3];
      else c = GC[(((r >> 3) << 1) + ((r & 7) >> 2)) & 3];
      html += '<i style="width:14px;height:14px;border-radius:3px;background:' + c + '"></i>';
    }
    el.style.cssText = "display:grid;grid-template-columns:repeat(8,14px);gap:2px;justify-content:center";
    el.innerHTML = html;
  });

  // Roofline 探索器（A100: 312 TFLOPS, 2 TB/s；decode 算术强度 ≈ batch）
  var roof = document.getElementById("roofline-explorer");
  if (roof) {
    var PEAK = 312, BW = 2, BALANCE = PEAK / BW;
    var W = 620, H = 300, PL = 46, PR = 14, PT = 16, PB = 34;
    var X0 = Math.log10(0.5), X1 = Math.log10(512);
    var Y0 = Math.log10(0.1), Y1 = Math.log10(1000);
    var px = function (ai) { return PL + (Math.log10(ai) - X0) / (X1 - X0) * (W - PL - PR); };
    var py = function (t) { return PT + (Y1 - Math.log10(t)) / (Y1 - Y0) * (H - PT - PB); };
    var ns = "http://www.w3.org/2000/svg";
    var svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", "0 0 " + W + " " + H);
    svg.setAttribute("style", "width:100%;height:auto;display:block");
    var el = function (tag, attrs, text) {
      var e = document.createElementNS(ns, tag);
      for (var k in attrs) e.setAttribute(k, attrs[k]);
      if (text != null) e.textContent = text;
      return e;
    };
    var axisStyle = { stroke: "#e4e4e7", "stroke-width": 1 };
    [1, 10, 100].forEach(function (t) {
      svg.appendChild(el("line", { x1: px(t), y1: py(0.1), x2: px(t), y2: py(1000), stroke: "#f4f4f5" }));
      svg.appendChild(el("text", { x: px(t), y: H - 12, "text-anchor": "middle", "font-size": 11, fill: "#a1a1aa" }, t));
    });
    [1, 10, 100].forEach(function (t) {
      svg.appendChild(el("line", { x1: px(0.5), y1: py(t), x2: px(512), y2: py(t), stroke: "#f4f4f5" }));
      svg.appendChild(el("text", { x: PL - 8, y: py(t) + 4, "text-anchor": "end", "font-size": 11, fill: "#a1a1aa" }, t));
    });
    svg.appendChild(el("text", { x: PL - 8, y: py(312) + 4, "text-anchor": "end", "font-size": 11, "font-weight": 600, fill: "#71717a" }, "312"));
    svg.appendChild(el("text", { x: (PL + W - PR) / 2, y: H - 12, "text-anchor": "middle", "font-size": 11.5, fill: "#71717a" }, ""));
    svg.appendChild(el("line", { x1: px(0.05 * 1), y1: py(0.1), x2: px(BALANCE), y2: py(PEAK), stroke: "#94a3b8", "stroke-width": 2.5, "stroke-linecap": "round" }));
    svg.appendChild(el("line", { x1: px(BALANCE), y1: py(PEAK), x2: px(512), y2: py(PEAK), stroke: "#94a3b8", "stroke-width": 2.5, "stroke-linecap": "round" }));
    svg.appendChild(el("line", { x1: px(BALANCE), y1: py(PEAK), x2: px(BALANCE), y2: py(0.1), stroke: "#d4d4d8", "stroke-dasharray": "4 4" }));
    svg.appendChild(el("text", { x: px(BALANCE), y: py(0.1) + 14, "text-anchor": "middle", "font-size": 11, fill: "#71717a" }, "平衡点 156"));
    svg.appendChild(el("text", { x: px(512) - 4, y: py(PEAK) - 8, "text-anchor": "end", "font-size": 11.5, fill: "#71717a" }, "算力上限 312 TFLOPS"));
    svg.appendChild(el("text", { x: px(1.6), y: py(2.2), "font-size": 11.5, fill: "#71717a", transform: "rotate(-33 " + px(1.6) + " " + py(2.2) + ")" }, "带宽斜率 2 TB/s"));
    var guideY = el("line", { stroke: "#7c3aed", "stroke-dasharray": "4 4", "stroke-width": 1.5 });
    var guideX = el("line", { stroke: "#7c3aed", "stroke-dasharray": "4 4", "stroke-width": 1.5 });
    var dot = el("circle", { r: 7, fill: "#2563eb", stroke: "#fff", "stroke-width": 2.5 });
    var dotLab = el("text", { "font-size": 12, "font-weight": 600, fill: "#1d4ed8" });
    svg.appendChild(guideY); svg.appendChild(guideX); svg.appendChild(dot); svg.appendChild(dotLab);
    roof.querySelector("[data-roofline-chart]").appendChild(svg);
    var slider = roof.querySelector("[data-p='batch']");
    var upd = function () {
      var b = Math.pow(2, parseFloat(slider.value));
      var batch = Math.round(b);
      var ai = b;
      var tflops = Math.min(PEAK, ai * BW);
      var util = tflops / PEAK * 100;
      var cb = ai >= BALANCE;
      roof.querySelector('[data-o="batch"]').textContent = batch;
      roof.querySelector('[data-o="ai"]').textContent = ai.toFixed(ai < 10 ? 1 : 0);
      roof.querySelector('[data-o="tflops"]').textContent = tflops.toFixed(0) + " TFLOPS";
      var boundEl = roof.querySelector('[data-o="bound"]');
      boundEl.textContent = cb ? "compute-bound" : "memory-bound";
      boundEl.style.color = cb ? "#047857" : "#b45309";
      roof.querySelector('[data-o="util"]').textContent = " " + util.toFixed(util < 10 ? 1 : 0) + "%";
      roof.querySelector('[data-o="utilbar"]').style.width = util + "%";
      dot.setAttribute("cx", px(ai)); dot.setAttribute("cy", py(tflops));
      guideY.setAttribute("x1", px(0.5)); guideY.setAttribute("x2", px(ai));
      guideY.setAttribute("y1", py(tflops)); guideY.setAttribute("y2", py(tflops));
      guideX.setAttribute("x1", px(ai)); guideX.setAttribute("x2", px(ai));
      guideX.setAttribute("y1", py(tflops)); guideX.setAttribute("y2", py(0.1));
      dotLab.setAttribute("x", Math.min(px(ai) + 12, W - 90));
      dotLab.setAttribute("y", py(tflops) - 10);
      dotLab.textContent = "batch=" + batch;
    };
    slider.addEventListener("input", upd);
    upd();
  }

  // 首页滚动入场动效（区块淡入上浮，章节卡片错峰）
  if (document.body.classList.contains("home-page")) {
    var revealEls = document.querySelectorAll(
      ".home .section-title, .home .learn-grid, .home .howto, .home .chapter-card"
    );
    revealEls.forEach(function (el) { el.classList.add("reveal"); });
    document.querySelectorAll(".home .chapter-card").forEach(function (card, i) {
      card.style.transitionDelay = Math.min(i, 6) * 55 + "ms";
    });
    var revealIO = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          revealIO.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1, rootMargin: "0px 0px -6% 0px" });
    revealEls.forEach(function (el) { revealIO.observe(el); });
  }
})();
