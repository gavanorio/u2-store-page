# Patch the glTF files: unique node names, texture URIs to the WebP set, chosen animation key baked into node TRS.
import json,os,struct,sys,numpy as np
M=json.load(open('manifest.json'))
H=M['hash']
base={}
for a,d in M['base'].items():
    os.makedirs('texl/'+a,exist_ok=True); base[a]={}
    for f,p in d.items():
        l='texl/%s/%s.webp'%(a,f.lower()[:-4])
        if not os.path.exists(l): os.link('tex/'+H[p]+'.webp',l)
        base[a][f.lower()]=os.path.abspath(l)
def tex(att,uri):
    n=os.path.basename(uri).lower()
    return base[att].get(n) or base['_U2CommonFuselage'].get(n)
CT={5126:('f',4),5123:('H',2),5125:('I',4),5121:('B',1),5120:('b',1),5122:('h',2)}
NC={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
def acc(g,buf,i):
    a=g['accessors'][i]; bv=g['bufferViews'][a['bufferView']]
    fmt,sz=CT[a['componentType']]; n=NC[a['type']]
    off=bv.get('byteOffset',0)+a.get('byteOffset',0)
    stride=bv.get('byteStride',sz*n)
    out=np.zeros((a['count'],n))
    for k in range(a['count']):
        out[k]=struct.unpack_from('<'+fmt*n,buf,off+k*stride)
    return out
# key choice: fraction of the animation length
KEY={'Front_Gear':None,'Back_Gear':None}  # filled by argument
def keyfrac(name,gear):
    n=name.lower()
    if n in('front_gear','back_gear'): return gear
    if 'wing_flex' in n: return 0.5
    if any(k in n for k in('elevator','rudder','aileron','trimtab','servotab','stabilizer_trim','rollspoiler')): return 0.5
    if 'syers_nose_rotation' in n: return 0.5
    return 0.0
def run(att,fn,gear,flexfrac=None):
    p='model/%s/%s'%(att,fn)
    g=json.load(open(p)); buf=open(p.replace('.gltf','.bin'),'rb').read()
    info={'anims':{}}
    for a in g.get('animations',[]):
        fr=keyfrac(a.get('name',''),gear)
        if flexfrac is not None and 'wing_flex' in a.get('name','').lower(): fr=flexfrac
        tmax=0
        for ch in a['channels']:
            s=a['samplers'][ch['sampler']]; t=acc(g,buf,s['input']); tmax=max(tmax,t[-1,0])
        for ch in a['channels']:
            s=a['samplers'][ch['sampler']]; t=acc(g,buf,s['input'])[:,0]; v=acc(g,buf,s['output'])
            tt=fr*tmax
            k=int(np.argmin(abs(t-tt)))
            if s.get('interpolation')=='CUBICSPLINE': val=v[3*k+1]
            else:
                # linear interpolation
                j=int(np.searchsorted(t,tt)); j=min(max(j,1),len(t)-1) if len(t)>1 else 0
                if len(t)>1:
                    w=(tt-t[j-1])/max(t[j]-t[j-1],1e-9); w=min(max(w,0),1)
                    val=v[j-1]*(1-w)+v[j]*w
                    if ch['target']['path']=='rotation':
                        a0,b0=v[j-1],v[j]
                        if np.dot(a0,b0)<0: b0=-b0
                        val=a0*(1-w)+b0*w; val/=np.linalg.norm(val)
                else: val=v[0]
            node=g['nodes'][ch['target']['node']]
            node.pop('matrix',None)
            node[ch['target']['path']]=[float(x) for x in val]
        info['anims'][a.get('name')]=(fr,float(tmax),len(a['channels']))
    g.pop('animations',None)
    names={}
    for i,n in enumerate(g['nodes']):
        names[i]=n.get('name','node')
        n['name']='n%d_%s'%(i,n.get('name','node'))
    miss=[]
    for im in g.get('images',[]):
        t=tex(att,im['uri'])
        if t: im['uri']=os.path.relpath(t,os.path.dirname(os.path.abspath(p))); im['mimeType']='image/webp'; im['name']=os.path.basename(im.get('name') or '')
        else: miss.append(im['uri'])
    for i,im in enumerate(g.get('images',[])): im['name']='IMG_'+att+'_'+str(i)
    out=p.replace('.gltf','.pose.gltf')
    json.dump(g,open(out,'w'))
    info['names']=names; info['missing']=miss
    info['parents']={c:i for i,n in enumerate(g['nodes']) for c in n.get('children',[])}
    info['mats']=[(m['name'],m.get('alphaMode','OPAQUE'),list(m.get('extensions',{}).keys())) for m in g.get('materials',[])]
    return info
if __name__=='__main__':
    gear=float(sys.argv[1]) if len(sys.argv)>1 else 0.0
    files={'_U2CommonFuselage':'_U2CommonFuselage_LOD00.gltf','_ASARS2':'_ASARS2.gltf','_IR_EO_CAMERA':'_IR_EO_CAMERA.gltf','_SPAN':'_SPAN.gltf','_SPAN_NOSE':'_SPAN_NOSE.gltf','_U2SCanopy':'_U2SCanopy.gltf'}
    allinfo={}
    for a,f in files.items():
        allinfo[a]=run(a,f,gear)
        print(a,'missing',allinfo[a]['missing'])
        for k,v in allinfo[a]['anims'].items(): print('   ',k,v)
    json.dump(allinfo,open('nodeinfo.json','w'))
