import sys,os,json,glob
from PIL import Image,ImageFilter,ImageChops
def compose(png,out_size,ground=None):
    im=Image.open(png).convert('RGBA')
    W,H=im.size
    if ground is not None:
        import numpy as np,math
        a=np.array(im.getchannel('A'))>128
        cols=np.where(a.any(axis=0))[0]; x0,x1=cols[0],cols[-1]
        bot=np.where(a.any(axis=0),H-1-np.argmax(a[::-1],axis=0),-1)
        xs=np.arange(W)
        mL=(xs<x0+0.6*(x1-x0)); mR=(xs>x0+0.7*(x1-x0))
        xm=int(np.argmax(np.where(mL,bot,-1))); xt=int(np.argmax(np.where(mR,bot,-1)))
        ang=math.degrees(math.atan2(bot[xm]-bot[xt],xt-xm))
        im=im.rotate(-ang,resample=Image.BICUBIC,center=(xm,int(bot[xm])))
        a=np.array(im.getchannel('A'))>128
        rows=np.where(a.any(axis=1))[0]; cols=np.where(a.any(axis=0))[0]
        gy=rows[-1]; cx=(cols[0]+cols[-1])//2
        canvas=Image.new('RGBA',(W,H),(0,0,0,0))
        canvas.paste(im,(W//2-cx,int(H*0.86)-gy))
        im=canvas; ground=0.86
        print(os.path.basename(png),'angle',round(ang,2))
    bg=Image.new('RGB',(W,H),'white')
    if ground is not None:
        a=im.getchannel('A')
        sh_h=max(8,int(H*0.050))
        sq=a.resize((W,sh_h),Image.BILINEAR).point(lambda v:int(v*0.55))
        layer=Image.new('L',(W,H),0)
        gy=int(ground*H)
        layer.paste(sq,(0,gy-sh_h//2))
        layer=layer.filter(ImageFilter.GaussianBlur(H*0.012))
        # contact shadow: stronger and tighter
        sq2=a.crop((0,gy-int(H*0.03),W,gy)).resize((W,max(4,int(H*0.012))),Image.BILINEAR)
        l2=Image.new('L',(W,H),0); l2.paste(sq2,(0,gy-2)); l2=l2.filter(ImageFilter.GaussianBlur(H*0.004)).point(lambda v:int(v*0.6))
        layer=ImageChops.lighter(layer,l2)
        bg.paste(Image.new('RGB',(W,H),(40,44,50)),(0,0),layer)
    bg.paste(im,(0,0),im)
    return bg.resize(out_size,Image.LANCZOS)
if __name__=='__main__':
    for f in sorted(glob.glob('out/final2/*.png')):
        n=os.path.basename(f)[:-4]
        if n.startswith('liv_'):
            g=json.load(open(f[:-4]+'.json'))['ground_frac']; im=compose(f,(1395,510),g)
        else: im=compose(f,(1300,470))
        im.save('out/final2/'+n+'.webp','WEBP',quality=88,method=6)
    print('ok')
