"""Refresh the "Recently shipped" section of the profile README.

Reads the user's public, non-fork repositories from the GitHub API, picks the
most recently pushed ones, and rewrites the block between the RECENT markers.
Uses only the standard library so the workflow needs no installs.
"""

import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

USER = os.environ.get("GH_USER", "arooj1")
COUNT = int(os.environ.get("RECENT_COUNT", "5"))
README = os.environ.get("README_PATH", "README.md")
EXCLUDE = {USER.lower()}  # the profile repo itself
START, END = "<!-- RECENT:START -->", "<!-- RECENT:END -->"


def fetch_repos():
    url = f"https://api.github.com/users/{USER}/repos?sort=pushed&per_page=50&type=owner"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def render(repos, now):
    repos = sorted(repos, key=lambda r: r["pushed_at"], reverse=True)
    picked = [
        r for r in repos
        if not r.get("fork") and not r.get("archived") and not r.get("private")
        and r["name"].lower() not in EXCLUDE
    ]
    # Collapse version variants (foo, foo-v2, foo-version-3) to the newest one.
    seen, unique = set(), []
    for r in picked:
        base = re.sub(r"[-_](?:version|v)[-_]?\d+$", "", r["name"].lower())
        if base not in seen:
            seen.add(base)
            unique.append(r)
    picked = unique[:COUNT]
    if not picked:
        return "_Nothing public yet — check back soon._"
    lines = []
    for r in picked:
        pushed = datetime.fromisoformat(r["pushed_at"].replace("Z", "+00:00"))
        when = f"{pushed:%b} {pushed.day}, {pushed.year}"
        desc = (r.get("description") or "").strip()
        lang = r.get("language")
        detail = desc if desc else (lang or "")
        sep = " — " if detail else ""
        lines.append(f"- [**{r['name']}**]({r['html_url']}){sep}{detail} · _{when}_")
    return "\n".join(lines)


def main():
    repos = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else fetch_repos()
    block = render(repos, datetime.now(timezone.utc))
    text = open(README, encoding="utf-8").read()
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(text):
        sys.exit("RECENT markers not found in README")
    new = pattern.sub(f"{START}\n{block}\n{END}", text)
    if new != text:
        open(README, "w", encoding="utf-8").write(new)
        print("README updated")
    else:
        print("No change")


if __name__ == "__main__":
    main()
