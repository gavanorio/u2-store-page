import bpy,sys,time,os,mathutils
sys.path.insert(0,'/home/claude/u2r')
import rlib,re
rlib.HIDE_PAT=re.compile(rlib.HIDE_PAT.pattern+'|pogo',re.I)
t=time.time()
liv=sys.argv[1]; item=sys.argv[2]
OUT='/home/claude/u2r/out/final2/'; os.makedirs(OUT,exist_ok=True)
if os.path.exists(OUT+item+'.png'): sys.exit()
bpy.ops.wm.open_mainfile(filepath='/home/claude/u2r/scene_ground.blend')
rlib.fix_materials()
sc=rlib.setup_render(2790,1020,samples=48); sc.render.use_persistent_data=False; sc.cycles.debug_use_compact_bvh=True
sc.render.film_transparent=True; sc.render.image_settings.color_mode='RGBA'
sunL=rlib.add_sun('KeyL',(-0.55,0.2,-0.8),3.2,angle=30)
sunR=rlib.add_sun('KeyR',(0.55,0.2,-0.8),3.2,angle=30)
NOSE={'U2S-USAF-6810329-Hawk':1,'U2S-USAF-801067':2}
def cfg(nose): return {'U2_NOSE_SELECT':nose,'U2_SUPERPODS':0,'U2_VARIANT':2,'U2_SPAN':1,'SIM ON GROUND':1,'RETRACT LEFT FLOAT EXTENDED':0,'RETRACT RIGHT FLOAT EXTENDED':0}
# art: (file, livery, nose, side, center_y, center_z, ortho)
ART=[('artw_nose_801069_left','U2S-USAF-801069',0,'L',-8.50,0.47,4.35),
     ('artw_nose_801069','U2S-USAF-801069',0,'R',-8.50,0.47,4.35),
     ('artw_nose_801077','U2S-USAF-801077',0,'R',-8.50,0.47,4.35),
     ('artw_nose_801094','U2S-USAF-801094',0,'L',-8.50,0.47,4.35),
     ('artw_span_801077','U2S-USAF-801077',0,'R',0.87,1.98,5.1),
     ('artw_span_801067','U2S-USAF-801067',2,'R',0.87,1.98,5.1),
     ('artw_nose_6810329_hawk','U2S-USAF-6810329-Hawk',1,'L',-8.45,0.47,4.35),
     ('artw_nose_801067','U2S-USAF-801067',2,'R',-7.05,0.62,5.7),
     ('artw_nose_801099','U2S-USAF-801099',0,'L',-7.75,0.62,5.7)]
def strip(down):
    for o in [o for o in bpy.data.objects if o.type=='MESH' and o.hide_render]: bpy.data.objects.remove(o,do_unlink=True)
    bpy.data.orphans_purge(do_local_ids=True,do_linked_ids=True,do_recursive=True)
    if down:
        for im in bpy.data.images:
            k=im.get('key','')
            if im.size[0]>1024 and 'albd' not in k and 'alb' not in k and 'decal' not in k: im.scale(1024,1024)
            elif im.size[0]>2048 and 'decal' not in k: im.scale(2048,2048)
rlib.set_livery(liv)
if item.startswith('liv_'):
    rlib.apply_config(cfg(NOSE.get(liv,0)))
    mn,mx=rlib.bounds(); print('BOUNDS',mn,mx,flush=True)
    sunR.hide_render=True
    cz=(mn[2]+mx[2])/2; cy=(mn[1]+mx[1])/2
    # frame: aircraft length 84% of the width; ground line at a fixed height
    osc=(mx[1]-mn[1])/0.84; hgt=osc*510/1395
    zc=mn[2]+hgt*0.40
    rlib.camera((80,cy,zc),(0,cy,zc),ortho=osc)
    strip(True)
    w,h=2790,1020
    open(OUT+item+'.json','w').write('{"ground_frac":%f}'%(0.5+ (zc-mn[2])/hgt))
else:
    a=[a for a in ART if a[0]==item][0]
    f,l,nose,s,cy,cz,osc=a
    rlib.apply_config(cfg(nose))
    sunL.hide_render=(s!='L'); sunR.hide_render=(s!='R')
    x=48 if s=='L' else -48
    rlib.camera((x,cy,cz),(0,cy,cz),ortho=osc)
    hh=osc*940/2600/2+0.3; hw=osc/2+0.3
    for o in bpy.data.objects:
        if o.type=='MESH' and not o.hide_render:
            ws=[o.matrix_world@mathutils.Vector(c) for c in o.bound_box]
            ys=[v.y for v in ws]; zs=[v.z for v in ws]
            if max(ys)<cy-hw or min(ys)>cy+hw or max(zs)<cz-hh or min(zs)>cz+hh: o.hide_render=True
    strip(False)
    w,h=2600,940
sc.render.resolution_x=w; sc.render.resolution_y=h; sc.render.filepath=OUT+item+'.png'
bpy.ops.render.render(write_still=True); print('RENDER',item,round(time.time()-t),flush=True)
