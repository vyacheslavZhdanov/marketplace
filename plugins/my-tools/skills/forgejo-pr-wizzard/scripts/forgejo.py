#!/usr/bin/env python3
"""
Мини-CLI для Forgejo (git.global.internal) поверх REST API, только stdlib.

Конфиг: .secrets/forgejo.json в корне git-репозитория текущей папки —
{"url": ..., "username": ..., "token": ...}
Доверие TLS: только к CA из .secrets/gri-ca.pem (или "ca_file" в конфиге), системное хранилище
не используется и не модифицируется. Системный прокси для хоста Forgejo игнорируется.

Репозиторий: --repo OWNER/NAME, иначе FORGEJO_REPO, иначе git remote "origin" текущей папки.

Использование:
  python forgejo.py whoami
  python forgejo.py repo list
  python forgejo.py pr list [--state open|closed|all] [--author me|LOGIN]
                                    [--reviewer me|LOGIN]
  python forgejo.py pr close 1 | pr reopen 1
  python forgejo.py pr edit 1 [--title ...] [--body ... | --body-file f.md] [--base ветка]
                                      [--draft | --ready] [--add-reviewer LOGIN ...]
                                      [--remove-reviewer LOGIN ...]
  python forgejo.py pr view 1
  python forgejo.py pr comments 1
  python forgejo.py pr diff 1
  python forgejo.py pr files 1
  python forgejo.py pr create --title "ECO-123 ..." [--body "..." | --body-file f.md]
                                      [--head ветка] [--base ветка] [--draft]
                                      [--reviewer login ...] [--dry-run]
  python forgejo.py pr comment 1 "текст"
  python forgejo.py pr review 1 --event COMMENT|APPROVE|REQUEST_CHANGES [--body "..."]
                                        [--line path:line:текст ...]
  python forgejo.py issue list [--state ...] | issue view 5 | issue comment 5 "текст"
  python forgejo.py api GET repos/{repo}/pulls [--data '{"k": "v"}']
  (в Git Bash путь пишется без ведущего '/', иначе MSYS превратит его в путь Windows)

Флаги --repo и --json указываются после подкоманды (--json печатает сырой JSON ответа).
"""

import argparse
import json
import os
import re
import ssl
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


PROJECT_ROOT = find_project_root()
SECRETS_DIR = PROJECT_ROOT / ".secrets"
CONFIG_FILE = SECRETS_DIR / "forgejo.json"
DEFAULT_CA_FILE = SECRETS_DIR / "gri-ca.pem"
PAGE_LIMIT = 50
TIMEOUT_SECONDS = 30


class ForgejoError(Exception):
    pass


class Client:
    def __init__(self, config: dict):
        self.base = config["url"].rstrip("/") + "/api/v1"
        self.host = re.sub(r"^https?://", "", config["url"]).strip("/").split("/")[0]
        self._token = config["token"].strip()
        ca_file = Path(config.get("ca_file") or DEFAULT_CA_FILE)
        if not ca_file.is_absolute():
            ca_file = PROJECT_ROOT / ca_file
        if not ca_file.exists():
            raise ForgejoError(f"CA-файл не найден: {ca_file}")
        context = ssl.create_default_context(cafile=str(ca_file))
        self._opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            urllib.request.HTTPSHandler(context=context),
        )

    def request(self, method: str, path: str, data=None, raw: bool = False):
        url = path if path.startswith("http") else self.base + path
        headers = {"Authorization": "token " + self._token, "Accept": "application/json"}
        body = None
        if data is not None:
            body = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with self._opener.open(req, timeout=TIMEOUT_SECONDS) as resp:
                payload = resp.read()
                if raw:
                    return payload.decode("utf-8", errors="replace")
                return json.loads(payload) if payload else None
        except urllib.error.HTTPError as e:
            text = e.read()[:1000].decode("utf-8", errors="replace")
            raise ForgejoError(f"HTTP {e.code} {method} {path}: {text}") from None
        except urllib.error.URLError as e:
            raise ForgejoError(f"Ошибка соединения {method} {path}: {e.reason}") from None
        except (OSError, ValueError) as e:
            raise ForgejoError(f"Ошибка запроса {method} {path}: {type(e).__name__}") from None

    def get(self, path: str, raw: bool = False):
        return self.request("GET", path, raw=raw)

    def get_all(self, path: str) -> list:
        sep = "&" if "?" in path else "?"
        items, page = [], 1
        while True:
            chunk = self.get(f"{path}{sep}limit={PAGE_LIMIT}&page={page}") or []
            items += chunk
            if len(chunk) < PAGE_LIMIT:
                return items
            page += 1


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        raise ForgejoError(f"Конфиг не найден: {CONFIG_FILE}")
    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    if not config.get("token", "").strip() or "<" in config.get("token", ""):
        raise ForgejoError(f"В {CONFIG_FILE} не задан token")
    return config


def git(*args: str) -> str:
    try:
        return subprocess.run(
            ["git", *args], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def resolve_repo(arg_repo: str | None, host: str) -> str:
    repo = arg_repo or os.environ.get("FORGEJO_REPO")
    if repo:
        return repo
    remote = git("remote", "get-url", "origin")
    # ssh://git@host:222/OWNER/NAME.git | git@host:OWNER/NAME.git | https://host/OWNER/NAME.git
    match = re.search(re.escape(host) + r"(?::\d+)?[:/](?P<repo>[^/]+/[^/]+?)(?:\.git)?/?$", remote)
    if not match:
        raise ForgejoError("Не удалось определить репозиторий: укажите --repo OWNER/NAME")
    return match.group("repo")


# ---------- форматирование ----------


def short_date(value: str | None) -> str:
    return (value or "")[:16].replace("T", " ")


def print_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def print_body(body: str | None, indent: str = "  "):
    text = (body or "").strip()
    if text:
        print(indent + text.replace("\n", "\n" + indent))


def pr_state(pr: dict) -> str:
    if pr.get("merged"):
        return "MERGED"
    if pr.get("draft"):
        return "DRAFT"
    return pr["state"].upper()


def merge_status(pr: dict) -> str:
    if pr.get("merged") or pr["state"] != "open":
        return "-"
    return "можно мёржить" if pr.get("mergeable") else "конфликты"


def reviewer_logins(pr: dict) -> list[str]:
    return [r["login"] for r in pr.get("requested_reviewers") or []]


WIP_PREFIX = re.compile(r"^\s*(WIP:|\[WIP\])\s*", re.IGNORECASE)


def with_draft(title: str, draft: bool) -> str:
    plain = WIP_PREFIX.sub("", title)
    return "WIP: " + plain if draft else plain


# ---------- команды ----------


def cmd_whoami(client, args):
    user = client.get("/user")
    if args.json:
        return print_json(user)
    print(f"{user['login']} ({user.get('full_name') or '-'}) @ {client.host}")


def cmd_repo_list(client, args):
    repos = client.get_all("/user/repos")
    if args.json:
        return print_json(repos)
    for repo in repos:
        print(f"{repo['full_name']}{'  [private]' if repo.get('private') else ''}")


def resolve_login(client, login: str | None) -> str | None:
    if login == "me":
        return client.get("/user")["login"]
    return login


def cmd_pr_list(client, args):
    prs = client.get_all(f"/repos/{args.repo}/pulls?state={args.state}")
    author = resolve_login(client, args.author)
    reviewer = resolve_login(client, args.reviewer)
    if author:
        prs = [pr for pr in prs if pr["user"]["login"] == author]
    if reviewer:
        prs = [pr for pr in prs if reviewer in reviewer_logins(pr)]
    if args.json:
        return print_json(prs)
    if not prs:
        print("PR не найдены")
    for pr in prs:
        print(
            f"#{pr['number']}\t{pr_state(pr)}\t{merge_status(pr)}\t{pr['user']['login']}\t"
            f"{pr['head']['ref']} -> {pr['base']['ref']}\t{pr['title']}"
        )
        print(f"\tревьюеры: {', '.join(reviewer_logins(pr)) or '-'}")


def cmd_pr_view(client, args):
    pr = client.get(f"/repos/{args.repo}/pulls/{args.number}")
    if args.json:
        return print_json(pr)
    reviewers = ", ".join(reviewer_logins(pr)) or "-"
    labels = ", ".join(label["name"] for label in pr.get("labels") or []) or "-"
    print(f"#{pr['number']} {pr['title']}")
    print(f"Статус:     {pr_state(pr)}, мёрж: {merge_status(pr)}")
    print(f"Автор:      {pr['user']['login']}")
    print(f"Ветки:      {pr['head']['ref']} -> {pr['base']['ref']}")
    print(f"Ревьюеры:   {reviewers}")
    print(f"Метки:      {labels}")
    print(f"Создан:     {short_date(pr['created_at'])}, обновлён: {short_date(pr['updated_at'])}")
    print(f"Ссылка:     {pr['html_url']}")
    print()
    print_body(pr.get("body") or "(без описания)", indent="")


def cmd_pr_comments(client, args):
    path = f"/repos/{args.repo}"
    comments = client.get_all(f"{path}/issues/{args.number}/comments")
    reviews = client.get_all(f"{path}/pulls/{args.number}/reviews")
    review_comments = {
        review["id"]: client.get(f"{path}/pulls/{args.number}/reviews/{review['id']}/comments")
        for review in reviews
        if review.get("comments_count")
    }
    if args.json:
        return print_json(
            {"comments": comments, "reviews": reviews, "review_comments": review_comments}
        )

    print(f"== Комментарии ({len(comments)})")
    for comment in comments:
        print(f"\n[{comment['id']}] {comment['user']['login']} @ {short_date(comment['created_at'])}")
        print_body(comment["body"])

    print(f"\n== Ревью ({len(reviews)})")
    for review in reviews:
        author = (review.get("user") or {}).get("login", "?")
        stale = " (stale)" if review.get("stale") else ""
        print(
            f"\n[review {review['id']}] {author} — {review['state']}{stale}"
            f" @ {short_date(review.get('submitted_at'))}"
        )
        print_body(review.get("body"))
        for comment in review_comments.get(review["id"]) or []:
            line = comment.get("position") or comment.get("original_position")
            resolved = " [resolved]" if comment.get("resolver") else ""
            print(f"  • {comment['path']}:{line} — {comment['user']['login']}{resolved}")
            print_body(comment["body"], indent="    ")


def cmd_pr_diff(client, args):
    print(client.get(f"/repos/{args.repo}/pulls/{args.number}.diff", raw=True))


def cmd_pr_files(client, args):
    files = client.get_all(f"/repos/{args.repo}/pulls/{args.number}/files")
    if args.json:
        return print_json(files)
    for f in files:
        print(f"{f['status']:<10} +{f['additions']:<5} -{f['deletions']:<5} {f['filename']}")


def read_body(args) -> str:
    if args.body_file == "-":
        return sys.stdin.read()
    if args.body_file:
        return Path(args.body_file).read_text(encoding="utf-8")
    return args.body or ""


def cmd_pr_create(client, args):
    repo_path = f"/repos/{args.repo}"
    head = args.head or git("rev-parse", "--abbrev-ref", "HEAD")
    if not head or head == "HEAD":
        raise ForgejoError("Не удалось определить текущую ветку: укажите --head")
    base = args.base or client.get(repo_path)["default_branch"]
    if head == base:
        raise ForgejoError(f"Ветка {head} совпадает с базовой")

    try:
        remote_branch = client.get(f"{repo_path}/branches/{urllib.parse.quote(head, safe='/')}")
    except ForgejoError:
        raise ForgejoError(f"Ветка {head} не найдена на сервере — сначала сделайте push") from None
    local_sha = git("rev-parse", head)
    if local_sha and local_sha != remote_branch["commit"]["id"]:
        print(f"Внимание: локальная {head} не совпадает с {args.repo}:{head} — забыли push?")

    existing = [
        pr for pr in client.get_all(f"{repo_path}/pulls?state=open") if pr["head"]["ref"] == head
    ]
    if existing:
        raise ForgejoError(f"Из {head} уже открыт PR: {existing[0]['html_url']}")

    title = with_draft(args.title, True) if args.draft else args.title
    payload = {"head": head, "base": base, "title": title, "body": read_body(args)}

    if args.dry_run:
        print_json({**payload, "reviewers": args.reviewer or []})
        print("dry-run: PR не создан")
        return

    pr = client.request("POST", f"{repo_path}/pulls", payload)
    if args.reviewer:
        try:
            client.request(
                "POST",
                f"{repo_path}/pulls/{pr['number']}/requested_reviewers",
                {"reviewers": args.reviewer},
            )
        except ForgejoError as e:
            print(f"PR создан, но ревьюеров назначить не удалось: {e}", file=sys.stderr)
    if args.json:
        return print_json(pr)
    print(f"PR #{pr['number']} создан: {head} -> {base}")
    print(pr["html_url"])


def set_pr_state(client, args, state: str):
    pr = client.request("PATCH", f"/repos/{args.repo}/pulls/{args.number}", {"state": state})
    if args.json:
        return print_json(pr)
    print(f"PR #{pr['number']}: {pr_state(pr)}")
    print(pr["html_url"])


def cmd_pr_close(client, args):
    set_pr_state(client, args, "closed")


def cmd_pr_reopen(client, args):
    set_pr_state(client, args, "open")


def cmd_pr_edit(client, args):
    pr_path = f"/repos/{args.repo}/pulls/{args.number}"
    payload = {}
    if args.title or args.draft or args.ready:
        title = args.title or client.get(pr_path)["title"]
        payload["title"] = with_draft(title, args.draft) if (args.draft or args.ready) else title
    if args.body is not None or args.body_file:
        payload["body"] = read_body(args)
    if args.base:
        payload["base"] = args.base
    if not (payload or args.add_reviewer or args.remove_reviewer):
        raise ForgejoError("Нечего менять: укажите хотя бы один параметр")

    if payload:
        client.request("PATCH", pr_path, payload)
    if args.add_reviewer:
        client.request("POST", f"{pr_path}/requested_reviewers", {"reviewers": args.add_reviewer})
    if args.remove_reviewer:
        client.request(
            "DELETE", f"{pr_path}/requested_reviewers", {"reviewers": args.remove_reviewer}
        )

    pr = client.get(pr_path)
    if args.json:
        return print_json(pr)
    print(f"PR #{pr['number']} обновлён: {pr['title']}")
    print(f"Ветки:    {pr['head']['ref']} -> {pr['base']['ref']}")
    print(f"Ревьюеры: {', '.join(reviewer_logins(pr)) or '-'}")
    print(pr["html_url"])


def cmd_comment(client, args):
    comment = client.request(
        "POST", f"/repos/{args.repo}/issues/{args.number}/comments", {"body": args.body}
    )
    if args.json:
        return print_json(comment)
    print(f"Комментарий добавлен: {comment['html_url']}")


def parse_line_comment(value: str) -> dict:
    path, sep, rest = value.partition(":")
    line, sep2, body = rest.partition(":")
    if not (sep and sep2 and line.lstrip("-").isdigit() and body):
        raise ForgejoError(f"--line ожидает path:line:текст, получено: {value}")
    number = int(line)
    # Положительный номер — строка новой версии файла, отрицательный — строка старой версии.
    position = {"new_position": number} if number > 0 else {"old_position": -number}
    return {"path": path, "body": body, **position}


def cmd_pr_review(client, args):
    payload = {
        "event": args.event,
        "body": args.body or "",
        "comments": [parse_line_comment(value) for value in args.line or []],
    }
    review = client.request("POST", f"/repos/{args.repo}/pulls/{args.number}/reviews", payload)
    if args.json:
        return print_json(review)
    print(f"Ревью {review['id']} отправлено: {review['state']}")


def ensure_issues_enabled(client, repo: str):
    if not client.get(f"/repos/{repo}").get("has_issues", True):
        raise ForgejoError(f"В репозитории {repo} отключены issues")


def cmd_issue_list(client, args):
    ensure_issues_enabled(client, args.repo)
    issues = client.get_all(f"/repos/{args.repo}/issues?state={args.state}&type=issues")
    if args.json:
        return print_json(issues)
    if not issues:
        print("Issues не найдены")
    for issue in issues:
        print(f"#{issue['number']}\t{issue['state'].upper()}\t{issue['user']['login']}\t{issue['title']}")


def cmd_issue_view(client, args):
    issue = client.get(f"/repos/{args.repo}/issues/{args.number}")
    comments = client.get_all(f"/repos/{args.repo}/issues/{args.number}/comments")
    if args.json:
        return print_json({"issue": issue, "comments": comments})
    print(f"#{issue['number']} {issue['title']}  [{issue['state'].upper()}]")
    print(f"Автор: {issue['user']['login']}, создан {short_date(issue['created_at'])}")
    print(f"Ссылка: {issue['html_url']}\n")
    print_body(issue.get("body") or "(без описания)", indent="")
    for comment in comments:
        print(f"\n[{comment['id']}] {comment['user']['login']} @ {short_date(comment['created_at'])}")
        print_body(comment["body"])


def cmd_api(client, args):
    path = args.path.replace("{repo}", args.repo) if "{repo}" in args.path else args.path
    # Git Bash превращает аргумент "/repos/..." в "C:/Program Files/Git/repos/...".
    if re.match(r"^[A-Za-z]:/", path):
        raise ForgejoError("Git Bash исказил путь — укажите его без ведущего '/': repos/{repo}")
    if not path.startswith(("/", "http")):
        path = "/" + path
    data = json.loads(args.data) if args.data else None
    result = client.request(args.method.upper(), path, data)
    print_json(result)


# ---------- argparse ----------


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--repo", help="OWNER/NAME (по умолчанию — из git remote origin)")
    common.add_argument("--json", action="store_true", help="вывести сырой JSON")

    parser = argparse.ArgumentParser(description="Мини-CLI для Forgejo")
    sub = parser.add_subparsers(dest="group", required=True)

    sub.add_parser("whoami", parents=[common]).set_defaults(func=cmd_whoami, needs_repo=False)

    repo = sub.add_parser("repo").add_subparsers(dest="action", required=True)
    repo.add_parser("list", parents=[common]).set_defaults(func=cmd_repo_list, needs_repo=False)

    pr = sub.add_parser("pr").add_subparsers(dest="action", required=True)
    p = pr.add_parser("list", parents=[common])
    p.add_argument("--state", choices=["open", "closed", "all"], default="open")
    p.add_argument("--author", metavar="LOGIN", help="автор PR; 'me' — вы")
    p.add_argument(
        "--reviewer", metavar="LOGIN", help="у кого запрошено ревью (ещё не отправлено); 'me' — вы"
    )
    p.set_defaults(func=cmd_pr_list)
    for name, func in [("close", cmd_pr_close), ("reopen", cmd_pr_reopen)]:
        p = pr.add_parser(name, parents=[common])
        p.add_argument("number", type=int)
        p.set_defaults(func=func)
    p = pr.add_parser("edit", parents=[common])
    p.add_argument("number", type=int)
    p.add_argument("--title")
    body = p.add_mutually_exclusive_group()
    body.add_argument("--body")
    body.add_argument("--body-file", help="файл с описанием; '-' — читать из stdin")
    p.add_argument("--base", help="новая целевая ветка")
    draft = p.add_mutually_exclusive_group()
    draft.add_argument("--draft", action="store_true", help="добавить 'WIP: ' в заголовок")
    draft.add_argument("--ready", action="store_true", help="убрать 'WIP:' из заголовка")
    p.add_argument("--add-reviewer", action="append", metavar="LOGIN")
    p.add_argument("--remove-reviewer", action="append", metavar="LOGIN")
    p.set_defaults(func=cmd_pr_edit)
    for name, func in [
        ("view", cmd_pr_view),
        ("comments", cmd_pr_comments),
        ("diff", cmd_pr_diff),
        ("files", cmd_pr_files),
    ]:
        p = pr.add_parser(name, parents=[common])
        p.add_argument("number", type=int)
        p.set_defaults(func=func)
    p = pr.add_parser("create", parents=[common])
    p.add_argument("--title", required=True)
    body = p.add_mutually_exclusive_group()
    body.add_argument("--body")
    body.add_argument("--body-file", help="файл с описанием; '-' — читать из stdin")
    p.add_argument("--head", help="ветка PR (по умолчанию — текущая)")
    p.add_argument("--base", help="целевая ветка (по умолчанию — default branch репозитория)")
    p.add_argument("--draft", action="store_true", help="черновик: префикс 'WIP: ' в заголовке")
    p.add_argument("--reviewer", action="append", metavar="LOGIN")
    p.add_argument("--dry-run", action="store_true", help="всё проверить, но PR не создавать")
    p.set_defaults(func=cmd_pr_create)
    p = pr.add_parser("comment", parents=[common])
    p.add_argument("number", type=int)
    p.add_argument("body")
    p.set_defaults(func=cmd_comment)
    p = pr.add_parser("review", parents=[common])
    p.add_argument("number", type=int)
    p.add_argument("--event", choices=["COMMENT", "APPROVE", "REQUEST_CHANGES"], required=True)
    p.add_argument("--body")
    p.add_argument(
        "--line",
        action="append",
        metavar="PATH:LINE:TEXT",
        help="комментарий к строке; LINE<0 — строка старой версии файла",
    )
    p.set_defaults(func=cmd_pr_review)

    issue = sub.add_parser("issue").add_subparsers(dest="action", required=True)
    p = issue.add_parser("list", parents=[common])
    p.add_argument("--state", choices=["open", "closed", "all"], default="open")
    p.set_defaults(func=cmd_issue_list)
    p = issue.add_parser("view", parents=[common])
    p.add_argument("number", type=int)
    p.set_defaults(func=cmd_issue_view)
    p = issue.add_parser("comment", parents=[common])
    p.add_argument("number", type=int)
    p.add_argument("body")
    p.set_defaults(func=cmd_comment)

    p = sub.add_parser("api", parents=[common], help="сырой запрос; {repo} подставляется")
    p.add_argument("method")
    p.add_argument("path", help="например repos/{repo}/pulls")
    p.add_argument("--data", help="JSON-тело запроса")
    p.set_defaults(func=cmd_api)
    return parser


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
    args = build_parser().parse_args()
    try:
        client = Client(load_config())
        needs_repo = getattr(args, "needs_repo", True)
        if needs_repo and not (args.group == "api" and "{repo}" not in args.path):
            args.repo = resolve_repo(args.repo, client.host)
        args.func(client, args)
    except ForgejoError as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
