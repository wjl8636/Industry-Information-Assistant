# 行业信息助手 · 深度研究 Agent 评测体系

> 参照参考项目 `deepresearch-agent-main` 的评测架构，为**本项目的 DeepResearch V2 多智能体引擎**从零搭建的可复现、可量化评测体系。核心解耦：**评测只依赖 `evaluation.core.runner.run_research()`，不关心 Agent 内部实现。**

## 一、评测对象与分层

本项目要测评的核心是 `backend/app/service/deep_research_v2/` 的多智能体深研引擎（六个 Agent：
架构师 / 侦探 / 分析师 / 极客 / 笔杆 / 毒舌评论家）。评测体系分四层：

| 层级 | 方法 | 成本 | 用途 |
|------|------|------|------|
| 📏 **规则指标** | 字符串/正则 + 内部信号 | 免费、可复现 | 批量运行 / CI / 消融 |
| 🧠 **内部信号** | `ResearchState` 的 facts/references/charts | 免费 | 引用闭环率、结构完整性 |
| 👨‍⚖️ **LLM-as-Judge** | 独立 Judge（多维度 0-10 分） | 需 API | 专家定性评分、抽查 |
| 📈 **统计显著性** | bootstrap 95% CI + Cohen's d | 免费 | 消融 / 对比的统计严谨性 |

## 二、目录结构

```
backend/evaluation/
├── core/                 # 测评核心层
│   ├── llm.py            #   评测用 LLM 统一后端（DashScope/OpenAI 兼容，policy 接口）
│   ├── judge.py          #   LLM-as-Judge：score_single / compare_two
│   ├── runner.py         #   运行器（关键解耦点）：run_research / run_research_full
│   └── ablation.py       #   消融框架：模块消融 + 审核轮数消融 + 统计显著
├── metrics/              # 指标层
│   ├── rule_based.py     #   规则指标 + 内部信号指标（含 evaluate_rule_metrics）
│   ├── judge_based.py    #   Judge 指标
│   ├── composite.py      #   规则(60%) + Judge(40%) 综合
│   └── stats.py          #   bootstrap CI / Cohen's d / 配对 t
├── benchmarks/
│   └── research_bench.py #   行业评测集（智慧交通/金融科技/医疗健康/能源电力/交叉）
├── scripts/              # 入口脚本
│   ├── run_eval.py       #   标准评测集
│   ├── run_ablation.py   #   消融实验
│   ├── run_judge.py      #   Judge 深度评分
│   ├── run_benchmark.py  #   Agent vs 单轮 LLM
│   └── run_all.py        #   一键批量实验
├── report.py             # 统一评测报告（JSON + Markdown）
└── eval_config.example.json
```

## 三、关键设计

### 1. 运行解耦（最重要）
`evaluation/core/runner.py` 提供统一入口 `run_research(query, config, modules)`，
内部适配本项目的 `DeepResearchV2Service.research_sync()`。它把 `ResearchState` 的结构化产物
（`final_report / quality_score / facts / references / charts`）暴露给指标层——**这是本项目相比参考项目额外的内部信号优势**。

```python
# 评测只需要这一行
result = run_research_full(query, config, modules)
# 结果含 final_report / facts / references / quality_score / elapsed_seconds
```

### 2. 规则指标（免费、可进 CI）
- `fact_accuracy`：报告是否包含 ground_truth 关键事实（可选语义版）
- `hallucination_rate`：无引用数值/绝对化表述风险
- `citation_coverage`：引用覆盖的段落比例
- `logical_consistency`：矛盾检测 + 逻辑连接词奖励
- `comprehensiveness`：expected_topics 覆盖度
- **`reference_closure`（内部信号）**：每条 reference 能否在 facts 中找到对应的 source_url
- **`structure_completeness`（内部信号）**：report/facts/references 是否齐备
- `composite_score`：默认权重 `factual 0.25 / logic 0.20 / citation 0.20 / bias 0.20 / comprehensiveness 0.15`

### 3. Judge 评分（独立，避免自评偏差）
Judge 用**独立的 `EvalLLM`** 而非项目流水线里的 CriticMaster——
避免「同一个流水线的 Agent 给自己打分」的系统性偏差。5 维度（事实/逻辑/引用/覆盖/整体，0-10）

### 4. 消融实验（带统计显著性）
本项目配置模型是代码配置 + `max_iterations`（控制审核轮数），已适配：

- **模块消融**：`full` vs `no_review`（关闭 CriticMaster 审核闭环=max_iterations=0）/ `no_web_search` / `no_local_search`
- **轮数消融**：`max_iterations` 0/1/2/3 → 对应对抗审核轮数
- 输出 `full vs 消融` 的 **bootstrap 95% CI + p 值 + Cohen's d**，拒绝「随机波动」

## 四、快速开始

### 前置
1. 启动中间件：`./start-services.sh start`（PostgreSQL/Redis/Milvus）
2. 配置 LLM：`backend/.env` 填入 `DASHSCOPE_API_KEY`（必填）、`BOCHA_API_KEY`（深研搜索）
3. 评测库依赖 `numpy`（bootstrap），可选 `matplotlib`、`yaml`

### 运行评测
```bash
cd backend

# 1. 标准评测集（规则指标，全部行业）
python -m evaluation.scripts.run_eval

# 2. 指定行业 / 题数 / 配置
python -m evaluation.scripts.run_eval --domain 智慧交通 --num_questions 2
python -m evaluation.scripts.run_eval --config evaluation/eval_config.example.json

# 3. 消融实验（模块 / 审核轮数）
python -m evaluation.scripts.run_ablation --mode module --questions 8
python -m evaluation.scripts.run_ablation --mode rounds --max_rounds 3 --questions 8

# 4. Judge 深度评分（对已有报告）
python -m evaluation.scripts.run_judge --query "你的问题" --report_file path/to/report.md

# 5. Agent vs 单轮 LLM
python -m evaluation.scripts.run_benchmark --num_questions 3

# 6. 一键批量实验（标准评测 + 两类消融 + 对比）
python -m evaluation.scripts.run_all --eval_questions 8 --ablation_questions 4
```

### 输出
运行后会生成：
- `backend/outputs/eval/*.json` / `*.md`（标准评测报告，含分行业统计）
- `backend/outputs/eval/ablation/*.json`（消融 + 统计显著性）
- `backend/outputs/eval/benchmark/results.json`（Agent vs LLM + CI）

## 五、如何扩展

### 扩充评测集
编辑 `benchmarks/research_bench.py` 的 `DEFAULT_QUESTIONS`，每道题提供 `expected_topics`（覆盖度）与 `ground_truth`（事实准确性），按行业分组。也可通过 `data_path` 加载外部 JSON。

### 增加指标
在 `metrics/rule_based.py` 加静态方法，并在 `evaluate_rule_metrics` 汇总；或改为 Judge 指标在 `metrics/judge_based.py` 扩展 `score_single` 的维度。

### 更细粒度的 Agent 消融
当前按 `max_iterations` / 搜索开关消融。若需对单个 Agent（如 wizard、writer）消融，可在 `deep_research_v2/graph.py` 增加开关参数，再在 `core/ablation.py` 的 `DEFAULT_MODULE_ABLATIONS` 中声明对应覆盖。

## 六、测试与验证
```bash
# 快速自检（不调用 LLM，验证规则指标 / 评测集 / 报告）
cd backend
python -c "from evaluation.benchmarks.research_bench import IndustryResearchBench; b=IndustryResearchBench(); print(len(b.questions), b.get_domains())"
python -c "from evaluation.metrics.stats import bootstrap_ci_paired; print(bootstrap_ci_paired([0.1,0.2,0.3]))"
```