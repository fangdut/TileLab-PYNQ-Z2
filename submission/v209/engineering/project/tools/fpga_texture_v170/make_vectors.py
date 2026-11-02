"""Small complete graph: 3x3/1x1, stride2, depthwise24, residual, PCA, NN, mask."""
from pathlib import Path
import argparse,numpy as np,torch
from PIL import Image
from prepare_integer import FixedGraph,project,integer_scores
from export_integer import export

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--side',type=int,default=64);p.add_argument('--width',type=int,default=13);p.add_argument('--height',type=int,default=9)
    a=p.parse_args()
    if a.side<32 or a.side>224 or a.side%16 or not 1<=a.width<=1024 or not 1<=a.height<=1024:
        raise ValueError('Use side 32..224 divisible by 16 and input dimensions 1..1024')
    a.out.mkdir(parents=True,exist_ok=False)
    torch.manual_seed(17001);torch.set_num_threads(4);g=FixedGraph.__new__(FixedGraph)
    g.side=a.side;g.feature_dim=128;g.scales={0:.025};g.fixed_input=True;g.nodes=[];g.quant={}
    # The final pointwise layer uses all 576 inputs (72 reduction taps),
    # exercising repeated accumulator-slot wrap and the real network's bound.
    configs=[(3,24,3,2,1,1),(24,24,3,1,1,24),(24,16,1,1,0,1),(16,24,1,1,0,1),(24,32,1,2,0,1),(32,32,3,2,1,32),(32,576,1,2,0,1),(576,96,1,1,0,1)]
    for i,(ic,oc,k,s,pad,groups) in enumerate(configs,1):
        n=dict(kind='conv',inputs=[i-1],weight=torch.zeros(oc,ic//groups,k,k),stride=s,pad=pad,groups=groups,relu=i<7,relu6=i<7)
        g.nodes.append(n);g.quant[i]=dict(weight=torch.randint(-3,4,(oc,ic//groups,k,k),dtype=torch.int32),bias=torch.randint(-30,31,(oc,),dtype=torch.int32),multiplier=torch.full((oc,),1<<26,dtype=torch.int64));g.scales[i]=.05
    g.nodes.append(dict(kind='add',inputs=[8,8]));g.quant[9]=dict(multipliers=[1<<27,1<<27]);g.scales[9]=.05;g.fa=6;g.fb=9
    g.input_m=[int(round((1<<48)/((2*a.side)**2*255*s*.025))) for s in [.229,.224,.225]]
    g.input_b=[int(round(-m/(s*.025)*(1<<48))) for m,s in zip([.485,.456,.406],[.229,.224,.225])]
    rgb=np.fromfunction(lambda y,x,c:(y*31+x*17+c*71)%256,(a.height,a.width,3),dtype=int).astype('u1');Image.fromarray(rgb).save(a.out/'input.png')
    codes=g.forward(a.out/'input.png',integer=True,output_codes=True)
    tensors=g.forward(a.out/'input.png',integer=True,return_values=True)
    for name,index in [('fa',g.fa),('fb',g.fb)]:
        tensor=tensors[index][0].numpy();c,h,w=tensor.shape;packed=np.zeros(((c+15)//16,h,w,16),dtype='i1')
        for channel in range(c):packed[channel//16,:,:,channel%16]=tensor[channel]
        packed.tofile(a.out/('test_'+name+'_expected.bin'))
    pw=torch.randint(-500,501,(128,64),dtype=torch.int32);bias=torch.randint(-10000,10001,(64,),dtype=torch.int64);centers=torch.randint(-300,301,(5,64),dtype=torch.int32)
    grid=a.side//8
    scores=integer_scores(project(codes,pw,bias,6),centers,grid).numpy().astype('<u4');threshold=int((scores.min()+scores.max())//2)
    head=dict(projection=pw.numpy(),bias=bias.numpy(),centers=centers.numpy(),shift=6,threshold=threshold,input_m=g.input_m,input_b=g.input_b)
    metadata=export(a.out,dict(nodes=g.nodes,quant=g.quant,scales=g.scales,fa=6,fb=9),head,a.side)
    (a.out/'model.bin').rename(a.out/'test_model.bin')
    packed=(rgb[:,:,0].astype('<u4')<<16)|(rgb[:,:,1].astype('<u4')<<8)|rgb[:,:,2].astype('<u4');packed.tofile(a.out/'test_rgb.bin')
    # Integer bilinear mask at the original image dimensions.
    mask=[]
    xd=2*a.width;yd=2*a.height
    for y in range(a.height):
        for x in range(a.width):
            xx=min(max((2*x+1)*grid-a.width,0),(grid-1)*xd);yy=min(max((2*y+1)*grid-a.height,0),(grid-1)*yd)
            x0=xx//xd;y0=yy//yd;x1=min(x0+1,grid-1);y1=min(y0+1,grid-1);fx=xx%xd;fy=yy%yd
            top=int(scores[y0,x0])*(xd-fx)+int(scores[y0,x1])*fx;bottom=int(scores[y1,x0])*(xd-fx)+int(scores[y1,x1])*fx
            mask.append(top*(yd-fy)+bottom*fy>threshold*xd*yd)
    pixels=a.width*a.height;score_end=16+grid*grid
    result=np.zeros(score_end+pixels,dtype='<u4');result[:9]=[0x17000001,0,int(scores.max())>threshold,int(scores.max()),threshold,grid,sum(mask),pixels,9]
    result[9]=1
    result[16:score_end]=scores.ravel();result[score_end:]=mask;result.tofile(a.out/'test_expected.bin');print(metadata['model_bytes'],scores,threshold,sum(mask),flush=True)
if __name__=='__main__':main()
