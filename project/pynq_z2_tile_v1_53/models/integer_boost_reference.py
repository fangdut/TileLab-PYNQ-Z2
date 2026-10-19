"""Portable integer ensemble inference; NumPy only, no scikit-learn runtime."""
import numpy as np

def validate(model):
    if model['fractional_bits']!=16 or not 1<=len(model['trees'])<=512:raise ValueError('Unsupported integer ensemble')
    bound=abs(model['baseline'])
    for tree in model['trees']:
        seen=set();stack=[(0,0)];leaves=[]
        while stack:
            i,depth=stack.pop()
            if i in seen or not 0<=i<len(tree) or depth>12:raise ValueError('Invalid tree graph')
            seen.add(i);node=tree[i]
            if type(node['value']) is not int:raise ValueError('Non-integer coefficient')
            if node['leaf']:leaves.append(node['value'])
            else:
                if not 0<=node['feature']<12 or not 0<=node['threshold']<=255:raise ValueError('Invalid uint8 split')
                stack.extend([(node['left'],depth+1),(node['right'],depth+1)])
        if len(seen)!=len(tree) or not leaves:raise ValueError('Unreachable nodes or missing leaves')
        bound+=max(map(abs,leaves))
    if bound>=2**31:raise ValueError('32-bit score overflow possible')
    return bound

def predict(features,model):
    validate(model);a=np.asarray(features)
    if a.dtype!=np.uint8 or a.shape[-1]!=12:raise ValueError('Expected 12 uint8 features')
    x=a.reshape(-1,12);result=np.full(len(x),model['baseline'],np.int64)
    for tree in model['trees']:
        idx=np.zeros(len(x),np.int16)
        leaf=np.array([n['leaf'] for n in tree]);feature=np.array([n['feature'] for n in tree]);threshold=np.array([n['threshold'] for n in tree]);left=np.array([n['left'] for n in tree]);right=np.array([n['right'] for n in tree]);value=np.array([n['value'] for n in tree],np.int64)
        for _ in range(13):
            active=np.flatnonzero(~leaf[idx])
            if not len(active):break
            old=idx[active];idx[active]=np.where(x[active,feature[old]]<=threshold[old],left[old],right[old])
        if np.any(~leaf[idx]):raise AssertionError('Incomplete traversal')
        result+=value[idx]
    return result.astype(np.int32).reshape(a.shape[:-1])

def exact_threshold_from_float_cache(features,cached,inside,model,threshold):
    """Prove decisions away from a rounding bound; recompute every ambiguous pixel.

    cached must be float32 decisions of the exact source float model named by
    model.source_model_sha256. Caller must verify this provenance and cache hash.
    The full integer inference path above remains available without a cache.
    """
    bound=validate(model);cached=np.asarray(cached)
    if cached.dtype!=np.float32 or cached.shape!=inside.shape:raise ValueError('Invalid float cache')
    rounding=(len(model['trees'])+1)*.5/65536.
    error=rounding+(bound/65536.+rounding)*float(np.finfo(np.float32).eps)+1e-8
    cutoff=threshold/65536.;ambiguous=inside&(np.abs(cached.astype(np.float64)-cutoff)<=error)
    result=(cached>=cutoff)&inside
    if ambiguous.any():result[ambiguous]=predict(np.asarray(features)[ambiguous],model)>=threshold
    return result,dict(total_pixels=int(inside.sum()),exact_recomputed=int(ambiguous.sum()),proven_error_bound=error)
