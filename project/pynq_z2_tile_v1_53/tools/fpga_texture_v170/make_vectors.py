"""Small complete graph: 3x3/1x1, stride2, depthwise24, residual, PCA, NN, mask."""
from pathlib import Path
import argparse,numpy as np,torch
from PIL import Image
from prepare_integer import FixedGraph,project,integer_scores
from export_integer import export

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    torch.manual_seed(17001);torch.set_num_threads(4);g=FixedGraph.__new__(FixedGraph)
    g.side=32;g.feature_dim=128;g.scales={0:.025};g.fixed_input=True;g.nodes=[];g.quant={}
    configs=[(3,24,3,2,1,1),(24,24,3,1,1,24),(24,32,1,2,0,1),(32,32,3,2,1,32),(32,96,1,2,0,1)]
    for i,(ic,oc,k,s,pad,groups) in enumerate(configs,1):
        n=dict(kind='conv',inputs=[i-1],weight=torch.zeros(oc,ic//groups,k,k),stride=s,pad=pad,groups=groups,relu=i<5,relu6=i<5)
        g.nodes.append(n);g.quant[i]=dict(weight=torch.randint(-3,4,(oc,ic//groups,k,k),dtype=torch.int32),bias=torch.randint(-30,31,(oc,),dtype=torch.int32),multiplier=torch.full((oc,),1<<26,dtype=torch.int64));g.scales[i]=.05
    g.nodes.append(dict(kind='add',inputs=[5,5]));g.quant[6]=dict(multipliers=[1<<27,1<<27]);g.scales[6]=.05;g.fa=4;g.fb=6
    g.input_m=[int(round((1<<48)/(64*64*255*s*.025))) for s in [.229,.224,.225]]
    g.input_b=[int(round(-m/(s*.025)*(1<<48))) for m,s in zip([.485,.456,.406],[.229,.224,.225])]
    rgb=np.fromfunction(lambda y,x,c:(y*31+x*17+c*71)%256,(9,13,3),dtype=int).astype('u1');Image.fromarray(rgb).save(a.out/'input.png')
    codes=g.forward(a.out/'input.png',integer=True,output_codes=True)
    pw=torch.randint(-500,501,(128,64),dtype=torch.int32);bias=torch.randint(-10000,10001,(64,),dtype=torch.int64);centers=torch.randint(-300,301,(5,64),dtype=torch.int32)
    scores=integer_scores(project(codes,pw,bias,6),centers,4).numpy().astype('<u4');threshold=int((scores.min()+scores.max())//2)
    head=dict(projection=pw.numpy(),bias=bias.numpy(),centers=centers.numpy(),shift=6,threshold=threshold,input_m=g.input_m,input_b=g.input_b)
    metadata=export(a.out,dict(nodes=g.nodes,quant=g.quant,scales=g.scales,fa=4,fb=6),head,32)
    (a.out/'model.bin').rename(a.out/'test_model.bin')
    packed=(rgb[:,:,0].astype('<u4')<<16)|(rgb[:,:,1].astype('<u4')<<8)|rgb[:,:,2].astype('<u4');packed.tofile(a.out/'test_rgb.bin')
    # Integer bilinear mask at the original image dimensions.
    mask=[]
    for y in range(9):
        for x in range(13):
            xx=min(max((2*x+1)*4-13,0),3*26);yy=min(max((2*y+1)*4-9,0),3*18)
            x0=xx//26;y0=yy//18;x1=min(x0+1,3);y1=min(y0+1,3);fx=xx%26;fy=yy%18
            top=int(scores[y0,x0])*(26-fx)+int(scores[y0,x1])*fx;bottom=int(scores[y1,x0])*(26-fx)+int(scores[y1,x1])*fx
            mask.append(top*(18-fy)+bottom*fy>threshold*26*18)
    result=np.zeros(149,dtype='<u4');result[:9]=[0x17000001,0,int(scores.max())>threshold,int(scores.max()),threshold,4,sum(mask),117,6]
    result[16:32]=scores.ravel();result[32:]=mask;result.tofile(a.out/'test_expected.bin');print(metadata['model_bytes'],scores,threshold,sum(mask),flush=True)
if __name__=='__main__':main()
