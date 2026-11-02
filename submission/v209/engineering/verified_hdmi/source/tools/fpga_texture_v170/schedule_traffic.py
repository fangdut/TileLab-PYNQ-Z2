"""Count logical convolution DDR reads; this is not an AXI/FPS measurement."""
from pathlib import Path
import argparse, hashlib, json, math


def analyze(graph):
    rows=[]
    for step,t in enumerate(graph['tasks'],1):
        kind=t[0]
        if kind not in (1,2):
            continue
        ih,iw,ic,oc,k,stride,pad=t[7:14]
        oh=(ih+2*pad-k)//stride+1
        groups=(ic+15)//16
        outputs=(oc+15)//16
        valid=lambda y,r: 0 <= y*stride+r-pad < ih
        original_lines=sum(valid(y,r) for y in range(oh) for r in range(k))
        old_input=original_lines*iw*16*outputs*(1 if kind==2 else groups)
        cached=kind==1 and k==1 and stride==1 and pad==0 and oc>16
        tile_rows=min(oh,16,8192//(groups*iw)) if cached else oh
        if tile_rows<1:
            raise ValueError('Pointwise tile exceeds existing projection RAM')
        tiles=math.ceil(oh/tile_rows)
        if cached:
            new_input=ih*iw*groups*16
        elif kind==2:
            fresh_lines=sum(valid(y,r) for y in range(oh) for r in range(k)
                            if y==0 or r>=k-stride)
            new_input=fresh_lines*iw*16*outputs
        else:
            new_input=old_input
        weights=outputs*(k*k*16 if kind==2 else math.ceil(ic/8)*k*k*16*8)
        # Two 32-bit arrays, read through word32() on the 64-bit model port.
        # Count each source-level 64-bit access, without claiming AXI beats.
        parameters=oc*2*8
        rows.append(dict(step=step,kind='depthwise' if kind==2 else 'convolution',
            cached_pointwise=cached,rows_per_tile=tile_rows,tiles=tiles,
            largest_cache_words=groups*iw*min(tile_rows,oh) if cached else 0,
            input_bytes_before=old_input,input_bytes_after=new_input,
            weights_and_parameters_before=weights+parameters,
            weights_and_parameters_after=(weights+parameters)*tiles))
    before=sum(r['input_bytes_before']+r['weights_and_parameters_before'] for r in rows)
    after=sum(r['input_bytes_after']+r['weights_and_parameters_after'] for r in rows)
    return dict(scope='STATIC_CONVOLUTION_SCHEDULE_NOT_AXI_OR_FPS_MEASUREMENT',
        comparison='HLS21 uncached rows versus HLS23 pointwise tiles and DW ring',
        logical_read_bytes_before=before,logical_read_bytes_after=after,
        logical_read_reduction_fraction=1-after/before,
        includes_repeated_weight_reads_per_tile=True,
        excludes=['DDR writes','preprocessing','residual adds','PCA','nearest codebook',
                  'AXI protocol overhead','burst alignment or physical DDR efficiency'],
        additional_cache_bram_bits=0,algorithm_or_threshold_changed=False,layers=rows)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--profile',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    graph=json.loads((a.profile/'graph.json').read_text())
    digest=hashlib.sha256((a.profile/'model.bin').read_bytes()).hexdigest()
    if digest!=graph['sha256']:
        raise ValueError('Model provenance mismatch')
    report=analyze(graph)
    report['model_sha256']=digest
    a.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='layers'}))


if __name__=='__main__':main()
