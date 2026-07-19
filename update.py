#!/usr/bin/env python3
"""
Regenerates dark.svg and light.svg — a terminal "neofetch" style profile card
for github.com/yellowflash011.

Live GitHub stats (repos, stars, commits, followers) are pulled from the
from the GitHub API when a token is present (the GitHub Action passes GITHUB_TOKEN).
Run locally with no token/network and it falls back to sensible defaults so the
SVGs always regenerate cleanly.

    python update.py
"""

import os
import json
import urllib.request
import urllib.error

USERNAME = "yellowflash011"

# ---- identity / content (edit these freely) --------------------------------
IDENTITY = {
    "host":     "sargodha",
    "user":     "hussain",
    "fields": [
        ("Subject", "Hussain Nazir Awan"),
        ("Role",    "Full Stack Web Developer"),
        ("Focus",   "Software Engineer"),
        ("Origin",  "Sargodha, Pakistan"),
        ("Status",  "open to work"),
    ],
    "stack": [
        ("Core",  "JavaScript · TypeScript"),
        ("Front", "React · Next.js · Three.js / WebGL"),
        ("Back",  "Node.js · Express · REST APIs"),
        ("Data",  "PostgreSQL · MongoDB"),
        ("Tools", "Git · Vite · Tailwind · Vercel"),
    ],
    "contact": [
        ("Web",    "hussain-nazir.vercel.app"),
        ("Mail",   "hnazeer566@gmail.com"),
        ("Linked", "in/hussain-nazir"),
        ("GitHub", "@yellowflash011"),
    ],
}

DEFAULTS = {
    "repos": 12, "stars": 8, "commits": 240, "followers": 5,
}

# ---- theme palettes --------------------------------------------------------
THEMES = {
    "dark": {
        "bg": "#0d1117", "border": "#1f2630",
        "accent": "#F5C518", "accent2": "#FCD34D",
        "key": "#F5C518", "value": "#c9d1d9", "muted": "#6e7681",
        "title": "#e6edf3", "add": "#3fb950", "del": "#f85149",
        "fill": "#F5C518", "track": "#21262d",
        "dot1": "#ff5f56", "dot2": "#ffbd2e", "dot3": "#27c93f",
    },
    "light": {
        "bg": "#ffffff", "border": "#d0d7de",
        "accent": "#9a6700", "accent2": "#bf8700",
        "key": "#9a6700", "value": "#1f2328", "muted": "#57606a",
        "title": "#1f2328", "add": "#1a7f37", "del": "#cf222e",
        "fill": "#bf8700", "track": "#eaeef2",
        "dot1": "#ff5f56", "dot2": "#ffbd2e", "dot3": "#27c93f",
    },
}

# solid-block letterforms — fallback if portrait.txt is missing
MONOGRAM = [
    "██    ██   ██    ██",
    "██    ██   ███   ██",
    "██    ██   ████  ██",
    "████████   ██ ██ ██",
    "████████   ██  ████",
    "██    ██   ██   ███",
    "██    ██   ██    ██",
]


def load_portrait():
    """ASCII portrait rows produced by portrait.py; None if not generated."""
    try:
        with open("portrait.txt", encoding="utf-8") as f:
            rows = [ln.rstrip("\n") for ln in f]
        while rows and not rows[-1].strip():
            rows.pop()
        return rows or None
    except FileNotFoundError:
        return None

FONT = ("ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, "
        "'Liberation Mono', 'Courier New', monospace")
RENDER_SCALE = 2.0    # high-res canvas — sharper on retina / GitHub
PORTRAIT_FS  = 11     # portrait glyph size (base, before scale; was 8)
WIDTH_BASE   = 1380   # wider card so the enlarged portrait fits
RIGHT_X_BASE = 630    # pushed right to make room for the portrait
FS = round(15 * RENDER_SCALE)
LH = round(22 * RENDER_SCALE)
CHAR = 9.02 * RENDER_SCALE


# ---- GitHub API ------------------------------------------------------------
def _api(url, token, graphql=None):
    headers = {"User-Agent": USERNAME, "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if graphql is not None:
        url = "https://api.github.com/graphql"
        data = json.dumps({"query": graphql}).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers,
                                 method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def fetch_stats():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    try:
        user = _api(f"https://api.github.com/users/{USERNAME}", token)
        followers = user.get("followers", 0)

        repos, stars = [], 0
        page = 1
        while True:
            batch = _api(
                f"https://api.github.com/users/{USERNAME}/repos"
                f"?per_page=100&page={page}&type=owner", token)
            if not batch:
                break
            repos.extend(batch)
            page += 1
            if len(batch) < 100:
                break

        owned = [r for r in repos if not r.get("fork")]
        for r in owned:
            stars += r.get("stargazers_count", 0)
        repo_count = len(owned)

        # commits (this year) via GraphQL — needs a token
        commits = DEFAULTS["commits"]
        if token:
            try:
                q = ('{ user(login: "%s") { contributionsCollection { '
                     'totalCommitContributions restrictedContributionsCount } } }'
                     % USERNAME)
                res = _api("", token, graphql=q)
                cc = res["data"]["user"]["contributionsCollection"]
                commits = (cc["totalCommitContributions"]
                           + cc["restrictedContributionsCount"])
            except Exception:
                pass

        return {"repos": repo_count, "stars": stars, "commits": commits,
                "followers": followers}
    except Exception as e:
        print("stats fetch failed, using defaults:", e)
        return DEFAULTS


# ---- SVG rendering ---------------------------------------------------------
def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def build_lines(stats):
    """Return list of lines; each line is [(text, color_key), ...]."""
    L = []
    user, host = IDENTITY["user"], IDENTITY["host"]
    handle = f"{user}@{host}"
    L.append([(user, "accent"), ("@", "muted"), (host, "accent2")])
    L.append([("─" * len(handle), "muted")])
    L.append([("", "muted")])

    def kv(k, v, kcol="key"):
        return [(f" {k:<8}", kcol), (": ", "muted"), (v, "value")]

    def title(t):
        return [(" ", "muted"), (t, "accent2"),
                (" " + "─" * max(0, 22 - len(t)), "muted")]

    for k, v in IDENTITY["fields"]:
        L.append(kv(k, v))
    L.append([("", "muted")])

    L.append(title("stack"))
    for k, v in IDENTITY["stack"]:
        L.append(kv(k, v))
    L.append([("", "muted")])

    L.append(title("contact"))
    for k, v in IDENTITY["contact"]:
        L.append(kv(k, v))
    L.append([("", "muted")])

    L.append(title("github stats"))
    L.append([(" Repos    ", "key"), (": ", "muted"),
              (f"{stats['repos']:<5}", "value"),
              ("Stars    : ", "muted"), (str(stats["stars"]), "accent2")])
    L.append([(" Commits  ", "key"), (": ", "muted"),
              (f"{stats['commits']:<5}", "value"),
              ("Followers: ", "muted"), (str(stats["followers"]), "accent2")])
    return L


def render(theme_name, stats):
    c = THEMES[theme_name]
    lines = build_lines(stats)
    sc = RENDER_SCALE

    pad = round(34 * sc)
    left_x = pad + round(12 * sc)
    right_x = round(RIGHT_X_BASE * sc)
    top = round(96 * sc)          # below the window title bar
    art = load_portrait()
    n = max(len(lines), len(MONOGRAM) + 8, len(art or []))
    height = top + n * LH + round(34 * sc)
    width = round(WIDTH_BASE * sc)

    def text(x, y, segs, size=FS, weight="400"):
        spans = "".join(
            f'<tspan fill="{c[col]}">{esc(t)}</tspan>' for t, col in segs)
        return (f'<text x="{x}" y="{y}" font-size="{size}" '
                f'font-weight="{weight}" xml:space="preserve">{spans}</text>')

    parts = []
    rx = round(14 * sc)
    # window frame
    parts.append(
        f'<rect x="1" y="1" width="{width-2}" height="{height-2}" rx="{rx}" '
        f'fill="{c["bg"]}" stroke="{c["border"]}" stroke-width="1.5"/>')
    # title bar
    title_h = round(40 * sc)
    parts.append(
        f'<rect x="1" y="1" width="{width-2}" height="{title_h}" rx="{rx}" '
        f'fill="{c["bg"]}"/>')
    parts.append(f'<line x1="1" y1="{title_h + 1}" x2="{width-1}" y2="{title_h + 1}" '
                 f'stroke="{c["border"]}" stroke-width="1"/>')
    for i, dot in enumerate(("dot1", "dot2", "dot3")):
        parts.append(f'<circle cx="{round((28 + i*22) * sc)}" cy="{round(21 * sc)}" '
                     f'r="{6.5 * sc}" fill="{c[dot]}"/>')
    parts.append(
        f'<text x="{width/2}" y="{round(26 * sc)}" text-anchor="middle" '
        f'font-size="{round(13 * sc)}" fill="{c["muted"]}" xml:space="preserve">'
        f'{USERNAME} — zsh — 80×24</text>')

    # left column: ASCII portrait (falls back to the HN monogram)
    if art:
        FS_P = round(PORTRAIT_FS * sc)
        LH_P = round(PORTRAIT_FS * 1.1 * sc, 1)
        art_h = len(art) * LH_P
        ay = top + (n * LH - (art_h + 3 * LH)) / 2 + LH_P
        for i, row in enumerate(art):
            parts.append(
                f'<text x="{left_x}" y="{round(ay + i*LH_P, 1)}" font-size="{FS_P}" '
                f'fill="{c["title"]}" xml:space="preserve">{esc(row)}</text>')
        by = ay + art_h + round(26 * sc)
    else:
        mono_h = len(MONOGRAM) * LH
        my = top + (n * LH - (mono_h + 3 * LH)) / 2 + LH
        for i, row in enumerate(MONOGRAM):
            parts.append(
                f'<text x="{left_x}" y="{my + i*LH}" font-size="{FS}" '
                f'fill="{c["accent"]}" xml:space="preserve" '
                f'font-weight="700">{esc(row)}</text>')
        by = my + mono_h + round(26 * sc)

    parts.append(text(left_x, by, [("⚡ ", "accent2"),
                                    ("yellowflash011", "title")], weight="700"))
    parts.append(text(left_x, by + LH, [("─" * 22, "muted")]))
    parts.append(text(left_x, by + LH*2,
                      [("the yellow flash", "accent"),
                       ("  ·  full-stack, web", "muted")]))

    # right column: readout
    for i, segs in enumerate(lines):
        parts.append(text(right_x, top + 18 + i * LH, segs))

    body = "\n  ".join(parts)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
            f'height="{height}" viewBox="0 0 {width} {height}" '
            f'font-family="{FONT}" text-rendering="geometricPrecision" '
            f'shape-rendering="geometricPrecision">\n  {body}\n</svg>\n')


def main():
    stats = fetch_stats()
    print("stats:", stats)
    for name in ("dark", "light"):
        svg = render(name, stats)
        with open(f"{name}.svg", "w", encoding="utf-8") as f:
            f.write(svg)
        print("wrote", f"{name}.svg")


if __name__ == "__main__":
    main()
