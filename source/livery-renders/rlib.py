import bpy,json,os,re,math,time,mathutils
from vis import rules
ROOT=os.path.dirname(os.path.abspath(__file__))
M=json.load(open(ROOT+'/manifest.json')); H=M['hash']
INFO=json.load(open(ROOT+'/nodeinfo.json'))
LIV={l:{f.lower()[:-4]:ROOT+'/tex/'+H[p]+'.webp' for f,p in d.items()} for l,d in M['liv'].items()}
RULES={'_U2CommonFuselage':rules(ROOT+'/model/_U2CommonFuselage/U2_Preflight_FS24.xml')+rules(ROOT+'/model/_U2CommonFuselage/U2_FlightSystems_FS20.xml')}
for a in ['_ASARS2','_IR_EO_CAMERA','_SPAN','_SPAN_NOSE','_U2SCanopy']: RULES[a]=rules(ROOT+'/model/%s/%s.xml'%(a,a))
def rpn(code,V):
    toks=re.findall(r'\([^)]*\)|if\{|els\{|\}|[^\s]+',code)
    def run(i,st,execu=True):
        while i<len(toks):
            t=toks[i]
            if t=='}': return i
            if t=='if{':
                c=st.pop() if execu else 0
                j=run(i+1,st,execu and bool(c)); i=j
                if i+1<len(toks) and toks[i+1]=='els{':
                    j=run(i+2,st,execu and not bool(c)); i=j
            elif not execu: pass
            elif t.startswith('('):
                m=re.match(r'\((\w):([^,]+),',t); st.append(float(V.get(m.group(2).strip(),0)) if m else 0.0)
            elif t in('==','!=','<','>','<=','>=','and','or','+','-','*','/','max','min'):
                b=st.pop(); a=st.pop()
                st.append({'==':a==b,'!=':a!=b,'<':a<b,'>':a>b,'<=':a<=b,'>=':a>=b,'and':bool(a) and bool(b),'or':bool(a) or bool(b),'+':a+b,'-':a-b,'*':a*b,'/':a/b if b else 0,'max':max(a,b),'min':min(a,b)}[t]*1.0)
            elif t=='!': st.append(0.0 if st.pop() else 1.0)
            elif t=='abs': st.append(abs(st.pop()))
            else:
                try: st.append(float(t))
                except: st.append(0.0)
            i+=1
        return i
    st=[]; run(0,st)
    return bool(st[-1]) if st else False
HIDE_PAT=re.compile(r'frost|clickspot|embiggener|RBF|U2_Tag_|^Covers|Chocks|_blurred|PILOT|AP_LIGHT',re.I)
def objinfo(o):
    m=re.match(r'n(\d+)_(.*)',o.name)
    att=o.get('att')
    if not m or not att: return None,None,None
    idx=int(m.group(1)); return att,idx,INFO[att]['names'][str(idx)]
def apply_config(V):
    """V: dict of L-vars. Sets hide_render on every object."""
    byatt={}
    for o in bpy.data.objects:
        att,idx,name=objinfo(o)
        if att is None: continue
        byatt.setdefault(att,{})[idx]=(o,name)
    for att,d in byatt.items():
        hidden=set()
        vis={}
        for node,code,cid in RULES.get(att,[]): vis.setdefault(node,[]).append(code)
        for idx,(o,name) in d.items():
            h=bool(HIDE_PAT.search(name))
            for code in vis.get(name,[]):
                if not rpn(code,V): h=True
            if h: hidden.add(idx)
        par=INFO[att]['parents']
        names=INFO[att]['names']
        # nodes that became bones or were skipped: evaluate by name too
        allhid=set(hidden)
        for i,nm in names.items():
            i=int(i)
            if i in d: continue
            h=bool(HIDE_PAT.search(nm))
            for code in vis.get(nm,[]):
                if not rpn(code,V): h=True
            if h: allhid.add(i)
        def ishid(i):
            while i is not None:
                if i in allhid: return True
                i=par.get(str(i))
            return False
        for idx,(o,name) in d.items():
            h=ishid(idx)
            if o.type=='MESH':
                mats=[s.material for s in o.material_slots if s.material]
                if mats and all(m.get('invisible') for m in mats): h=True
            o.hide_render=h; o.hide_viewport=h
def fix_materials():
    G={a:json.load(open(ROOT+'/model/%s/%s'%(a,f))) for a,f in [('_U2CommonFuselage','_U2CommonFuselage_LOD00.gltf'),('_ASARS2','_ASARS2.gltf'),('_IR_EO_CAMERA','_IR_EO_CAMERA.gltf'),('_SPAN','_SPAN.gltf'),('_SPAN_NOSE','_SPAN_NOSE.gltf'),('_U2SCanopy','_U2SCanopy.gltf')]}
    ext={}
    for a,g in G.items():
        for m in g['materials']: ext[(a,m['name'])]=m
    for m in bpy.data.materials:
        a=m.get('att'); base=re.sub(r'\.\d{3}$','',m.name)
        gm=ext.get((a,m.name)) or ext.get((a,base)) or {}
        e=gm.get('extensions',{})
        if 'ASOBO_material_invisible' in e or 'frost' in m.name.lower() or 'Invisible' in m.name: m['invisible']=1
        if not m.use_nodes: continue
        nt=m.node_tree
        bs=[n for n in nt.nodes if n.type=='BSDF_PRINCIPLED']
        gb=e.get('ASOBO_material_blend_gbuffer')
        if gb and bs and not m.get('invisible'):
            f=gb.get('baseColorBlendFactor',1)
            if f<1:
                f=0.32 if f>=0.1 else 0.15
                a=bs[0].inputs['Alpha']
                if a.links:
                    src=a.links[0].from_socket
                    mul=nt.nodes.new('ShaderNodeMath'); mul.operation='MULTIPLY'; mul.inputs[1].default_value=f
                    nt.links.new(src,mul.inputs[0]); nt.links.new(mul.outputs[0],a)
                else: a.default_value*=f
        if ('WINDSHIELD' in m.name.upper() or 'ASOBO_material_windshield' in e) and bs:
            b=bs[0]
            for l in list(b.inputs['Base Color'].links): nt.links.remove(l)
            for l in list(b.inputs['Alpha'].links): nt.links.remove(l)
            amber='AMBER' in m.name.upper()
            b.inputs['Base Color'].default_value=(0.45,0.3,0.15,1) if amber else (0.16,0.27,0.42,1)
            b.inputs['Alpha'].default_value=0.62; b.inputs['Roughness'].default_value=0.06; b.inputs['Metallic'].default_value=0.0
            m['glass']=1
        for n in list(nt.nodes):
            if n.type=='NORMAL_MAP':
                l=n.inputs['Color'].links
                if l:
                    src=l[0].from_socket
                    sep=nt.nodes.new('ShaderNodeSeparateColor'); inv=nt.nodes.new('ShaderNodeMath'); inv.operation='SUBTRACT'; inv.inputs[0].default_value=1.0
                    comb=nt.nodes.new('ShaderNodeCombineColor')
                    nt.links.new(src,sep.inputs[0]); nt.links.new(sep.outputs[0],comb.inputs[0]); nt.links.new(sep.outputs[1],inv.inputs[1]); nt.links.new(inv.outputs[0],comb.inputs[1]); nt.links.new(sep.outputs[2],comb.inputs[2])
                    nt.links.new(comb.outputs[0],n.inputs['Color'])
            if n.type=='BSDF_PRINCIPLED':
                for k in ('Emission Strength',):
                    if k in n.inputs: n.inputs[k].default_value=0
def set_livery(name):
    liv=LIV.get(name,{})
    n=0
    for im in bpy.data.images:
        if im.packed_file:
            try: im.unpack(method='REMOVE')
            except Exception as ex: print('unpack',im.name,ex)
        fp=bpy.path.abspath(im.filepath)
        if '/texl/' not in fp and '/tex/' not in fp: continue
        if 'key' not in im.keys(): im['key']=os.path.basename(fp)[:-5]; im['basepath']=fp
        want=liv.get(im['key'],im['basepath'])
        if bpy.path.abspath(im.filepath)!=want:
            im.filepath=want; n+=1
    return n
def setup_render(w,h,samples=32,bg=(0.604,0.639,0.671)):
    sc=bpy.context.scene
    sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=samples
    sc.cycles.use_denoising=True
    try: sc.cycles.denoiser='OPENIMAGEDENOISE'
    except Exception as e: print('den',e)
    sc.cycles.max_bounces=3; sc.cycles.diffuse_bounces=2; sc.cycles.glossy_bounces=2; sc.cycles.transparent_max_bounces=12; sc.cycles.transmission_bounces=4
    sc.cycles.use_adaptive_sampling=True; sc.cycles.adaptive_threshold=0.03
    sc.cycles.texture_limit_render='OFF'
    sc.render.resolution_x=w; sc.render.resolution_y=h; sc.render.resolution_percentage=100
    sc.render.use_persistent_data=True
    sc.render.threads_mode='AUTO'
    sc.view_settings.view_transform='Standard'; sc.view_settings.look='None'
    sc.render.image_settings.file_format='PNG'; sc.render.image_settings.color_mode='RGB'
    sc.render.film_transparent=False
    w_=bpy.data.worlds.new('W') if not bpy.data.worlds else bpy.data.worlds[0]
    sc.world=w_; w_.use_nodes=True; nt=w_.node_tree; nt.nodes.clear()
    out=nt.nodes.new('ShaderNodeOutputWorld'); mix=nt.nodes.new('ShaderNodeMixShader'); lp=nt.nodes.new('ShaderNodeLightPath')
    amb=nt.nodes.new('ShaderNodeBackground'); amb.name='AMB'; amb.inputs[0].default_value=(1,1,1,1); amb.inputs[1].default_value=1.5
    cam=nt.nodes.new('ShaderNodeBackground'); cam.name='CAMBG'; cam.inputs[0].default_value=(*[srgb2lin(c) for c in bg],1); cam.inputs[1].default_value=1
    nt.links.new(lp.outputs['Is Camera Ray'],mix.inputs[0]); nt.links.new(amb.outputs[0],mix.inputs[1]); nt.links.new(cam.outputs[0],mix.inputs[2]); nt.links.new(mix.outputs[0],out.inputs[0])
    return sc
def set_bg(rgb):
    n=bpy.context.scene.world.node_tree.nodes['CAMBG']; n.inputs[0].default_value=(*[srgb2lin(c) for c in rgb],1)
def srgb2lin(c): return c/12.92 if c<=0.04045 else ((c+0.055)/1.055)**2.4
def add_sun(name,rot_deg,strength,angle=20):
    d=bpy.data.lights.new(name,'SUN'); d.energy=strength; d.angle=math.radians(angle)
    o=bpy.data.objects.new(name,d); bpy.context.scene.collection.objects.link(o)
    o.rotation_euler=mathutils.Vector(rot_deg).to_track_quat('-Z','Y').to_euler(); return o
def camera(loc,target,lens=None,ortho=None,name='Cam'):
    c=bpy.data.objects.get(name)
    if not c:
        c=bpy.data.objects.new(name,bpy.data.cameras.new(name)); bpy.context.scene.collection.objects.link(c)
    c.location=loc
    d=mathutils.Vector(target)-mathutils.Vector(loc)
    c.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
    if ortho: c.data.type='ORTHO'; c.data.ortho_scale=ortho
    else: c.data.type='PERSP'; c.data.lens=lens
    c.data.clip_start=0.5; c.data.clip_end=2000
    bpy.context.scene.camera=c; return c
def bounds(pred=lambda o:True):
    mn=[1e9]*3; mx=[-1e9]*3
    for o in bpy.data.objects:
        if o.type=='MESH' and not o.hide_render and pred(o):
            for c in o.bound_box:
                w=o.matrix_world@mathutils.Vector(c)
                for k in range(3): mn[k]=min(mn[k],w[k]); mx[k]=max(mx[k],w[k])
    return mn,mx
