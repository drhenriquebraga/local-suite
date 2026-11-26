"""Host-only discovery of manual copies, never evidence of AUTO completion.

Viewer adapters deliberately leave radai_sets/radai_batch/radai_watcher intact.
Manual copies use a separate filename namespace and complete DICOM references.
"""
from functools import wraps
from collections import OrderedDict
import importlib
import os
from pathlib import Path
import threading

import pydicom

from radai_rt_importar import PREFIX as IMPORTADO, sufixo_serie

PREFIX = 'RS_LOCAL_SUITE_EDIT_'
NAMESPACES = (PREFIX, IMPORTADO)
MAX_COPIES = 256
MAX_SOURCE_CACHE = 64
MAX_HEADER_CACHE = 256
_SOURCE_CACHE = OrderedDict()
_HEADER_CACHE = OrderedDict()
_IMPORTS = OrderedDict()
_IMPORT_LABELS = OrderedDict()
_CACHE_LOCK = threading.RLock()
_PLUGIN_HEADERS = OrderedDict()
_TAGS = ['Modality','PatientID','IssuerOfPatientID','StudyInstanceUID',
         'SeriesInstanceUID','FrameOfReferenceUID','ReferencedFrameOfReferenceSequence']


def _path_key(path):
    return os.path.normcase(os.path.abspath(str(path)))


def _signature(path):
    stat=Path(path).stat()
    return stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns


def _remember(cache,key,value,limit):
    cache[key]=value
    cache.move_to_end(key)
    while len(cache)>limit:cache.popitem(last=False)


def _source_identity(root,uid,parar=None):
    key=(_path_key(root),str(uid))
    with _CACHE_LOCK:
        cached=_SOURCE_CACHE.get(key)
        if cached:
            try:
                if _signature(cached['path'])==cached['signature']:
                    _SOURCE_CACHE.move_to_end(key)
                    return cached['identity']
            except OSError:pass
            _SOURCE_CACHE.pop(key,None)
    import radai_rt
    files=radai_rt.fatias_da_serie(str(root),str(uid),primeira=True,parar=parar)
    if not files:return None
    path=Path(files[0]);signature=_signature(path)
    source=pydicom.dcmread(str(path),stop_before_pixels=True,force=True,specific_tags=_TAGS)
    if (str(source.get('SeriesInstanceUID',''))!=str(uid)
            or str(source.get('Modality','')) not in ('CT','MR')):return None
    identity=tuple(str(source.get(key,'')) for key in
                   ('PatientID','IssuerOfPatientID','StudyInstanceUID','FrameOfReferenceUID'))
    if not identity[2] or not identity[3] or _signature(path)!=signature:return None
    with _CACHE_LOCK:
        _remember(_SOURCE_CACHE,key,dict(path=path,signature=signature,identity=identity),MAX_SOURCE_CACHE)
        return identity


def _manual_header(path):
    key=_path_key(path)
    with _CACHE_LOCK:
        signature=_signature(path)
        cached=_HEADER_CACHE.get(key)
        if cached and cached['signature']==signature:
            _HEADER_CACHE.move_to_end(key)
            return cached['identity']
        _HEADER_CACHE.pop(key,None)
        ds=pydicom.dcmread(str(path),stop_before_pixels=True,specific_tags=_TAGS)
        if str(ds.get('Modality',''))!='RTSTRUCT':return None
        references=frozenset((str(f.get('FrameOfReferenceUID','')),str(s.get('SeriesInstanceUID','')))
                             for f in ds.get('ReferencedFrameOfReferenceSequence',[])
                             for st in f.get('RTReferencedStudySequence',[])
                             for s in st.get('RTReferencedSeriesSequence',[]))
        identity=(str(ds.get('PatientID','')),str(ds.get('IssuerOfPatientID','')),
                  str(ds.get('StudyInstanceUID','')),references)
        if _signature(path)!=signature:return None
        _remember(_HEADER_CACHE,key,dict(signature=signature,identity=identity),MAX_HEADER_CACHE)
        return identity


def manual_copies(folder, uid, parar=None):
    """Return names only after validating the selected native series identity."""
    if not folder or not uid:
        return []
    root=Path(folder)
    try:
        from heapq import nlargest
        def nomes(entradas):
            for item in entradas:
                if parar and parar():
                    raise InterruptedError("Leitura interrompida.")
                if (item.name.startswith(NAMESPACES) and item.name.lower().endswith('.dcm')
                        and item.is_file(follow_symlinks=False)):
                    yield item.name
        with os.scandir(root) as entradas:
            candidates=[root / nome for nome in nlargest(MAX_COPIES, nomes(entradas))]
        if not candidates:return []
        identity=_source_identity(root,uid,parar)
        if not identity:return []
        patient,issuer,study,frame=identity
    except (OSError,ValueError,TypeError,pydicom.errors.InvalidDicomError):
        return []
    result=[]
    for path in candidates:
        if parar and parar():
            break
        try:
            if path.name.startswith(IMPORTADO):
                if not path.name.startswith(IMPORTADO+sufixo_serie(uid)+'_'):
                    continue
                key=(_path_key(path), _signature(path), identity, uid)
                with _CACHE_LOCK:
                    checked=_IMPORTS.get(key, False)
                if not checked:
                    from radai_rt_importar import _validar
                    label=_validar(path,root,uid)
                    with _CACHE_LOCK:
                        _remember(_IMPORT_LABELS,path.name,label,MAX_HEADER_CACHE)
                        _remember(_IMPORTS,key,True,MAX_HEADER_CACHE)
                result.append(path.name)
                continue
            header=_manual_header(path)
            if not header:continue
            own_patient,own_issuer,own_study,references=header
            if own_patient!=patient or own_study!=study:continue
            if own_issuer and own_issuer!=issuer:continue
            if (frame,str(uid)) in references:result.append(path.name)
        except (OSError,ValueError,TypeError,pydicom.errors.InvalidDicomError):
            continue
    return result


def _row(name):
    if str(name).startswith(IMPORTADO):
        with _CACHE_LOCK:
            label = _IMPORT_LABELS.get(name, 'RTSTRUCT') + ' · ' + name.rsplit('_', 1)[-1][:8]
        return dict(arquivo=name,conjunto='importado',cod='importado',nome=label,curto=label,
                    rotulo=label,entregue=False,plugin=False,manual=False)
    return {'arquivo':name,'conjunto':'manual','cod':'manual','nome':name,
            'curto':name,'rotulo':name,'entregue':False,'plugin':False,'manual':True}


def _plugin_header(path):
    """Read identity and model provenance without decoding any contour coordinates."""
    import re
    from pydicom.uid import RTStructureSetStorage
    key = (_path_key(path), _signature(path))
    with _CACHE_LOCK:
        if key in _PLUGIN_HEADERS:
            _PLUGIN_HEADERS.move_to_end(key)
            return _PLUGIN_HEADERS[key]
    ds = pydicom.dcmread(str(path), stop_before_pixels=True, specific_tags=_TAGS +
                         ['SOPClassUID', 'StructureSetLabel', 'StructureSetROISequence'])
    if str(ds.get('SOPClassUID', '')) != str(RTStructureSetStorage) or ds.get('Modality') != 'RTSTRUCT':
        return None
    refs = {(str(f.get('FrameOfReferenceUID', '')), str(s.get('SeriesInstanceUID', '')))
            for f in ds.get('ReferencedFrameOfReferenceSequence', [])
            for st in f.get('RTReferencedStudySequence', [])
            for s in st.get('RTReferencedSeriesSequence', [])}
    rois = ds.get('StructureSetROISequence', [])
    frames = {str(r.get('ReferencedFrameOfReferenceUID', '')) for r in rois}
    if len(refs) != 1 or len(frames) != 1 or next(iter(refs))[0] not in frames:
        return None
    titles = {'anatomy_synthseg': 'SynthSeg', 'anatomy_cerebra_ants': 'CerebrA / ANTs', 'cranio_buti': 'Buti'}
    models = []
    for roi in rois:
        model = re.search(r'NeuroRT / modelo ([\w.-]+)', str(roi.get('ROIDescription', '')))
        if model and model.group(1) not in models:
            models.append(model.group(1))
    label = ' + '.join(titles.get(m, m) for m in models) or str(ds.get('StructureSetLabel', '')).strip()
    frame, uid = next(iter(refs))
    identity = tuple(str(ds.get(k, '')) for k in ('PatientID','IssuerOfPatientID','StudyInstanceUID'))
    value = (identity, frame, uid, label)
    if _signature(path) != key[1]:
        return None
    with _CACHE_LOCK:
        _remember(_PLUGIN_HEADERS, key, value, MAX_HEADER_CACHE)
    return value


def published_sets(folder, uid):
    """Supplement the legacy filename-based sets with DICOM-linked suite exports."""
    if not folder or not uid:
        return []
    root = Path(folder)
    prefixes = ('rs_neurort', 'rs_radai_nod_lung_', 'rs_radai_study_lung_', 'rs_radai_itv4d_',
                'rs_vascular_', 'rs_nidus')
    try:
        paths = [p for p in root.iterdir() if p.name.lower().startswith(prefixes)
                 and p.suffix.lower() in ('.dcm', '.dicom') and p.is_file() and not p.is_symlink()]
        if not paths:
            return []
        source = _source_identity(root, uid)
        if not source:
            return []
        patient, issuer, study, source_frame = source
    except (OSError, ValueError, TypeError, pydicom.errors.InvalidDicomError):
        return []
    rows = []
    for path in paths:
        try:
            header = _plugin_header(path)
            if not header:
                continue
            (own_patient, own_issuer, own_study), frame, referenced_uid, label = header
            if (own_patient != patient or (own_issuer and own_issuer != issuer)
                    or own_study != study or frame != source_frame or referenced_uid != uid):
                continue
            neuro = path.name.lower().startswith('rs_neurort')
            title = ('NEURO RT · ' if neuro and label else '') + (label or path.stem)
            rows.append((path.stat().st_mtime_ns, dict(arquivo=path.name, conjunto='neuro' if neuro else 'plugin',
                         nome=title, plugin=True)))
        except (OSError, ValueError, TypeError, pydicom.errors.InvalidDicomError):
            continue
    return [row for _, row in sorted(rows, key=lambda item: (-item[0], item[1]['arquivo']))]


def _wrap(module,name,factory):
    original=getattr(module,name)
    if getattr(original,'_manual_contour_discovery',False):return
    wrapped=factory(original)
    wrapped._manual_contour_discovery=True
    setattr(module,name,wrapped)


def _viewer_functions():
    try:
        view=importlib.import_module('radai_viewseg')
    except ImportError:
        view=None
    if view is not None:
        def cp_files(original):
            @wraps(original)
            def wrapped(folder,uid,outros=()):
                found=list(original(folder,uid,outros))
                return found+[n for n in manual_copies(folder,uid) if n not in found]
            return wrapped
        def cp_label(original):
            @wraps(original)
            def wrapped(name):
                return _row(name) if str(name).startswith(NAMESPACES) else original(name)
            return wrapped
        _wrap(view,'_rs_da_pasta',cp_files)
        _wrap(view,'rotulo_do_arquivo',cp_label)
    try:
        recon=importlib.import_module('radai_recon3d_screen')
        recon_core=importlib.import_module('radai_recon3d')
    except ImportError:
        return
    def manual_xor_reader(original):
        @wraps(original)
        def wrapped(dataset,name):
            # Scope this compatibility adapter to our unchanged manual copies;
            # never relabel or mutate the input dataset or other RTSTRUCTs.
            filename=Path(str(getattr(dataset,'filename','') or '')).name
            if not (filename.startswith(IMPORTADO) or (filename.startswith(PREFIX)
                    and str(dataset.get('StructureSetLabel','')).strip()=='RADAI_EDIT')):
                return original(dataset,name)
            names,contours=recon_core._mapas_do_rtstruct(dataset)
            number=next((n for n,label in names if label==name),None)
            if number is None or number not in contours:return original(dataset,name)
            sequence=list(contours[number].get('ContourSequence',[]))
            types={str(c.get('ContourGeometricType','')).strip().upper() for c in sequence}
            if types!={'CLOSEDPLANAR_XOR'}:return original(dataset,name)
            import numpy as np
            output=[]
            for contour in sequence:
                try:
                    values=recon_core._numeros_crus(contour,recon_core._TAG_CONTOUR_DATA)
                    if not values or len(values)<9 or len(values)%3:continue
                    points=np.asarray(values,dtype=np.float64).reshape(-1,3)
                    if np.isfinite(points).all():output.append(points)
                except (ValueError,TypeError):continue
            return output
        return wrapped
    _wrap(recon_core,'contornos_da_roi',manual_xor_reader)
    def recon_files(original):
        @wraps(original)
        def wrapped(folder,uid=''):
            found=list(original(folder,uid))
            names={r.get('arquivo') for r in found}
            return found+[_row(n) for n in manual_copies(folder,uid) if n not in names]
        return wrapped
    def recon_line(original):
        @wraps(original)
        def wrapped(line,folder,series):
            accepted=original(line,folder,series)
            if accepted is not False and manual_copies(folder,series.get('uid')):
                line['segmentada']=True
                line['contornos_manuais']=True
            return accepted
        return wrapped
    def recon_archive(original):
        @wraps(original)
        def wrapped(tool,limite=60,parar=None):
            result=original(tool,limite,parar=parar)
            # Protocol-specific reconstructions keep their original model/map
            # requirements. General anatomy and vascular viewers accept ROIs.
            if tool not in ('geral','vascular','neuro'):return result
            import radai_tabela_acervo,radai_thumbnail
            rows=list(result.get('series',[]))
            if len(rows)>=limite or (parar and parar()):return result
            present={r.get('bilhete') for r in rows}
            for row in radai_tabela_acervo.linhas(limite=200,parar=parar).get('series',[]):
                if len(rows)>=limite or (parar and parar()):break
                ticket=row.get('bilhete')
                if not ticket or ticket in present:continue
                folder,uid=radai_thumbnail.resolver(ticket)
                if manual_copies(folder,uid,parar):
                    rows.append(dict(row,estado='ok',segmentada=True,contornos_manuais=True,estudo_3d=[]))
                    present.add(ticket)
            return dict(result,series=rows[:int(limite or 60)])
        return wrapped
    _wrap(recon,'arquivos_da_serie',recon_files)
    _wrap(recon,'linha_da_pasta',recon_line)
    _wrap(recon,'acervo',recon_archive)
    recon.registrar_varredura()


def _viewer_routes(app):
    for route in app.routes:
        if getattr(route,'path','')!='/api/recon3d/estado':continue
        original=route.dependant.call
        if getattr(original,'_manual_contour_discovery',False):continue
        def factory(previous):
            @wraps(previous)
            def wrapped(b:str='',**kwargs):
                result=previous(b=b,**kwargs)
                if str(b).startswith('neuro:'):return result
                if not isinstance(result,dict):return result
                import radai_thumbnail
                folder,uid=radai_thumbnail.resolver(b)
                copies=manual_copies(folder,uid)
                if not copies:return result
                rows=list(result.get('conjuntos',[]));names={r.get('arquivo') for r in rows}
                rows.extend(_row(n) for n in copies if n not in names)
                return dict(result,segmentada=True,contornos_manuais=True,conjuntos=rows)
            wrapped._manual_contour_discovery=True
            return wrapped
        wrapped=factory(original)
        route.endpoint=wrapped
        route.dependant.call=wrapped


def install(app):
    _viewer_functions()
    _viewer_routes(app)
    if not getattr(app.state,'manual_contour_discovery',False):
        app.state.manual_contour_discovery=True
        # The host may mount RECON after the editor. Wrap once routes exist.
        app.router.add_event_handler('startup',lambda:(_viewer_functions(),_viewer_routes(app)))
