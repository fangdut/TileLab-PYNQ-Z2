"""Check every packed ROM entry and every header accepted by the geometry guard."""
from pathlib import Path
import argparse,hashlib,json,re
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise ValueError('Fresh proof required')
    source=Path(__file__).with_name('texture_geometry_lut.cpp');s=source.read_text()
    table=re.search(r'words\[32\]=\{([^}]+)\}',s)
    assert table
    words=[int(x.rstrip('U')) for x in table[1].split(',')];assert len(words)==32
    for g,w in enumerate(words):
        a_length=w&2047;b_length=w>>11
        assert a_length==2*g*g and b_length==6*(g//2)*(g//2)
    assert 'side<8||side>224||grid!=side/8' in s
    legal=[]
    for side in range(8,225):
        g=side//8;a_length=2*g*g;b_length=6*(g//2)**2
        assert g<32 and a_length<2048 and b_length<2048 and a_length+b_length<=4096
        assert words[g]==a_length+(b_length<<11)
        legal.append(dict(side=side,grid=g,fa_words=a_length,fb_words=b_length))
    assert max(x['fa_words']+x['fb_words'] for x in legal)==2744
    result=dict(scope='EXHAUSTIVE_LAYOUT_GEOMETRY_ONLY_NOT_FULL_DETECTOR_OR_FPS',passed=True,
                rom_entries=32,legal_sides=len(legal),max_words=2744,cache_words=4096,
                source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),cases=legal)
    a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='cases'}))
if __name__=='__main__':main()
