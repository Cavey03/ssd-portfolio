"""Inline SVG and HTML diagrams for the study summaries.

Every figure draws with CSS variables (--stroke, --tint, --ink, --muted, --line, --paper) so it follows the
page theme, the unit colour and light/dark mode automatically.
"""
import math
import random


def _svg(w, h, body, label):
    return (f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{label}" '
            f'xmlns="http://www.w3.org/2000/svg">{body}</svg>')


def _t(x, y, s, cls="", anchor="middle", size=None):
    st = f' style="font-size:{size}px"' if size else ""
    return f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" class="{cls}"{st}>{s}</text>'


def net(layers, left=None, right=None, names=None, back=False, label="Network diagram"):
    """Columns of nodes, fully connected. left/right: labels for the first/last column."""
    lm = 74 if left else 24
    rm = 74 if right else 24
    top = 34 if back else 14
    w = 380
    gap = 44
    rows = max(layers)
    h = top + rows * gap + (26 if names else 8) + (22 if back else 0)
    xs = [lm + i * (w - lm - rm) / (len(layers) - 1) for i in range(len(layers))]

    def ys(n):
        span = (n - 1) * gap
        mid = top + (rows * gap) / 2 - gap / 2 + 6
        return [mid - span / 2 + j * gap for j in range(n)]

    out = []
    for i in range(len(layers) - 1):
        for y1 in ys(layers[i]):
            for y2 in ys(layers[i + 1]):
                out.append(f'<line class="ed" x1="{xs[i]:.1f}" y1="{y1:.1f}" x2="{xs[i+1]:.1f}" y2="{y2:.1f}"/>')
    for i, n in enumerate(layers):
        for j, y in enumerate(ys(n)):
            out.append(f'<circle class="nd" cx="{xs[i]:.1f}" cy="{y:.1f}" r="13"/>')
            if i == 0 and left:
                out.append(_t(xs[i] - 20, y + 3.5, left[j], "lbl", "end"))
            if i == len(layers) - 1 and right:
                out.append(_t(xs[i] + 20, y + 3.5, right[j], "lbl", "start"))
    if names:
        yb = top + rows * gap + 14
        for i, nm in enumerate(names):
            out.append(_t(xs[i], yb, nm, "cap"))
    if back:
        out.append(f'<path class="arw" d="M{xs[0]:.0f} 12 H{xs[-1]-6:.0f}" marker-end="url(#ah)"/>')
        out.append(_t((xs[0] + xs[-1]) / 2, 9, "forward propagation: predict", "cap"))
        yb = h - 10
        out.append(f'<path class="arw dash" d="M{xs[-1]:.0f} {yb} H{xs[0]+6:.0f}" marker-end="url(#ah)"/>')
        out.append(_t((xs[0] + xs[-1]) / 2, yb - 5, "backpropagation: error flows back", "cap"))
    defs = ('<defs><marker id="ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" '
            'orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10z" class="ahd"/></marker></defs>')
    return _svg(w, h, defs + "".join(out), label)


def neuron():
    out = []
    ins = [("x₁", "w₁"), ("x₂", "w₂"), ("x₃", "w₃")]
    for k, (x, wl) in enumerate(ins):
        y = 26 + k * 44
        out.append(f'<line class="ed strong" x1="44" y1="{y}" x2="176" y2="70"/>')
        out.append(f'<circle class="nd" cx="34" cy="{y}" r="12"/>')
        out.append(_t(34, y + 4, x, "lbl"))
        out.append(_t(108, (y + 70) / 2 - 5, wl, "cap"))
    out.append('<circle class="nd" cx="190" cy="70" r="20"/>')
    out.append(_t(190, 76, "Σ", "lbl", size=17))
    out.append('<line class="ed strong" x1="210" y1="70" x2="246" y2="70"/>')
    out.append('<rect class="nd" x="246" y="54" width="40" height="32" rx="3"/>')
    out.append(_t(266, 75, "f", "lbl", size=15))
    out.append('<line class="ed strong" x1="286" y1="70" x2="322" y2="70"/>')
    out.append('<circle class="nd" cx="334" cy="70" r="12"/>')
    out.append(_t(334, 74, "y", "lbl"))
    out.append(_t(190, 112, "weighted sum", "cap"))
    out.append(_t(266, 112, "activation", "cap"))
    out.append(_t(334, 112, "output", "cap"))
    return _svg(370, 124, "".join(out), "A single neuron: inputs times weights, summed, then an activation function")


def _plot(fn, x0, x1, y0, y1, title, w=200, h=130, pts=160):
    px = lambda x: 10 + (x - x0) / (x1 - x0) * (w - 20)
    py = lambda y: h - 22 - (y - y0) / (y1 - y0) * (h - 40)
    out = [f'<line class="ax" x1="10" y1="{py(0):.1f}" x2="{w-10}" y2="{py(0):.1f}"/>',
           f'<line class="ax" x1="{px(0):.1f}" y1="12" x2="{px(0):.1f}" y2="{h-22}"/>']
    p = []
    for i in range(pts + 1):
        x = x0 + (x1 - x0) * i / pts
        p.append(f"{px(x):.1f},{py(max(y0, min(y1, fn(x)))):.1f}")
    out.append(f'<polyline class="cv" points="{" ".join(p)}"/>')
    out.append(_t(w / 2, h - 6, title, "lbl"))
    return _svg(w, h, "".join(out), title)


def activations():
    sig = lambda x: 1 / (1 + math.exp(-x))
    plots = [
        _plot(lambda x: max(0.0, x), -3, 3, -1.2, 3, "relu: max(0, x)"),
        _plot(sig, -6, 6, -1.1, 1.1, "sigmoid: 0 to 1"),
        _plot(math.tanh, -4, 4, -1.1, 1.1, "tanh: −1 to 1"),
    ]
    return '<div class="plots">' + "".join(plots) + "</div>"


def _bowl(inp, steps, w0, wmin, wmax, emax, title, w=260, h=170):
    goal = 0.8
    err = lambda wt: (inp * wt - goal) ** 2
    px = lambda x: 14 + (x - wmin) / (wmax - wmin) * (w - 28)
    py = lambda y: h - 26 - min(y, emax) / emax * (h - 46)
    out = [f'<line class="ax" x1="14" y1="{h-26}" x2="{w-14}" y2="{h-26}"/>']
    pts = [f"{px(wmin + (wmax-wmin)*i/200):.1f},{py(err(wmin + (wmax-wmin)*i/200)):.1f}" for i in range(201)]
    out.append(f'<polyline class="cv soft" points="{" ".join(pts)}"/>')
    wt = w0
    path = []
    for k in range(steps):
        path.append((wt, err(wt)))
        wt = wt - inp * (inp * wt - goal)
    d = " ".join(f"{'M' if i == 0 else 'L'}{px(a):.1f} {py(b):.1f}" for i, (a, b) in enumerate(path))
    out.append(f'<path class="arw thin" d="{d}"/>')
    for i, (a, b) in enumerate(path):
        out.append(f'<circle class="pt" cx="{px(a):.1f}" cy="{py(b):.1f}" r="{4.2 if i == 0 else 3.4}"/>')
    out.append(_t(w / 2, h - 8, title, "lbl"))
    out.append(_t(18, 16, "error", "cap", "start"))
    out.append(_t(w - 14, h - 32, "weight →", "cap", "end"))
    return _svg(w, h, "".join(out), title)


def bowls():
    a = _bowl(0.5, 7, 0.5, 0, 3.2, 0.7, "input 0.5: steps roll downhill")
    b = _bowl(2.0, 4, 0.5, -3, 3.6, 34, "input 2, no alpha: overshoots, diverges")
    return '<div class="plots two">' + a + b + "</div>"


def overfit():
    w, h = 340, 170
    px = lambda x: 34 + x / 100 * (w - 60)
    py = lambda y: h - 28 - (y - 0.0) / 1.0 * (h - 48)
    tr = [(x, 1 - 0.92 * math.exp(-x / 14)) for x in range(0, 101, 2)]
    te = [(x, (0.80 * (1 - math.exp(-x / 7))) if x <= 20 else 0.80 * (1 - math.exp(-20 / 7)) - (x - 20) * 0.0011)
          for x in range(0, 101, 2)]
    line = lambda s: " ".join(f"{px(a):.1f},{py(b):.1f}" for a, b in s)
    out = [f'<line class="ax" x1="34" y1="{h-28}" x2="{w-20}" y2="{h-28}"/>',
           f'<line class="ax" x1="34" y1="14" x2="34" y2="{h-28}"/>',
           f'<polyline class="cv" points="{line(tr)}"/>',
           f'<polyline class="cv dash" points="{line(te)}"/>',
           f'<line class="ax dash" x1="{px(20):.1f}" y1="18" x2="{px(20):.1f}" y2="{h-28}"/>',
           _t(px(20) + 5, h - 36, "best point to stop", "cap", "start"),
           _t(w - 22, py(tr[-1][1]) - 6, "training accuracy", "lbl", "end"),
           _t(w - 22, py(te[-1][1]) + 14, "test accuracy", "lbl", "end"),
           _t((w + 34) / 2, h - 8, "training iterations →", "cap"),
           _t(12, 18, "acc", "cap", "start")]
    return _svg(w, h, "".join(out), "Training accuracy keeps rising while test accuracy peaks and then falls")


def conv():
    n, k, c = 8, 3, 13
    img = [[1 if (r + q == 7 or r == 7) else 0 for q in range(n)] for r in range(n)]
    ker = [[0, 0, 1], [0, 1, 0], [1, 0, 0]]
    outm = [[sum(ker[a][b] * img[i + a][j + b] for a in range(k) for b in range(k)) for j in range(n - k + 1)]
            for i in range(n - k + 1)]
    wi, wj = 2, 3
    out = []
    ox, oy = 8, 18
    for r in range(n):
        for q in range(n):
            cls = "cell on" if img[r][q] else "cell"
            out.append(f'<rect class="{cls}" x="{ox+q*c}" y="{oy+r*c}" width="{c}" height="{c}"/>')
    out.append(f'<rect class="win" x="{ox+wj*c}" y="{oy+wi*c}" width="{k*c}" height="{k*c}"/>')
    out.append(_t(ox + n * c / 2, 12, "input 8×8", "cap"))
    kx = ox + n * c + 34
    ky = oy + (n * c - k * c) / 2
    for r in range(k):
        for q in range(k):
            cls = "cell on" if ker[r][q] else "cell"
            out.append(f'<rect class="{cls}" x="{kx+q*c}" y="{ky+r*c}" width="{c}" height="{c}"/>')
    out.append(_t(kx + k * c / 2, ky - 6, "kernel 3×3", "cap"))
    out.append(_t(kx - 16, ky + k * c / 2 + 4, "×", "lbl", size=14))
    rx = kx + k * c + 40
    ry = oy + c
    out.append(_t(rx - 20, ry + 3 * c + 4, "→", "lbl", size=15))
    m = n - k + 1
    for r in range(m):
        for q in range(m):
            v = outm[r][q] / 3
            out.append(f'<rect class="cell" x="{rx+q*c}" y="{ry+r*c}" width="{c}" height="{c}"/>')
            if v:
                out.append(f'<rect class="heat" x="{rx+q*c}" y="{ry+r*c}" width="{c}" height="{c}" '
                           f'style="opacity:{0.2+0.8*v:.2f}"/>')
    out.append(f'<rect class="win" x="{rx+wj*c}" y="{ry+wi*c}" width="{c}" height="{c}"/>')
    out.append(_t(rx + m * c / 2, ry - 6, "output 6×6", "cap"))
    w = rx + m * c + 10
    return _svg(w, oy + n * c + 6, "".join(out),
                "A 3 by 3 kernel slides over an 8 by 8 image and produces a 6 by 6 output")


def pool():
    vals = [[1, 3, 2, 0], [5, 6, 1, 2], [0, 2, 7, 4], [1, 1, 3, 8]]
    c = 30
    out = []
    ox, oy = 8, 20
    for r in range(4):
        for q in range(4):
            blk = (r // 2) * 2 + q // 2
            out.append(f'<rect class="cell b{blk}" x="{ox+q*c}" y="{oy+r*c}" width="{c}" height="{c}"/>')
            mx = max(vals[(r // 2) * 2 + a][(q // 2) * 2 + b] for a in range(2) for b in range(2))
            cls = "lbl strong" if vals[r][q] == mx else "cap"
            out.append(_t(ox + q * c + c / 2, oy + r * c + c / 2 + 4, vals[r][q], cls, size=12))
    out.append(_t(ox + 2 * c, 13, "feature map 4×4", "cap"))
    out.append(_t(ox + 4 * c + 26, oy + 2 * c + 5, "→", "lbl", size=16))
    rx = ox + 4 * c + 52
    ry = oy + c
    for r in range(2):
        for q in range(2):
            blk = r * 2 + q
            mx = max(vals[r * 2 + a][q * 2 + b] for a in range(2) for b in range(2))
            out.append(f'<rect class="cell b{blk}" x="{rx+q*c}" y="{ry+r*c}" width="{c}" height="{c}"/>')
            out.append(_t(rx + q * c + c / 2, ry + r * c + c / 2 + 4, mx, "lbl strong", size=12))
    out.append(_t(rx + c, ry - 7, "2×2 max pool", "cap"))
    return _svg(rx + 2 * c + 10, oy + 4 * c + 8, "".join(out),
                "Max pooling keeps the largest value in each 2 by 2 block")


def kmeans():
    rng = random.Random(7)
    centres = [(70, 60), (190, 50), (140, 130)]
    marks = []
    for ci, (cx, cy) in enumerate(centres):
        for _ in range(16):
            x, y = rng.gauss(cx, 17), rng.gauss(cy, 14)
            if ci == 0:
                marks.append(f'<circle class="pt" cx="{x:.1f}" cy="{y:.1f}" r="3.6"/>')
            elif ci == 1:
                marks.append(f'<circle class="ptw" cx="{x:.1f}" cy="{y:.1f}" r="3.6"/>')
            else:
                marks.append(f'<rect class="pt" x="{x-3.2:.1f}" y="{y-3.2:.1f}" width="6.4" height="6.4"/>')
    for cx, cy in centres:
        marks.append(f'<path class="cen" d="M{cx-7} {cy-7} L{cx+7} {cy+7} M{cx+7} {cy-7} L{cx-7} {cy+7}"/>')
    marks.append(_t(130, 176, "3 clusters found; × = centroid (mean of its points)", "cap"))
    return _svg(260, 184, "".join(marks), "k-means: points grouped into three clusters around centroids")


def svm():
    rng = random.Random(3)
    out = []
    a = [(rng.uniform(20, 120), rng.uniform(20, 150)) for _ in range(30)]
    b = [(rng.uniform(140, 250), rng.uniform(20, 150)) for _ in range(30)]
    a = [(x, y) for x, y in a if x + 0.3 * (y - 85) < 104][:14]
    b = [(x, y) for x, y in b if x + 0.3 * (y - 85) > 160][:14]
    a += [(98, 70)]
    b += [(165, 100)]
    line = lambda off: f'M{132+off+0.3*65:.1f} 20 L{132+off-0.3*65:.1f} 150'
    out.append(f'<path class="arw thin dash" d="{line(-33)}"/>')
    out.append(f'<path class="arw thin dash" d="{line(33)}"/>')
    out.append(f'<path class="cv" d="{line(0)}"/>')
    for x, y in a:
        out.append(f'<circle class="pt" cx="{x:.1f}" cy="{y:.1f}" r="3.6"/>')
    for x, y in b:
        out.append(f'<rect class="ptw" x="{x-3.4:.1f}" y="{y-3.4:.1f}" width="6.8" height="6.8"/>')
    for x, y in [(98, 70), (165, 100)]:
        out.append(f'<circle class="ring" cx="{x}" cy="{y}" r="8"/>')
    out.append(_t(135, 172, "widest margin; ringed points = support vectors", "cap"))
    return _svg(270, 180, "".join(out), "A support vector classifier separating two classes with the widest margin")


def nested():
    out = ['<rect class="nd soft" x="6" y="6" width="300" height="128" rx="10"/>',
           _t(20, 26, "Artificial intelligence", "lbl", "start"),
           '<rect class="nd" x="40" y="36" width="250" height="88" rx="8"/>',
           _t(54, 56, "Machine learning", "lbl", "start"),
           '<rect class="nd strongfill" x="80" y="66" width="190" height="46" rx="6"/>',
           _t(175, 94, "Deep learning (neural networks)", "lbl")]
    return _svg(312, 140, "".join(out), "Deep learning inside machine learning inside artificial intelligence")


def flow(steps, loop=None):
    """steps: list of (title, sub) or (title, sub, 'x') for a not-in-Trask step."""
    parts = []
    for i, s in enumerate(steps):
        x = len(s) > 2 and s[2] == "x"
        parts.append(f'<div class="step{" xstep" if x else ""}"><b>{s[0]}</b><span>{s[1]}</span></div>')
        if i < len(steps) - 1:
            parts.append('<div class="arrow" aria-hidden="true">→</div>')
    lp = f'<div class="loop">↺ {loop}</div>' if loop else ""
    return f'<div class="flow">{"".join(parts)}</div>{lp}'


def splitbar():
    return ('<div class="split" role="img" aria-label="Typical split: 70 percent training, 15 validation, 15 test">'
            '<div style="flex:70"><b>Training</b><span>~70% · fit the weights</span></div>'
            '<div style="flex:15"><b>Val</b><span>~15% · tune</span></div>'
            '<div style="flex:15"><b>Test</b><span>~15% · score once</span></div></div>'
            '<p class="split-cap">Typical proportions (not from Trask; the book uses separate train and test sets)</p>')


def transfer():
    return ('<div class="tl">'
            '<div class="tl-row"><span class="tl-k">Pretrained</span>'
            '<div class="blk">edges</div><div class="blk">textures</div><div class="blk">shapes</div>'
            '<div class="blk">objects</div><div class="blk head">1000 ImageNet classes</div></div>'
            '<div class="tl-row"><span class="tl-k">Transferred</span>'
            '<div class="blk frozen">edges</div><div class="blk frozen">textures</div><div class="blk frozen">shapes</div>'
            '<div class="blk">objects</div><div class="blk head new">22 glitch classes</div></div>'
            '<p class="tl-cap">Hatched = frozen (copied, not trained). Plain = retrained or fine-tuned. '
            'Highlighted = new output layer.</p></div>')
