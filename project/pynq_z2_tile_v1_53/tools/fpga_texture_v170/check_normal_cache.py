"""Bind the compact normalization memory and convolution-only RAM controls."""
from pathlib import Path
import argparse,hashlib,json,re

def inspect(hls):
    hls=Path(hls);source=hls/'src/texture_integer.cpp';code=source.read_text()
    if 'normal_line' not in code:return None
    for token in ['ap_uint<24> normal_line[224];','ap_uint<24> normalized=0;',
                  'if(c==2)normal_line[x]=normalized;','work[y*side+x]=pack_t(normal_line[x]);',
                  'if(c==0)normalized=0;','side>224']:
        if token not in code:raise ValueError('Compact normalization source contract changed')
    start=code.index('if(h[0]!=0x17000001||!width');end=code.index('    i16 query[64];',start)
    if re.search(r'\bline\[',code[start:end]):raise ValueError('Preprocessing still accesses convolution line storage')
    root=hls/'solution/syn/verilog';top=root/'texture_integer.v';text=top.read_text();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();memories={}
    for name,width,depth in [('normal_line',24,224),('line',128,2048)]:
        module='texture_integer_'+name+'_RAM_2P_BRAM_1R1W';rtl=root/(module+'.v');r=rtl.read_text()
        for key,value in [('DataWidth',width),('AddressRange',depth)]:
            if not re.search(r'parameter\s+'+key+r'\s*=\s*'+str(value)+r'\s*;',r):raise ValueError('Generated cache dimensions changed: '+name)
        matches=re.findall(r'\b'+module+r'\s*#\((.*?)\)\s*'+name+r'_U\((.*?)\n\);',text,re.S)
        if len(matches)!=1:raise ValueError('Separate cache instance missing: '+name)
        params,ports=matches[0]
        for key,value in [('DataWidth',width),('AddressRange',depth)]:
            if not re.search(r'\.'+key+r'\(\s*'+str(value)+r'\s*\)',params):raise ValueError('Top cache parameter override changed: '+name)
        connections=dict(re.findall(r'\.(\w+)\((\w+)\)',ports))
        if name=='line':
            for port in ['address0','ce0','address1','ce1','we1','d1']:
                if not re.fullmatch(r'grp_conv_fu_\d+_line_r_\w+',connections.get(port,'')):
                    raise ValueError('Convolution RAM control still shared with another phase: '+port)
        elif any('grp_conv' in connections.get(port,'') for port in ['address0','ce0','address1','ce1','we1','d1']):
            raise ValueError('Normalization cache aliases convolution controls')
        memories[name]=dict(width=width,depth=depth,rtl_sha256=sha(rtl),connections=connections)
    return dict(scope='GENERATED_CACHE_SEPARATION_NOT_FULL_RTL_ROUTING_OR_BOARD',passed=True,
        source_sha256=sha(source),top_rtl_sha256=sha(top),memories=memories,
        added_logical_bits=24*224,convolution_controls_direct=True,normal_rgb_zero_extended_to_128=True,
        interpretation='Dedicated generated storage/control verified; resource/timing/FPS improvement requires routed and physical board evidence.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--hls',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result=inspect(a.hls)
    if result is None:raise ValueError('No separate normalization cache')
    a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
