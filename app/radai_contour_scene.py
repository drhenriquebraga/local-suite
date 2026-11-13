"""Bounded, display-only native-grid surfaces; never smooth or edit a mask."""
import numpy as np

MAX_CROP_VOXELS = 12_000_000
MAX_ROI_FACES = 250_000
MAX_SCENE_FACES = 500_000


def scene(session,known=None):
    from skimage.measure import marching_cubes
    from radai_contour_edit import EditError, fail
    if known is None:known={}
    if not isinstance(known,dict) or len(known)>1024 or any(not isinstance(k,str) or type(v) is not int or v<0 for k,v in known.items()):
        fail('INVALID_INPUT','Inventário de prévia inválido.')
    meshes,skipped,total=[],[],0
    for number,roi in sorted(session.rois.items(),key=lambda pair:(pair[0] not in session.dirty,pair[0])):
        if not roi.get('editable',True):
            skipped.append(dict(roi=number,reason='UNSUPPORTED_CONTOUR'));continue
        was_loaded=number in session.masks
        try:
            cached=session.mesh_cache.get(number)
            if cached is None:
                m=session.mask(number)
                occupied=[np.flatnonzero(np.any(m,axis=tuple(j for j in range(3) if j!=i))) for i in range(3)]
                if not len(occupied[0]):
                    cached=dict(vertices=[],faces=[],coordinate_system='LPS_mm',geometry_revision=session.revision)
                else:
                    lo=np.array([v[0] for v in occupied]);hi=np.array([v[-1]+1 for v in occupied]);shape=hi-lo
                    voxels=int(np.prod(shape+2))
                    if voxels>MAX_CROP_VOXELS:fail('RESOURCE_LIMIT','A região excede o limite desta prévia 3D.')
                    session._memory(voxels*16)
                    crop=np.pad(m[tuple(slice(a,b) for a,b in zip(lo,hi))].astype(np.float32),1)
                    vertices,faces,_,_=marching_cubes(crop,level=.5,allow_degenerate=False)
                    if len(faces)>MAX_ROI_FACES:fail('RESOURCE_LIMIT','A superfície excede o limite desta prévia 3D.')
                    ijk=vertices+lo-1
                    lps=session.geo['origin']+(ijk[:,::-1]*np.asarray(session.geo['spacing'][::-1]))@session.geo['direction'].T
                    cached=dict(vertices=np.round(lps,5).tolist(),faces=faces.tolist(),coordinate_system='LPS_mm',geometry_revision=session.revision)
            if total+len(cached['faces'])>MAX_SCENE_FACES:
                skipped.append(dict(roi=number,reason='RESOURCE_LIMIT'));continue
            session.mesh_cache[number]=cached
            total+=len(cached['faces'])
            if known.get(str(number))==cached['geometry_revision']:
                meshes.append(dict(roi=number,name=roi['name'],color=roi['color'],unchanged=True,
                                   coordinate_system='LPS_mm',geometry_revision=cached['geometry_revision']))
            else:meshes.append(dict(roi=number,name=roi['name'],color=roi['color'],**cached))
        except EditError as exc:
            skipped.append(dict(roi=number,reason=exc.code))
        finally:
            # Imported unchanged masks can be rasterized lazily again; the small
            # surface cache avoids retaining a full grid for every existing ROI.
            if not was_loaded and number not in session.dirty:
                session.masks.pop(number,None)
    retained={m['roi'] for m in meshes}
    for number in list(session.mesh_cache):
        if number not in retained:session.mesh_cache.pop(number,None)
    return dict(session=session.id,revision=session.revision,uid=session.geo['uid'],
                frame_uid=session.geo['frame'],meshes=meshes,skipped=skipped)
