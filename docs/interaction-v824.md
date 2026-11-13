# Interaction fixes after 8.23

Author requested changes on 2026-11-13. Baseline Suite e2cc54f / Neuro 53584cb.
No model or Python changes. Preserve published pins and parallel engineering work.

## Work ownership

- Root: shared folder selector, date sorting, viewer guidance, remove DICOM toolbar
  from the skin/bolus work area; integration, verification and light release.
- nidus_v824: actual thinking-states recipe, automatic temporal discovery from the
  current study, projection paint/save feedback, cache and consensus refresh.
- editor_v824: patient/series identity, inline/resumable draft, native ROI editor,
  automatic anchor interpolation with explicit preview/apply, center and 3D.
- brachy_v824: isolated source from published Bolus v8.10; skin paint and channel
  coverage with existing physical clearance, wall and curvature checks preserved.

## Accepted interaction

- Selecting a folder initiates the series scan once; no second search button.
  Manual pasted paths remain usable through Enter. Folder list defaults to newest.
- Editor uses large axial plus coronal/sagittal/3D stacked; drafts persist locally
  in the current application session when returning. Export remains explicit.
- Interpolation uses consecutive manually drawn anchor planes, preserves anchors,
  shows preview, and commits only through Apply. No range form exposed.
- Patient geometry and identity stay bound to the selected native series. Do not
  silently transfer contours to another series or invent CINE acquisitions.
- Existing and new ROI previews update locally in 3D; export writes a separate
  UNAPPROVED RTSTRUCT with the existing integrity verification.

## Release gates

Browser interaction reproductions of reported failures, interpolation/geometry
regressions, series generation/cancellation tests, brachy phantom coverage and
clearance tests, 12-language strings, build/pin/runtime/installer validation,
GitHub and mirror checks including blocked-GitHub startup. No clinical images,
weights or Python in published artifacts.
