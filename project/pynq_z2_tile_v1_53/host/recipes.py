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
        if 'weak_passes' in item and (type(item['weak_passes']) is not int or item['weak_passes'] not in (2,4,8) or item.get('requires_weak_support') is not True):raise ValueError('Invalid recipe growth mode')
        if 'low_gate' in item and type(item['low_gate']) is not bool:raise ValueError('Invalid recipe product gate')
        if 'wide_weak' in item and (type(item['wide_weak']) is not bool or (item['wide_weak'] and (item.get('weak_passes') not in (4,8) or item.get('requires_weak_support') is not True))):raise ValueError('Invalid wide weak support recipe')
        if 'ridge' in item and (type(item['ridge']) is not bool or (item['ridge'] and (item.get('threshold')!=90 or item.get('wide_weak') is not True or item.get('weak_passes') not in (4,8) or item.get('requires_weak_support') is not True))):raise ValueError('Invalid directional mean recipe')
        for key in ('wide_line','directional_growth','pixel_boost'):
            if key in item and type(item[key]) is not bool:raise ValueError('Invalid support profile recipe flag')
        if item.get('pixel_boost') and (item.get('wide_line') or item.get('directional_growth') or item.get('threshold')!=90 or item.get('ridge') is not True or item.get('wide_weak') is not True or item.get('requires_weak_support') is not True or item.get('weak_passes')!=4):raise ValueError('Invalid integer boost recipe')
        if item.get('wide_line') and item.get('directional_growth'):raise ValueError('Mutually exclusive support profiles')
        if item.get('weak_passes')==8 and not item.get('directional_growth'):raise ValueError('Eight passes require directional recipe')
        if item.get('wide_line') or item.get('directional_growth'):
            if item.get('threshold')!=90 or item.get('ridge') is not True or item.get('wide_weak') is not True or item.get('requires_weak_support') is not True or item.get('weak_passes')!=(8 if item.get('directional_growth') else 4):raise ValueError('Invalid fixed support recipe')
        item['sha256']=hashlib.sha256(json.dumps(item,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        result.append(item)
    if len({r['id'] for r in result})!=len(result):raise ValueError('Duplicate recipe identity')
    return result
def evidence(frame,catalog):
    t=(frame['config_word']>>8)&255
    enabled=bool(frame['config_word']&(1<<24));pixel_boost=((frame['config_word']>>29)&3)==3;passes=(8 if frame['config_word']&(1<<30) and not pixel_boost else 4 if frame['config_word']&(1<<25) else 2) if enabled else 0
    low_gate=bool(frame['config_word']&(1<<26))
    wide_weak=bool(frame['config_word']&(1<<27))
    ridge=bool(frame['config_word']&(1<<28))
    wide_line=bool(frame['config_word']&(1<<29)) and not pixel_boost;directional_growth=bool(frame['config_word']&(1<<30)) and not pixel_boost
    matches=[r for r in catalog if r['threshold']==t and (r.get('requires_weak_support',False)==enabled if 'requires_weak_support' in r else True) and (r.get('weak_passes',2)==passes if enabled else True) and r.get('low_gate',False)==low_gate and r.get('wide_weak',False)==wide_weak and r.get('ridge',False)==ridge and r.get('wide_line',False)==wide_line and r.get('directional_growth',False)==directional_growth and r.get('pixel_boost',False)==pixel_boost]
    # A delayed queue event is attributed by captured configuration, never by
    # the current UI selection. Threshold, growth, and product gate all matter.
    recipe=matches[0] if len(matches)==1 else None
    return dict(applied_threshold=t,applied_low_threshold=(t+1)//2 if enabled else None,weak_support_enabled=enabled,weak_passes=passes,low_gate_enabled=low_gate,wide_weak_enabled=wide_weak,wide_line_enabled=wide_line,directional_growth_enabled=directional_growth,pixel_boost_enabled=pixel_boost,applied_product_gate_sum=160 if low_gate else 320,recipe_id=recipe['id'] if recipe else 'custom_or_unknown',recipe_name=recipe['name'] if recipe else '自定义或历史参数',recipe_sha256=recipe['sha256'] if recipe else None,recipe_attribution='MATCHED_CAPTURED_THRESHOLD_GROWTH_PRODUCT_GATE_AND_SCALE_NOT_REQUEST_TIME',recipe_calibration_sha256=recipe.get('calibration_sha256') if recipe else None)
