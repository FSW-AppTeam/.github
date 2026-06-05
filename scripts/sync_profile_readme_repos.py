#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from urllib.error import HTTPError, URLError
from dataclasses import dataclass
from pathlib import Path


README_PATH = Path("profile/README.md")
ORG_NAME = os.environ.get("ORG_NAME", "FSW-AppTeam")
TOKEN = os.environ.get("GITHUB_TOKEN")
TABLE_HEADER = "| Repository | Short Description |"
TABLE_DIVIDER = "| --- | --- |"
ROW_PATTERN = re.compile(
    r"^\|\s*\[`(?P<name>[^`]+)`\]\([^)]*\)\s*\|\s*(?P<description>.*?)\s*\|$"
)


@dataclass(frozen=True)
class Repo:
    name: str
    description: str


def github_get_json(url: str) -> tuple[list[dict], str | None]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "sync-profile-readme-repos",
    }
    if TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN

    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request) as response:
            payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, list):
                raise RuntimeError(
                    f"Expected a list response from GitHub API for URL '{url}', received {type(payload).__name__}."
                )
            return payload, response.headers.get("Link")
    except HTTPError as exc:
        raise RuntimeError(
            f"GitHub API request failed with HTTP {exc.code} for '{url}'. "
            "Ensure network access is available and GITHUB_TOKEN is valid."
        ) from exc
    except URLError as exc:
        raise RuntimeError(
            f"Failed to reach GitHub API for '{url}'. Ensure network access is available."
        ) from exc


def parse_next_link(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        section = part.strip()
        if 'rel="next"' in section:
            match = re.search(r"<([^>]+)>", section)
            if match:
                return match.group(1)
    return None


def fetch_org_repos(org: str) -> list[Repo]:
    url = f"https://api.github.com/orgs/{urllib.parse.quote(org)}/repos?type=public&per_page=100"
    repos: list[Repo] = []
    while url:
        payload, link_header = github_get_json(url)
        for item in payload:
            repos.append(
                Repo(
                    name=item["name"],
                    description=(item.get("description") or "No description available.").strip(),
                )
            )
        url = parse_next_link(link_header)
    return sorted(repos, key=lambda repo: repo.name.lower())


def parse_existing_descriptions(lines: list[str], start_idx: int, end_idx: int) -> dict[str, str]:
    descriptions: dict[str, str] = {}
    for line in lines[start_idx:end_idx]:
        match = ROW_PATTERN.match(line.strip())
        if match:
            descriptions[match.group("name")] = match.group("description").strip()
    return descriptions


def find_table_bounds(lines: list[str]) -> tuple[int, int]:
    header_idx = -1
    for idx, line in enumerate(lines):
        if line.strip() == TABLE_HEADER:
            header_idx = idx
            break
    if header_idx == -1:
        raise RuntimeError(f"Could not find table header '{TABLE_HEADER}' in {README_PATH}.")

    end_idx = header_idx + 2
    while end_idx < len(lines) and lines[end_idx].lstrip().startswith("|"):
        end_idx += 1
    return header_idx, end_idx


def render_table(repos: list[Repo], existing_descriptions: dict[str, str]) -> list[str]:
    rendered = [TABLE_HEADER, TABLE_DIVIDER]
    for repo in repos:
        description = existing_descriptions.get(repo.name, repo.description)
        rendered.append(
            f"| [`{repo.name}`](https://github.com/{ORG_NAME}/{repo.name}) | {description} |"
        )
    return rendered


def main() -> int:
    if not README_PATH.exists():
        raise FileNotFoundError(f"{README_PATH} does not exist.")

    readme_content = README_PATH.read_text(encoding="utf-8")
    lines = readme_content.splitlines()
    start_idx, end_idx = find_table_bounds(lines)
    existing_descriptions = parse_existing_descriptions(lines, start_idx + 2, end_idx)

    repos = fetch_org_repos(ORG_NAME)
    updated_table_lines = render_table(repos, existing_descriptions)

    new_lines = lines[:start_idx] + updated_table_lines + lines[end_idx:]
    new_content = "\n".join(new_lines).rstrip() + "\n"

    if new_content != readme_content:
        README_PATH.write_text(new_content, encoding="utf-8")
        print(f"Updated {README_PATH} with {len(repos)} repositories.")
    else:
        print(f"No changes needed in {README_PATH}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
