#!/usr/bin/env python3
"""
Мини-CLI для self-hosted Jira (Server/DC) поверх REST API v2, только stdlib.

Конфиг: .secrets/jira.json в корне git-репозитория текущей папки —
{"url": "https://jira.sun-team.ru", "token": "<Personal Access Token>"}
Авторизация: только Bearer PAT (Basic отключена на сервере).
Системный прокси игнорируется: через него хост Jira недоступен.

Использование:
  python jira.py whoami
  python jira.py issue ECO-123 [--fields summary,status]
  python jira.py search "project = ECO AND ..." [--fields summary,customfield_10818] [--max 100]
  python jira.py api GET rest/api/2/field

Флаг --json (после подкоманды) печатает сырой JSON ответа.
"""

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def find_project_root() -> Path:
    """Корень git-репозитория текущей папки (скрипт лежит в плагине, а не в проекте)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True
        )
        return Path(result.stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        return Path.cwd()


CONFIG_FILE = find_project_root() / ".secrets" / "jira.json"
TIMEOUT_SECONDS = 30
PAGE_LIMIT = 100


class JiraError(Exception):
    pass


class Client:
    def __init__(self, config: dict):
        self.base = config["url"].rstrip("/")
        self._token = config["token"].strip()
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def request(self, method: str, path: str, data=None):
        url = path if path.startswith("http") else f"{self.base}/{path.lstrip('/')}"
        body = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(url, data=body, method=method)
        req.add_header("Authorization", f"Bearer {self._token}")
        req.add_header("Accept", "application/json")
        if body is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with self._opener.open(req, timeout=TIMEOUT_SECONDS) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:500]
            raise JiraError(f"HTTP {e.code} {method} {url}\n{detail}") from None
        except urllib.error.URLError as e:
            raise JiraError(f"Нет связи с {self.base}: {e.reason} (нужен VPN?)") from None
        return json.loads(raw) if raw else None

    def get(self, path: str):
        return self.request("GET", path)

    def browse_url(self, key: str) -> str:
        return f"{self.base}/browse/{key}"


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        raise JiraError(
            f"Нет {CONFIG_FILE}. Создай его: "
            '{"url": "https://jira.sun-team.ru", "token": "<Personal Access Token>"}'
        )
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def print_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def format_value(value) -> str:
    if isinstance(value, dict):
        return str(value.get("name") or value.get("displayName") or value.get("value") or value)
    if isinstance(value, list):
        return ", ".join(format_value(v) for v in value)
    return "" if value is None else str(value)


def cmd_whoami(client, args):
    me = client.get("rest/api/2/myself")
    if args.json:
        return print_json(me)
    print(f"{me.get('name')} ({me.get('displayName')}) — {client.base}")


def cmd_issue(client, args):
    query = urllib.parse.urlencode({"fields": args.fields})
    issue = client.get(f"rest/api/2/issue/{args.key}?{query}")
    if args.json:
        return print_json(issue)
    print(f"{issue['key']}  {client.browse_url(issue['key'])}")
    for name, value in issue["fields"].items():
        print(f"  {name}: {format_value(value)}")


def cmd_search(client, args):
    issues, start = [], 0
    while len(issues) < args.max:
        query = urllib.parse.urlencode(
            {
                "jql": args.jql,
                "fields": args.fields,
                "startAt": start,
                "maxResults": min(PAGE_LIMIT, args.max - len(issues)),
            }
        )
        page = client.get(f"rest/api/2/search?{query}")
        issues.extend(page["issues"])
        start += len(page["issues"])
        if not page["issues"] or start >= page["total"]:
            break
    if args.json:
        return print_json(issues)
    print(f"Найдено: {len(issues)}")
    fields = [f for f in args.fields.split(",") if f]
    for issue in issues:
        values = [f"{f}={format_value(issue['fields'].get(f))}" for f in fields if f != "summary"]
        summary = issue["fields"].get("summary", "")
        print("\t".join([issue["key"], *values, summary, client.browse_url(issue["key"])]))


def cmd_api(client, args):
    data = json.loads(args.data) if args.data else None
    print_json(client.request(args.method.upper(), args.path, data))


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="сырой JSON ответа")

    parser = argparse.ArgumentParser(description="Мини-CLI для Jira (REST API v2)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("whoami", parents=[common]).set_defaults(func=cmd_whoami)

    p = sub.add_parser("issue", parents=[common])
    p.add_argument("key")
    p.add_argument("--fields", default="summary,status,assignee")
    p.set_defaults(func=cmd_issue)

    p = sub.add_parser("search", parents=[common])
    p.add_argument("jql")
    p.add_argument("--fields", default="summary")
    p.add_argument("--max", type=int, default=200)
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("api", parents=[common], help="сырой запрос")
    p.add_argument("method")
    p.add_argument("path")
    p.add_argument("--data")
    p.set_defaults(func=cmd_api)
    return parser


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args()
    try:
        args.func(Client(load_config()), args)
    except JiraError as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
