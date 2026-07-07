# 标准视觉抽取流水线（可复用到全部 29 批）

目标：把扫描版 PDF（无文字层）可复现地转成**黄金样本同等质量**的结构化词库。
核心思路：确定性脚本负责“渲染/校验/转换/导入”，**抽取本身由视觉模型完成**（而非 tesseract+正则）。

## 流水线阶段

```
批次 PDF
  ① render_batch.py      → 高清页图 page_XXX.png + manifest.json
  ② [视觉模型]           → 每页 JSON（依据 extraction_prompt.md + entry_schema.json）
  ③ validate_merge.py    → 校验、剔除碎片、跨页/跨批合并 → merged.json + 质量报告
  ④ to_csv.py            → 导入就绪 CSV
  ⑤ [管理端导入]           → 入库（状态 reviewed）
  ⑥ 人工抽检 → fix_data.py --apply → 发布
```

## 各阶段命令

**① 渲染**
```bash
python render_batch.py zhongkao_vocab_p011-p020.pdf --out out_p011 --dpi 200 --trim --mask-qr
```

**② 视觉抽取**（每页一次）：把 `out_p011/page_XXX.png` + `extraction_prompt.md` 交给视觉模型，保存输出为 `page_XXX.json`。
可手动（直接在本对话里把图给我），也可写个小脚本批量调你自己的 LLM API。

**③ 校验 + 合并**
```bash
python validate_merge.py --batch zhongkao_vocab_p011-p020.pdf --out merged_p011.json \
  --start-index 57 out_p011/page_*.json
```
`--start-index` 接上一批最后编号（p001-p010 已到 56，所以下一批从 57 开始）。

**④ 转 CSV**
```bash
python to_csv.py merged_p011.json --out batch_p011.csv --status reviewed
```

**⑤ 导入**：管理端“词条导入”上传 `batch_p011.csv`（状态 reviewed = 待校对）。

**⑥ 发布**：人工抽检无误后
```bash
python fix_data.py --apply    # 发布待校对词条
```

## 质量门槛（每批必过）
- 抽取完整率 ≥ 95%（对照页面编号连续性）
- 核心字段（音标/搭配/例句）准确率 ≥ 90%
- 无 `None`/碎片词（validate_merge 会自动剔除并报告）
- 跨批次词正确合并（partial 应为 0）

## 文件清单
- `render_batch.py` — PDF→页图
- `extraction_prompt.md` — 视觉抽取契约（核心）
- `entry_schema.json` — 词条 JSON 规范
- `validate_merge.py` — 校验 + 跨批合并
- `to_csv.py` — 转导入 CSV
- `vocab_common.py` — 公共工具
- `fix_data.py` — 发布/清理（复用之前那份）
