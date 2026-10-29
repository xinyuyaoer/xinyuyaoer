"""Refresh profile assets using public APIs and anonymized contribution counts."""
import json
import subprocess
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USER = "xinyuyaoer"


def api(path, query=None):
    args = ["gh", "api", path]
    if query:
        args += ["-f", "query=" + query]
    return json.loads(subprocess.check_output(args, text=True))


query = '''query { user(login:"xinyuyaoer") { contributionsCollection {
  contributionCalendar { totalContributions weeks {
    contributionDays { date contributionCount }
  } }
} } }'''
response = api("graphql", query)
if response.get("errors"):
    raise RuntimeError(response["errors"])
calendar = response["data"]["user"]["contributionsCollection"]["contributionCalendar"]
days = [d for w in calendar["weeks"] for d in w["contributionDays"]]
today = date.fromisoformat(days[-1]["date"])
recent = [d for d in days if d["date"] >= (today - timedelta(days=29)).isoformat()]
months = defaultdict(int)
for d in days:
    months[d["date"][:7]] += d["contributionCount"]
# Keep twelve calendar months; the current month is partial.
months = list(sorted(months.items()))[-12:]
repos = []
page = 1
while True:
    batch = api(f"users/{USER}/repos?type=owner&sort=pushed&per_page=100&page={page}")
    repos += [r for r in batch if not r["private"] and not r["fork"]
              and not r["archived"] and r["name"] != USER and r["size"] > 0]
    if len(batch) < 100:
        break
    page += 1
repos = sorted(repos, key=lambda r: r["pushed_at"] or "", reverse=True)[:3]
stamp = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
(ROOT / "assets").mkdir(exist_ok=True)

for mode, bg, fg, muted, line, panel, accent in [
    ("light", "#ffffff", "#24283b", "#626b83", "#e4e7f0", "#f5f6fc", "#7066db"),
    ("dark", "#0d1117", "#e5e9f5", "#9ca7bd", "#30374a", "#171d2c", "#a89cff"),
]:
    parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="840" height="408" viewBox="0 0 840 408" role="img" aria-labelledby="title desc">
<title id="title">GitHub activity · HE YUXIN</title>
<desc id="desc">Contributions in the past year, last thirty days, active days, and monthly contribution totals. Includes anonymized private contributions.</desc>
<rect x="1" y="1" width="838" height="406" rx="18" fill="{bg}" stroke="{line}"/>
<style>text{{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;fill:{fg}}}.muted{{fill:{muted}}}.accent{{fill:{accent}}}</style>''']

    def text(x, y, value, size=13, cls="", weight=400):
        parts.append(f'<text x="{x}" y="{y}" font-size="{size}" class="{cls}" font-weight="{weight}">{escape(str(value))}</text>')

    text(30, 40, "GITHUB / ACTIVITY", 12, "accent", 650)
    text(30, 73, "A little progress, over time.", 25, weight=650)
    metrics = [(calendar["totalContributions"], "Contributions · past year"),
               (sum(d["contributionCount"] for d in recent), "Contributions · last 30 days"),
               (sum(d["contributionCount"] > 0 for d in recent), "Active days · last 30 days")]
    for i, (value, label) in enumerate(metrics):
        x = 30 + i * 264
        parts.append(f'<rect x="{x}" y="96" width="250" height="88" rx="10" fill="{panel}"/>')
        text(x + 17, 135, value, 30, "accent", 650)
        text(x + 17, 162, label, 12, "muted")
    text(30, 222, "Monthly contributions", 14, weight=600)
    text(607, 222, "Current month is partial", 11, "muted")
    peak = max(1, max(v for _, v in months))
    for i, (month, value) in enumerate(months):
        x = 44 + i * 65
        h = max(2, round(value / peak * 86))
        parts.append(f'<rect x="{x}" y="{338-h}" width="36" height="{h}" rx="4" fill="{accent}" opacity="{1 if i == 11 else .58}"/>')
        text(x + 5, 328 - h, value, 11, "muted")
        text(x + 4, 359, month[5:], 11, "muted")
    text(30, 389, "Public activity + anonymized private contributions", 11, "muted")
    text(650, 389, f"Updated {stamp}", 11, "muted")
    parts.append("</svg>")
    (ROOT / "assets" / f"activity-{mode}.svg").write_text("\n".join(parts) + "\n")

readme = '''# Hi, I'm HE YUXIN 👋

Student at the **University of Electronic Science and Technology of China (UESTC)**.

Learning, experimenting, and building — one step at a time.

### Activity at a glance

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/activity-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/activity-light.svg">
  <img alt="GitHub contributions over the past year, recent activity, and monthly trends" src="assets/activity-light.svg" width="100%">
</picture>

### Latest public code updates

| Repository | Latest push | Language |
| :--- | :--- | :--- |
'''
for r in repos:
    readme += f'| [{r["name"]}]({r["html_url"]}) | {r["pushed_at"][:10]} | {r["language"] or "—"} |\n'
readme += f'''
<sub>Public, original repositories · sorted by latest push · refreshed daily. Private repository details stay private.</sub>

[Browse public repositories](https://github.com/{USER}?tab=repositories&amp;type=source) · [Contribution history](https://github.com/{USER}?tab=overview#year-list-container)
'''
(ROOT / "README.md").write_text(readme)
print(f"Updated profile: {calendar['totalContributions']} contributions; {len(repos)} public updates")
