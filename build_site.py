#!/usr/bin/env python3
"""把 LLM 推理优化学习材料构建为静态 HTML 站点（shadcn 风格 tech blog）。"""
import html
import re
from pathlib import Path

import markdown
from markdown.extensions.toc import slugify_unicode

ROOT = Path(__file__).parent
SITE = ROOT / "site"
CHAPTERS_OUT = SITE / "chapters"

CHAPTERS = [
    {
        "num": "01",
        "file": "01_inference_fundamentals.md",
        "title": "LLM 推理基础",
        "subtitle": "推理到底慢在哪？",
        "desc": "自回归生成的本质、Prefill 与 Decode 两个阶段、为什么推理是 memory-bound、关键性能指标。",
    },
    {
        "num": "02",
        "file": "02_kv_cache_and_memory.md",
        "title": "KV Cache 与内存优化",
        "subtitle": "显存都去哪了？",
        "desc": "KV Cache 的原理与显存开销、PagedAttention、Continuous Batching、MQA / GQA。",
    },
    {
        "num": "03",
        "file": "03_quantization.md",
        "title": "量化",
        "subtitle": "精度换速度，到底怎么换？",
        "desc": "均匀量化的数学、PTQ 主流方法（GPTQ / AWQ / FP8）、Weight-Only 与反量化开销。",
    },
    {
        "num": "04",
        "file": "04_parallelism_and_serving.md",
        "title": "并行与服务架构",
        "subtitle": "大模型怎么切、怎么服务？",
        "desc": "TP / PP / DP / SP / CP / EP 六种并行、调度器设计、Prefill-Decode 分离架构与资源配比。",
    },
    {
        "num": "05",
        "file": "05_advanced_techniques.md",
        "title": "进阶优化技术",
        "subtitle": "还有哪些黑科技？",
        "desc": "Speculative Decoding、FlashAttention、Kernel Fusion、Prefix Caching。",
    },
    {
        "num": "06",
        "file": "06_framework_ecosystem.md",
        "title": "推理框架生态",
        "subtitle": "生产环境用什么？",
        "desc": "vLLM / TensorRT-LLM / SGLang / TGI / LMDeploy 对比，选型决策树与学习资源。",
    },
    {
        "num": "07",
        "file": "07_cluster_and_infra.md",
        "title": "推理集群与基础设施",
        "subtitle": "怎么把模型跑在“云”上？",
        "desc": "Autoscaling、负载均衡与路由、GPU 资源管理、CPU/GPU 混合部署与成本优化。",
    },
]

# (chapter file, header 文本子串) -> (动画文件, 动画标题, 说明)
ANIMATIONS = {
    ("01_inference_fundamentals.md", "2. 两个阶段"): (
        "prefill-vs-decode",
        "Prefill vs Decode：两种瓶颈",
        "Prefill 一次并行处理整个 prompt（compute-bound）；Decode 逐 token 串行，每步都要把全部权重和 KV Cache 从 HBM 搬进计算单元（memory-bound）。",
    ),
    ("01_inference_fundamentals.md", "3.1 算术强度"): (
        "arithmetic-intensity",
        "Roofline 模型：算术强度决定瓶颈",
        "算术强度 = FLOPs ÷ 访存字节数。Decode 只有 ≈1 FLOP/byte，卡在带宽墙上；增大 batch 把工作点右移，逼近算力上限。",
    ),
    ("02_kv_cache_and_memory.md", "1. 朴素推理的问题"): (
        "naive-vs-kv-cache",
        "朴素推理 vs KV Cache",
        "朴素推理每生成一个 token 都要重算全部历史 K/V（O(N²)）；KV Cache 每步只追加一组 K/V，计算量降为 O(N)。",
    ),
    ("02_kv_cache_and_memory.md", "4.1 PagedAttention"): (
        "paged-attention",
        "PagedAttention：像操作系统一样管理显存",
        "逻辑块经 Block Table 映射到非连续物理块，按需分配、用满再申请，显存浪费从 60–80% 降到 <4%。",
    ),
    ("02_kv_cache_and_memory.md", "4.3 Continuous Batching"): (
        "continuous-batching",
        "Continuous Batching：迭代级调度",
        "静态批处理中先完成的请求空占 slot；连续批处理在每个 iteration 边界完成即补位，GPU 不空转。",
    ),
    ("02_kv_cache_and_memory.md", "5.1 Multi-Query"): (
        "mha-gqa-mqa",
        "MHA / GQA / MQA：共享 K/V 的取舍",
        "多个 Q 头共享同一组 K/V，KV Cache 成倍缩小；注意力多样性主要来自 Q 的多样性，而非 K/V。",
    ),
    ("03_quantization.md", "2.1 均匀量化"): (
        "uniform-quantization",
        "均匀量化：FP32 → INT8 的线性映射",
        "x_q = round(x / s)，scale s 由 absmax 决定；超出范围的值被截断（clipping），四舍五入引入量化误差。",
    ),
    ("04_parallelism_and_serving.md", "2.1 Tensor Parallelism"): (
        "tensor-parallelism",
        "Tensor Parallelism：切开矩阵乘法",
        "按列切分权重到多卡各自计算，再按行切分时用 All-Reduce 求和；每层两次 All-Reduce 是 TP 的通信税。",
    ),
    ("04_parallelism_and_serving.md", "4.3 分离式架构"): (
        "pd-disaggregation",
        "Prefill-Decode 分离架构",
        "Prefill 池（算力导向）与 Decode 池（带宽导向）分离，KV Cache 经高速互联传输，两池按 T_p : T_d 独立伸缩。",
    ),
    ("05_advanced_techniques.md", "1. Speculative Decoding"): (
        "speculative-decoding",
        "Speculative Decoding：猜 + 验证",
        "小模型一次猜 γ 个 token，大模型用一次前向传播并行验证；接受前缀、截断分叉点，串行 5 步变 2 步。",
    ),
    ("05_advanced_techniques.md", "2. FlashAttention"): (
        "flash-attention",
        "FlashAttention：Tiling + Online Softmax",
        "把 Q/K/V 分块搬进 SRAM，用 running max/sum 在线归并，从不把 N² 的注意力矩阵写进 HBM。",
    ),
    ("07_cluster_and_infra.md", "2. Autoscaling"): (
        "llm-autoscaling",
        "LLM Autoscaling：冷启动与预测式扩容",
        "GPU 实例冷启动要 5–10 分钟，反应式扩容必然滞后于流量突增；预测式扩容提前就位，削平排队尖峰。",
    ),
}


def md_converter():
    return markdown.Markdown(
        extensions=[
            "tables",
            "fenced_code",
            "codehilite",
            "toc",
            "attr_list",
            "sane_lists",
            "md_in_html",
        ],
        extension_configs={
            "toc": {"slugify": slugify_unicode, "separator": "-"},
            "codehilite": {"guess_lang": False, "css_class": "codehilite"},
        },
        output_format="html5",
    )


def normalize_lists(md_text):
    # python-markdown 要求列表前有空行；源文件大量"段落紧接列表"的写法，统一补空行
    out = []
    in_code = False
    item = re.compile(r"^([-*]|\d+\.) ")
    prev_item = re.compile(r"^\s*([-*]|\d+\.) ")
    for ln in md_text.split("\n"):
        if ln.strip().startswith(("```", "~~~")):
            in_code = not in_code
        if not in_code and item.match(ln) and out:
            prev = out[-1]
            if prev.strip() and not prev_item.match(prev) and not prev.lstrip().startswith(("#", ">", "|")):
                out.append("")
        out.append(ln)
    return "\n".join(out)


def strip_gifs(html_text):
    return re.sub(r'<img[^>]*src="animations/out/[^"]*"[^>]*>', "", html_text)


def rewrite_links(html_text):
    # 章际 .md 链接 -> .html（同目录）
    html_text = re.sub(r'href="(\d{2}_[a-z_]+)\.md(#[^"]*)?"', r'href="\1.html\2"', html_text)
    html_text = re.sub(r'href="README\.md"', 'href="../index.html"', html_text)
    return html_text


def wrap_tables(html_text):
    html_text = html_text.replace("<table>", '<div class="table-wrap"><table>')
    html_text = html_text.replace("</table>", "</table></div>")
    return html_text


def style_callouts(html_text):
    def repl(match):
        inner = match.group(1)
        cls = "callout"
        if "⚠️" in inner[:120]:
            cls += " callout-warn"
        elif "💡" in inner[:120]:
            cls += " callout-tip"
        return f'<blockquote class="{cls}">{inner}</blockquote>'

    return re.sub(r"<blockquote>(.*?)</blockquote>", repl, html_text, flags=re.S)


def split_and_render_answers(html_text):
    """把思考题末尾合并的 <details>参考答案</details> 拆开，
    渲染其中的 markdown 后分别挂到对应题目 <li> 下面。"""
    m = re.search(
        r"<details>\s*<summary>参考答案</summary>(.*?)</details>", html_text, flags=re.S
    )
    if not m:
        return html_text
    inner = m.group(1)
    parts = re.split(r"\*\*第\s*(\d+)\s*题\*\*[:：]?\s*", inner)
    answers = {}
    it = iter(parts[1:])
    for num, ans in zip(it, it):
        md = md_converter()
        answers[int(num)] = md.convert(ans.strip())

    # 找 details 之前最近的 <ol>...</ol>（题目列表）
    ol_end = html_text.rfind("</ol>", 0, m.start())
    ol_start = html_text.rfind("<ol>", 0, m.start())
    between = html_text[ol_end + len("</ol>") : m.start()]
    if ol_start == -1 or ol_end == -1 or ol_start > ol_end or between.strip():
        # 结构不符合预期：保底只修复 markdown 渲染，整体替换 details
        md = md_converter()
        rendered = md.convert(inner)
        fallback = (
            '<details class="answer"><summary>参考答案</summary>'
            + rendered
            + "</details>"
        )
        return html_text[: m.start()] + fallback + html_text[m.end() :]

    ol_inner = html_text[ol_start + len("<ol>") : ol_end]
    questions = re.findall(r"<li>(.*?)</li>", ol_inner, flags=re.S)
    if not questions:
        return html_text
    rebuilt = ['<ol class="quiz-list">']
    for i, q in enumerate(questions, start=1):
        ans_html = answers.get(i)
        if ans_html:
            rebuilt.append(
                f'<li>{q}<details class="answer"><summary>参考答案</summary>{ans_html}</details></li>'
            )
        else:
            rebuilt.append(f"<li>{q}</li>")
    rebuilt.append("</ol>")
    return (
        html_text[:ol_start]
        + "".join(rebuilt)
        + html_text[ol_end + len("</ol>") : m.start()]
        + html_text[m.end() :]
    )


def figure_html(anim_file, anim_title, caption):
    src = f"../animations/{anim_file}/index.html?autoplay=1"
    return (
        f'<figure class="anim-figure">'
        f'<figcaption><span class="anim-badge"><svg viewBox="0 0 24 24" fill="currentColor" width="11" height="11"><path d="M8 5.5v13l11-6.5z"/></svg>动画演示</span>'
        f'<span class="anim-title">{html.escape(anim_title)}</span>'
        f'<a class="anim-open" href="{src}" target="_blank" rel="noopener">新窗口打开<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="11" height="11"><path d="M7 17L17 7M9 7h8v8"/></svg></a></figcaption>'
        f'<div class="anim-embed"><iframe src="{src}" title="{html.escape(anim_title)}" loading="lazy" scrolling="no"></iframe></div>'
        f'<p class="anim-caption">{html.escape(caption)}</p>'
        f"</figure>"
    )


def inject_animations(html_text, chapter_file):
    for (chap, header_sub), (anim_file, anim_title, caption) in ANIMATIONS.items():
        if chap != chapter_file:
            continue
        pattern = re.compile(r'(<h[23][^>]*>(?:(?!</h[23]>).)*?</h[23]>)', re.S)

        def repl(match):
            header_html = match.group(1)
            text = re.sub(r"<[^>]+>", "", header_html)
            if header_sub in text:
                return header_html + "\n" + figure_html(anim_file, anim_title, caption)
            return header_html

        html_text = pattern.sub(repl, html_text)
    return html_text


def toc_html(toc_tokens):
    def render(tokens, depth=0):
        if not tokens:
            return ""
        items = []
        for tok in tokens:
            if tok["level"] <= 3:
                items.append(
                    f'<li class="toc-l{tok["level"]}"><a href="#{tok["id"]}" data-toc-link>{html.escape(tok["name"])}</a>'
                    + render(tok.get("children", []), depth + 1)
                    + "</li>"
                )
            else:
                items.append(render(tok.get("children", []), depth + 1))
        return '<ul class="toc-list">' + "".join(items) + "</ul>"

    return render(toc_tokens)


NAV = """<header class="site-header">
  <div class="container header-inner">
    <a class="brand" href="{root}index.html">
      <span class="brand-mark">λ</span>
      <span class="brand-name">LLM 推理优化</span>
    </a>
    <nav class="site-nav">{links}</nav>
    <details class="mobile-nav">
      <summary>章节</summary>
      <div class="mobile-nav-panel">{links}</div>
    </details>
  </div>
</header>"""

def asset_version():
    v = 0
    for name in ("blog.css", "blog.js"):
        f = SITE / "assets" / name
        if f.exists():
            v = max(v, int(f.stat().st_mtime))
    return v


ASSET_V = asset_version()


def page_shell(title, description, body, root_prefix, toc="", home=False):
    links = "".join(
        f'<a href="{root_prefix}chapters/{c["file"].replace(".md", ".html")}" title="第 {c["num"]} 章">{c["num"]}</a>'
        for c in CHAPTERS
    )
    nav = NAV.format(root=root_prefix, links=links)
    toc_html_text = f'<aside class="toc"><div class="toc-title">本页目录</div>{toc}</aside>' if toc else ""
    if home:
        main_html = f'<main class="container home">\n{body}\n</main>'
    else:
        main_html = f'<main class="container main-grid">\n  <article class="prose">\n{body}\n  </article>\n  {toc_html_text}\n</main>'
    body_cls = ' class="home-page"' if home else ""
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} · LLM 推理优化</title>
<meta name="description" content="{html.escape(description)}">
<link rel="stylesheet" href="{root_prefix}assets/blog.css?v={ASSET_V}">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='7' fill='%2318181b'/%3E%3Ctext x='16' y='22' font-family='Menlo,monospace' font-size='17' font-weight='600' fill='%23fafafa' text-anchor='middle'%3E%CE%BB%3C/text%3E%3C/svg%3E">
</head>
<body{body_cls}>
{nav}
{main_html}
<script src="{root_prefix}assets/blog.js?v={ASSET_V}"></script>
</body>
</html>"""


def build_chapter(chap, idx):
    src = (ROOT / chap["file"]).read_text(encoding="utf-8")
    md = md_converter()
    body = md.convert(normalize_lists(src))
    body = strip_gifs(body)
    body = inject_animations(body, chap["file"])
    body = split_and_render_answers(body)
    body = rewrite_links(body)
    body = wrap_tables(body)
    body = style_callouts(body)

    prev_link = ""
    next_link = ""
    if idx > 0:
        p = CHAPTERS[idx - 1]
        prev_link = (
            f'<a class="pager-card" href="{p["file"].replace(".md", ".html")}">'
            f'<span class="pager-dir">← 上一章</span><span class="pager-title">{p["num"]} · {p["title"]}</span></a>'
        )
    if idx < len(CHAPTERS) - 1:
        n = CHAPTERS[idx + 1]
        next_link = (
            f'<a class="pager-card pager-next" href="{n["file"].replace(".md", ".html")}">'
            f'<span class="pager-dir">下一章 →</span><span class="pager-title">{n["num"]} · {n["title"]}</span></a>'
        )
    pager = f'<nav class="pager">{prev_link}{next_link}</nav>'

    header = (
        f'<div class="chapter-head">'
        f'<div class="breadcrumb"><a href="../index.html">首页</a><span class="sep">/</span>第 {chap["num"]} 章</div>'
        f"</div>"
    )
    full_body = header + body + pager
    toc = toc_html(md.toc_tokens)
    return page_shell(
        f'{chap["num"]} · {chap["title"]}',
        chap["desc"],
        full_body,
        "../",
        toc,
    )


def build_index():
    cards = []
    for chap in CHAPTERS:
        cards.append(
            f'<a class="chapter-card" href="chapters/{chap["file"].replace(".md", ".html")}">'
            f'<div class="card-top"><span class="card-num">{chap["num"]}</span></div>'
            f'<div class="card-title">{chap["title"]}</div>'
            f'<div class="card-sub">{chap["subtitle"]}</div>'
            f'<div class="card-desc">{chap["desc"]}</div>'
            f'<span class="card-cta">开始阅读 →</span></a>'
        )
    cards_html = '<div class="chapter-grid">' + "".join(cards) + "</div>"

    learn_items = [
        "LLM 推理的两个阶段（Prefill / Decode）及其截然不同的性能特征",
        "为什么推理是 memory-bound 而非 compute-bound",
        "KV Cache 的原理、痛点与优化（PagedAttention 等）",
        "量化的数学原理与工程实践（GPTQ / AWQ / FP8）",
        "并行策略：Tensor Parallelism / Pipeline Parallelism",
        "进阶技术：Speculative Decoding / FlashAttention / Kernel Fusion",
        "主流推理框架对比（vLLM / TGI / TensorRT-LLM / SGLang）",
        "推理集群与基础设施：Autoscaling、负载均衡、GPU 资源管理、成本优化",
    ]
    learn_html = '<ul class="learn-grid">' + "".join(
        f'<li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15"><path d="M20 6L9 17l-5-5"/></svg>{html.escape(t)}</li>'
        for t in learn_items
    ) + "</ul>"

    body = f"""
<section class="hero">
  <img class="hero-img" src="assets/07908e56-e128-4457-9d02-d8fb57b41c04.jpeg" alt="LLM 推理优化封面图">
  <div class="hero-overlay">
    <h1>LLM 推理优化<br><span class="h1-mid">从原理到生产部署</span></h1>
    <p class="hero-sub">从「为什么慢」出发，逐层拆解 KV Cache、量化、并行与调度，把从单卡到推理集群的核心优化手段讲透。</p>
    <div class="hero-actions">
      <a class="btn btn-primary" href="chapters/01_inference_fundamentals.html">从第 01 章开始</a>
      <a class="btn btn-outline" href="#route">查看学习路线</a>
    </div>
  </div>
</section>

<section>
  <h2 class="section-title">你会学到什么</h2>
  {learn_html}
</section>

<section id="route">
  <h2 class="section-title">学习路线</h2>
  {cards_html}
</section>

<section>
  <h2 class="section-title">建议学习方式</h2>
  <ol class="howto">
    <li>按顺序读，每章都有「算法同学容易混淆的直觉」提示。</li>
    <li>动画可以反复看：它们把每章最核心、最难靠文字建立的直觉做了可视化。</li>
    <li>每章末尾有思考题，建议自己想一下再看答案。</li>
    <li>涉及代码的地方会给出最小可运行示例（PyTorch）。</li>
    <li>第 7 章涉及 K8s / 云服务，建议结合实际部署经验理解。</li>
  </ol>
</section>
"""
    return page_shell("LLM 推理优化学习路线", "从为什么慢出发，逐层拆解 LLM 推理优化：KV Cache、量化、并行、框架与集群。", body, "", home=True)


def main():
    CHAPTERS_OUT.mkdir(parents=True, exist_ok=True)
    for idx, chap in enumerate(CHAPTERS):
        out = build_chapter(chap, idx)
        (CHAPTERS_OUT / chap["file"].replace(".md", ".html")).write_text(out, encoding="utf-8")
        print(f"built chapters/{chap['file'].replace('.md', '.html')}")
    (SITE / "index.html").write_text(build_index(), encoding="utf-8")
    print("built index.html")


if __name__ == "__main__":
    main()
