"""Spec 93 -- renders PNG plots from a report dict already produced by
`report.generate_report`. Never recomputes a number independently of the
report -- same "one source of truth" discipline the report itself follows.
`matplotlib` is an optional dependency (`pip install erpguard[benchmark]`),
imported lazily so importing this module never fails on a default install.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

_COMPARISON_METRICS = (
    "task_success_rate", "unsafe_side_effect_rate", "correct_block_rate", "false_block_rate",
)


def render_comparison_bar_chart(report: dict[str, Any], *, out_path: Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")  # headless -- no display server in CI or a benchmark worker
    import matplotlib.pyplot as plt

    configurations = list(report["configurations"])
    fig, ax = plt.subplots(figsize=(9, 5))
    bar_width = 0.8 / max(len(_COMPARISON_METRICS), 1)

    for metric_index, metric in enumerate(_COMPARISON_METRICS):
        values = [report["comparison"].get(metric, {}).get(config) for config in configurations]
        positions = [
            i + metric_index * bar_width for i in range(len(configurations))
        ]
        ax.bar(
            positions,
            [v if v is not None else 0 for v in values],
            width=bar_width, label=metric,
        )

    ax.set_xticks([i + bar_width * (len(_COMPARISON_METRICS) - 1) / 2 for i in range(len(configurations))])
    ax.set_xticklabels(configurations, rotation=15)
    ax.set_ylim(0, 1)
    ax.set_ylabel("rate")
    ax.set_title(f"ERPRiskBench comparison -- {report['dataset_version']}")
    ax.legend(loc="upper right", fontsize="small")
    fig.tight_layout()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)
    return out_path
