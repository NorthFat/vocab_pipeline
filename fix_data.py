# -*- coding: utf-8 -*-
"""
修复脚本：发布黄金样本词条 + 清理旧 seed 演示假数据。

用法（在你项目根目录运行，先看报告，再真正改）：
  python fix_data.py                      # dry-run：只打印会发生什么，不改数据
  python fix_data.py --apply              # 发布黄金样本 + 将 seed 假数据隐藏（status=draft）
  python fix_data.py --apply --delete-seed  # 发布黄金样本 + 直接删除 seed 假数据（连带其题目）
  python fix_data.py --db /path/to/app.db --apply

判定规则：
  - 黄金样本：source_batch = 'zhongkao_vocab_p001-p010.pdf' 或 source_text 含 'AI 视觉抽取'
  - 旧 seed 假数据：source_text 含 '内置演示'
"""
import argparse
import sqlite3
import sys
from pathlib import Path

GOLDEN_BATCH = "zhongkao_vocab_p001-p010.pdf"
GOLDEN_WHERE = "(source_batch = ? OR source_text LIKE '%AI 视觉抽取%')"
SEED_WHERE = "source_text LIKE '%内置演示%'"


def find_db(explicit):
    if explicit:
        return Path(explicit)
    for c in ["data/app.db", "zkvocab/data/app.db", "app.db"]:
        p = Path(c)
        if p.exists():
            return p
    return None


def counts(conn):
    def one(sql, args=()):
        return conn.execute(sql, args).fetchone()[0]
    total = one("SELECT COUNT(*) FROM vocabulary_entries")
    published = one("SELECT COUNT(*) FROM vocabulary_entries WHERE status='published'")
    reviewed = one("SELECT COUNT(*) FROM vocabulary_entries WHERE status='reviewed'")
    draft = one("SELECT COUNT(*) FROM vocabulary_entries WHERE status='draft'")
    golden = one(f"SELECT COUNT(*) FROM vocabulary_entries WHERE {GOLDEN_WHERE}", (GOLDEN_BATCH,))
    golden_pub = one(f"SELECT COUNT(*) FROM vocabulary_entries WHERE {GOLDEN_WHERE} AND status='published'", (GOLDEN_BATCH,))
    seed = one(f"SELECT COUNT(*) FROM vocabulary_entries WHERE {SEED_WHERE}")
    return dict(total=total, published=published, reviewed=reviewed, draft=draft,
               golden=golden, golden_pub=golden_pub, seed=seed)


def report(tag, c):
    print(f"[{tag}] 总词条={c['total']} | 已发布={c['published']} 待校对={c['reviewed']} 草稿={c['draft']} "
          f"| 黄金样本={c['golden']}(已发布 {c['golden_pub']}) | seed假数据={c['seed']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=None)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--delete-seed", action="store_true")
    args = ap.parse_args()

    db = find_db(args.db)
    if not db or not db.exists():
        print("❌ 找不到 app.db，请用 --db 指定路径。")
        sys.exit(1)
    print(f"DB: {db.resolve()}")
    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA foreign_keys = ON")

    before = counts(conn)
    report("before", before)

    # 预览待发布的黄金词条
    to_publish = conn.execute(
        f"SELECT word FROM vocabulary_entries WHERE {GOLDEN_WHERE} AND status<>'published' ORDER BY source_page, word",
        (GOLDEN_BATCH,),
    ).fetchall()
    print(f"\n将发布黄金词条 {len(to_publish)} 条: " + ", ".join(w[0] for w in to_publish[:20]) + (" ..." if len(to_publish) > 20 else ""))
    action = "删除" if args.delete_seed else "隐藏(status=draft)"
    print(f"将对 seed 假数据执行: {action}，共 {before['seed']} 条")

    if not args.apply:
        print("\n(dry-run) 未修改任何数据。确认无误后加 --apply 执行。")
        conn.close()
        return

    # 1) 发布黄金样本（词条 + 其题目）
    conn.execute(
        f"UPDATE vocabulary_entries SET status='published' WHERE {GOLDEN_WHERE} AND status<>'published'",
        (GOLDEN_BATCH,),
    )
    conn.execute(
        f"""UPDATE questions SET status='published'
            WHERE entry_id IN (SELECT id FROM vocabulary_entries WHERE {GOLDEN_WHERE})""",
        (GOLDEN_BATCH,),
    )

    # 2) 处理 seed 假数据
    if args.delete_seed:
        conn.execute(f"DELETE FROM vocabulary_entries WHERE {SEED_WHERE}")  # 表已建 ON DELETE CASCADE
    else:
        conn.execute(f"UPDATE vocabulary_entries SET status='draft' WHERE {SEED_WHERE}")

    conn.commit()
    after = counts(conn)
    report("after ", after)
    print("\n✅ 完成。学生端「词库」现在应只看到已发布的黄金词条（如 advice 应显示音标 /ədˈvaɪs/）。")
    conn.close()


if __name__ == "__main__":
    main()
