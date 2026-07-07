# -*- coding: utf-8 -*-
"""
Stage 3: 将校验合并后的 JSON 转成导入就绪的 CSV（匹配 /api/admin/entries/import）。
用法： python to_csv.py merged.json --out batch.csv [--status reviewed]
"""
import argparse
import csv
import json
from pathlib import Path

from vocab_common import CSV_COLS, join_cell, usage_cell

PROVENANCE = "来源：辽宁省中考英语词汇用法手册（东北师范大学出版社）；AI 视觉抽取；例句译文按原意补译，需人工抽检校对。"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_file")
    ap.add_argument("--out", required=True)
    ap.add_argument("--status", default="reviewed", choices=["draft", "reviewed", "published"])
    args = ap.parse_args()

    data = json.loads(Path(args.json_file).read_text(encoding="utf-8"))
    with open(args.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLS)
        w.writeheader()
        for r in data:
            w.writerow({
                "id": r.get("id", ""),
                "word": r.get("word", ""),
                "phonetic": r.get("phonetic", ""),
                "part_of_speech": r.get("part_of_speech", ""),
                "meanings": join_cell(r.get("meanings", [])),
                "word_forms": join_cell(r.get("word_forms", [])),
                "core_usages": usage_cell(r.get("core_usages", [])),
                "related_words": join_cell(r.get("related_words", [])),
                "examples_en": join_cell([x.get("en", "") for x in r.get("examples", [])]),
                "examples_cn": join_cell([x.get("cn", "") for x in r.get("examples", [])]),
                "exam_tags": join_cell(r.get("exam_tags", [])),
                "common_errors": join_cell(r.get("common_errors", [])),
                "source_page": r.get("source_page", ""),
                "source_batch": r.get("source_batch", ""),
                "source_text": r.get("source_text") or PROVENANCE,
                "confidence": r.get("confidence", "medium"),
                "status": r.get("status", args.status),
            })
    print(f"→ 已写出 {args.out}（{len(data)} 条，status={args.status}）")
    print("下一步：管理端导入该 CSV → 人工抽检 → python fix_data.py --apply 发布。")


if __name__ == "__main__":
    main()
