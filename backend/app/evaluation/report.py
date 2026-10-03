from typing import Union, List, Dict
from app.evaluation.evaluator import ComparisonResult, ThreeWayComparisonResult, EvaluationResult

def _format_system_block(lines: List[str], header: str, res: EvaluationResult, k_vals: List[int]) -> None:
    lines.append(header)
    lines.append("-" * len(header))
    for k in k_vals:
        lines.append(f"Hit@{k}: {res.metrics_by_k[k]['hit_rate']:.4f}")
    for k in k_vals:
        lines.append(f"Recall@{k}: {res.metrics_by_k[k]['recall']:.4f}")
    for k in k_vals:
        lines.append(f"Precision@{k}: {res.metrics_by_k[k]['precision']:.4f}")
    lines.append(f"MRR: {res.mrr:.4f}")
    lines.append(f"MAP: {res.map_score:.4f}")
    lines.append("")

def _format_delta_block(
    lines: List[str],
    header: str,
    delta_k: Dict[int, Dict[str, float]],
    delta_mrr: float,
    delta_map: float,
    k_vals: List[int]
) -> None:
    lines.append(header)
    lines.append("-" * len(header))
    for k in k_vals:
        d_val = delta_k[k]["hit_rate"]
        lines.append(f"Hit@{k}: {d_val:+.4f}")
    for k in k_vals:
        d_val = delta_k[k]["recall"]
        lines.append(f"Recall@{k}: {d_val:+.4f}")
    for k in k_vals:
        d_val = delta_k[k]["precision"]
        lines.append(f"Precision@{k}: {d_val:+.4f}")
    lines.append(f"MRR: {delta_mrr:+.4f}")
    lines.append(f"MAP: {delta_map:+.4f}")
    lines.append("")

def format_evaluation_report(comparison: Union[ComparisonResult, ThreeWayComparisonResult]) -> str:
    """
    Renders an objective, human-readable evaluation report.
    Supports both 2-way and 3-way comparisons without subjective language.
    """
    lines: List[str] = []
    lines.append("RAG EVALUATION REPORT")
    lines.append("=====================")
    lines.append("")

    if isinstance(comparison, ThreeWayComparisonResult):
        b = comparison.baseline
        p81 = comparison.phase81
        p83 = comparison.phase83
        k_vals = sorted(list(b.metrics_by_k.keys()))

        lines.append("Dataset:")
        lines.append(f"Cases: {b.total_cases}")
        lines.append("")

        # 1. BASELINE
        _format_system_block(lines, "BASELINE — Semantic Retrieval", b, k_vals)

        # 2. PHASE 8.1
        _format_system_block(lines, "PHASE 8.1 — Semantic + Lexical Retrieval", p81, k_vals)

        # 3. PHASE 8.3
        _format_system_block(lines, "PHASE 8.3 — Advanced Multi-Signal Retrieval", p83, k_vals)

        # 4. DELTA: Phase 8.1 - Baseline
        _format_delta_block(
            lines,
            "DELTA (Phase 8.1 - Baseline)",
            comparison.delta_81_vs_baseline,
            comparison.delta_mrr_81_vs_baseline,
            comparison.delta_map_81_vs_baseline,
            k_vals
        )

        # 5. DELTA: Phase 8.3 - Baseline
        _format_delta_block(
            lines,
            "DELTA (Phase 8.3 - Baseline)",
            comparison.delta_83_vs_baseline,
            comparison.delta_mrr_83_vs_baseline,
            comparison.delta_map_83_vs_baseline,
            k_vals
        )

        # 6. DELTA: Phase 8.3 - Phase 8.1
        _format_delta_block(
            lines,
            "DELTA (Phase 8.3 - Phase 8.1)",
            comparison.delta_83_vs_81,
            comparison.delta_mrr_83_vs_81,
            comparison.delta_map_83_vs_81,
            k_vals
        )

        # CATEGORY RESULTS
        lines.append("CATEGORY RESULTS")
        lines.append("----------------")
        all_cats = sorted(set(b.category_metrics.keys()).union(p81.category_metrics.keys()).union(p83.category_metrics.keys()))
        for cat in all_cats:
            b_cat = b.category_metrics.get(cat, {})
            p81_cat = p81.category_metrics.get(cat, {})
            p83_cat = p83.category_metrics.get(cat, {})
            d_cat = comparison.category_deltas_83_vs_81.get(cat, {})
            count = b_cat.get("count", p83_cat.get("count", 0))

            lines.append(f"Category: {cat} (N={count})")
            lines.append(
                f"  Baseline  -> Hit@1: {b_cat.get('hit_at_1', 0.0):.4f} | "
                f"Hit@3: {b_cat.get('hit_at_3', 0.0):.4f} | "
                f"Hit@5: {b_cat.get('hit_at_5', 0.0):.4f} | "
                f"Recall@5: {b_cat.get('recall_at_5', 0.0):.4f} | "
                f"MRR: {b_cat.get('mrr', 0.0):.4f}"
            )
            lines.append(
                f"  Phase 8.1 -> Hit@1: {p81_cat.get('hit_at_1', 0.0):.4f} | "
                f"Hit@3: {p81_cat.get('hit_at_3', 0.0):.4f} | "
                f"Hit@5: {p81_cat.get('hit_at_5', 0.0):.4f} | "
                f"Recall@5: {p81_cat.get('recall_at_5', 0.0):.4f} | "
                f"MRR: {p81_cat.get('mrr', 0.0):.4f}"
            )
            lines.append(
                f"  Phase 8.3 -> Hit@1: {p83_cat.get('hit_at_1', 0.0):.4f} | "
                f"Hit@3: {p83_cat.get('hit_at_3', 0.0):.4f} | "
                f"Hit@5: {p83_cat.get('hit_at_5', 0.0):.4f} | "
                f"Recall@5: {p83_cat.get('recall_at_5', 0.0):.4f} | "
                f"MRR: {p83_cat.get('mrr', 0.0):.4f}"
            )
            lines.append(
                f"  Delta(8.3-8.1) -> Hit@1: {d_cat.get('hit_at_1', 0.0):+.4f} | "
                f"Hit@3: {d_cat.get('hit_at_3', 0.0):+.4f} | "
                f"Hit@5: {d_cat.get('hit_at_5', 0.0):+.4f} | "
                f"Recall@5: {d_cat.get('recall_at_5', 0.0):+.4f} | "
                f"MRR: {d_cat.get('mrr', 0.0):+.4f}"
            )
            lines.append("")

    else:
        # 2-way comparison backward compatibility
        b = comparison.baseline
        e = comparison.enhanced
        d_k = comparison.delta_metrics_by_k
        k_vals = sorted(list(b.metrics_by_k.keys()))

        lines.append("Dataset:")
        lines.append(f"Cases: {b.total_cases}")
        lines.append("")

        _format_system_block(lines, "BASELINE — Semantic Retrieval", b, k_vals)
        _format_system_block(lines, "PHASE 8.1 — Enhanced Retrieval", e, k_vals)
        _format_delta_block(lines, "DELTA (Phase 8.1 - Baseline)", d_k, comparison.delta_mrr, comparison.delta_map, k_vals)

        lines.append("CATEGORY RESULTS")
        lines.append("----------------")
        for cat in sorted(b.category_metrics.keys()):
            b_cat = b.category_metrics[cat]
            e_cat = e.category_metrics.get(cat, {})
            d_cat = comparison.category_deltas.get(cat, {})
            count = b_cat.get("count", 0)

            lines.append(f"Category: {cat} (N={count})")
            lines.append(
                f"  Baseline  -> Hit@1: {b_cat.get('hit_at_1', 0.0):.4f} | "
                f"Hit@3: {b_cat.get('hit_at_3', 0.0):.4f} | "
                f"Hit@5: {b_cat.get('hit_at_5', 0.0):.4f} | "
                f"Recall@5: {b_cat.get('recall_at_5', 0.0):.4f} | "
                f"MRR: {b_cat.get('mrr', 0.0):.4f}"
            )
            lines.append(
                f"  Enhanced  -> Hit@1: {e_cat.get('hit_at_1', 0.0):.4f} | "
                f"Hit@3: {e_cat.get('hit_at_3', 0.0):.4f} | "
                f"Hit@5: {e_cat.get('hit_at_5', 0.0):.4f} | "
                f"Recall@5: {e_cat.get('recall_at_5', 0.0):.4f} | "
                f"MRR: {e_cat.get('mrr', 0.0):.4f}"
            )
            lines.append(
                f"  Delta     -> Hit@1: {d_cat.get('hit_at_1', 0.0):+.4f} | "
                f"Hit@3: {d_cat.get('hit_at_3', 0.0):+.4f} | "
                f"Hit@5: {d_cat.get('hit_at_5', 0.0):+.4f} | "
                f"Recall@5: {d_cat.get('recall_at_5', 0.0):+.4f} | "
                f"MRR: {d_cat.get('mrr', 0.0):+.4f}"
            )
            lines.append("")

    if comparison.answer_evaluation:
        ae = comparison.answer_evaluation
        lines.append("ANSWER GROUNDING EVALUATION (Phase 8.4)")
        lines.append("---------------------------------------")
        lines.append(f"Evaluated Cases: {ae.total_answers}")
        lines.append(f"Grounded Answer Rate: {ae.grounded_answer_rate:.4f}")
        lines.append(f"Unsupported Claim Rate: {ae.unsupported_claim_rate:.4f}")
        lines.append(f"Numeric Consistency Rate: {ae.numeric_consistency_rate:.4f}")
        lines.append(f"No-Context Rejection Rate: {ae.no_context_rejection_rate:.4f}")
        lines.append("")

    return "\n".join(lines).strip()
