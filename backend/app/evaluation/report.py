from app.evaluation.evaluator import ComparisonResult

def format_evaluation_report(comparison: ComparisonResult) -> str:
    """
    Renders an objective, human-readable evaluation report comparing
    the Baseline Semantic Retrieval against Phase 8.1 Enhanced Retrieval.
    No subjective adjectives ('excellent', 'poor', 'best') are used.
    """
    b = comparison.baseline
    e = comparison.enhanced
    d_k = comparison.delta_metrics_by_k
    k_vals = sorted(list(b.metrics_by_k.keys()))

    lines = []
    lines.append("RAG EVALUATION REPORT")
    lines.append("=====================")
    lines.append("")
    lines.append("Dataset:")
    lines.append(f"Cases: {b.total_cases}")
    lines.append("")

    # BASELINE
    lines.append("BASELINE — Semantic Retrieval")
    lines.append("-----------------------------")
    for k in k_vals:
        lines.append(f"Hit@{k}: {b.metrics_by_k[k]['hit_rate']:.4f}")
    for k in k_vals:
        lines.append(f"Recall@{k}: {b.metrics_by_k[k]['recall']:.4f}")
    for k in k_vals:
        lines.append(f"Precision@{k}: {b.metrics_by_k[k]['precision']:.4f}")
    lines.append(f"MRR: {b.mrr:.4f}")
    lines.append(f"MAP: {b.map_score:.4f}")
    lines.append("")

    # PHASE 8.1
    lines.append("PHASE 8.1 — Enhanced Retrieval")
    lines.append("------------------------------")
    for k in k_vals:
        lines.append(f"Hit@{k}: {e.metrics_by_k[k]['hit_rate']:.4f}")
    for k in k_vals:
        lines.append(f"Recall@{k}: {e.metrics_by_k[k]['recall']:.4f}")
    for k in k_vals:
        lines.append(f"Precision@{k}: {e.metrics_by_k[k]['precision']:.4f}")
    lines.append(f"MRR: {e.mrr:.4f}")
    lines.append(f"MAP: {e.map_score:.4f}")
    lines.append("")

    # DELTA
    lines.append("DELTA (Phase 8.1 - Baseline)")
    lines.append("----------------------------")
    for k in k_vals:
        delta_val = d_k[k]['hit_rate']
        sign = "+" if delta_val >= 0 else ""
        lines.append(f"Hit@{k}: {sign}{delta_val:.4f}")
    for k in k_vals:
        delta_val = d_k[k]['recall']
        sign = "+" if delta_val >= 0 else ""
        lines.append(f"Recall@{k}: {sign}{delta_val:.4f}")
    for k in k_vals:
        delta_val = d_k[k]['precision']
        sign = "+" if delta_val >= 0 else ""
        lines.append(f"Precision@{k}: {sign}{delta_val:.4f}")
    mrr_sign = "+" if comparison.delta_mrr >= 0 else ""
    map_sign = "+" if comparison.delta_map >= 0 else ""
    lines.append(f"MRR: {mrr_sign}{comparison.delta_mrr:.4f}")
    lines.append(f"MAP: {map_sign}{comparison.delta_map:.4f}")
    lines.append("")

    # CATEGORY RESULTS
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
            f"  Phase 8.1 -> Hit@1: {e_cat.get('hit_at_1', 0.0):.4f} | "
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

    return "\n".join(lines).strip()
