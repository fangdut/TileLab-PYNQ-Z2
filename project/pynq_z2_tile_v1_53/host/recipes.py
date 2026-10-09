"""Immutable material recipes. Only parameters and evidence provenance, no vision."""
from pathlib import Path
import json,hashlib
def load(root):
    p=Path(root)/'host/recipes.json'
    if not p.exists():return []
    data=json.loads(p.read_text(encoding='utf-8'))
    result=[]
    for item in data['recipes']:
        item=dict(item)
        if type(item.get('threshold')) is not int or not 1<=item['threshold']<=255:raise ValueError('Invalid recipe threshold')
        if 'weak_passes' in item and (type(item['weak_passes']) is not int or item['weak_passes'] not in (2,4) or item.get('requires_weak_support') is not True):raise ValueError('Invalid recipe growth mode')
        if 'low_gate' in item and type(item['low_gate']) is not bool:raise ValueError('Invalid recipe product gate')
        if 'wide_weak' in item and (type(item['wide_weak']) is not bool or (item['wide_weak'] and (item.get('weak_passes')!=4 or item.get('requires_weak_support') is not True))):raise ValueError('Invalid wide weak support recipe')
        item['sha256']=hashlib.sha256(json.dumps(item,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        result.append(item)
    if len({r['id'] for r in result})!=len(result):raise ValueError('Duplicate recipe identity')
    return result
def evidence(frame,catalog):
    t=(frame['config_word']>>8)&255
    enabled=bool(frame['config_word']&(1<<24));passes=(4 if frame['config_word']&(1<<25) else 2) if enabled else 0
    low_gate=bool(frame['config_word']&(1<<26))
    wide_weak=bool(frame['config_word']&(1<<27))
    matches=[r for r in catalog if r['threshold']==t and (r.get('requires_weak_support',False)==enabled if 'requires_weak_support' in r else True) and (r.get('weak_passes',2)==passes if enabled else True) and r.get('low_gate',False)==low_gate and r.get('wide_weak',False)==wide_weak]
    # A delayed queue event is attributed by captured configuration, never by
    # the current UI selection. Threshold, growth, and product gate all matter.
    recipe=matches[0] if len(matches)==1 else None
    return dict(applied_threshold=t,applied_low_threshold=(t+1)//2 if enabled else None,weak_support_enabled=enabled,weak_passes=passes,low_gate_enabled=low_gate,wide_weak_enabled=wide_weak,applied_product_gate_sum=160 if low_gate else 320,recipe_id=recipe['id'] if recipe else 'custom_or_unknown',recipe_name=recipe['name'] if recipe else '自定义或历史参数',recipe_sha256=recipe['sha256'] if recipe else None,recipe_attribution='MATCHED_CAPTURED_THRESHOLD_GROWTH_PRODUCT_GATE_AND_SCALE_NOT_REQUEST_TIME',recipe_calibration_sha256=recipe.get('calibration_sha256') if recipe else None)
