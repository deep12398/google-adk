"""端到端评测——AgentEvaluator 集成测试。

使用 AgentEvaluator.evaluate() 运行完整管线：
  .test.json → 加载 EvalSet → 运行 Agent → 评估结果

注意：此测试需要 LLM API（Gemini），因此标记为 slow。
运行方式：pytest tests/test_e2e.py -v -m "not slow"  跳过
         pytest tests/test_e2e.py -v                  全部运行（需要 API key）
"""

import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from google.adk.evaluation import AgentEvaluator


# ---------- 端到端测试 ----------


@pytest.mark.slow
@pytest.mark.asyncio
async def test_e2e_single_turn():
    """端到端评测：单轮对话。

    AgentEvaluator.evaluate() 会：
      1. 读取 eval_data/research.test.json
      2. 读取 eval_data/test_config.json（criteria 配置）
      3. 对每个 EvalCase 运行 Agent
      4. 用 TrajectoryEvaluator + ResponseEvaluator 评估
      5. Assert 所有指标达到阈值
    """
    await AgentEvaluator.evaluate(
        agent_module="agents.research_agent",
        eval_dataset_file_path_or_dir=str(BASE_DIR / "eval_data" / "research.test.json"),
        num_runs=1,
        agent_name="research_agent",
        print_detailed_results=True,
    )


@pytest.mark.slow
@pytest.mark.asyncio
async def test_e2e_multi_turn():
    """端到端评测：多轮对话。"""
    await AgentEvaluator.evaluate(
        agent_module="agents.research_agent",
        eval_dataset_file_path_or_dir=str(BASE_DIR / "eval_data" / "multi_turn.test.json"),
        num_runs=1,
        agent_name="research_agent",
        print_detailed_results=True,
    )


@pytest.mark.slow
@pytest.mark.asyncio
async def test_e2e_all_eval_data():
    """端到端评测：整个 eval_data 目录。

    传入目录路径时，AgentEvaluator 会递归查找所有 .test.json 文件。
    """
    await AgentEvaluator.evaluate(
        agent_module="agents.research_agent",
        eval_dataset_file_path_or_dir=str(BASE_DIR / "eval_data"),
        num_runs=1,
        agent_name="research_agent",
        print_detailed_results=True,
    )
