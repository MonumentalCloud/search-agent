from typing import Iterable, List, Tuple, Callable, Any

import numpy as np


class CrossEncoderReranker:
    def __init__(self) -> None:
        # Transparent placeholder: simple BM25-ish heuristic by overlap count
        pass

    def score(self, pairs: Iterable[Tuple[str, str]]) -> List[float]:
        scores: List[float] = []
        for q, d in pairs:
            q_terms = set(q.lower().split())
            d_terms = set(d.lower().split())
            overlap = len(q_terms.intersection(d_terms))
            scores.append(float(overlap))
        return scores


def mmr_select(items: List[Tuple[float, Any, Any]], lambda_score: float, top_k: int) -> List[Any]:
    # items: List of (score, feature, payload)
    selected: List[Any] = []
    candidates = items[:]
    if not candidates:
        return selected

    # Normalize scores
    scores = np.array([s for s, _, _ in candidates], dtype=float)
    if scores.max() > 0:
        scores = scores / (scores.max() + 1e-9)

    picked = [False] * len(candidates)
    for _ in range(min(top_k, len(candidates))):
        best_idx = -1
        best_val = -1.0
        for i, (s, feat, payload) in enumerate(candidates):
            if picked[i]:
                continue
            diversity_penalty = 0.0
            for j, sel in enumerate(picked):
                if not sel:
                    continue
                _, feat_j, _ = candidates[j]
                # Simple diversity: penalize if section equal or entity tuple equal
                if isinstance(feat, dict) and isinstance(feat_j, dict):
                    if feat.get("section") and feat.get("section") == feat_j.get("section"):
                        diversity_penalty += 0.5
                    if feat.get("entities") and feat.get("entities") == feat_j.get("entities"):
                        diversity_penalty += 0.5
            val = lambda_score * scores[i] - (1 - lambda_score) * diversity_penalty
            if val > best_val:
                best_val = val
                best_idx = i
        if best_idx >= 0:
            picked[best_idx] = True
            selected.append(candidates[best_idx][2])
        else:
            break
    return selected

