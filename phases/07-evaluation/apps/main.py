"""Phase 07 入口——评测运行器。

两种模式：
  MODE=manual  手动构造 Invocation + 各种 Evaluator 对比（不需要 LLM API）
  MODE=e2e     AgentEvaluator 端到端评测（需要 LLM API）

用法：
  cd phases/07-evaluation/
  MODE=manual python apps/main.py
  MODE=e2e python apps/main.py
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google.genai import types

from google.adk.evaluation.eval_case import IntermediateData, Invocation
from google.adk.evaluation.eval_metrics import EvalMetric, EvalStatus
from google.adk.evaluation.trajectory_evaluator import (
    TrajectoryEvaluator,
    ToolTrajectoryCriterion,
)
from google.adk.evaluation.response_evaluator import ResponseEvaluator

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from evaluators.custom_evaluator import QualityEvaluator
from evaluators.faithfulness_evaluator import FaithfulnessEvaluator
from evaluators.composite_evaluator import CompositeEvaluator
from evaluators.metrics_reporter import MetricsReporter


# ---------- 辅助函数 ----------


def make_invocation(
    query: str,
    tool_calls: list[tuple[str, dict]] | None = None,
    tool_responses: list[tuple[str, dict]] | None = None,
    response: str = "",
) -> Invocation:
    """构造 Invocation 对象（支持工具调用和工具返回）。"""
    intermediate = None
    if tool_calls or tool_responses:
        intermediate = IntermediateData(
            tool_uses=[
                types.FunctionCall(name=name, args=args)
                for name, args in (tool_calls or [])
            ],
            tool_responses=[
                types.FunctionResponse(name=name, response=resp)
                for name, resp in (tool_responses or [])
            ],
        )

    return Invocation(
        user_content=types.Content(
            parts=[types.Part.from_text(text=query)],
            role="user",
        ),
        final_response=types.Content(
            parts=[types.Part.from_text(text=response)],
            role="model",
        ),
        intermediate_data=intermediate,
    )


# ---------- 手动评测模式 ----------


def run_manual_evaluation() -> None:
    """手动构造 Invocation，演示各种 Evaluator。"""

    print("=" * 60)
    print("Phase 07 — 手动评测模式（Manual Evaluation）")
    print("=" * 60)

    # --- 构造测试数据（含工具返回，用于忠实度评估）---

    actual_good = [
        make_invocation(
            "Research AI trends",
            tool_calls=[("search_web", {"query": "AI trends"})],
            tool_responses=[
                ("search_web", {
                    "status": "success",
                    "results": [
                        {"title": "Latest developments in AI trends",
                         "snippet": "Recent research shows significant progress in AI trends. "
                                    "Key trends include automation, scalability, and integration."},
                        {"title": "AI trends - Industry Report 2025",
                         "snippet": "The AI market is projected to grow significantly. "
                                    "Major players are investing heavily in this space."},
                    ],
                }),
            ],
            response=(
                "Based on my research, the latest AI trends include significant progress "
                "in automation, scalability, and integration. The AI market is projected "
                "to grow significantly, with major players investing heavily."
            ),
        ),
    ]

    actual_bad = [
        make_invocation(
            "Research AI trends",
            tool_calls=[("wrong_tool", {"query": "AI"})],
            tool_responses=[
                ("wrong_tool", {"error": "tool not found"}),
            ],
            response="OK.",
        ),
    ]

    # 瞎编的回答（工具返回的是 AI 内容，但回答说的是天气）
    actual_hallucinated = [
        make_invocation(
            "Research AI trends",
            tool_calls=[("search_web", {"query": "AI trends"})],
            tool_responses=[
                ("search_web", {
                    "results": [
                        {"snippet": "AI trends include automation and scalability."},
                    ],
                }),
            ],
            response=(
                "The weather forecast shows sunny skies with temperatures "
                "reaching 28 degrees celsius. Perfect day for outdoor activities."
            ),
        ),
    ]

    expected = [
        make_invocation(
            "Research AI trends",
            tool_calls=[("search_web", {"query": "AI trends"})],
            response=(
                "AI trends include automation, scalability, and integration. "
                "Major progress has been made in the field."
            ),
        ),
    ]

    # === 1. TrajectoryEvaluator（三种模式）===

    print("\n--- 1. TrajectoryEvaluator ---\n")

    for match_type in ToolTrajectoryCriterion.MatchType:
        evaluator = TrajectoryEvaluator(
            eval_metric=EvalMetric(
                metric_name="tool_trajectory_avg_score",
                threshold=1.0,
                criterion=ToolTrajectoryCriterion(
                    threshold=1.0,
                    match_type=match_type,
                ),
            ),
        )

        result_good = evaluator.evaluate_invocations(actual_good, expected)
        result_bad = evaluator.evaluate_invocations(actual_bad, expected)

        print(f"  [{match_type.name}]")
        print(f"    Good agent: score={result_good.overall_score:.1f}  status={result_good.overall_eval_status.name}")
        print(f"    Bad agent:  score={result_bad.overall_score:.1f}  status={result_bad.overall_eval_status.name}")

    # === 2. ResponseEvaluator（ROUGE-1）===

    print("\n--- 2. ResponseEvaluator (ROUGE-1) ---\n")

    response_eval = ResponseEvaluator(
        threshold=0.5,
        metric_name="response_match_score",
    )

    result_good = response_eval.evaluate_invocations(actual_good, expected)
    result_bad = response_eval.evaluate_invocations(actual_bad, expected)

    print(f"  Good agent: score={result_good.overall_score:.3f}  status={result_good.overall_eval_status.name}")
    print(f"  Bad agent:  score={result_bad.overall_score:.3f}  status={result_bad.overall_eval_status.name}")

    # === 3. QualityEvaluator（自定义）===

    print("\n--- 3. QualityEvaluator (Custom) ---\n")

    quality_eval = QualityEvaluator(
        required_tool="search_web",
        min_response_length=50,
    )

    result_good = quality_eval.evaluate_invocations(actual_good, expected)
    result_bad = quality_eval.evaluate_invocations(actual_bad, expected)

    print(f"  Good agent: score={result_good.overall_score:.1f}  status={result_good.overall_eval_status.name}")
    print(f"  Bad agent:  score={result_bad.overall_score:.1f}  status={result_bad.overall_eval_status.name}")

    # === 4. FaithfulnessEvaluator（忠实度）===

    print("\n--- 4. FaithfulnessEvaluator (Faithfulness + Relevancy) ---\n")

    faith_eval = FaithfulnessEvaluator(
        faithfulness_weight=0.6,
        relevancy_weight=0.4,
        threshold=0.3,
    )

    result_good = faith_eval.evaluate_invocations(actual_good, expected)
    result_bad = faith_eval.evaluate_invocations(actual_bad, expected)
    result_hall = faith_eval.evaluate_invocations(actual_hallucinated, expected)

    print(f"  Good agent:         score={result_good.overall_score:.3f}  status={result_good.overall_eval_status.name}")
    print(f"  Bad agent:          score={result_bad.overall_score:.3f}  status={result_bad.overall_eval_status.name}")
    print(f"  Hallucinated agent: score={result_hall.overall_score:.3f}  status={result_hall.overall_eval_status.name}")

    # === 5. CompositeEvaluator（加权复合）===

    print("\n--- 5. CompositeEvaluator (Weighted Composite) ---\n")

    composite = CompositeEvaluator(
        evaluators={
            "trajectory": (TrajectoryEvaluator(threshold=0.8), 0.3),
            "faithfulness": (FaithfulnessEvaluator(), 0.4),
            "quality": (QualityEvaluator(), 0.3),
        },
        threshold=0.5,
    )

    print("  [Good Agent]")
    composite.evaluate_invocations(actual_good, expected)
    composite.print_report()

    print("\n  [Bad Agent]")
    composite.evaluate_invocations(actual_bad, expected)
    composite.print_report()

    print("\n  [Hallucinated Agent]")
    composite.evaluate_invocations(actual_hallucinated, expected)
    composite.print_report()

    # === 6. MetricsReporter（结构化报告）===

    print("\n--- 6. MetricsReporter (JSON Report) ---\n")

    reporter = MetricsReporter(report_dir=str(BASE_DIR / "reports"))

    # 收集三个 Agent 的各维度分数
    for label, data in [
        ("good_agent", actual_good),
        ("bad_agent", actual_bad),
        ("hallucinated_agent", actual_hallucinated),
    ]:
        composite.evaluate_invocations(data, expected)
        cr = composite.last_composite_result

        reporter.add_result(
            case_id=label,
            metrics=cr.dimension_scores,
            status="PASSED" if cr.overall_score >= 0.5 else "FAILED",
            metadata={"composite_score": cr.overall_score},
        )

    reporter.print_summary()

    report_path = reporter.save_report()
    print(f"\n  Report saved to: {report_path}")

    print("\n" + "=" * 60)
    print("Manual evaluation complete.")
    print("=" * 60)


# ---------- 端到端评测模式 ----------


async def run_e2e_evaluation() -> None:
    """使用 AgentEvaluator 运行端到端评测。"""
    from google.adk.evaluation import AgentEvaluator

    print("=" * 60)
    print("Phase 07 — 端到端评测模式（E2E Evaluation）")
    print("=" * 60)

    eval_data_dir = str(BASE_DIR / "eval_data")

    print(f"\nEval data directory: {eval_data_dir}")
    print("Running AgentEvaluator.evaluate()...\n")

    try:
        await AgentEvaluator.evaluate(
            agent_module="apps.app",
            eval_dataset_file_path_or_dir=eval_data_dir,
            num_runs=1,
            agent_name="research_agent",
            print_detailed_results=True,
        )
        print("\nE2E evaluation passed!")
    except AssertionError as e:
        print(f"\nE2E evaluation failed (some metrics below threshold):\n{e}")
    except Exception as e:
        print(f"\nE2E evaluation error: {type(e).__name__}: {e}")


# ---------- 入口 ----------


def main() -> None:
    mode = os.getenv("MODE", "manual").lower()

    if mode == "manual":
        run_manual_evaluation()
    elif mode == "e2e":
        asyncio.run(run_e2e_evaluation())
    else:
        print(f"Unknown MODE={mode}. Use MODE=manual or MODE=e2e.")
        sys.exit(1)


if __name__ == "__main__":
    main()
