#!/usr/bin/env python3
"""Genera assets/profile-card.svg: un panel de perfil estilo "hub" con datos reales de GitHub.

Solo usa la librería estándar de Python. Necesita un token en GITHUB_TOKEN para la API GraphQL
(en GitHub Actions alcanza con el GITHUB_TOKEN del workflow).

    python3 scripts/generate_profile_card.py                  # datos de la API
    python3 scripts/generate_profile_card.py --data datos.json  # datos de un archivo
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import math
import os
import re
import sys
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
FONT_FILE = ROOT / "assets/fonts/Inter-latin-var.woff2"
METRICS_FILE = ROOT / "assets/fonts/inter-metrics.json"

# ---------------------------------------------------------------------------
# Paleta
# ---------------------------------------------------------------------------
BG = "#000000"
CARD = "#0a0a0a"
BORDER = "#262626"
TEXT = "#fafafa"
TEXT_2 = "#d4d4d8"
MUTED = "#a1a1aa"
DIM = "#71717a"
ACCENT = "#22c55e"
HEAT = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]

LANG_COLORS = {
    "Assembly": "#6E4C13", "C": "#555555", "C#": "#178600", "C++": "#f34b7d", "CMake": "#DA3434",
    "CSS": "#663399", "Dart": "#00B4AB", "Dockerfile": "#384d54", "GDScript": "#355570",
    "Game Maker Language": "#71b417", "Go": "#00ADD8", "HLSL": "#aace60", "HTML": "#e34c26",
    "Java": "#b07219", "JavaScript": "#f1e05a", "Jupyter Notebook": "#DA5B0B", "Kotlin": "#A97BFF",
    "Lua": "#000080", "Makefile": "#427819", "Objective-C": "#438eff", "OpenSCAD": "#e5cd45",
    "PHP": "#4F5D95", "PowerShell": "#012456", "Python": "#3572A5", "Ruby": "#701516",
    "Rust": "#dea584", "Shell": "#89e051", "ShaderLab": "#222c37", "Swift": "#F05138",
    "TypeScript": "#3178c6", "Vue": "#41b883", "Zig": "#ec915c",
}

DOMAINS = {
    "Systems": {"C", "C++", "Rust", "Go", "Zig", "Assembly"},
    "Web Dev": {"JavaScript", "TypeScript", "HTML", "CSS", "Vue", "PHP", "Svelte"},
    "Game Dev": {"C#", "GDScript", "Game Maker Language", "Lua", "ShaderLab", "HLSL"},
    "Scripting": {"Python", "Jupyter Notebook", "Shell", "PowerShell", "Ruby"},
    "JVM": {"Java", "Kotlin", "Scala"},
    "Mobile": {"Swift", "Objective-C", "Dart"},
}

# ---------------------------------------------------------------------------
# Textos (en / es)
# ---------------------------------------------------------------------------
STRINGS = {
    "en": {
        "welcome": "Welcome to {name}'s Hub",
        "subtitle": "Explore their open source contributions and projects",
        "powered": "Powered by", "powered_by": "GitHub Actions",
        "repos": "TOTAL REPOS", "stars": "TOTAL STARS", "followers_up": "FOLLOWERS",
        "years": "YEARS ACTIVE", "year": "YEAR ACTIVE",
        "contributions": "Contributions", "total": "Total Contributions:",
        "last52": "Last 52 weeks of activity.",
        "core": "CORE TECHNOLOGIES", "langs": "{n} langs", "based": "Based on top {n} repos",
        "projects": "Notable Projects", "sort": "Most Stars", "follow": "Follow on GitHub",
        "joined": "Joined {month} {year}", "followers": "followers", "following": "following",
        "views": "views", "nodesc": "No description provided",
        "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "months_long": ["January", "February", "March", "April", "May", "June", "July", "August",
                        "September", "October", "November", "December"],
        "days": ["Mon", "Wed", "Fri"],
        "tags": {"Popular Creator": "Popular Creator", "Influencer": "Influencer",
                 "Rising Star": "Rising Star", "Polyglot": "Polyglot",
                 "Highly Active": "Highly Active", "Active": "Active"},
    },
    "es": {
        "welcome": "Bienvenido al Hub de {name}",
        "subtitle": "Explorá sus contribuciones open source y proyectos",
        "powered": "Impulsado por", "powered_by": "GitHub Actions",
        "repos": "REPOSITORIOS", "stars": "ESTRELLAS", "followers_up": "SEGUIDORES",
        "years": "AÑOS ACTIVO", "year": "AÑO ACTIVO",
        "contributions": "Contribuciones", "total": "Contribuciones totales:",
        "last52": "Actividad de las últimas 52 semanas.",
        "core": "TECNOLOGÍAS PRINCIPALES", "langs": "{n} lenguajes",
        "based": "Basado en los {n} repos principales",
        "projects": "Proyectos destacados", "sort": "Más estrellas", "follow": "Seguir en GitHub",
        "joined": "Se unió en {month} de {year}", "followers": "seguidores", "following": "siguiendo",
        "views": "visitas", "nodesc": "Sin descripción",
        "months": ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"],
        "months_long": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                        "septiembre", "octubre", "noviembre", "diciembre"],
        "days": ["Lun", "Mié", "Vie"],
        "tags": {"Popular Creator": "Creador Popular", "Influencer": "Influencer",
                 "Rising Star": "Estrella en Ascenso", "Polyglot": "Políglota",
                 "Highly Active": "Muy Activo", "Active": "Activo", "Systems": "Sistemas",
                 "Web Dev": "Desarrollo Web", "Mobile": "Móvil"},
    },
}

# Íconos estilo lucide (viewBox 24x24, trazo)
ICONS = {
    "folder": '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>',
    "star": '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    "building": '<rect width="16" height="20" x="4" y="2" rx="2" ry="2"/><path d="M9 22v-4h6v4"/><path d="M8 6h.01M16 6h.01M12 6h.01M12 10h.01M12 14h.01M16 10h.01M16 14h.01M8 10h.01M8 14h.01"/>',
    "pin": '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
    "calendar": '<rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
    "link": '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
    "eye": '<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
    "bookmark": '<path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"/>',
    "chevron": '<path d="m6 9 6 6 6-6"/>',
    "fork": '<circle cx="12" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><circle cx="18" cy="6" r="3"/><path d="M18 9v2c0 .6-.4 1-1 1H7c-.6 0-1-.4-1-1V9"/><path d="M12 12v3"/>',
}
GITHUB_MARK = (
    "M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 "
    "0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 "
    "0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 "
    "1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61"
    ".55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 "
    "0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z"
)

# ---------------------------------------------------------------------------
# Datos
# ---------------------------------------------------------------------------
QUERY = """
query($login: String!) {
  user(login: $login) {
    login name bio company location websiteUrl createdAt url
    avatarUrl(size: 300)
    followers { totalCount }
    following { totalCount }
    allRepos: repositories(privacy: PUBLIC, ownerAffiliations: OWNER) { totalCount }
    repositories(first: 100, privacy: PUBLIC, ownerAffiliations: OWNER, isFork: false,
                 orderBy: {field: STARGAZERS, direction: DESC}) {
      nodes {
        name description url stargazerCount forkCount isArchived pushedAt
        primaryLanguage { name color }
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
  }
}
"""

LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}


def http_get(url: str, headers: dict | None = None, data: bytes | None = None) -> tuple[bytes, str]:
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "profile-card", **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read(), resp.headers.get("Content-Type", "")


def fetch_data(login: str, token: str) -> dict:
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    raw, _ = http_get("https://api.github.com/graphql", {"Authorization": f"bearer {token}",
                                                         "Content-Type": "application/json"}, body)
    payload = json.loads(raw)
    if payload.get("errors"):
        raise SystemExit(f"GraphQL error: {payload['errors']}")
    u = payload["data"]["user"]
    cal = u["contributionsCollection"]["contributionCalendar"]
    return {
        "login": u["login"], "name": u["name"], "bio": u["bio"], "company": u["company"],
        "location": u["location"], "website": u["websiteUrl"], "created_at": u["createdAt"],
        "avatar_url": u["avatarUrl"], "followers": u["followers"]["totalCount"],
        "following": u["following"]["totalCount"], "total_repos": u["allRepos"]["totalCount"],
        "repos": [
            {
                "name": r["name"], "description": r["description"], "url": r["url"],
                "stars": r["stargazerCount"], "forks": r["forkCount"], "pushed_at": r["pushedAt"],
                "language": (r["primaryLanguage"] or {}).get("name"),
                "languages": [{"name": e["node"]["name"], "color": e["node"]["color"], "size": e["size"]}
                              for e in r["languages"]["edges"]],
            }
            for r in u["repositories"]["nodes"]
        ],
        "contributions": {
            "total": cal["totalContributions"],
            "days": [{"date": d["date"], "count": d["contributionCount"], "level": LEVELS[d["contributionLevel"]]}
                     for w in cal["weeks"] for d in w["contributionDays"]],
        },
    }


def fetch_views(login: str) -> int | None:
    """Lee el contador de visitas de komarev (el mismo que cuenta las visitas del perfil)."""
    try:
        raw, _ = http_get(f"https://komarev.com/ghpvc/?username={login}&abbreviated=false")
    except OSError as exc:
        print(f"warning: no se pudo leer el contador de visitas: {exc}", file=sys.stderr)
        return None
    numbers = re.findall(r">\s*([\d,.]+)\s*<", raw.decode("utf-8", "replace"))
    return int(numbers[-1].replace(",", "").replace(".", "")) if numbers else None


def avatar_data_uri(url: str) -> str:
    sep = "&" if "?" in url else "?"
    raw, ctype = http_get(f"{url}{sep}s=300" if "s=" not in url and "size=" not in url else url)
    ctype = ctype.split(";")[0] or "image/png"
    return f"data:{ctype};base64,{base64.b64encode(raw).decode()}"


# ---------------------------------------------------------------------------
# Medición de texto con las métricas de Inter
# ---------------------------------------------------------------------------
_METRICS = json.loads(METRICS_FILE.read_text())
_UPM = _METRICS["unitsPerEm"]


def text_width(text: str, size: float, weight: int = 400, spacing: float = 0.0) -> float:
    table = _METRICS["weights"][str(weight)]
    units = sum(table.get(str(ord(ch)), _UPM * 0.6) for ch in text)
    return units * size / _UPM + spacing * len(text)


def wrap(text: str, size: float, weight: int, max_width: float, max_lines: int) -> list[str]:
    words, lines, line = text.split(), [], ""
    for i, word in enumerate(words):
        candidate = f"{line} {word}".strip()
        if text_width(candidate, size, weight) <= max_width:
            line = candidate
            continue
        if line:
            lines.append(line)
        line = word
        if len(lines) == max_lines:
            break
    else:
        if line:
            lines.append(line)
        return lines
    # Se pasó del máximo: recortar la última línea con "…"
    last = lines[max_lines - 1] + " " + " ".join(words[i:])
    while last and text_width(last + "…", size, weight) > max_width:
        last = last[:-1]
    lines[max_lines - 1] = last.rstrip(" ,.;:-—") + "…"
    return lines[:max_lines]


def ellipsize(text: str, size: float, weight: int, max_width: float) -> str:
    if text_width(text, size, weight) <= max_width:
        return text
    while text and text_width(text + "…", size, weight) > max_width:
        text = text[:-1]
    return text.rstrip() + "…"


# ---------------------------------------------------------------------------
# Utilidades de SVG
# ---------------------------------------------------------------------------
def fmt_k(n: int) -> str:
    if n < 1000:
        return str(n)
    value = f"{n / 1000:.1f}".rstrip("0").rstrip(".")
    return f"{value}k"


def hex_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def luminance(rgb: tuple[int, int, int]) -> float:
    def ch(c: int) -> float:
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def readable(color: str) -> str:
    """Aclara un color de lenguaje hasta que se lea bien sobre fondo negro."""
    rgb = hex_rgb(color)
    t = 0.0
    mixed = rgb
    while luminance(mixed) < 0.22 and t < 1:
        t += 0.05
        mixed = tuple(round(c + (255 - c) * t) for c in rgb)
    return "#%02x%02x%02x" % mixed


def lang_color(name: str, color: str | None = None) -> str:
    return color or LANG_COLORS.get(name) or "#8b949e"


def t(x: float, y: float, s: str, size: float, fill: str = TEXT, weight: int = 400,
      anchor: str = "start", spacing: float = 0.0, extra: str = "") -> str:
    attrs = f'x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}"'
    if weight != 400:
        attrs += f' font-weight="{weight}"'
    if anchor != "start":
        attrs += f' text-anchor="{anchor}"'
    if spacing:
        attrs += f' letter-spacing="{spacing}"'
    return f"<text {attrs}{extra}>{escape(s)}</text>"


def icon(name: str, x: float, y: float, size: float, color: str = MUTED, fill: str = "none",
         stroke_width: float = 2.0) -> str:
    scale = size / 24
    return (f'<g transform="translate({x:.1f} {y:.1f}) scale({scale:.4f})" fill="{fill}" stroke="{color}" '
            f'stroke-width="{stroke_width}" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</g>')


def gh_mark(x: float, y: float, size: float, color: str) -> str:
    return f'<path transform="translate({x:.1f} {y:.1f}) scale({size / 16:.4f})" fill="{color}" d="{GITHUB_MARK}"/>'


def card(x: float, y: float, w: float, h: float, r: float = 10) -> str:
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}" '
            f'fill="{CARD}" stroke="{BORDER}"/>')


def pill(x: float, y: float, label: str, color: str, size: float = 13, h: float = 28,
         dot: bool = True) -> tuple[str, float]:
    pad = 12
    tw = text_width(label, size, 500)
    w = pad + (12 if dot else 0) + tw + pad
    parts = [f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h}" rx="{h / 2}" fill="{color}" '
             f'fill-opacity="0.13" stroke="{color}" stroke-opacity="0.4"/>']
    tx = x + pad
    if dot:
        parts.append(f'<circle cx="{x + pad + 3.5:.1f}" cy="{y + h / 2:.1f}" r="3.5" fill="{readable(color)}"/>')
        tx += 12
    parts.append(t(tx, y + h / 2 + size * 0.36, label, size, readable(color), 500))
    return "".join(parts), w


# ---------------------------------------------------------------------------
# Lógica del perfil
# ---------------------------------------------------------------------------
def language_shares(repos: list[dict]) -> list[tuple[str, str, float]]:
    """Promedio, por repo, de la proporción de cada lenguaje (así un repo enorme no tapa al resto)."""
    totals: dict[str, float] = {}
    colors: dict[str, str] = {}
    counted = 0
    for repo in repos:
        langs = repo.get("languages") or []
        size = sum(l["size"] for l in langs)
        if not size:
            continue
        counted += 1
        for l in langs:
            totals[l["name"]] = totals.get(l["name"], 0) + l["size"] / size
            colors[l["name"]] = lang_color(l["name"], l.get("color"))
    if not counted:
        return []
    shares = [(name, colors[name], value / counted) for name, value in totals.items()]
    return sorted(shares, key=lambda s: -s[2])


def auto_tags(data: dict, shares: list, stars: int, contributions: int) -> list[str]:
    tags = []
    if stars >= 1000 or data["followers"] >= 1000:
        tags.append("Popular Creator")
    if data["followers"] >= 5000:
        tags.append("Influencer")
    if not tags and (stars >= 25 or data["followers"] >= 50):
        tags.append("Rising Star")
    if shares:
        top = shares[0][0]
        tags += [domain for domain, langs in DOMAINS.items() if top in langs][:1]
    if len(shares) >= 6:
        tags.append("Polyglot")
    if contributions >= 1000:
        tags.append("Highly Active")
    elif contributions >= 250:
        tags.append("Active")
    return tags


def pick_projects(repos: list[dict], login: str, config: dict) -> list[dict]:
    candidates = [r for r in repos if r["name"].lower() != login.lower()]
    if config.get("projects"):
        by_name = {r["name"].lower(): r for r in candidates}
        return [by_name[n.lower()] for n in config["projects"] if n.lower() in by_name]
    def pushed(repo: dict) -> float:
        stamp = repo.get("pushed_at")
        return dt.datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp() if stamp else 0.0

    candidates.sort(key=lambda r: (-r["stars"], -r["forks"], not r.get("description"), -pushed(r)))
    return candidates[: config.get("max_projects", 6)]


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
W = 1000
LX, LW = 32, 236
RX, RW = 292, 676
TOP = 24


def render(data: dict, config: dict, avatar_uri: str | None, views: int | None,
           now: dt.datetime) -> str:
    s = STRINGS[config.get("lang", "en")]
    tag_label = lambda tag: s["tags"].get(tag, tag)  # noqa: E731
    login = data["login"]
    name = config.get("name") or data.get("name") or login
    repos = data["repos"]
    stars = sum(r["stars"] for r in repos)
    days = data["contributions"]["days"]
    weeks: list[list[dict]] = []
    for day in days:
        date = dt.date.fromisoformat(day["date"])
        weekday = (date.weekday() + 1) % 7  # domingo = 0
        if not weeks or weekday == 0:
            weeks.append([None] * 7)  # type: ignore[list-item]
        weeks[-1][weekday] = {**day, "d": date}
    weeks = weeks[-52:]
    contrib_total = data["contributions"].get("total")
    if contrib_total is None:
        contrib_total = sum(d["count"] for w in weeks for d in w if d)

    top_repos = repos[:20]
    shares = language_shares(top_repos)
    tags = config.get("tags") or auto_tags(data, shares, stars, contrib_total)
    tags = list(dict.fromkeys([*tags, *config.get("extra_tags", [])]))
    created = dt.datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
    years = max(1, int((now - created).days / 365.25))

    out: list[str] = []
    add = out.append

    # ---------------- Columna izquierda ----------------
    cx, cy, r = LX + LW / 2, TOP + LW / 2, LW / 2
    add(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#27272a"/>')
    if avatar_uri:
        add(f'<clipPath id="avatar"><circle cx="{cx}" cy="{cy}" r="{r - 4}"/></clipPath>')
        add(f'<image href="{avatar_uri}" x="{cx - r + 4}" y="{cy - r + 4}" width="{2 * r - 8}" '
            f'height="{2 * r - 8}" clip-path="url(#avatar)" preserveAspectRatio="xMidYMid slice"/>')
    y = TOP + LW + 38
    add(t(LX, y, ellipsize(name, 25, 600, LW), 25, TEXT, 600))
    y += 28
    add(t(LX, y, f"@{login}", 18, MUTED))
    y += 18
    add(f'<rect x="{LX}" y="{y}" width="{LW}" height="38" rx="8" fill="#18181b" stroke="{BORDER}"/>')
    label_w = text_width(s["follow"], 14.5, 500)
    bx = LX + (LW - label_w - 24) / 2
    add(gh_mark(bx, y + 11, 16, TEXT))
    add(t(bx + 24, y + 24.5, s["follow"], 14.5, TEXT, 500))
    y += 38 + 18

    tx = LX
    for tag in tags:
        label = tag_label(tag)
        w = text_width(label, 13, 500) + 24
        if tx > LX and tx + w > LX + LW:
            tx, y = LX, y + 34
        add(f'<rect x="{tx:.1f}" y="{y}" width="{w:.1f}" height="27" rx="13.5" fill="{CARD}" stroke="#3f3f46"/>')
        add(t(tx + 12, y + 18.2, label, 13, "#e4e4e7", 500))
        tx += w + 8
    y += 27 + 30

    def info(icon_name: str, label: str) -> None:
        nonlocal y
        add(icon(icon_name, LX, y - 13, 17, MUTED, stroke_width=1.8))
        add(t(LX + 27, y, ellipsize(label, 15, 400, LW - 27), 15, TEXT_2))
        y += 29

    if data.get("company"):
        info("building", data["company"].lstrip("@"))
    location = config.get("location") or data.get("location")
    if location:
        info("pin", location)
    if data.get("website") and config.get("show_website", True):
        info("link", re.sub(r"^https?://(www\.)?", "", data["website"]).rstrip("/"))
    info("calendar", s["joined"].format(month=s["months_long"][created.month - 1], year=created.year))
    y += 10

    add(icon("users", LX, y - 13, 17, TEXT_2, stroke_width=1.8))
    fx = LX + 27
    for i, (num, word) in enumerate(((data["followers"], s["followers"]), (data["following"], s["following"]))):
        if i:
            add(t(fx + 6, y, "·", 15, DIM))
            fx += 22
        add(t(fx, y, str(num), 15, TEXT, 600))
        fx += text_width(str(num), 15, 600) + 5
        add(t(fx, y, word, 15, TEXT_2))
        fx += text_width(word, 15)
    y += 39
    if views is not None:
        add(icon("eye", LX, y - 13, 17, MUTED, stroke_width=1.8))
        add(t(LX + 27, y, str(views), 15, TEXT, 600))
        add(t(LX + 27 + text_width(str(views), 15, 600) + 5, y, s["views"], 15, TEXT_2))
    left_bottom = y

    # ---------------- Bienvenida ----------------
    y = TOP
    add(card(RX, y, RW, 90))
    possessive = name.rstrip(".")
    add(t(RX + 26, y + 40, s["welcome"].format(name=possessive), 22.5, TEXT, 600))
    add(t(RX + 26, y + 67, s["subtitle"], 15, MUTED))
    pw = text_width(s["powered_by"], 13, 500)
    add(t(RX + RW - 26 - pw - 4, y + 51, s["powered"], 13, DIM, anchor="end"))
    add(t(RX + RW - 26, y + 51, s["powered_by"], 13, ACCENT, 500, anchor="end"))

    # ---------------- Estadísticas ----------------
    y = TOP + 90 + 16
    gap = 16
    sw = (RW - 3 * gap) / 4
    stats = [("folder", fmt_k(data["total_repos"]), s["repos"]),
             ("star", fmt_k(stars), s["stars"]),
             ("users", fmt_k(data["followers"]), s["followers_up"]),
             ("clock", str(years), s["years"] if years != 1 else s["year"])]
    for i, (ic, value, label) in enumerate(stats):
        x = RX + i * (sw + gap)
        add(card(x, y, sw, 104))
        add(icon(ic, x + sw / 2 - 11, y + 17, 22, MUTED, stroke_width=1.6))
        add(t(x + sw / 2, y + 71, value, 33, TEXT, 700, "middle", -0.5))
        add(t(x + sw / 2, y + 91, label, 12, MUTED, 500, "middle", 1.6))

    # ---------------- Contribuciones ----------------
    y = TOP + 90 + 16 + 104 + 18
    ch = 194
    add(card(RX, y, RW, ch))
    add(t(RX + 22, y + 34, s["contributions"], 18, TEXT, 600))
    total_label = fmt_k(contrib_total)
    add(t(RX + RW - 22, y + 34, total_label, 15, TEXT, 600, "end"))
    add(t(RX + RW - 22 - text_width(total_label, 15, 600) - 5, y + 34, s["total"], 15, TEXT_2, anchor="end"))
    gx0, gx1 = RX + 22 + 34, RX + RW - 22
    step = (gx1 - gx0) / max(len(weeks), 1)
    cell = step * 0.8
    gy0 = y + 66
    month_cols = [(col, d["d"].month) for col, week in enumerate(weeks) for d in week if d and d["d"].day == 1]
    first_day = next((d for d in weeks[0] if d), None) if weeks else None
    if first_day and (not month_cols or month_cols[0][0] >= 3):
        month_cols.insert(0, (0, first_day["d"].month))
    for col, month in month_cols:
        label = s["months"][month - 1]
        mx = gx0 + col * step
        if mx + text_width(label, 11.5) <= RX + RW - 10:
            add(t(mx, y + 58, label, 11.5, MUTED))
    for col, week in enumerate(weeks):
        for row, day in enumerate(week):
            if not day:
                continue
            add(f'<rect x="{gx0 + col * step:.2f}" y="{gy0 + row * step:.2f}" width="{cell:.2f}" '
                f'height="{cell:.2f}" rx="2.4" fill="{HEAT[day["level"]]}"/>')
    for row, label in zip((1, 3, 5), s["days"]):
        add(t(RX + 22, gy0 + row * step + cell * 0.78, label, 11.5, MUTED))
    add(t(RX + 22, y + ch - 20, s["last52"], 13.5, MUTED))

    # ---------------- Tecnologías ----------------
    y += ch + 18
    th = 190
    hw = (RW - 18) / 2
    add(card(RX, y, hw, th))
    add(t(RX + 22, y + 36, s["core"], 13, MUTED, 600, spacing=1.6))
    px, py = RX + 22, y + 56
    for lang, color, _ in shares[:8]:
        width = pill(0, 0, lang, color)[1]
        if px > RX + 22 and px + width > RX + hw - 22:
            px, py = RX + 22, py + 38
        if py + 28 > y + th - 14:
            break
        svg, width = pill(px, py, lang, color)
        add(svg)
        px += width + 10

    dx = RX + hw + 18
    add(card(dx, y, hw, th))
    top5 = shares[:5]
    dcx, dcy, dr, thick = dx + 22 + 55, y + 22 + 57, 46, 17
    if top5:
        shown = sum(sh for _, _, sh in top5)
        circ = 2 * math.pi * dr
        offset = 0.0
        for lang, color, share in top5:
            frac = share / shown
            add(f'<circle cx="{dcx}" cy="{dcy}" r="{dr}" fill="none" stroke="{color}" stroke-width="{thick}" '
                f'stroke-dasharray="{frac * circ:.2f} {circ:.2f}" stroke-dashoffset="{-offset:.2f}" '
                f'transform="rotate(-90 {dcx} {dcy})"/>')
            offset += frac * circ
    else:
        add(f'<circle cx="{dcx}" cy="{dcy}" r="{dr}" fill="none" stroke="#27272a" stroke-width="{thick}"/>')
    add(t(dcx, dcy + 5, s["langs"].format(n=len(top5)), 13.5, MUTED, anchor="middle"))
    lx0 = dcx + dr + thick / 2 + 26
    for i, (lang, color, share) in enumerate(top5):
        ly = y + 38 + i * 26
        pct = "<1%" if share < 0.005 else f"{round(share * 100)}%"
        add(f'<circle cx="{lx0 + 5}" cy="{ly - 5}" r="5.5" fill="{readable(color)}"/>')
        add(t(lx0 + 20, ly, ellipsize(lang, 15, 400, dx + hw - 22 - 42 - lx0 - 20), 15, TEXT))
        add(t(dx + hw - 22, ly, pct, 15, TEXT_2, anchor="end"))
    counted = sum(1 for r in top_repos if r.get("languages"))
    add(t(dx + 24, y + th - 18, s["based"].format(n=counted), 13.5, MUTED))

    # ---------------- Proyectos ----------------
    y += th + 30
    add(icon("bookmark", RX, y + 5, 22, MUTED, stroke_width=1.8))
    add(t(RX + 32, y + 24, s["projects"], 21, TEXT, 600))
    sw_ = text_width(s["sort"], 15, 400) + 50
    add(f'<rect x="{RX + RW - sw_:.1f}" y="{y - 4}" width="{sw_:.1f}" height="38" rx="8" fill="{BG}" stroke="{BORDER}"/>')
    add(t(RX + RW - sw_ + 16, y + 20, s["sort"], 15, TEXT))
    add(icon("chevron", RX + RW - 30, y + 7, 16, TEXT_2, stroke_width=1.8))
    y += 52

    projects = pick_projects(repos, login, config)
    pw_ = (RW - 18) / 2
    for row_start in range(0, len(projects), 2):
        row = projects[row_start:row_start + 2]
        rendered = []
        for i, repo in enumerate(row):
            x = RX + i * (pw_ + 18)
            parts = []
            lang = repo.get("language")
            badge_w = 0.0
            if lang:
                color = lang_color(lang, next((l["color"] for l in repo.get("languages", []) if l["name"] == lang), None))
                label = ellipsize(lang, 12, 500, 120)
                badge_w = text_width(label, 12, 500) + 22
                parts.append(f'<rect x="{x + pw_ - 18 - badge_w:.1f}" y="{y + 16}" width="{badge_w:.1f}" height="24" '
                             f'rx="12" fill="{color}" fill-opacity="0.13" stroke="{color}" stroke-opacity="0.4"/>')
                parts.append(t(x + pw_ - 18 - badge_w / 2, y + 32.3, label, 12, readable(color), 500, "middle"))
            parts.append(icon("folder", x + 22, y + 20, 18, MUTED, stroke_width=1.8))
            parts.append(t(x + 50, y + 35, ellipsize(repo["name"], 17, 600, pw_ - 50 - badge_w - 26), 17, ACCENT, 600))
            desc = (repo.get("description") or "").strip()
            lines = wrap(desc, 15, 400, pw_ - 44, 3) if desc else [s["nodesc"]]
            for j, line in enumerate(lines):
                line = ellipsize(line, 15, 400, pw_ - 44)
                parts.append(t(x + 22, y + 66 + j * 22, line, 15, TEXT_2 if desc else DIM))
            sy = y + 66 + (len(lines) - 1) * 22 + 32
            parts.append(icon("star", x + 22, sy - 13, 16, MUTED, fill=MUTED, stroke_width=1.5))
            parts.append(t(x + 44, sy, fmt_k(repo["stars"]), 14.5, MUTED))
            fx = x + 44 + text_width(fmt_k(repo["stars"]), 14.5) + 20
            parts.append(icon("fork", fx, sy - 13, 16, MUTED, stroke_width=1.8))
            parts.append(t(fx + 22, sy, fmt_k(repo["forks"]), 14.5, MUTED))
            rendered.append((x, sy, parts))
        h = max(sy for _, sy, _ in rendered) - y + 26
        for x, _, parts in rendered:
            add(card(x, y, pw_, h))
            out.extend(parts)
        y += h + 18

    # ---------------- Pie ----------------
    y = max(y, left_bottom + 30) + 14
    foot = f"github.com/{login}"
    fw = text_width(foot, 15)
    add(f'<rect x="{RX + RW - fw - 40:.1f}" y="{y - 19}" width="26" height="26" rx="7" fill="#18181b"/>')
    add(gh_mark(RX + RW - fw - 35, y - 14, 16, TEXT))
    add(t(RX + RW, y, foot, 15, MUTED, anchor="end"))
    height = y + 22

    font = base64.b64encode(FONT_FILE.read_bytes()).decode()
    head = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height:.0f}" '
        f'viewBox="0 0 {W} {height:.0f}" role="img" aria-labelledby="card-title">'
        f'<title id="card-title">{escape(name)} (@{escape(login)}) · GitHub</title>'
        "<style>"
        "@font-face{font-family:'InterCard';font-weight:100 900;"
        f"src:url(data:font/woff2;base64,{font}) format('woff2')}}"
        "text{font-family:'InterCard',Inter,-apple-system,'Segoe UI',Helvetica,Arial,sans-serif}"
        "</style>"
        '<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#101010"/><stop offset="0.25" stop-color="#000"/></linearGradient></defs>'
        f'<rect width="{W}" height="{height:.0f}" rx="16" fill="url(#bg)"/>'
    )
    return head + "".join(out) + "</svg>\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=str(ROOT / "profile.config.json"))
    parser.add_argument("--out", default=str(ROOT / "assets/profile-card.svg"))
    parser.add_argument("--data", help="JSON con los datos ya descargados (no llama a la API)")
    parser.add_argument("--dump-data", help="guardar los datos descargados en este archivo")
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text()) if Path(args.config).exists() else {}
    login = config.get("login") or os.environ.get("GITHUB_REPOSITORY_OWNER")
    if args.data:
        data = json.loads(Path(args.data).read_text())
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token or not login:
            raise SystemExit("Hace falta GITHUB_TOKEN y un login (profile.config.json o GITHUB_REPOSITORY_OWNER)")
        data = fetch_data(login, token)
    if args.dump_data:
        Path(args.dump_data).write_text(json.dumps(data, indent=2, ensure_ascii=False))

    views = data.get("views") if args.data else fetch_views(data["login"])
    try:
        avatar = avatar_data_uri(data["avatar_url"])
    except OSError as exc:
        print(f"warning: no se pudo descargar el avatar: {exc}", file=sys.stderr)
        avatar = None
    svg = render(data, config, avatar, views, dt.datetime.now(dt.timezone.utc))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(svg)
    print(f"{args.out}: {len(svg) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
