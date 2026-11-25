"""Import RT structures for viewing alongside their referenced source series."""
import hashlib
import math
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import pydicom
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

PREFIX = "RS_IMPORT_"
CAP = 128 * 1024 * 1024
INCOMPATIVEL = "As referências DICOM do RTSTRUCT não correspondem à série selecionada."
INVALIDO = "Selecione um arquivo DICOM RTSTRUCT com contornos."


def sufixo_serie(uid):
    return hashlib.sha256(str(uid).encode("ascii")).hexdigest()[:24]


def _validar(arquivo, pasta, uid):
    import radai_contour_discovery as discovery
    import radai_rt
    from pydicom.uid import RTStructureSetStorage

    ds = pydicom.dcmread(arquivo, stop_before_pixels=True)
    if (str(ds.get("SOPClassUID", "")) != str(RTStructureSetStorage)
            or str(ds.get("Modality", "")) != "RTSTRUCT" or not ds.get("SOPInstanceUID")):
        raise ValueError(INVALIDO)
    identidade = discovery._source_identity(pasta, uid)
    if not identidade:
        raise ValueError(INCOMPATIVEL)
    paciente, emissor, estudo, frame = identidade
    patient_rs = str(ds.get("PatientID", ""))
    issuer_rs = str(ds.get("IssuerOfPatientID", ""))
    study_rs = str(ds.get("StudyInstanceUID", ""))
    references = {(str(f.get("FrameOfReferenceUID", "")), str(r.get("SeriesInstanceUID", "")))
                  for f in ds.get("ReferencedFrameOfReferenceSequence", [])
                  for st in f.get("RTReferencedStudySequence", [])
                  for r in st.get("RTReferencedSeriesSequence", [])}
    if (paciente != patient_rs or (issuer_rs and issuer_rs != emissor)
            or (references and (frame, str(uid)) not in references)):
        raise ValueError(INCOMPATIVEL)
    rois = {int(r.ROINumber) for r in ds.get("StructureSetROISequence", [])
            if str(r.get("ReferencedFrameOfReferenceUID", "")) == frame}
    ref_sops = set()
    desenhado = False
    for roi in ds.get("ROIContourSequence", []):
        contours = roi.get("ContourSequence", [])
        if contours and int(roi.ReferencedROINumber) not in rois:
            raise ValueError(INCOMPATIVEL)
        for contour in contours:
            pontos = contour.get("ContourData", [])
            tipo = str(contour.get("ContourGeometricType", ""))
            if tipo in ("CLOSED_PLANAR", "CLOSEDPLANAR_XOR") and len(pontos) >= 9:
                if (len(pontos) != int(contour.NumberOfContourPoints) * 3
                        or not all(math.isfinite(float(x)) for x in pontos)):
                    raise ValueError(INVALIDO)
                desenhado = True
            for image in contour.get("ContourImageSequence", []):
                ref_sops.add(str(image.get("ReferencedSOPInstanceUID", "")))
    if not desenhado:
        raise ValueError(INVALIDO)
    for ref_frame in ds.get("ReferencedFrameOfReferenceSequence", []):
        for referenced_study in ref_frame.get("RTReferencedStudySequence", []):
            for series in referenced_study.get("RTReferencedSeriesSequence", []):
                if str(series.get("SeriesInstanceUID", "")) != str(uid):
                    continue
                for image in series.get("ContourImageSequence", []):
                    ref_sops.add(str(image.get("ReferencedSOPInstanceUID", "")))
    if not references and not ref_sops and study_rs != estudo:
        raise ValueError(INCOMPATIVEL)
    if ref_sops:
        sops = {str(pydicom.dcmread(f, stop_before_pixels=True, force=True,
                        specific_tags=["SOPInstanceUID"]).get("SOPInstanceUID", ""))
                for f in radai_rt.fatias_da_serie(str(pasta), str(uid))}
        if "" in ref_sops or not ref_sops.issubset(sops):
            raise ValueError(INCOMPATIVEL)
    return str(ds.get("StructureSetLabel", "")).strip() or "RTSTRUCT"


def _publicar(temporario, pasta, uid, digest):
    rotulo = _validar(temporario, pasta, uid)
    nome = PREFIX + sufixo_serie(uid) + "_" + digest + ".dcm"
    os.replace(temporario, Path(pasta) / nome)
    return {"ok": True, "arquivo": nome, "cod": "importado", "curto": rotulo,
            "rotulo": rotulo, "plugin": False, "entregue": False}


def montar(app):
    @app.post("/api/rtstruct/importar")
    async def importar(request: Request, b: str = ""):
        import radai_thumbnail

        if (request.headers.get("sec-fetch-site") == "cross-site"
                or request.headers.get("origin", str(request.base_url).rstrip("/")).rstrip("/")
                != str(request.base_url).rstrip("/")):
            return JSONResponse({"erro": "Origem do pedido inválida."}, status_code=403)
        pasta, uid = radai_thumbnail.resolver(b)
        if not pasta or not uid:
            return JSONResponse({"erro": "Escolha uma série."}, status_code=404)
        temporario = None
        try:
            with NamedTemporaryFile(dir=pasta, suffix=".part", delete=False) as f:
                temporario = f.name
                digest = hashlib.sha256()
                tamanho = 0
                async for bloco in request.stream():
                    tamanho += len(bloco)
                    if tamanho > CAP:
                        return JSONResponse({"erro": "O arquivo excede 128 MB."}, status_code=413)
                    digest.update(bloco)
                    f.write(bloco)
            return await run_in_threadpool(_publicar, temporario, pasta, uid, digest.hexdigest())
        except (ValueError, KeyError, AttributeError, TypeError, pydicom.errors.InvalidDicomError) as exc:
            erro = INCOMPATIVEL if str(exc) == INCOMPATIVEL else INVALIDO
            return JSONResponse({"erro": erro}, status_code=422)
        except OSError:
            return JSONResponse({"erro": "Não consegui gravar."}, status_code=500)
        finally:
            if temporario:
                Path(temporario).unlink(missing_ok=True)


CONTROLE = """<label class="ui-bt op" style="position:relative"><span data-radai-frase>Importar RTSTRUCT</span>
<input type="file" data-rs-import accept=".dcm,application/dicom,application/octet-stream" aria-label="Importar RTSTRUCT" style="position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:pointer"></label>
<span data-rs-status role="status" aria-live="polite"></span>"""

JS = """
if(typeof document!=="undefined" && document.addEventListener)document.addEventListener('change',async function(e){
 const input=e.target;
 if(!input.matches('[data-rs-import]')||!input.files.length)return;
 const file=input.files[0]; input.value='';
 const ticket=()=>window.CP&&CP.serie?CP.serie.b:(window.R3?R3.b:'');
 const b=ticket(), status=document.querySelector('[data-rs-status]');
 const tell=s=>window.uiTexto?uiTexto(status,s):status.textContent=s;
 if(!b){tell('Escolha uma série.');return}
 input.disabled=true;
 try{
  const r=await fetch('/api/rtstruct/importar?b='+encodeURIComponent(b),
    {method:'POST',headers:{'Content-Type':'application/dicom'},body:file});
  const row=await r.json();
  if(b!==ticket())return;
  if(!r.ok||!row.ok)throw Error(row.erro||'Não consegui importar.');
  if(window.CP&&CP.serie){
   if(!CP.serie.rs.some(item=>item.arquivo===row.arquivo))CP.serie.rs.push(row);
   cpAbrirSerie(CP.serie);cpTrocarArquivo(1,row.arquivo);
  }else if(window.R3){
   if(window.R3M)R3M.preset={rs:row.arquivo,nomes:[]};
   r3Abrir(b,R3.rotulo);
  }
  tell('Importado.');
 }catch(err){tell(err.message||'Não consegui importar.')}
 finally{input.disabled=false}
});
"""
