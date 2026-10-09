# -*- coding: utf-8 -*-
"""
Eval 评测说明
============

对标 DRB（DeepResearch Bench）中文子集口径的配对评测。

数据
----
- 来源：github.com/Ayanami0730/deep_research_bench
  data/test_data/raw_data/reference.jsonl（100 题，50 中文 + 50 英文）
- 本评测取中文 id 1-5，只取 prompt，不复制参考正文
- 生成：python app/eval/build_drb_subset.py /path/to/reference.jsonl
  → dataset/cn_drb_5.jsonl

配置（backend/.env，可选）
-------------------------
EVAL_LLM_BASE_URL=https://llm.goaichat.top/v1
EVAL_LLM_API_KEY=sk-...          # 中转 key
EVAL_LLM_MODEL=deepseek-v4-pro

评分口径
--------
- RACE 四维：comprehensiveness / depth / instruction_following / readability
- FACT：citation_accuracy / effective_citations
- Judge 用 deepseek-v4-pro，temperature=0，双判取均值
- 分数为 0-1，仅供本项目内部配对对比，不与 DRB leaderboard 直接比较

用法
----
python app/eval/run_comparison.py                 # 全跑
python app/eval/run_comparison.py --n 2           # 只跑前 2 题
python app/eval/run_comparison.py --skip-multi    # 只跑 Direct（冒烟）
python app/eval/aggregate.py                      # 聚合指标
