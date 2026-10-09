"""Offline attribution of missed annotated pixels, not a detector candidate.

The categories partition baseline false negatives in a fixed decision order.
Reachability is an optimistic bound, never a proposed deployable detector.
"""
import numpy as np
from weak_reference import grow


def diagnose(score, truth, roi, high=90, low=45, passes=4):
    score, truth, roi = np.asarray(score), np.asarray(truth), np.asarray(roi)
    if score.ndim != 2 or score.shape != truth.shape or score.shape != roi.shape:
        raise ValueError('Expected three same-shaped 2D arrays')
    if truth.dtype != bool or roi.dtype != bool or not 0 <= low < high or passes < 1:
        raise ValueError('Invalid masks or thresholds')
    seeds = (score > high) & roi
    weak = (score > low) & roi
    baseline = seeds.copy()
    reachable, connected = seeds.copy(), seeds.copy()
    curves = []
    for step in range(1, 33):
        reachable = grow(reachable, roi, 1)
        connected = grow(connected, weak, 1)
        if step <= passes:
            baseline = grow(baseline, weak, 3)
        if step == passes:
            reachable_limit, connected_limit = reachable.copy(), connected.copy()
        if step in (1, 2, 4, 8, 16, 32):
            curves.append(dict(steps=step, unconstrained_truth=int((truth & reachable).sum()),
                               weak_connected_truth=int((truth & connected).sum())))
    if passes > 32:
        raise ValueError('Diagnostic supports at most 32 steps')
    assert not np.any(baseline & ~connected_limit)
    missed = truth & ~baseline
    remaining = missed.copy()
    categories = {}
    for name, condition in (
        ('outside_roi', ~roi),
        ('response_at_or_below_low', score <= low),
        ('no_seed_within_growth_radius', ~reachable_limit),
        ('no_weak_path_within_growth_steps', ~connected_limit),
        ('three_neighbor_support_requirement', np.ones_like(roi)),
    ):
        selected = remaining & condition
        categories[name] = int(selected.sum())
        remaining &= ~selected
    assert not remaining.any() and sum(categories.values()) == int(missed.sum())
    bands = {}
    for name, band in (
        ('0_to_34', score <= 34), ('35_to_45', (score > 34) & (score <= 45)),
        ('46_to_90', (score > 45) & (score <= 90)), ('above_90', score > 90),
    ):
        bands[name] = dict(truth=int((truth & band).sum()), missed=int((missed & band).sum()))
    result = dict(truth=int(truth.sum()), tp=int((baseline & truth).sum()),
                  fp=int((baseline & ~truth).sum()), fn=int(missed.sum()),
                  seed_truth=int((seeds & truth).sum()), categories=categories,
                  score_bands=bands, optimistic_reachability=curves)
    return baseline, result


def box_coverage(truth, boxes):
    """Coverage is localization completeness, not pixel accuracy/precision."""
    covered = np.zeros_like(truth, dtype=bool)
    h, w = truth.shape
    for x0, y0, x1, y1 in boxes:
        if not 0 <= x0 <= x1 < w or not 0 <= y0 <= y1 < h:
            raise ValueError('Box outside image')
        covered[y0:y1+1, x0:x1+1] = True
    return dict(covered_truth=int((truth & covered).sum()), truth=int(truth.sum()),
                box_pixels=int(covered.sum()))
