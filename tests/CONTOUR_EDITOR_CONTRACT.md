# Shared host contour editor

Canonical modules: `app/radai_contour_edit.py` and `app/radai_contour_edit_api.py`.
Mount with `radai_contour_edit_api.montar(app)` in the Suite router. No pinned
RECON code was changed.

## Existing code used

- Suite `radai_viewer.RadaiPalco`: existing MPR toolbar/click adapter, plane
  selectors and normalized image points. New adapters launch one host editor.
- Suite `radai_thumbnail.resolver`: opaque series ticket resolution;
  `radai_tabela_acervo.resolver` additionally checks archive membership.
- ContourLab `radai_viewseg`: read-only /api/verseg/{forma,ct,estruturas,
  contornos,centro,recon3d,nuvem3d}; this was not a generic ROI editor.
- ContourLab `engine`: `_adicionar_roi` (no polygon simplification),
  `_mascara_para_o_rt_utils`, `para_o_plano_da_serie`, `gravar_rtstruct`, and
  `gravar_dicom_em_fluxo` are the same primitives used by the existing writer.
- NEURO `export_study` also uses this writer. NIDUS's private consensus mask
  editor remains separate; the toolbar opens this host service.

## API

Base `/api/contour-edit`. POST `/open` accepts `{b,source,uid?,rs?}` with source
`thumbnail` or `archive`; it never accepts an arbitrary image directory.
`rs` is an opaque listed ID or a listed basename. Default is a blank session
with compatible RTSTRUCT choices. `/state?s=` returns the same state.

State: `session,csrf,revision,shape[z,y,x],spacing[z,y,x],origin,direction,
window{center,width},plane_labels,rois[{id,name,color,edited,editable,reason}],
rs_files[{id,name,label}],source_rtstruct,can_undo,can_redo`.

All mutations after open include `{s,csrf,revision}`. Invalid token is403;
stale revision is409. Endpoints:

- `/import {rs,discard:false}`; `discard:true` is explicit intentional discard.
- `/new-roi {name,color}`, `/rename {roi,name}`.
- `/stroke {roi,plane,index,points,diameter_mm,operation}`; operation brush,
  erase, polygon, polygon-erase. 1–4096 points, normalized pixel-edge coordinates.
- `/undo`, `/redo` include drawing and metadata creation/renaming.
- `/interpolate {roi,plane,apply:false}` detects all manual anchors in that
  plane and previews each consecutive interval. Imported contours supply
  nonempty reference slices when no manual pair is present. The legacy
  `start,end` API remains supported; the UI no longer exposes these controls.
  `/interpolate {roi,apply:true,preview_id}` applies only the same-revision preview.
  Manual reference planes are preserved. Import never implicitly fills gaps.
- `/center {roi}` returns the native `indices_zyx` and physical `center_lps`.
- `/scene {known?:{roi:geometry_revision}}` returns named, colored LPS meshes.
  Unchanged geometry returns metadata with `unchanged:true`; the client merges
  it with its previous mesh. Per-ROI invalidation and GPU buffers avoid a full
  scene rebuild after one brush. Skipped complex/unsupported ROIs are explicit.
- `/save` returns `basename,download_url,fallback,message`.
- `/close` releases the session.

GET `/image?s=&plane=&index=&center=&width=` returns a full-size PNG. GET
`/overlay?s=&roi=&plane=&index=&preview_id=` returns
`{width,height,polygons:[[[u,v],...]],color,revision}`. Planes are acquisition
grid z/y/x, not silently resampled anatomical LPS planes. Images and overlays
use exactly the same plane transform.

Limits:128 million voxels;1.5GiB estimated per-session image/masks;2 sessions;
1hour idle expiration;32MiB drawing undo deltas;512KiB request bodies.

## Preservation and geometry

Only classic single-frame CT/MR, identical orientation and pixel spacing,
uniform nonoverlapping slice planes, same patient/study/FrameOfReference are
supported. Enhanced, irregular grids, gantry shear, invalid references and
foreign contour grids are rejected rather than approximated. Compatible
RTSTRUCT choices are filtered by patient,study,referenced series and frame.
Unsupported non-closed/mixed-frame ROIs remain in the original and copied output.

Edited masks alone use the common writer. Unedited StructureSetROISequence,
ROIContourSequence, RTROIObservationsSequence datasets are deep-copied unchanged.
Renaming alone preserves contour datasets without rasterizing them. Export
gets new SOPInstanceUID and SeriesInstanceUID, UNAPPROVED status and clears old
review/signature fields. Original bytes are never replaced. Read-only source
directories produce a new staging file with an explicit download message.

rt-utils1.2.7 reverses row/column PixelSpacing in its affine for nonsquare
pixels. `writer_add_roi` checks the actual matrix against the source affine and
temporarily swaps those two values only in the writer's private in-memory
headers if required, restoring them afterward. It does not patch rt-utils or
the existing engine globally. Oblique contours are transformed to their local
plane for TPS finishing and returned to LPS through the engine's primitives.

XOR and keyhole holes are supported. Separate nested CLOSED_PLANAR loops without
explicit XOR semantics are rejected as ambiguous rather than silently filled.
Eclipse-style newly generated inner/outer loops are labeled CLOSEDPLANAR_XOR;
Monaco uses the common writer's keyhole technique.

New masks also reuse `engine._trocar_mascara_terminal` to retain voxel-boundary
holes and single-voxel components. Before publishing, the final file is read
back and every edited mask must match the native mask voxel for voxel. A failed
comparison aborts publication. Writes use an exclusive temporary file and an
atomic rename; interrupted writes do not appear as DICOM files.

Manual files keep the `RS_LOCAL_SUITE_EDIT_` prefix. Host-only viewer discovery
validates complete DICOM series, study, patient and frame references. It adds
these copies to the 2D/3D viewers without adding evidence of AUTO completion.
The host supplies an XOR reader adapter only for its manual copies; the pinned
RECON package and the segmentation completion rules remain unchanged. Viewer
header caches are bounded and invalidate when file metadata changes.

## Editor workspace and NIDUS bridge (8.24)

The header displays source patient ID/name, study and series metadata using
text nodes. These identities never enter telemetry or public artifacts.
Layout uses a large acquisition axial plane and coronal, sagittal and 3D
stacked on the right. Native LPS edge labels remain authoritative for oblique
acquisitions; no hidden anatomical resampling is introduced.

`RadaiContourEditor.open({b,source,rs?,inlineRoot?,onPreview?,externalScene?,onClose?})`
supports the NIDUS workspace in the current page. `onPreview` receives complete
mesh arrays (the host merges API deltas), session/revision and
`reference:{b,source,uid,frame_uid}`. Consumers must match their active source
and generation. Each mesh has `geometry_revision` to reuse native GL buffers.
`externalScene:{element,resize?,request?,center?}` moves the existing NIDUS
canvas/wrapper into the 3D panel without cloning its renderer. A placeholder
and original inline style restore it on return; reopening remounts it.

Returning with edits suspends the draft in the current page, without exporting
or rereading DICOM. Opening the same source/ticket/RTSTRUCT resumes it. Explicit
discard releases it; clean sessions release memory on return. Normal page
navigation warns about unsaved edits. Drafts are session memory, not disk
backups; the existing two-session and one-hour idle resource limits apply.
`onClose(receipt|null,{draft,lastSavedReceipt,reference,session,revision})`
distinguishes the current draft from an earlier exported copy. A later brush
never deletes or replaces that earlier file. Export remains an explicit action
and retains all atomic-write and voxel round-trip checks.

The standalone 3D viewer is local WebGL with native-grid surfaces, no smoothing
or resampling, up to 250k faces per ROI and 500k total. ROI crop cap is 12M voxels;
complex/unsupported surfaces remain editable in MPR and are reported as skipped.

## Primary standard sources

- [DICOM PS3.3 C.8.8.5 Structure Set](https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.8.8.5.html): ROI numbers, frame and image series references.
- [C.8.8.6 ROI Contour](https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.8.8.6.html): closed planar versus XOR, patient-space points and contour image references.
- [C.8.8.6.3 Inner/outer contours](https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.8.8.6.3.html): keyhole and explicit XOR hole representations.
- [C.8.8.6.4 Source pixel planes](https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.8.8.6.4.html): contour grid can differ from acquisition grid; missing planes can represent actual gaps. Interpolation is an explicit editing operation, never an import assumption.

## Regression

`tests/test_contour_edit.py` and `tests/test_contour_edit_api.py`: synthetic
oblique CT,0.6×1.2×2.5mm spacing, XOR hole,1voxel, blank slice gaps, unsupported
Enhanced/irregular geometry, reference mismatch, brush/undo/redo, preview
revision, manual anchors, rename preserving contour data, original byte hash,
untouched three ROI datasets, changed source, read-only download fallback,
origin/CSRF/revision checks, payload/session limits, HTTP image/overlay/save flow.
Run with embedded Python and `RADAI_CONTOUR_APP` set if ContourLab app is not
the sibling canonical directory.
