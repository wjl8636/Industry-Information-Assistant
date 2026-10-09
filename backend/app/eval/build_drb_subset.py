# -*- coding: utf-8 -*-
"""
Build DRB 中文子集 jsonl（ids 1-5）用于本项目评测。

来源：https://github.com/Ayanami0730/deep_research_bench
  data/test_data/raw_data/reference.jsonl (100题, 50中文+50英文)

本脚本从 DRB 仓库的 reference.jsonl 抽取 id 1-5 的 prompt，生成本项目
eval 数据集。仅取 prompt（问题），不取参考文章——避免直接复制其参考正文。

用法：
    python app/eval/build_drb_subset.py /path/to/deep_research_bench/data/test_data/raw_data/reference.jsonl
"""

import json
import sys
import os

IDS = [1, 2, 3, 4, 5]

OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset", "cn_drb_5.jsonl")


def build(src_path: str) -> None:
    with open(src_path, encoding="utf-8") as f:
        lines = f.readlines()

    picked = []
    for line in lines:
        d = json.loads(line)
        if d.get("id") in IDS:
            picked.append(d)

    # 按 id 排序
    picked.sort(key=lambda x: x["id"])

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for d in picked:
            record = {
                "id": d["id"],
                "prompt": d["prompt"],
                "source": "DeepResearchBench",
                "source_id": d["id"],
                "lang": "zh",
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"written {len(picked)} records -> {OUT_PATH}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    build(sys.argv[1])