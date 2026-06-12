#!/usr/bin/env python3
"""CLI Task Manager - タスク管理ツール"""

import argparse
import json
import os
import sys
from datetime import datetime, date
from pathlib import Path

DATA_FILE = Path.home() / ".task_manager" / "tasks.json"

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
PRIORITY_LABELS = {"high": "🔴 高", "medium": "🟡 中", "low": "🟢 低"}


def load_tasks() -> dict:
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"tasks": [], "next_id": 1}


def save_tasks(data: dict):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_date(s: str) -> str:
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return s
    except ValueError:
        print(f"エラー: 日付は YYYY-MM-DD 形式で入力してください (例: 2026-06-30)", file=sys.stderr)
        sys.exit(1)


def is_overdue(due: str | None) -> bool:
    if not due:
        return False
    return date.fromisoformat(due) < date.today()


def format_task(task: dict, verbose: bool = False) -> str:
    status = "✅" if task["done"] else ("⚠️ " if is_overdue(task.get("due")) else "☐ ")
    due_str = f"  期限: {task['due']}" if task.get("due") else ""
    priority = PRIORITY_LABELS.get(task.get("priority", "medium"), "🟡 中")
    tags = f"  タグ: {', '.join(task['tags'])}" if task.get("tags") else ""
    category = f"  カテゴリ: {task['category']}" if task.get("category") else ""
    line = f"[{task['id']:3d}] {status} {task['title']}"
    if verbose:
        details = []
        if task.get("due"):
            details.append(f"期限: {task['due']}")
        details.append(f"優先度: {priority}")
        if task.get("category"):
            details.append(f"カテゴリ: {task['category']}")
        if task.get("tags"):
            details.append(f"タグ: {', '.join(task['tags'])}")
        details.append(f"作成日: {task['created_at'][:10]}")
        return line + "\n       " + " | ".join(details)
    meta = f"  [{priority}]{due_str}{category}{tags}"
    return line + meta


def cmd_add(args):
    data = load_tasks()
    tags = [t.strip() for t in args.tags.split(",")] if args.tags else []
    task = {
        "id": data["next_id"],
        "title": args.title,
        "done": False,
        "priority": args.priority,
        "due": parse_date(args.due) if args.due else None,
        "category": args.category or None,
        "tags": tags,
        "created_at": datetime.now().isoformat(),
    }
    data["tasks"].append(task)
    data["next_id"] += 1
    save_tasks(data)
    print(f"タスクを追加しました: [{task['id']}] {task['title']}")


def cmd_list(args):
    data = load_tasks()
    tasks = data["tasks"]

    if args.category:
        tasks = [t for t in tasks if t.get("category") == args.category]
    if args.tag:
        tasks = [t for t in tasks if args.tag in t.get("tags", [])]
    if args.priority:
        tasks = [t for t in tasks if t.get("priority") == args.priority]
    if not args.all:
        tasks = [t for t in tasks if not t["done"]]

    if not tasks:
        print("該当するタスクはありません。")
        return

    tasks = sorted(tasks, key=lambda t: (
        t["done"],
        PRIORITY_ORDER.get(t.get("priority", "medium"), 1),
        t.get("due") or "9999-99-99",
    ))

    for t in tasks:
        print(format_task(t, verbose=args.verbose))


def cmd_done(args):
    data = load_tasks()
    for task in data["tasks"]:
        if task["id"] == args.id:
            task["done"] = True
            save_tasks(data)
            print(f"完了にしました: [{task['id']}] {task['title']}")
            return
    print(f"エラー: ID {args.id} のタスクが見つかりません。", file=sys.stderr)
    sys.exit(1)


def cmd_delete(args):
    data = load_tasks()
    original_len = len(data["tasks"])
    removed = [t for t in data["tasks"] if t["id"] == args.id]
    if not removed:
        print(f"エラー: ID {args.id} のタスクが見つかりません。", file=sys.stderr)
        sys.exit(1)
    data["tasks"] = [t for t in data["tasks"] if t["id"] != args.id]
    save_tasks(data)
    print(f"削除しました: [{removed[0]['id']}] {removed[0]['title']}")


def cmd_edit(args):
    data = load_tasks()
    for task in data["tasks"]:
        if task["id"] != args.id:
            continue
        if args.title:
            task["title"] = args.title
        if args.priority:
            task["priority"] = args.priority
        if args.due:
            task["due"] = parse_date(args.due)
        if args.category:
            task["category"] = args.category
        if args.tags is not None:
            task["tags"] = [t.strip() for t in args.tags.split(",") if t.strip()]
        save_tasks(data)
        print(f"更新しました: [{task['id']}] {task['title']}")
        return
    print(f"エラー: ID {args.id} のタスクが見つかりません。", file=sys.stderr)
    sys.exit(1)


def cmd_show(args):
    data = load_tasks()
    for task in data["tasks"]:
        if task["id"] == args.id:
            print(format_task(task, verbose=True))
            return
    print(f"エラー: ID {args.id} のタスクが見つかりません。", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        prog="task",
        description="CLIタスク管理ツール",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # add
    p_add = sub.add_parser("add", help="タスクを追加する")
    p_add.add_argument("title", help="タスクのタイトル")
    p_add.add_argument("--due", metavar="YYYY-MM-DD", help="期限日")
    p_add.add_argument("--priority", choices=["high", "medium", "low"], default="medium", help="優先度")
    p_add.add_argument("--category", help="カテゴリ")
    p_add.add_argument("--tags", help="タグ (カンマ区切り, 例: work,urgent)")

    # list
    p_list = sub.add_parser("list", help="タスク一覧を表示する")
    p_list.add_argument("--all", action="store_true", help="完了済みも含めて表示")
    p_list.add_argument("--category", help="カテゴリでフィルタ")
    p_list.add_argument("--tag", help="タグでフィルタ")
    p_list.add_argument("--priority", choices=["high", "medium", "low"], help="優先度でフィルタ")
    p_list.add_argument("-v", "--verbose", action="store_true", help="詳細表示")

    # done
    p_done = sub.add_parser("done", help="タスクを完了にする")
    p_done.add_argument("id", type=int, help="タスクID")

    # delete
    p_del = sub.add_parser("delete", help="タスクを削除する")
    p_del.add_argument("id", type=int, help="タスクID")

    # edit
    p_edit = sub.add_parser("edit", help="タスクを編集する")
    p_edit.add_argument("id", type=int, help="タスクID")
    p_edit.add_argument("--title", help="新しいタイトル")
    p_edit.add_argument("--due", metavar="YYYY-MM-DD", help="期限日")
    p_edit.add_argument("--priority", choices=["high", "medium", "low"], help="優先度")
    p_edit.add_argument("--category", help="カテゴリ")
    p_edit.add_argument("--tags", help="タグ (カンマ区切り)")

    # show
    p_show = sub.add_parser("show", help="タスクの詳細を表示する")
    p_show.add_argument("id", type=int, help="タスクID")

    args = parser.parse_args()
    {
        "add": cmd_add,
        "list": cmd_list,
        "done": cmd_done,
        "delete": cmd_delete,
        "edit": cmd_edit,
        "show": cmd_show,
    }[args.command](args)


if __name__ == "__main__":
    main()
