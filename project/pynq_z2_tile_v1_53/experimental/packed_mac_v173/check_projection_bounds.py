"""Prove full signed8/signed16 projection sum ranges for the actual bias table."""
from pathlib import Path
import argparse,struct,json,hashlib

def main():
    p=argparse.ArgumentParser()
    for n in ['model','source','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();data=a.model.read_bytes();h=struct.unpack_from('<64I',data)
    weights=struct.unpack_from('<8192h',data,h[11]*8)
    biases=struct.unpack_from('<64q',data,h[12]*8)
    # Includes -128 activations and -32768 weights, beyond frozen-model needs.
    delta_bound=8*128*32768;partial_bound=128*128*32768
    bias_bound=max(abs(v) for v in biases);final_bound=bias_bound+partial_bound
    assert delta_bound<(1<<31) and partial_bound<(1<<31)
    assert final_bound<(1<<63) and 0<h[14]<63
    rounded_bound=(final_bound+(1<<(h[14]-1)))>>h[14]
    assert rounded_bound<(1<<31)
    report=dict(scope='EXACT_PROJECTION_INTEGER_RANGE_PROOF_NOT_RTL_OR_BOARD',
        model_sha256=hashlib.sha256(data).hexdigest(),source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),
        activations_domain=[-128,127],weights_domain=[-32768,32767],
        eight_term_magnitude_bound=delta_bound,all_128_term_magnitude_bound=partial_bound,
        signed32_sums_safe=True,actual_bias_magnitude_bound=bias_bound,
        biased_sum_magnitude_bound=final_bound,signed64_bias_add_safe=True,
        rounding_shift=h[14],rounded_magnitude_bound=rounded_bound,signed32_rounded_cast_safe=True,
        actual_projection_weight_range=[min(weights),max(weights)],
        accumulator_recurrence_distance=64,rtl_pipeline_latency_and_ii_still_required=True)
    a.out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
