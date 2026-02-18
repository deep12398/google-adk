"""结构化评测报告生成器。

灵感来自 n6-agent 的 langsmith_metrics_evaluation_report.json：
  每次评测生成一份 JSON 报告，包含时间戳、各指标的 avg/min/max、
  每个用例的详细分数。便于历史对比和回归检测。

用法：
    reporter = MetricsReporter(report_dir="./reports")

    # 收集评测结果
    reporter.add_result("case_1", {
        "trajectory": 1.0,
        "faithfulness": 0.8,
        "quality": 0.9,
    })

    # 生成报告
    report = reporter.generate_report()
    reporter.save_report()  # 保存到 reports/ 目录
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


class MetricsReporter:
    """结构化评测报告生成器。

    收集多个评测用例的分数，生成类似 n6-agent 的结构化 JSON 报告。

    报告格式：
    {
      "evaluation_summary": {
        "timestamp": "ISO-8601",
        "total_cases": 3,
        "pass_rate": 0.667,
        "average_metrics": {
          "trajectory": {"avg": 0.8, "min": 0.5, "max": 1.0},
          ...
        }
      },
      "detailed_results": [
        {"case_id": "case_1", "metrics": {...}, "status": "PASSED"},
        ...
      ]
    }
    """

    def __init__(self, report_dir: str | Path = "./reports"):
        self._report_dir = Path(report_dir)
        self._results: list[dict[str, Any]] = []

    def add_result(
        self,
        case_id: str,
        metrics: dict[str, float],
        status: str = "PASSED",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """添加一个评测用例的结果。

        Args:
            case_id: 评测用例 ID。
            metrics: 各指标分数 dict，如 {"trajectory": 1.0, "faithfulness": 0.8}。
            status: 状态字符串（PASSED / FAILED）。
            metadata: 附加元数据（query、response 摘要等）。
        """
        entry: dict[str, Any] = {
            "case_id": case_id,
            "metrics": metrics,
            "status": status,
        }
        if metadata:
            entry["metadata"] = metadata
        self._results.append(entry)

    def generate_report(self) -> dict[str, Any]:
        """生成结构化报告。"""
        if not self._results:
            return {
                "evaluation_summary": {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "total_cases": 0,
                    "pass_rate": 0.0,
                    "average_metrics": {},
                },
                "detailed_results": [],
            }

        # 收集所有 metric 名称
        all_metric_names: set[str] = set()
        for result in self._results:
            all_metric_names.update(result["metrics"].keys())

        # 计算每个 metric 的 avg/min/max
        average_metrics: dict[str, dict[str, Any]] = {}
        for metric_name in sorted(all_metric_names):
            values = [
                r["metrics"][metric_name]
                for r in self._results
                if metric_name in r["metrics"]
            ]
            if values:
                average_metrics[metric_name] = {
                    "avg": round(mean(values), 3),
                    "min": round(min(values), 3),
                    "max": round(max(values), 3),
                    "count": len(values),
                }

        # 通过率
        passed = sum(1 for r in self._results if r["status"] == "PASSED")
        pass_rate = round(passed / len(self._results), 3)

        report = {
            "evaluation_summary": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_cases": len(self._results),
                "passed": passed,
                "failed": len(self._results) - passed,
                "pass_rate": pass_rate,
                "average_metrics": average_metrics,
            },
            "detailed_results": self._results,
        }

        return report

    def save_report(self, filename: str | None = None) -> Path:
        """保存报告到 JSON 文件。

        Args:
            filename: 文件名。默认按时间戳生成。

        Returns:
            保存的文件路径。
        """
        self._report_dir.mkdir(parents=True, exist_ok=True)

        if filename is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"eval_report_{ts}.json"

        filepath = self._report_dir / filename
        report = self.generate_report()

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return filepath

    def print_summary(self) -> None:
        """打印报告摘要到控制台。"""
        report = self.generate_report()
        summary = report["evaluation_summary"]

        print(f"  Timestamp:   {summary['timestamp']}")
        print(f"  Total cases: {summary['total_cases']}")
        print(f"  Passed:      {summary.get('passed', 0)}")
        print(f"  Failed:      {summary.get('failed', 0)}")
        print(f"  Pass rate:   {summary['pass_rate']:.1%}")
        print()

        if summary["average_metrics"]:
            print("  Metric Summary:")
            for metric, stats in summary["average_metrics"].items():
                print(
                    f"    {metric:20s}  "
                    f"avg={stats['avg']:.3f}  "
                    f"min={stats['min']:.3f}  "
                    f"max={stats['max']:.3f}"
                )
