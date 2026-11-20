import bpy,sys,time,os,json
sys.path.insert(0,'/home/claude/u2r')
import rlib
t=time.time()
bpy.ops.wm.open_mainfile(filepath='/home/claude/u2r/scene_raw.blend')
rlib.fix_materials()
sc=rlib.setup_render(2790,1020,samples=48); sc.render.use_persistent_data=False; sc.cycles.debug_use_compact_bvh=True
sunL=rlib.add_sun('KeyL',(-0.55,0.25,-0.8),3.2,angle=30)
sunR=rlib.add_sun('KeyR',(0.55,0.25,-0.8),3.2,angle=30)
GREY=(0.604,0.639,0.671); WHITE=(1,1,1)
OUT='/home/claude/u2r/out/final/'; os.makedirs(OUT,exist_ok=True)
NOSE={'U2S-USAF-6810329-Hawk':1,'U2S-USAF-801067':2}
SIDE={'U2S-USAF-801067':'R'}
def cfg(nose): return {'U2_NOSE_SELECT':nose,'U2_SUPERPODS':0,'U2_VARIANT':2,'U2_SPAN':1}
def side(s):
    sunL.hide_render=(s!='L'); sunR.hide_render=(s!='R')
    return 75 if s=='L' else -75
def render(name,w,h):
    f=OUT+name+'.png'
    sc.render.resolution_x=w; sc.render.resolution_y=h; sc.render.filepath=f
    bpy.ops.render.render(write_still=True); print('RENDER',name,round(time.time()-t),flush=True)
# art: (file, livery, nose, side, center_y, center_z, ortho)
ART=[('artw_nose_801069','U2S-USAF-801069',0,'R',-8.50,0.47,4.35),
     ('artw_nose_801069_left','U2S-USAF-801069',0,'L',-8.50,0.47,4.35),
     ('artw_nose_801077','U2S-USAF-801077',0,'R',-8.50,0.47,4.35),
     ('artw_nose_801094','U2S-USAF-801094',0,'R',-8.50,0.47,4.35),
     ('artw_span_801077','U2S-USAF-801077',0,'R',0.87,1.98,5.1),
     ('artw_span_801067','U2S-USAF-801067',2,'R',0.87,1.98,5.1),
     ('artw_nose_6810329_hawk','U2S-USAF-6810329-Hawk',1,'L',-8.45,0.47,4.35),
     ('artw_nose_801067','U2S-USAF-801067',2,'R',-7.05,0.62,5.7),
     ('artw_nose_801099','U2S-USAF-801099',0,'L',-7.75,0.62,5.7)]
only=sys.argv[1] if len(sys.argv)>1 else ''
item=sys.argv[2] if len(sys.argv)>2 else ''
def strip(down):
    for o in [o for o in bpy.data.objects if o.type=='MESH' and o.hide_render]: bpy.data.objects.remove(o,do_unlink=True)
    bpy.data.orphans_purge(do_local_ids=True,do_linked_ids=True,do_recursive=True)
    if down:
        for im in bpy.data.images:
            k=im.get('key','')
            if im.size[0]>1024 and 'albd' not in k and 'alb' not in k and 'decal' not in k: im.scale(1024,1024)
            elif im.size[0]>2048 and 'decal' not in k: im.scale(2048,2048)
    print('STRIP objs',len(bpy.data.objects),'imgs',len(bpy.data.images),flush=True)
for liv in sorted(rlib.LIV):
    name='liv_'+liv.lower()
    arts=[a for a in ART if a[1]==liv]
    todo=[x for x in [name]+[a[0] for a in arts] if not os.path.exists(OUT+x+'.png') and (not item or x==item)]
    if only and only != liv: continue
    if not todo: continue
    rlib.set_livery(liv)
    if name in todo:
        rlib.set_bg(GREY); rlib.apply_config(cfg(NOSE.get(liv,0)))
        x=side(SIDE.get(liv,'L'))
        rlib.camera((x,-0.3,8.5),(0,-0.3,1.55),lens=116); sc.cycles.texture_limit_render='2048'
        if item: strip(True)
        render(name,2790,1020)
    for (f,l,nose,s,cy,cz,osc) in arts:
        if f not in todo: continue
        rlib.set_bg(WHITE); rlib.apply_config(cfg(nose))
        x=side(s)
        rlib.camera((x*0.6,cy,cz),(0,cy,cz),ortho=osc); sc.cycles.texture_limit_render='OFF'
        import mathutils
        hh=osc*940/2600/2+0.3; hw=osc/2+0.3
        for o in bpy.data.objects:
            if o.type=='MESH' and not o.hide_render:
                ws=[o.matrix_world@mathutils.Vector(c) for c in o.bound_box]
                ys=[w.y for w in ws]; zs=[w.z for w in ws]
                if max(ys)<cy-hw or min(ys)>cy+hw or max(zs)<cz-hh or min(zs)>cz+hh: o.hide_render=True
        if item: strip(False)
        render(f,2600,940)
print('ALLDONE',round(time.time()-t))
