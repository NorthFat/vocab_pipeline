# -*- coding: utf-8 -*-
"""
Stage 1: 将批次 PDF 渲染为高清页图，供视觉模型抽取。
- 渲染每页为 PNG（默认 200 DPI）
- 可选略去四周白边（--trim）
- 可选把右下角二维码区域置白（--mask-qr）
- 输出 page_XXX.png + manifest.json

用法： python render_batch.py zhongkao_vocab_p011-p020.pdf --out out_p011 --dpi 200 --trim --mask-qr
注：页码映射（PDF页序 → 书内页码）由 --page-offset 控制（书内页 = PDF页序 + offset）。
本书 p001-p010 批：PDF 第4页=书页1，即 offset=-3（前3页为封面/目录）。其余批次通常 offset=0。
"""
import argparse
import json
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageOps


def trim_white(img, border=8):
    gray = img.convert("L")
    inv = ImageOps.invert(gray)
    bbox = inv.getbbox()
    if not bbox:
        return img
    l, t, r, b = bbox
    l = max(0, l - border); t = max(0, t - border)
    r = min(img.width, r + border); b = min(img.height, b + border)
    return img.crop((l, t, r, b))


def mask_qr(img, frac=0.16):
    """Paint the bottom-right square white (typical QR position)."""
    w, h = img.size
    box = (int(w * (1 - frac)), int(h * (1 - frac)), w, h)
    img.paste((255, 255, 255), box)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--out", required=True)
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--trim", action="store_true")
    ap.add_argument("--mask-qr", action="store_true")
    ap.add_argument("--page-offset", type=int, default=0, help="书内页 = PDF页序(1-based) + offset")
    args = ap.parse_args()

    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    pdf = pdfium.PdfDocument(args.pdf)
    scale = args.dpi / 72.0
    manifest = {"pdf": Path(args.pdf).name, "dpi": args.dpi, "pages": []}

    for i in range(len(pdf)):
        page = pdf[i]
        pil = page.render(scale=scale).to_pil().convert("RGB")
        if args.trim:
            pil = trim_white(pil)
        if args.mask_qr:
            pil = mask_qr(pil)
        book_page = i + 1 + args.page_offset
        name = f"page_{book_page:03d}.png"
        pil.save(out / name)
        manifest["pages"].append({"pdf_index": i + 1, "book_page": book_page, "image": name})

    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"→ 渲染 {len(pdf)} 页到 {out}/（{args.dpi} DPI）")
    print("下一步：把每张 page_*.png 连同 extraction_prompt.md 交给视觉模型，得到每页 JSON。")


if __name__ == "__main__":
    main()
