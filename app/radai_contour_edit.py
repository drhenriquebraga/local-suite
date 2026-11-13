"""Host-owned contour editing on an unchanged classic CT/MR acquisition grid.

No registration, inferred slice interpolation on import, or source overwrites.
Only edited ROIs pass through ContourLab's writer. Other ROI datasets survive
verbatim (their DICOM values, references and contour coordinates are preserved).
"""
import copy
import hashlib
import io
import math
import os
from pathlib import Path
import secrets
import shutil
import tempfile
import threading
import time

import numpy as np
import pydicom
from pydicom.sequence import Sequence
from pydicom.uid import generate_uid, ImplicitVRLittleEndian

MAX_VOXELS = 128_000_000
MAX_MEMORY = 1536 * 1024**2
MAX_HISTORY = 32 * 1024**2
MAX_HISTORY_ACTIONS = 256
MAX_POINTS = 4096
TTL = 3600
MAX_SESSIONS = 2
PLANES = {'axial': 0, 'coronal': 1, 'sagittal': 2, 'sagital': 2}
_SESSIONS = {}
_LOCK = threading.RLock()


class EditError(ValueError):
    def __init__(self, code, message, status=400):
        super().__init__(message)
        self.code, self.status = code, status


def fail(code, message, status=400):
    raise EditError(code, message, status)


def _finite(value, size=None):
    try:
        a = np.asarray(value, dtype=float)
        if not np.all(np.isfinite(a)) or (size is not None and a.size != size):
            raise ValueError()
        return a
    except (ValueError, TypeError):
        fail('INVALID_INPUT', 'Valores geométricos inválidos.')


def _signature(path):
    st = Path(path).stat()
    return st.st_size, st.st_mtime_ns


def _digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def resolve_ticket(ticket, source='thumbnail', uid=None):
    if not isinstance(ticket, str) or not ticket or len(ticket) > 128:
        fail('INVALID_TICKET', 'Escolha a série novamente.')
    if source == 'archive':
        import radai_tabela_acervo as resolver
    elif source in ('thumbnail', '', None):
        import radai_thumbnail as resolver
    else:
        fail('INVALID_TICKET', 'Origem da série inválida.')
    folder, selected = resolver.resolver(ticket)
    if not folder or not selected or (uid and str(uid) != str(selected)):
        fail('INVALID_TICKET', 'A seleção expirou. Escolha a série novamente.')
    import radai_rt
    files = radai_rt.fatias_da_serie(folder, selected)
    return Path(folder).resolve(), str(selected), files


def load_geometry(files, uid):
    if len(files) < 2 or len(files) > 4096:
        fail('UNSUPPORTED_GEOMETRY', 'A série não possui uma grade de imagem compatível.')
    headers = [pydicom.dcmread(str(p), stop_before_pixels=True, force=True) for p in files]
    first = headers[0]
    if str(first.get('Modality', '')) not in ('CT', 'MR'):
        fail('UNSUPPORTED_GEOMETRY', 'O editor aceita séries clássicas de TC ou RM.')
    orientation = _finite(first.get('ImageOrientationPatient'), 6).reshape(2, 3)
    x, y = orientation
    if not (np.allclose(orientation @ orientation.T, np.eye(2), atol=1e-4)):
        fail('UNSUPPORTED_GEOMETRY', 'Orientação DICOM inválida.')
    z = np.cross(x, y)
    spacing_yx = _finite(first.get('PixelSpacing'), 2)
    rows, cols = int(first.get('Rows', 0)), int(first.get('Columns', 0))
    frame, study, patient = (str(first.get(k, '')) for k in ('FrameOfReferenceUID', 'StudyInstanceUID', 'PatientID'))
    if not frame or not study or rows < 2 or cols < 2 or np.min(spacing_yx) <= 0:
        fail('UNSUPPORTED_GEOMETRY', 'A série não fornece referência espacial completa.')
    if len(files) * rows * cols > MAX_VOXELS:
        fail('RESOURCE_LIMIT', 'Esta série excede o limite de memória do editor.')
    positions, sops = [], set()
    for ds in headers:
        if (int(ds.get('NumberOfFrames', 1)) != 1 or 'PerFrameFunctionalGroupsSequence' in ds
                or str(ds.get('SOPClassUID', '')) not in ('1.2.840.10008.5.1.4.1.1.2', '1.2.840.10008.5.1.4.1.1.4')
                or str(ds.get('SeriesInstanceUID', '')) != uid
                or str(ds.get('FrameOfReferenceUID', '')) != frame
                or str(ds.get('StudyInstanceUID', '')) != study
                or str(ds.get('PatientID', '')) != patient
                or str(ds.get('Modality', '')) != str(first.Modality)
                or str(ds.get('PhotometricInterpretation', '')) != str(first.get('PhotometricInterpretation',''))
                or int(ds.get('Rows', 0)) != rows or int(ds.get('Columns', 0)) != cols
                or int(ds.get('SamplesPerPixel', 1)) != 1
                or not np.allclose(_finite(ds.get('PixelSpacing'), 2), spacing_yx, atol=1e-5)
                or not np.allclose(_finite(ds.get('ImageOrientationPatient'), 6), orientation.ravel(), atol=1e-5)):
            fail('UNSUPPORTED_GEOMETRY', 'Séries Enhanced, misturadas ou com geometria variável ainda não são editáveis.')
        sop = str(ds.get('SOPInstanceUID', ''))
        if not sop or sop in sops:
            fail('UNSUPPORTED_GEOMETRY', 'A série contém imagens repetidas ou sem identificador.')
        sops.add(sop)
        positions.append(_finite(ds.get('ImagePositionPatient'), 3))
    order = np.argsort(np.asarray(positions) @ z)
    headers = [headers[i] for i in order]
    files = [Path(files[i]) for i in order]
    positions = np.asarray(positions)[order]
    projections = positions @ z
    dz = float(np.median(np.diff(projections))) if len(files) > 1 else float(first.get('SliceThickness', 1))
    if (not np.isfinite(dz) or dz <= 0 or (len(files) > 1 and
            not np.allclose(np.diff(projections), dz, atol=max(.01, dz * .001), rtol=0))
            or not np.allclose(positions, positions[0] + np.arange(len(files))[:, None] * dz * z, atol=.01)):
        fail('UNSUPPORTED_GEOMETRY', 'Cortes irregulares, repetidos ou inclinados não serão reamostrados automaticamente.')
    volume = np.empty((len(files), rows, cols), dtype=np.float32)
    for i, path in enumerate(files):
        ds = pydicom.dcmread(str(path), force=True)
        raw = np.asarray(ds.pixel_array)
        if raw.shape != (rows, cols):
            fail('UNSUPPORTED_GEOMETRY', 'Dimensões de pixel incompatíveis.')
        scale, intercept = float(ds.get('RescaleSlope', 1)), float(ds.get('RescaleIntercept', 0))
        if not np.isfinite(scale + intercept):
            fail('UNSUPPORTED_GEOMETRY', 'Escala de pixel inválida.')
        volume[i] = raw.astype(np.float32) * scale + intercept
    return dict(volume=volume, headers=headers, files=files, spacing=(dz, *spacing_yx),
                origin=positions[0], direction=np.column_stack((x, y, z)), frame=frame,
                study=study, patient=patient, uid=uid, mono1=str(first.get('PhotometricInterpretation', '')) == 'MONOCHROME1')


def _plane(a, axis, index):
    return (a[index, :, :] if axis == 0 else a[:, index, :] if axis == 1 else a[:, :, index])


def writer_add_roi(engine,rt,mask,name,color,geometry):
    """Compensate only rt-utils' non-square-pixel matrix, in private headers.

    This is deliberately capability-checked, not a process-wide monkeypatch.
    PixelSpacing stored on disk and every patient's source file stay unchanged.
    """
    from rt_utils import image_helper
    expected=np.eye(4)
    expected[:3,:3]=geometry['direction']*np.asarray(geometry['spacing'][::-1])[None,:]
    expected[:3,3]=geometry['origin']
    actual=image_helper.get_pixel_to_patient_transformation_matrix(rt.series_data)
    saved=[]
    try:
        if not np.allclose(actual,expected,rtol=1e-5,atol=1e-4):
            for ds in rt.series_data:
                saved.append((ds,list(ds.PixelSpacing)))
                ds.PixelSpacing=list(ds.PixelSpacing)[::-1]
            actual=image_helper.get_pixel_to_patient_transformation_matrix(rt.series_data)
            if not np.allclose(actual,expected,rtol=1e-5,atol=1e-4):
                fail('WRITER_GEOMETRY','O gravador não representa esta grade sem alterar sua geometria.')
        engine._adicionar_roi(rt,engine._mascara_para_o_rt_utils(mask),name,color)
        if np.any(mask):
            # Reuse the host's voxel-boundary extractor. rt-utils' ordinary
            # center-line loops include foreground boundary pixels around a
            # hole; labelling those loops XOR would enlarge the hole on import.
            # This helper already handles single voxels, thin components and
            # nested holes. The dataset remains in patient LPS until save().
            engine._trocar_mascara_terminal(
                rt.ds, rt.series_data, name, len(rt.ds.StructureSetROISequence),
                mask, color, None, tuple(geometry['spacing'][1:][::-1]))
    finally:
        for ds,spacing in saved: ds.PixelSpacing=spacing


def _polygon_mask(points, shape, edge_tolerance=1e-7):
    """Pixel-center parity, including edge points; handles closed keyhole loops."""
    pts = _finite(points)
    if pts.ndim != 2 or pts.shape[1] != 2 or not 3 <= len(pts) <= 100000:
        fail('INVALID_CONTOUR', 'Contorno fechado inválido.')
    h, w = shape
    result = np.zeros(shape, bool)
    lo = np.maximum(np.floor(pts.min(axis=0)).astype(int), 0)
    hi = np.minimum(np.ceil(pts.max(axis=0)).astype(int), [w - 1, h - 1])
    if np.any(hi < lo):
        return result
    xx, yy = np.meshgrid(np.arange(lo[0], hi[0]+1), np.arange(lo[1], hi[1]+1))
    inside, edge = np.zeros(xx.shape, bool), np.zeros(xx.shape, bool)
    for a, b in zip(pts, np.roll(pts, -1, axis=0)):
        dx, dy = b - a
        if abs(dy) > 1e-12:
            inside ^= ((a[1] > yy) != (b[1] > yy)) & (xx < (dx * (yy-a[1]) / dy + a[0]))
        cross = (xx-a[0])*dy-(yy-a[1])*dx
        tolerance=float(edge_tolerance)
        edge |= (np.abs(cross) <= tolerance*max(float(np.hypot(dx,dy)),1e-12)) & (xx >= min(a[0],b[0])-tolerance) & (xx <= max(a[0],b[0])+tolerance) & (yy >= min(a[1],b[1])-tolerance) & (yy <= max(a[1],b[1])+tolerance)
    result[lo[1]:hi[1]+1, lo[0]:hi[0]+1] = inside | edge
    return result


class Session:
    def __init__(self, folder, uid, files):
        self.id, self.csrf = secrets.token_urlsafe(24), secrets.token_urlsafe(32)
        self.folder, self.geo = Path(folder), load_geometry(files, uid)
        self.lock = threading.RLock()
        self.touched = time.monotonic()
        self.revision, self.original, self.source_path, self.source_hash = 0, None, None, None
        self.rois, self.masks, self.dirty, self.undo_stack, self.redo_stack = {}, {}, set(), [], []
        self.previews, self.saved, self.renamed, self.anchors = {}, {}, set(), {}
        self.source_signatures = {str(p): _signature(p) for p in self.geo['files']}
        a=self.geo['volume'];sample=a.ravel()[::max(1,a.size//200000)]
        lo,hi=np.percentile(sample,[1,99]);self.window={'center':float((hi+lo)/2),'width':float(max(1,hi-lo))}
        self.rs_files = self._find_rs()

    def _find_rs(self):
        out = {}
        for p in sorted(self.folder.iterdir()):
            if not p.is_file() or p.suffix.lower() not in ('.dcm', '.dicom', ''):
                continue
            try:
                ds = pydicom.dcmread(str(p), stop_before_pixels=True, force=True,
                                     specific_tags=['Modality', 'StructureSetLabel', 'StudyInstanceUID', 'SOPInstanceUID','PatientID','ReferencedFrameOfReferenceSequence'])
                compatible=False
                for frame in ds.get('ReferencedFrameOfReferenceSequence',[]):
                    if str(frame.get('FrameOfReferenceUID',''))!=self.geo['frame']:continue
                    for study in frame.get('RTReferencedStudySequence',[]):
                        if any(str(s.get('SeriesInstanceUID',''))==self.geo['uid'] for s in study.get('RTReferencedSeriesSequence',[])):compatible=True
                if (compatible and str(ds.get('Modality', '')) == 'RTSTRUCT'
                        and str(ds.get('StudyInstanceUID', '')) == self.geo['study']
                        and str(ds.get('PatientID',''))==self.geo['patient']):
                    key = secrets.token_urlsafe(12)
                    out[key] = dict(path=p, name=p.name, label=str(ds.get('StructureSetLabel', p.name)))
            except Exception:
                continue
        return out

    def state(self):
        a = self.geo['volume']
        return dict(session=self.id, csrf=self.csrf, revision=self.revision,
                    shape=list(a.shape), spacing=[float(v) for v in self.geo['spacing']],
                    origin=self.geo['origin'].tolist(), direction=self.geo['direction'].tolist(),
                    plane_labels={'axial':'Axial da aquisição','coronal':'Coronal da aquisição','sagittal':'Sagital da aquisição'},
                    center=self.window['center'], width=self.window['width'],window=dict(self.window),
                    rois=[dict(id=i, name=v['name'], color=v['color'], edited=i in self.dirty or i in self.renamed,
                               editable=v.get('editable',True), reason=v.get('reason','')) for i,v in self.rois.items()],
                    rs_files=[dict(id=k,name=v['name'],label=v['label']) for k,v in self.rs_files.items()],
                    source_rtstruct=self.source_path.name if self.source_path else '',
                    can_undo=bool(self.undo_stack), can_redo=bool(self.redo_stack))

    def check(self, csrf, revision):
        if not isinstance(csrf,str) or not secrets.compare_digest(csrf,self.csrf):
            fail('INVALID_TOKEN','A sessão de edição expirou.',403)
        if type(revision) is not int or revision != self.revision:
            fail('STALE_REVISION','A edição mudou. Atualize a tela antes de continuar.',409)

    def bump(self):
        self.revision += 1
        self.previews.clear()
        self.touched = time.monotonic()

    def _rs(self, key):
        found = self.rs_files.get(str(key))
        if not found:
            matches=[v for v in self.rs_files.values() if v['name']==key]
            found=matches[0] if len(matches)==1 else None
        if not found:
            fail('INVALID_SOURCE','Selecione um RTSTRUCT da lista da série.')
        return found['path']

    def import_rs(self,key,discard=False):
        if (self.dirty or self.undo_stack or self.renamed) and not discard:
            fail('UNSAVED_CHANGES','Abra uma nova sessão para trocar o RTSTRUCT e preservar esta edição.',409)
        path=self._rs(key)
        ds=pydicom.dcmread(str(path),force=True)
        if (str(ds.get('Modality',''))!='RTSTRUCT' or str(ds.get('StudyInstanceUID',''))!=self.geo['study']
                or str(ds.get('PatientID',''))!=self.geo['patient']):
            fail('INVALID_REFERENCE','O RTSTRUCT não corresponde ao paciente e estudo selecionados.')
        refs=set()
        for frame in ds.get('ReferencedFrameOfReferenceSequence',[]):
            for study in frame.get('RTReferencedStudySequence',[]):
                refs.update(str(s.get('SeriesInstanceUID','')) for s in study.get('RTReferencedSeriesSequence',[]))
        if self.geo['uid'] not in refs:
            fail('INVALID_REFERENCE','O RTSTRUCT não referencia a série selecionada. Não há registro espacial automático.')
        contours={int(r.ReferencedROINumber):r for r in ds.get('ROIContourSequence',[])}
        rois={}
        for roi in ds.get('StructureSetROISequence',[]):
            number=int(roi.ROINumber)
            if number in rois:
                fail('INVALID_REFERENCE','O RTSTRUCT contém números de ROI repetidos.')
            rc=contours.get(number)
            reason=''
            if str(roi.get('ReferencedFrameOfReferenceUID',''))!=self.geo['frame']:
                reason='A estrutura usa outro referencial espacial.'
            elif rc is not None and any(str(c.get('ContourGeometricType','')) not in ('CLOSED_PLANAR','CLOSEDPLANAR_XOR') for c in rc.get('ContourSequence',[])):
                reason='Esta estrutura não é formada apenas por contornos fechados planos.'
            color=[int(c) for c in (rc.get('ROIDisplayColor',[255,190,64]) if rc else [255,190,64])]
            rois[number]=dict(name=str(roi.get('ROIName','ROI %s'%number)),color=color,original=roi,contours=rc,editable=not reason,reason=reason)
        self.rois,self.original,self.source_path,self.source_hash=rois,ds,path,_digest(path)
        self.masks.clear(); self.redo_stack.clear(); self.undo_stack.clear();self.previews.clear()
        self.dirty.clear();self.renamed.clear();self.anchors.clear()
        self.bump()
        return self.state()

    def _memory(self, extra=0):
        used=(self.geo['volume'].nbytes+sum(m.nbytes for m in self.masks.values())
              +sum(p['mask'].nbytes for p in self.previews.values())
              +sum(self._history_bytes(r) for r in self.undo_stack+self.redo_stack)+extra)
        if used>MAX_MEMORY:
            fail('RESOURCE_LIMIT','O limite de memória desta edição foi atingido. Salve e abra uma nova sessão.')

    @staticmethod
    def _history_bytes(record):
        if record[1] is not None:
            return (128+sum(a.nbytes for a in record[1:4])
                    +sum(len(a)*64 for a in record[5:7]))
        # Structural records contain only names or the small newly-created ROI
        # metadata. Imported contour datasets are never copied into history.
        return 512+sum(len(v.encode('utf-8')) for v in record[2:4] if isinstance(v,str))

    def _push_history(self, record):
        size=self._history_bytes(record)
        if size>MAX_HISTORY:
            fail('RESOURCE_LIMIT','Esta ação é grande demais para desfazer com segurança. Edite uma região menor.')
        retained=list(self.undo_stack)
        released=sum(self._history_bytes(r) for r in self.redo_stack)
        while retained and (len(retained)>=MAX_HISTORY_ACTIONS or
                sum(self._history_bytes(r) for r in retained)+size>MAX_HISTORY):
            released+=self._history_bytes(retained.pop(0))
        self._memory(size-released)
        self.undo_stack=retained+[record]
        self.redo_stack.clear()

    def mask(self,number):
        number=int(number)
        if number not in self.rois:
            fail('INVALID_ROI','Estrutura não encontrada.')
        roi=self.rois[number]
        if not roi.get('editable',True):
            fail('UNSUPPORTED_CONTOUR',roi['reason'])
        if number in self.masks:
            return self.masks[number]
        self._memory(self.geo['volume'].size)
        m=np.zeros(self.geo['volume'].shape,bool)
        rc=roi.get('contours')
        if rc:
            source_planes=rc.get('SourcePixelPlanesCharacteristicsSequence',[])
            if source_planes:
                p=source_planes[0]
                if (len(source_planes)!=1 or int(p.get('Rows',0))!=m.shape[1]
                        or int(p.get('Columns',0))!=m.shape[2]
                        or int(p.get('NumberOfFrames',0))!=m.shape[0]
                        or not np.allclose(_finite(p.get('PixelSpacing'),2),self.geo['spacing'][1:],atol=1e-5)
                        or abs(float(p.get('SpacingBetweenSlices',0))-self.geo['spacing'][0])>.01
                        or not np.allclose(_finite(p.get('ImagePositionPatient'),3),self.geo['origin'],atol=.01)
                        or not np.allclose(_finite(p.get('ImageOrientationPatient'),6),self.geo['direction'][:,:2].T.ravel(),atol=1e-5)):
                    fail('UNSUPPORTED_CONTOUR','A estrutura possui uma grade de contorno diferente. Não será reamostrada automaticamente.')
            supported={str(c.get('ContourGeometricType','')) for c in rc.get('ContourSequence',[])}
            if len(supported)>1:
                fail('UNSUPPORTED_CONTOUR','Tipos CLOSED_PLANAR e CLOSEDPLANAR_XOR misturados não são editáveis.')
            valid_sops={str(h.SOPInstanceUID):i for i,h in enumerate(self.geo['headers'])}
            planar_areas={}
            inv=self.geo['direction'].T
            spacing=np.asarray(self.geo['spacing'][::-1])
            for c in rc.get('ContourSequence',[]):
                pts=_finite(c.get('ContourData',[]))
                if pts.size<9 or pts.size%3:
                    fail('INVALID_CONTOUR','A estrutura contém contorno degenerado.')
                xyz=(pts.reshape(-1,3)-self.geo['origin'])@inv.T/spacing
                k=int(round(float(np.mean(xyz[:,2]))))
                if (not 0<=k<m.shape[0] or np.max(np.abs(xyz[:,2]-k))*spacing[2]>.05
                        or xyz[:,0].min()<-.51 or xyz[:,0].max()>m.shape[2]-.49
                        or xyz[:,1].min()<-.51 or xyz[:,1].max()>m.shape[1]-.49):
                    fail('UNSUPPORTED_CONTOUR','O contorno não coincide com os cortes adquiridos. A importação não reamostra estruturas.')
                for ref in c.get('ContourImageSequence',[]):
                    if valid_sops.get(str(ref.get('ReferencedSOPInstanceUID','')))!=k:
                        fail('INVALID_REFERENCE','A referência de imagem do contorno não corresponde à sua posição.')
                # The shared writer emits patient coordinates to 4 decimal
                # places. Allow <=0.0002 mm of DS roundoff at a pixel boundary,
                # irrespective of oblique orientation or in-plane spacing.
                area=_polygon_mask(xyz[:,:2],m.shape[1:],.0002/min(spacing[:2]))
                if 'CLOSEDPLANAR_XOR' in supported:
                    m[k]^=area
                else:
                    # Nested separate CLOSED_PLANAR loops have ambiguous legacy
                    # hole semantics. Never silently fill or carve such a hole.
                    for previous in planar_areas.get(k,[]):
                        if area.any() and previous.any() and (np.all(previous[area]) or np.all(area[previous])):
                            fail('AMBIGUOUS_HOLES','A estrutura contém contornos internos CLOSED_PLANAR sem regra XOR explícita. O original foi preservado; esta estrutura não será editada automaticamente.')
                    planar_areas.setdefault(k,[]).append(area)
                    m[k]|=area
        self.masks[number]=m
        return m

    def plane(self,plane,index):
        if plane not in PLANES:
            fail('INVALID_PLANE','Plano inválido.')
        axis=PLANES[plane]
        if type(index) is not int or not 0<=index<self.geo['volume'].shape[axis]:
            fail('INVALID_SLICE','Corte fora da série.')
        return axis,index

    def image(self,plane,index,center=None,width=None):
        from PIL import Image
        axis,index=self.plane(plane,index)
        a=_plane(self.geo['volume'],axis,index)
        defaults=self.window
        center=float(defaults['center'] if center is None else center)
        width=float(defaults['width'] if width is None else width)
        if not math.isfinite(center+width) or width<=0:
            fail('INVALID_WINDOW','Janela inválida.')
        pixels=np.clip((a-center+width/2)*255/width,0,255).astype(np.uint8)
        if self.geo['mono1']: pixels=255-pixels
        out=io.BytesIO(); Image.fromarray(pixels).save(out,format='PNG')
        return out.getvalue()

    def overlay(self,number,plane,index,preview_id=None):
        from skimage.measure import find_contours
        axis,index=self.plane(plane,index)
        mask=self.mask(number)
        if preview_id:
            preview=self.previews.get(preview_id)
            if not preview or preview['revision']!=self.revision or preview['roi']!=int(number):
                fail('STALE_PREVIEW','A prévia expirou.',409)
            mask=preview['mask']
        a=_plane(mask,axis,index); h,w=a.shape
        polygons=[]
        for c in find_contours(np.pad(a.astype(np.uint8),1),.5):
            polygons.append(np.column_stack(((c[:,1]-.5)/w,(c[:,0]-.5)/h)).tolist())
        return dict(width=w,height=h,polygons=polygons,color=self.rois[int(number)]['color'],revision=self.revision)

    def new_roi(self,name,color):
        name=str(name or '').strip()
        if not name or len(name)>64 or any(ord(c)<32 or c=='\\' for c in name):
            fail('INVALID_NAME','Use um nome de estrutura com até 64 caracteres.')
        if any(v['name']==name for v in self.rois.values()):
            fail('INVALID_NAME','Já existe uma estrutura com este nome.')
        if not isinstance(color,list) or len(color)!=3 or any(type(c)is not int or not 0<=c<=255 for c in color):
            fail('INVALID_COLOR','Cor inválida.')
        number=max(self.rois,default=0)+1
        roi=dict(name=name,color=color,editable=True)
        self._push_history((number,None,None,copy.deepcopy(roi),False))
        self.rois[number]=roi
        self.dirty.add(number); self.bump()
        return self.state()

    def rename(self,number,name):
        number=int(number); name=str(name or '').strip()
        if number not in self.rois or not name or len(name)>64 or any(ord(c)<32 or c=='\\' for c in name):
            fail('INVALID_NAME','Nome da estrutura inválido.')
        if any(i!=number and v['name']==name for i,v in self.rois.items()):
            fail('INVALID_NAME','Já existe uma estrutura com este nome.')
        old=self.rois[number]['name']
        if name==old:return self.state()
        self._push_history((number,None,old,name,number in self.renamed))
        self.rois[number]['name']=name;self.renamed.add(number);self.bump()
        return self.state()

    def _record(self,number,before,after,anchor=None):
        # Count before allocating indices: a large interpolation must not first
        # create an int64 index for every changed voxel merely to reject it.
        old_flat,new_flat=before.ravel(),after.ravel()
        block=1024*1024;count=0
        for start in range(0,old_flat.size,block):
            count+=int(np.count_nonzero(old_flat[start:start+block]!=new_flat[start:start+block]))
            if count*6+128>MAX_HISTORY:
                fail('RESOURCE_LIMIT','Esta ação é grande demais para desfazer com segurança. Edite uma região menor.')
        if not count:return
        self._memory(count*6+block*9)
        changes=np.empty(count,dtype=np.uint32);offset=0
        for start in range(0,old_flat.size,block):
            local=np.flatnonzero(old_flat[start:start+block]!=new_flat[start:start+block])
            changes[offset:offset+len(local)]=local+start;offset+=len(local)
        anchors=set(self.anchors.get(number,set()))
        updated=anchors|({anchor} if anchor is not None else set())
        record=(number,changes,before.ravel()[changes].copy(),after.ravel()[changes].copy(),number in self.dirty,anchors,updated)
        self._push_history(record)
        before.ravel()[changes]=after.ravel()[changes]
        self.anchors[number]=updated
        self.dirty.add(number); self.bump()

    def stroke(self,number,plane,index,points,diameter_mm=5,operation='brush'):
        axis,index=self.plane(plane,index)
        if operation not in ('brush','erase','polygon','polygon-erase'):
            fail('INVALID_OPERATION','Ferramenta inválida.')
        points=_finite(points)
        if points.ndim!=2 or points.shape[1]!=2 or not 1<=len(points)<=MAX_POINTS or points.min()<0 or points.max()>1:
            fail('INVALID_INPUT','Traçado inválido.')
        m=self.mask(number); self._memory(m.nbytes)
        after=m.copy(); a=_plane(after,axis,index); h,w=a.shape
        xy=points*np.array([w,h])-.5
        if operation.startswith('polygon'):
            selected=_polygon_mask(xy,a.shape)
        else:
            diameter=float(diameter_mm)
            if not math.isfinite(diameter) or not .1<=diameter<=100:
                fail('INVALID_INPUT','Diâmetro do pincel deve estar entre 0,1 e 100 mm.')
            sp=np.delete(np.asarray(self.geo['spacing']),axis)
            coords=xy*np.array([sp[1],sp[0]])
            selected=np.zeros(a.shape,bool)
            for start,end in zip(coords,np.vstack((coords[1:],coords[-1:]))):
                radius=diameter/2
                low=np.maximum(np.floor((np.minimum(start,end)-radius)/[sp[1],sp[0]]).astype(int),0)
                high=np.minimum(np.ceil((np.maximum(start,end)+radius)/[sp[1],sp[0]]).astype(int),[w-1,h-1])
                if np.any(high<low):continue
                xx,yy=np.meshgrid(np.arange(low[0],high[0]+1),np.arange(low[1],high[1]+1))
                px=xx*sp[1];py=yy*sp[0]
                delta=end-start; length=float(delta@delta)
                t=np.zeros(xx.shape) if length==0 else np.clip(((px-start[0])*delta[0]+(py-start[1])*delta[1])/length,0,1)
                selected[low[1]:high[1]+1,low[0]:high[0]+1]|=(px-start[0]-t*delta[0])**2+(py-start[1]-t*delta[1])**2 <= radius**2
        a[selected]=operation not in ('erase','polygon-erase')
        self._record(int(number),m,after,anchor=(axis,index))
        return self.state()

    def history(self,redo=False):
        source=self.redo_stack if redo else self.undo_stack
        target=self.undo_stack if redo else self.redo_stack
        if source:
            record=source.pop(); number,indices,old,new,was_dirty=record[:5]
            if indices is None:
                value=new if redo else old
                if value is None:
                    self.rois.pop(number,None);self.masks.pop(number,None);self.dirty.discard(number);self.renamed.discard(number)
                elif isinstance(value,str):
                    self.rois[number]['name']=value
                    if redo or was_dirty:self.renamed.add(number)
                    else:self.renamed.discard(number)
                else:
                    self.rois[number]=copy.deepcopy(value)
                    if old is None:self.dirty.add(number)
                    elif redo or was_dirty:self.renamed.add(number)
                    else:self.renamed.discard(number)
            else:
                self.mask(number).ravel()[indices]=new if redo else old
                if redo or was_dirty: self.dirty.add(number)
                else: self.dirty.discard(number)
                if len(record)>5:self.anchors[number]=set(record[6 if redo else 5])
            target.append(record); self.bump()
        return self.state()

    def interpolate(self,number,plane=None,start=None,end=None,apply=False,preview_id=None):
        if apply:
            p=self.previews.get(preview_id)
            if not p or p['revision']!=self.revision or p['roi']!=int(number):
                fail('STALE_PREVIEW','A prévia expirou. Prepare a interpolação novamente.',409)
            self._record(int(number),self.mask(number),p['mask'])
            return self.state()
        from scipy.ndimage import distance_transform_edt
        axis,start=self.plane(plane,start); _,end=self.plane(plane,end)
        if end-start<2:
            fail('INVALID_INTERVAL','Escolha dois cortes separados por pelo menos um corte intermediário.')
        m=self.mask(number); self._memory(m.nbytes)
        a,b=_plane(m,axis,start),_plane(m,axis,end)
        if not a.any() or not b.any():
            fail('INVALID_INTERVAL','Os dois cortes de referência precisam conter um contorno.')
        sp=np.delete(np.asarray(self.geo['spacing']),axis)
        def sdf(bits): return distance_transform_edt(bits,sampling=sp)-distance_transform_edt(~bits,sampling=sp)
        da,db=sdf(a),sdf(b); result=m.copy()
        protected={index for p,index in self.anchors.get(int(number),()) if p==axis}
        for i in range(start+1,end):
            if i in protected:continue
            t=(i-start)/(end-start)
            _plane(result,axis,i)[:]=(da*(1-t)+db*t)>=0
        key=secrets.token_urlsafe(20)
        self.previews={key:dict(mask=result,roi=int(number),revision=self.revision)}
        return dict(preview_id=key,revision=self.revision,start=start,end=end,plane=plane,
                    changed_voxels=int(np.count_nonzero(result!=m)),session=self.id)

    def _verify_sources(self):
        for path,signature in self.source_signatures.items():
            if not Path(path).is_file() or _signature(path)!=signature:
                fail('SOURCE_CHANGED','A série original mudou. Reabra antes de exportar.',409)
        if self.source_path and _digest(self.source_path)!=self.source_hash:
            fail('SOURCE_CHANGED','O RTSTRUCT original mudou. Reabra antes de exportar.',409)

    def _verify_written_masks(self, dataset):
        """Reject lossy export before publication, using the same native grid."""
        contours={int(rc.ReferencedROINumber):rc for rc in dataset.get('ROIContourSequence',[])}
        probe=object.__new__(Session)
        probe.geo=self.geo
        probe.rois={}
        probe.masks={}
        probe.previews={}
        probe.undo_stack=[]
        probe.redo_stack=[]
        for number in sorted(self.dirty):
            expected=self.mask(number)
            if not expected.any():
                if contours.get(number) and contours[number].get('ContourSequence'):
                    fail('WRITER_GEOMETRY','O gravador não preservou a máscara editada. Nada foi gravado.')
                continue
            self._memory(expected.nbytes+1024*1024)
            probe.rois={number:dict(editable=True,contours=contours.get(number))}
            try:
                actual=probe.mask(number)
            except EditError:
                fail('WRITER_GEOMETRY','O gravador não preservou a máscara editada. Nada foi gravado.')
            a,b=actual.ravel(),expected.ravel()
            for start in range(0,a.size,1024*1024):
                if not np.array_equal(a[start:start+1024*1024],b[start:start+1024*1024]):
                    fail('WRITER_GEOMETRY','O gravador não preservou a máscara editada. Nada foi gravado.')
            probe.masks.clear()
            del actual,a,b

    def _publish_copy(self, source, destination):
        # A directory scan never sees a half-written DICOM file.
        part=destination.with_name(destination.name+'.'+secrets.token_hex(8)+'.part')
        try:
            with part.open('xb') as target,source.open('rb') as stream:
                shutil.copyfileobj(stream,target)
                target.flush()
                os.fsync(target.fileno())
            self._verify_sources()
            if os.name=='nt':
                os.rename(part,destination)  # Windows refuses replacement.
            else:
                os.link(part,destination)  # Atomic and exclusive on POSIX.
                part.unlink()
        finally:
            if part.exists(): part.unlink()

    def save(self):
        if not self.dirty and not self.renamed:
            fail('NO_CHANGES','Não há alterações para gravar.')
        self._verify_sources()
        import engine
        from rt_utils import RTStructBuilder
        with tempfile.TemporaryDirectory(prefix='radai_edit_writer_') as stage:
            clean=Path(stage)/'series'; clean.mkdir()
            for i,src in enumerate(self.geo['files']):
                engine.copiar_como_parte_10(src,clean/('slice_%05d.dcm'%i))
            rt=RTStructBuilder.create_new(dicom_series_path=str(clean))
            mapping={}
            for number in sorted(self.dirty):
                mask=self.mask(number)
                label='ROI_EDIT_%d'%number
                writer_add_roi(engine,rt,mask,label,self.rois[number]['color'],self.geo)
                mapping[len(rt.ds.StructureSetROISequence)]=number
            generated=Path(stage)/'generated.dcm'
            plane=engine.plano_da_serie(clean)
            engine.para_o_plano_da_serie(rt.ds,plane)
            def closed_types(dataset,report):
                # Monaco uses keyhole polygons. Separate inner/outer contours
                # require the normative XOR type, not implicit winding rules.
                if report.get('tps') != engine.TPS_MONACO:
                    for rc in dataset.get('ROIContourSequence',[]):
                        for c in rc.get('ContourSequence',[]): c.ContourGeometricType='CLOSEDPLANAR_XOR'
            engine.gravar_rtstruct(rt.ds,str(generated),plano=plane,
                                  dxdy=tuple(self.geo['spacing'][1:][::-1]),finalizar=closed_types)
            new=pydicom.dcmread(str(generated))
            out=copy.deepcopy(self.original if self.original is not None else new)
            if self.original is None:
                for seq in ('StructureSetROISequence','ROIContourSequence','RTROIObservationsSequence'): out[seq].value=Sequence()
            for seq,attr in (('StructureSetROISequence','ROINumber'),('ROIContourSequence','ReferencedROINumber'),('RTROIObservationsSequence','ReferencedROINumber')):
                retained=[r for r in out.get(seq,[]) if int(getattr(r,attr)) not in self.dirty]
                for r in new.get(seq,[]):
                    old=int(getattr(r,attr)); number=mapping.get(old)
                    if number is None: continue
                    r=copy.deepcopy(r); setattr(r,attr,number)
                    if seq=='StructureSetROISequence':
                        r.ROIName=self.rois[number]['name']; r.ROIGenerationAlgorithm='MANUAL'
                        r.ROIGenerationDescription='Local Suite contour editor; manual edits; unapproved'
                    elif seq=='RTROIObservationsSequence':
                        r.ObservationNumber=number
                        if 'ROIObservationLabel' in r: r.ROIObservationLabel=self.rois[number]['name'][:16]
                    retained.append(r)
                setattr(out,seq,Sequence(retained))
            for r in out.get('StructureSetROISequence',[]):
                number=int(r.ROINumber)
                if number in self.renamed:r.ROIName=self.rois[number]['name']
            for r in out.get('RTROIObservationsSequence',[]):
                number=int(r.ReferencedROINumber)
                if number in self.renamed and 'ROIObservationLabel' in r:r.ROIObservationLabel=self.rois[number]['name'][:16]
            if not out.get('StructureSetROISequence'):
                fail('EMPTY_RESULT','Todas as estruturas estão vazias; nenhum RTSTRUCT foi gravado.')
            # Referenced source data and unchanged ROI items come from original.
            out.SOPInstanceUID=generate_uid(); out.SeriesInstanceUID=generate_uid()
            out.file_meta.MediaStorageSOPInstanceUID=out.SOPInstanceUID
            out.file_meta.TransferSyntaxUID=ImplicitVRLittleEndian
            out.ApprovalStatus='UNAPPROVED'
            out.StructureSetLabel='RADAI_EDIT'
            out.StructureSetName='Local Suite edited contours'
            out.SeriesDescription='Local Suite edited contours'
            out.StructureSetDescription='Manual contour editing; original preserved. Review required.'
            out.decode()
            out.SpecificCharacterSet='ISO_IR 192'
            now=time.localtime(); out.StructureSetDate=time.strftime('%Y%m%d',now); out.StructureSetTime=time.strftime('%H%M%S',now)
            out.InstanceCreationDate=out.StructureSetDate; out.InstanceCreationTime=out.StructureSetTime
            for key in ('ReviewDate','ReviewTime','ReviewerName','DigitalSignaturesSequence','MACParametersSequence'):
                if key in out: del out[key]
            filename='RS_LOCAL_SUITE_EDIT_%s_%s.dcm'%(time.strftime('%Y%m%d_%H%M%S',now),secrets.token_hex(4))
            tmp=Path(stage)/'final.dcm'
            engine.gravar_dicom_em_fluxo(out,str(tmp),implicit_vr=True,little_endian=True)
            checked=pydicom.dcmread(str(tmp))
            written={int(r.ReferencedROINumber) for r in checked.get('ROIContourSequence',[]) if r.get('ContourSequence')}
            for number in self.dirty:
                if self.mask(number).any() and number not in written:
                    fail('UNWRITABLE_ROI','Uma estrutura é pequena demais para gerar contorno fechado. Nada foi gravado.')
            self._verify_written_masks(checked)
            fallback=False; dest=self.folder/filename
            try:
                self._publish_copy(tmp,dest)
            except OSError:
                target_dir=Path(tempfile.gettempdir())/'radai_contour_edits'; target_dir.mkdir(exist_ok=True)
                dest=target_dir/filename; fallback=True
                self._publish_copy(tmp,dest)
            key=secrets.token_urlsafe(20); self.saved[key]=dest
            return dict(session=self.id,revision=self.revision,basename=filename,
                        download_url='/api/contour-edit/download?s=%s&file=%s'%(self.id,key),
                        fallback=fallback,message=('A pasta original não permite gravação. Baixe a cópia pelo botão de download.' if fallback else 'Nova cópia gravada ao lado da série. O original foi preservado.'))


def open_session(ticket,source='thumbnail',uid=None,rs=None):
    folder,uid,files=resolve_ticket(ticket,source,uid)
    with _LOCK:
        now=time.monotonic()
        for key in list(_SESSIONS):
            if now-_SESSIONS[key].touched>TTL: del _SESSIONS[key]
        if len(_SESSIONS)>=MAX_SESSIONS:
            fail('SESSION_LIMIT','Feche uma sessão de edição antes de abrir outra.',409)
        session=Session(folder,uid,files)
        if rs: session.import_rs(rs)
        _SESSIONS[session.id]=session
        return session.state()


def get_session(key):
    with _LOCK:
        session=_SESSIONS.get(str(key))
        if session is None or time.monotonic()-session.touched>TTL:
            _SESSIONS.pop(str(key),None)
            fail('SESSION_EXPIRED','A sessão expirou. Abra a série novamente.',404)
        session.touched=time.monotonic()
        return session


def close_session(key):
    with _LOCK: _SESSIONS.pop(str(key),None)
