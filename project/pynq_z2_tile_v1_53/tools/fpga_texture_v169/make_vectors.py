from pathlib import Path
import argparse,numpy as np,torch,torch.nn.functional as F

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    torch.manual_seed(169);rng=np.random.default_rng(169)
    blob=np.zeros(64+96*16,np.uint32);chunks=[];position=len(blob)
    def data(v):
        nonlocal position
        v=np.asarray(v,dtype='<f4').ravel().view('<u4');offset=position;position+=len(v);chunks.append(v);return offset
    tasks=[]
    def conv(src,dst,weight,bias):
        tasks.append([1,src,dst,data(weight.numpy()),data(bias.numpy()),16,16,3,8,3,2,1,0,0,0,0])
    wa=torch.randn(8,3,3,3)*.035;ba=torch.randn(8)*.02;wb=torch.randn(8,3,3,3)*.035;bb=torch.randn(8)*.02
    conv(0,1024,wa,ba);conv(0,1536,wb,bb)
    tasks.append([3,1024,2048,1536,0,512,0,0,0,0,0,0,0,0,0,0])
    def pool(op,src,dst,h,w,stride):tasks.append([op,src,dst,0,0,h,w,8,0,3,stride,1,0,0,0,0])
    pool(2,2048,2560,8,8,2);pool(4,2560,2688,4,4,1)
    pool(2,2560,2816,4,4,2);pool(4,2816,2848,2,2,1)
    projection=torch.randn(16,8)*.2;mean=torch.randn(16)*.02;centers=torch.randn(4,8)*.1
    po=data(projection.T.numpy());mo=data(mean.numpy());co=data(centers.numpy())
    image=rng.integers(0,256,(9,13,3),np.uint8);x=torch.from_numpy(image).permute(2,0,1)[None].float()/255
    x=F.interpolate(x,(16,16),mode='bilinear',align_corners=False)
    x=(x-torch.tensor([.485,.456,.406])[None,:,None,None])/torch.tensor([.229,.224,.225])[None,:,None,None]
    x=F.relu(F.conv2d(x,wa,ba,2,1)+F.conv2d(x,wb,bb,2,1));x=F.max_pool2d(x,3,2,1)
    fa=F.avg_pool2d(x,3,1,1);fb=F.avg_pool2d(F.max_pool2d(x,3,2,1),3,1,1);fb=F.interpolate(fb,(4,4),mode='bilinear',align_corners=False)
    f=torch.cat([fa,fb],1)[0].permute(1,2,0).reshape(16,16);q=(f-mean)@projection
    raw=torch.sqrt(((q[:,None,:]-centers[None,:,:])**2).sum(2).min(1).values).reshape(1,1,4,4)
    score=F.avg_pool2d(F.pad(raw,(1,1,1,1),mode='replicate'),3,1)
    threshold=float(score.median());mask=F.interpolate(score,(9,13),mode='bilinear',align_corners=False)[0,0]>threshold
    blob[:32]=[0x16900001,position,len(tasks),16,4,8,4,0,3000,3200,3216,2688,2848,po,mo,co,np.float32(threshold).view(np.uint32),4000,0,0,8,8]+[0]*10
    for i,t in enumerate(tasks):blob[64+i*16:80+i*16]=t
    np.concatenate([blob]+chunks).astype('<u4').tofile(a.out/'test_model.bin')
    packed=(image[:,:,0].astype(np.uint32)<<16)|(image[:,:,1].astype(np.uint32)<<8)|image[:,:,2].astype(np.uint32)
    packed.astype('<u4').tofile(a.out/'test_rgb.bin')
    result=np.zeros(32+117,np.uint32);result[:9]=[0x16900001,0,int(score.max()>threshold),np.float32(score.max()).view(np.uint32),np.float32(threshold).view(np.uint32),4,int(mask.sum()),117,len(tasks)]
    result[16:32]=score.numpy().astype('<f4').reshape(-1).view('<u4');result[32:]=mask.numpy().ravel().astype(np.uint32);result.astype('<u4').tofile(a.out/'test_expected.bin')

if __name__=='__main__':main()
