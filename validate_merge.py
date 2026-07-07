# -*- coding: utf-8 -*-
"""
Stage 2: 校验 + 跨批次合并。
输入：按页码/批次顺序传入的一个或多个抽取 JSON（每个是词条数组）。
输出：清洗并合并后的 <out>.json + 质量报告。
用法： python validate_merge.py --batch BATCH --out merged.json --start-index 57 page_*.json
"""
import argparse
import json
from pathlib import Path

from vocab_common import VALID_CONFIDENCE, clean_id_part, is_probably_garbage


def load(files):
    items = []
    for f in files:
        data = json.loads(Path(f).read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = [data]
        for e in data:
            e.setdefault("_src_file", Path(f).name)
            items.append(e)
    return items


def is_word_legal(e, errors):
    """Stage-1 filter: only reject truly illegal/garbage words.
    Continuation fragments (empty meanings) are allowed through so the merge
    step can complete them."""
    w = (e.get("word") or "").strip()
    if is_probably_garbage(w):
        errors.append(f"剔除碎片/非法词条: {w!r} (src={e.get('_src_file')})")
        return False
    return True


def finalize_one(e, errors):
    """Stage-3 validation, applied AFTER cross-batch merge."""
    w = (e.get("word") or "").strip()
    if not e.get("meanings"):
        errors.append(f"{w}: meanings 为空（合并后仍为空，已跳过）")
        return False
    if e.get("confidence") not in VALID_CONFIDENCE:
        e["confidence"] = "medium"
    if not e.get("phonetic"):
        e["needs_review"] = True
    for k in ["word_forms", "core_usages", "related_words", "examples", "exam_tags", "common_errors"]:
        e.setdefault(k, [])
    return True


def merge_cross_batch(items):
    merged = []
    i, n = 0, len(items)
    while i < n:
        cur = items[i]
        if cur is not None and (cur.get("needs_merge_next_page") or cur.get("partial")):
            for j in range(i + 1, min(i + 3, n)):
                nxt = items[j]
                if nxt is None:
                    continue
                if (nxt.get("word", "").strip().lower() == cur.get("word", "").strip().lower()
                        or nxt.get("is_continuation")):
                    for k in ["core_usages", "related_words", "examples", "exam_tags", "common_errors", "meanings"]:
                        cur[k] = (cur.get(k) or []) + (nxt.get(k) or [])
                    cur["source_page_end"] = nxt.get("source_page", cur.get("source_page"))
                    cur["source_page_start"] = cur.get("source_page_start", cur.get("source_page"))
                    cur.pop("partial", None)
                    cur.pop("needs_merge_next_page", None)
                    cur["needs_review"] = True
                    items[j] = None
                    break
        if cur is not None:
            merged.append(cur)
        i += 1
    return merged


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--batch", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--start-index", type=int, default=1)
    args = ap.parse_args()

    items = load(args.files)
    errors = []
    legal = [e for e in items if is_word_legal(e, errors)]
    merged = merge_cross_batch(legal)
    valid = [e for e in merged if finalize_one(e, errors)]

    out = []
    for idx, e in enumerate(valid, start=args.start_index):
        e["source_batch"] = e.get("source_batch") or args.batch
        e["id"] = f"entry_{idx:03d}_{clean_id_part(e['word'])}"
        e.pop("_src_file", None)
        e.pop("is_continuation", None)
        out.append(e)

    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    total = len(out)
    low = [e["word"] for e in out if e.get("confidence") != "high"]
    still_partial = [e["word"] for e in out if e.get("partial")]
    need_rev = [e["word"] for e in out if e.get("needs_review")]
    no_ph = [e["word"] for e in out if not e.get("phonetic")]
    print(f"=== 质量报告 ({args.batch}) ===")
    print(f"输入 {len(items)} 条 → 有效 {len(valid)} → 合并后 {total} 条")
    print(f"剔除碎片/非法: {len(errors)}")
    for e in errors:
        print("   -", e)
    print(f"需人工复核: {len(need_rev)}；无音标: {len(no_ph)} -> {no_ph[:15]}")
    print(f"非high置信: {len(low)} -> {low[:15]}")
    print(f"仍未闭合(partial): {still_partial}")
    print(f"→ 已写出 {args.out}")
    if still_partial:
        print("⚠ 仍有未闭合词条：把下一批抽取结果一起传入重跑以完成合并。")


if __name__ == "__main__":
    main()
