#!/usr/bin/env python3
"""Genera terminal.svg: whoami + lenguajes más usados + en qué estás trabajando ahora."""
import json
import os
import urllib.request
from html import escape

USER = os.environ.get("GH_USER", "TU_USUARIO")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUTPUT = "terminal.svg"

PROMPT_USER = "atjos"
PROMPT_HOST = "tyrell"
WHOAMI = "atjos"
TOP_N = 4
EXCLUDE = set()
MAX_CHARS = 62                 # largo máximo del texto de "now"

BG, BAR_TOP, TRACK = "#021a2e", "#022b4a", "#053a63"
C_TEXT, C_ACCENT, C_DIM, C_MUTED = "#a8d5e4", "#8cc1d9", "#4b94b2", "#2e6f98"
RANK_COLORS = ["#a8d5e4", "#8cc1d9", "#66a5c3", "#4b94b2", "#3481a3", "#2e6f98"]

CHAR_W, FS, LH, X0, W = 9.6, 16, 24, 28, 820
PROMPT_TXT = f"{PROMPT_USER}@{PROMPT_HOST}:~$ "

GQL = """query($login:String!){user(login:$login){
  repositories(ownerAffiliations:OWNER,isFork:false,first:100,orderBy:{field:PUSHED_AT,direction:DESC}){
    nodes{name primaryLanguage{name}
      defaultBranchRef{target{... on Commit{messageHeadline}}}
      languages(first:10,orderBy:{field:SIZE,direction:DESC}){edges{size node{name}}}}}}}"""


def cut(s, n=MAX_CHARS):
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[:n - 1] + "…"


def fetch_data():
    totals, current = {}, None
    try:
        req = urllib.request.Request(
            "https://api.github.com/graphql",
            data=json.dumps({"query": GQL, "variables": {"login": USER}}).encode(),
            headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            nodes = json.load(r)["data"]["user"]["repositories"]["nodes"]
        for repo in nodes:
            # el repo de perfil se ignora: el propio workflow le hace commit
            if current is None and repo["name"].lower() != USER.lower():
                ref = repo.get("defaultBranchRef") or {}
                current = {
                    "name": repo["name"],
                    "lang": (repo.get("primaryLanguage") or {}).get("name", "—"),
                    "commit": (ref.get("target") or {}).get("messageHeadline", "—"),
                }
            for e in repo["languages"]["edges"]:
                name = e["node"]["name"]
                if name not in EXCLUDE:
                    totals[name] = totals.get(name, 0) + e["size"]
    except Exception as ex:
        print("No se pudieron leer los datos:", ex)
    if not totals:
        totals = {"Python": 60, "MATLAB": 25, "TeX": 15}
    total = sum(totals.values())
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:TOP_N]
    return [(n, s * 100 / total) for n, s in ranked], current


def prompt_tspans():
    return (f'<tspan fill="{C_TEXT}">{escape(PROMPT_USER)}</tspan><tspan fill="{C_DIM}">@</tspan>'
            f'<tspan fill="{C_ACCENT}">{escape(PROMPT_HOST)}</tspan><tspan fill="{C_DIM}">:~$ </tspan>')


def typed(cmd, y, start, clip_id, cps=0.04):
    """Línea con prompt que se escribe letra por letra."""
    n = len(PROMPT_TXT) + len(cmd)
    w = n * CHAR_W
    dur = max(n * cps, 0.1)
    values = ";".join(f"{i * CHAR_W:.1f}" for i in range(n + 1))
    clip = (f'<clipPath id="{clip_id}"><rect x="{X0}" y="{y - 18}" height="26" width="0">'
            f'<animate attributeName="width" values="{values}" dur="{dur:.2f}s" begin="{start:.2f}s" '
            f'fill="freeze" calcMode="discrete"/></rect></clipPath>')
    txt = (f'<text x="{X0}" y="{y}" textLength="{w:.1f}" lengthAdjust="spacingAndGlyphs" '
           f'clip-path="url(#{clip_id})" xml:space="preserve">{prompt_tspans()}'
           f'<tspan fill="{C_TEXT}">{escape(cmd)}</tspan></text>')
    return clip + txt, start + dur


def fade(inner, start, dur=0.25):
    return (f'<g opacity="0">{inner}<animate attributeName="opacity" from="0" to="1" '
            f'dur="{dur}s" begin="{start:.2f}s" fill="freeze"/></g>')


def build_svg(langs, current):
    parts, y, t = [], 74, 0.5

    # whoami
    c, t = typed("whoami", y, t, "c1")
    parts.append(c)
    y += LH
    parts.append(fade(f'<text x="{X0}" y="{y}" fill="{C_ACCENT}" font-weight="bold" xml:space="preserve">'
                      f'{escape(WHOAMI)}</text>', t + 0.15))
    t += 0.5

    # lenguajes más usados
    y += LH + 14
    c, t = typed("top-langs", y, t, "c2", cps=0.035)
    parts.append(c)
    t += 0.3

    bar_x, bar_w = X0 + 130, 390
    y += 8
    for i, (name, pct) in enumerate(langs):
        y += 28
        color = RANK_COLORS[min(i, len(RANK_COLORS) - 1)]
        fill_w = max(pct / 100 * bar_w, 4)
        inner = (
            f'<text x="{X0}" y="{y}" fill="{color}" xml:space="preserve">{escape(name)}</text>'
            f'<rect x="{bar_x}" y="{y - 12}" width="{bar_w}" height="12" rx="3" fill="{TRACK}"/>'
            f'<rect x="{bar_x}" y="{y - 12}" width="0" height="12" rx="3" fill="{color}">'
            f'<animate attributeName="width" from="0" to="{fill_w:.1f}" dur="0.7s" begin="{t:.2f}s" fill="freeze"/></rect>'
            f'<text x="{bar_x + bar_w + 16}" y="{y}" fill="{C_TEXT}">{pct:.1f}%</text>')
        parts.append(fade(inner, t, 0.2))
        t += 0.25

    # trabajando ahora
    if current:
        y += LH + 14
        c, t = typed("now", y, t + 0.2, "c3")
        parts.append(c)
        t += 0.3
        rows = [("project", current["name"], C_ACCENT, "bold"),
                ("lenguage", current["lang"], C_TEXT, "normal"),
                ("commit", current["commit"], C_TEXT, "normal")]
        for label, value, color, weight in rows:
            y += LH
            parts.append(fade(
                f'<text x="{X0}" y="{y}" fill="{C_MUTED}" xml:space="preserve">{label}</text>'
                f'<text x="{bar_x}" y="{y}" fill="{color}" font-weight="{weight}" '
                f'xml:space="preserve">{escape(cut(value))}</text>', t))
            t += 0.2

    # prompt final con cursor parpadeando
    y += 40
    parts.append(fade(f'<text x="{X0}" y="{y}" xml:space="preserve">{prompt_tspans()}</text>', t))
    cursor_x = X0 + len(PROMPT_TXT) * CHAR_W
    parts.append(
        f'<rect x="{cursor_x:.1f}" y="{y - 14}" width="9" height="18" fill="{C_TEXT}" opacity="0">'
        f'<animate attributeName="opacity" values="0;1" dur="1s" begin="{t + 0.3:.2f}s" '
        f'repeatCount="indefinite" calcMode="discrete"/></rect>')

    height = y + 30
    chrome = (
        f'<rect width="{W}" height="{height}" fill="{BG}"/>'
        f'<rect width="{W}" height="38" fill="{BAR_TOP}"/>'
        f'<circle cx="22" cy="19" r="6" fill="{C_TEXT}"/><circle cx="42" cy="19" r="6" fill="{C_DIM}"/>'
        f'<circle cx="62" cy="19" r="6" fill="{C_MUTED}"/>'
        f'<text x="{W // 2}" y="24" text-anchor="middle" font-size="13" fill="{C_DIM}">'
        f'{escape(PROMPT_USER)}@{escape(PROMPT_HOST)}: ~ — bash</text>')

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" viewBox="0 0 {W} {height}">'
        f'<style>text{{font-family:"Cascadia Code","JetBrains Mono",Consolas,"DejaVu Sans Mono",monospace;'
        f'font-size:{FS}px}}</style>'
        f'<clipPath id="card"><rect width="{W}" height="{height}" rx="12"/></clipPath>'
        f'<g clip-path="url(#card)">{chrome}{"".join(parts)}</g>'
        f'<rect x="0.5" y="0.5" width="{W - 1}" height="{height - 1}" rx="12" fill="none" stroke="{TRACK}"/></svg>')


if __name__ == "__main__":
    langs, current = fetch_data()
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(build_svg(langs, current))
    print("Generado", OUTPUT)
