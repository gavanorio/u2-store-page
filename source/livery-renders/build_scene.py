import bpy,json,os,sys,time
t0=time.time()
bpy.ops.wm.read_factory_settings(use_empty=True)
files={'_U2CommonFuselage':'_U2CommonFuselage_LOD00.pose.gltf','_ASARS2':'_ASARS2.pose.gltf','_IR_EO_CAMERA':'_IR_EO_CAMERA.pose.gltf','_SPAN':'_SPAN.pose.gltf','_SPAN_NOSE':'_SPAN_NOSE.pose.gltf','_U2SCanopy':'_U2SCanopy.pose.gltf'}
for att,f in files.items():
    before=set(bpy.data.objects); bm=set(bpy.data.materials); bi=set(bpy.data.images)
    bpy.ops.import_scene.gltf(filepath=os.path.abspath('model/%s/%s'%(att,f)),merge_vertices=False,import_shading='NORMALS')
    for o in set(bpy.data.objects)-before: o['att']=att
    for m in set(bpy.data.materials)-bm: m['att']=att
    for i in set(bpy.data.images)-bi: i['att']=att
    print('IMPORTED',att,len(set(bpy.data.objects)-before),time.time()-t0,flush=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath('scene_raw.blend'))
import mathutils
mn=[1e9]*3; mx=[-1e9]*3
for o in bpy.data.objects:
    if o.type=='MESH' and o.get('att')=='_U2CommonFuselage':
        for c in o.bound_box:
            w=o.matrix_world@mathutils.Vector(c)
            for k in range(3): mn[k]=min(mn[k],w[k]); mx[k]=max(mx[k],w[k])
print('BOUNDS',mn,mx)
print('OBJ',len(bpy.data.objects),'MESH',len([o for o in bpy.data.objects if o.type=='MESH']),'ARM',[o.name for o in bpy.data.objects if o.type=='ARMATURE'],'IMG',len(bpy.data.images),'MAT',len(bpy.data.materials))
print('TRIS',sum(len(o.data.loop_triangles) or len(o.data.polygons) for o in bpy.data.objects if o.type=='MESH'))
