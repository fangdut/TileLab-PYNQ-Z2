# Procedural subset; no optional photo dataset required.
# Copied from benchmark.py SHA256 e500b0b23bf665c12e649e0f3134595d646db30f81bd02bbb94897195fbd1b90
import numpy as np
from fixtures import STYLES,frame,capture,add_defect

def make_cases():
    cases = []
    normals = [('identity', {}), ('integer_shift', dict(dx=2, dy=-1, noise=1)), ('fractional_shift', dict(dx=0.375, dy=-0.25, noise=1)), ('color_cast', dict(dx=-1, dy=2, gains=(1.04, 0.97, 1.02), offsets=(2, -3, 1), noise=1)), ('mild_blur', dict(blur=0.25, noise=0.5)), ('jpeg92', dict(jpeg=92))]
    for i, style in enumerate(STYLES):
        reference = frame(style)
        for name, kwargs in normals:
            cases.append(dict(id=f'{style}_normal_{name}', cohort='PROCEDURAL_NORMAL_CAPTURE_SIMULATION', style=style, reference=reference, current=capture(reference, **kwargs), truth=np.zeros((500, 500), bool), expected='no_candidate', parameters=kwargs))
        for width, bright, edge in [(1, False, False), (2, False, False), (1, True, False), (3, False, True)]:
            current, truth = add_defect(reference, width, bright, edge)
            kwargs = dict(dx=1, dy=-1, gains=(0.98, 1.01, 0.99), noise=0.5)
            cases.append(dict(id=f'{style}_line_w{width}_bright{int(bright)}_edge{int(edge)}', cohort='PROCEDURAL_ARTIFICIAL_LINE', style=style, reference=reference, current=capture(current, **kwargs), truth=truth, expected='localized_candidate', parameters=dict(width=width, bright=bright, edge=edge, capture=kwargs)))
        invalid = [('wrong_pattern', frame(STYLES[(i + 1) % len(STYLES)])), ('shift6', capture(reference, dx=6)), ('rotation', capture(reference, angle=0.8)), ('dark_exposure', capture(reference, gains=(0.55, 0.55, 0.55)))]
        blocked = reference.copy()
        blocked[170:520, 470:720] = 240
        invalid.append(('occluded', blocked))
        for name, current in invalid:
            cases.append(dict(id=f'{style}_invalid_{name}', cohort='PROCEDURAL_REJECT_OR_REVIEW_STRESS', style=style, reference=reference, current=current, truth=np.zeros((500, 500), bool), expected='not_clean', parameters=dict(condition=name)))
    return cases
