"""Spec 93 -- orchestrates N repeats x the requested configurations over a
loaded dataset. Pure in the sense that it takes cases in and returns
`CaseOutcome` rows out; persistence is the application layer's job
(`erpguard/application/benchmark/service.py`), matching every other
domain/application split in this codebase.
"""

from __future__ import annotations

from erpguard.benchmark.configurations import direct_tool_agent, erpguard_candidate, fixed_workflow
from erpguard.benchmark.dataset import BenchmarkCase
from erpguard.benchmark.fake_erp_store import FakeErpStore
from erpguard.benchmark.types import CaseOutcome

CONFIGURATIONS = {
    fixed_workflow.NAME: fixed_workflow.run_case,
    erpguard_candidate.NAME: erpguard_candidate.run_case,
    direct_tool_agent.NAME: direct_tool_agent.run_case,
}


def run_benchmark(
    *, cases: list[BenchmarkCase], configurations: list[str], repeats: int = 1,
) -> list[tuple[str, int, CaseOutcome]]:
    """Returns a flat list of (configuration, repeat_index, outcome).

    Each (configuration, repeat) pair gets its own fresh `FakeErpStore` --
    Sec 28.4's "same initial state per comparison" invariant: no run leaks
    orders into another run's store.
    """

    unknown = set(configurations) - set(CONFIGURATIONS)
    if unknown:
        raise ValueError(f"unknown_benchmark_configurations:{sorted(unknown)}")

    results: list[tuple[str, int, CaseOutcome]] = []
    for configuration in configurations:
        run_case = CONFIGURATIONS[configuration]
        for repeat_index in range(repeats):
            store = FakeErpStore()
            for case in cases:
                outcome = run_case(case, store)
                results.append((configuration, repeat_index, outcome))
    return results
