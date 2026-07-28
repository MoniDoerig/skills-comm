#!/usr/bin/env bash
# registration_qc.sh — orchestrate registration QC with validated binaries.
#
# Runs the metric battery (Jacobian regularity, intensity similarity, label
# overlap) and renders the diagnostic visuals, then writes a metrics file and a
# report scaffold. It does NOT compute any metric itself — every number comes
# from a validated tool (ANTs / FSL / c3d); this script only orchestrates and
# parses. It also does NOT decide the verdict: a human/agent applies the rubric
# in references/rubric.md to the metrics + visuals. Keep this script as the
# reproducibility record of exactly what was run.
#
# Usage:
#   registration_qc.sh --fixed F --moving-warped W --outdir D --subject ID \
#     [--warp WARP] [--moving-labels ML --ref-labels RL] [--mask M] \
#     [--mode same|cross] [--timestamp TS]
#
# Required: --fixed, --moving-warped, --outdir, --subject
# Optional: --warp (enables Jacobian), --moving-labels + --ref-labels (enables
#           Dice; both must be in the target space), --mask (restrict metrics),
#           --mode (same|cross modality; sets similarity metric; default same)

set -euo pipefail

# --- Pin tool versions (adjust to versions present; discover with `ml avail`) ---
# module load ants/2.6.0 fsl/6.0.7.16 convert3d
# (Left commented so the script also runs where tools are already on PATH.)

MODE="same"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
WARP=""; MOVING_LABELS=""; REF_LABELS=""; MASK=""
FIXED=""; MOVING_WARPED=""; OUTDIR=""; SUBJECT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --fixed) FIXED="$2"; shift 2;;
    --moving-warped) MOVING_WARPED="$2"; shift 2;;
    --warp) WARP="$2"; shift 2;;
    --moving-labels) MOVING_LABELS="$2"; shift 2;;
    --ref-labels) REF_LABELS="$2"; shift 2;;
    --mask) MASK="$2"; shift 2;;
    --mode) MODE="$2"; shift 2;;
    --subject) SUBJECT="$2"; shift 2;;
    --outdir) OUTDIR="$2"; shift 2;;
    --timestamp) TIMESTAMP="$2"; shift 2;;
    *) echo "Unknown arg: $1" >&2; exit 1;;
  esac
done

[[ -n "$FIXED" && -n "$MOVING_WARPED" && -n "$OUTDIR" && -n "$SUBJECT" ]] || {
  echo "ERROR: --fixed, --moving-warped, --outdir, --subject are required" >&2; exit 1; }

# --- Verify required binaries are available (do not assume) ---
need() { command -v "$1" >/dev/null 2>&1 || { echo "ERROR: '$1' not on PATH — load its module" >&2; exit 1; }; }
need MeasureImageSimilarity
need fslstats
HAVE_C3D=0; command -v c3d >/dev/null 2>&1 && HAVE_C3D=1

QC="${OUTDIR}/qc"; mkdir -p "$QC"
PREFIX="${QC}/${SUBJECT}_${TIMESTAMP}"
METRICS="${PREFIX}_metrics.txt"
REPORT="${PREFIX}_ai_eval.md"
: > "$METRICS"

log() { echo "$1" | tee -a "$METRICS"; }
log "# Registration QC metrics — ${SUBJECT} @ ${TIMESTAMP}"
log "fixed=${FIXED}  moving_warped=${MOVING_WARPED}  mode=${MODE}"

# --- 1. Deformation regularity (Jacobian) — requires the warp field ---
FOLD_PCT="n/a"; JAC_MIN="n/a"; JAC_MAX="n/a"; LOGJAC_SD="n/a"; FOLDING="unknown"
if [[ -n "$WARP" ]]; then
  need CreateJacobianDeterminantImage
  JAC="${PREFIX}_jac.nii.gz"; LOGJAC="${PREFIX}_logjac.nii.gz"
  CreateJacobianDeterminantImage 3 "$WARP" "$JAC" 0 0
  CreateJacobianDeterminantImage 3 "$WARP" "$LOGJAC" 1 0
  read -r JAC_MIN JAC_MAX < <(fslstats "$JAC" -R)
  if [[ -n "$MASK" ]]; then LOGJAC_SD=$(fslstats "$LOGJAC" -k "$MASK" -s); else LOGJAC_SD=$(fslstats "$LOGJAC" -s); fi
  if [[ "$HAVE_C3D" -eq 1 ]]; then
    FOLD=$(c3d "$JAC" -thresh -inf 0 1 0 -voxel-sum | grep -oE '[0-9.eE+-]+' | tail -1)
    TOT=$(fslstats "$JAC" -V | awk '{print $1}')
    FOLD_PCT=$(awk -v f="$FOLD" -v t="$TOT" 'BEGIN{ if(t>0) printf "%.4f", 100*f/t; else print "n/a" }')
  fi
  FOLDING=$(awk -v m="$JAC_MIN" 'BEGIN{ print (m+0<=0)?"YES":"no" }')
  log "Jacobian: min=${JAC_MIN} max=${JAC_MAX} logJacSD=${LOGJAC_SD} foldingPct=${FOLD_PCT} folding=${FOLDING}"
else
  log "Jacobian: SKIPPED (no --warp) — folding/regularity NOT assessable"
fi

# --- 2. Intensity similarity (metric by modality) — in-mask if provided ---
case "$MODE" in
  cross) MET="MI[${FIXED},${MOVING_WARPED},1,32]";;
  *)     MET="CC[${FIXED},${MOVING_WARPED},1,4]";;
esac
if [[ -n "$MASK" ]]; then
  SIM=$(MeasureImageSimilarity -d 3 -m "$MET" -x "$MASK" | tail -1)
else
  SIM=$(MeasureImageSimilarity -d 3 -m "$MET" | tail -1)
fi
log "Similarity(${MODE}, ${MET%%[*}): ${SIM}"

# --- 3. Label overlap — requires both label maps in the target space ---
MEAN_DICE="n/a"; WORST_ROI="n/a"; WORST_DICE="n/a"
if [[ -n "$MOVING_LABELS" && -n "$REF_LABELS" ]]; then
  need LabelOverlapMeasures
  OVCSV="${PREFIX}_overlap.csv"
  LabelOverlapMeasures 3 "$MOVING_LABELS" "$REF_LABELS" "$OVCSV" >/dev/null
  # CSV cols: Label,Total,Jaccard,Dice,... ; average Dice over labels>0, find worst.
  MEAN_DICE=$(awk -F, 'NR>1 && $1+0>0 {s+=$4; n++} END{ if(n>0) printf "%.4f", s/n; else print "n/a" }' "$OVCSV")
  read -r WORST_ROI WORST_DICE < <(awk -F, 'NR>1 && $1+0>0 {if(w==""||$4+0<w){w=$4;r=$1}} END{print r, w}' "$OVCSV")
  log "Overlap: meanDice=${MEAN_DICE} worstROI=${WORST_ROI} worstDice=${WORST_DICE} (csv=${OVCSV})"
else
  log "Overlap: SKIPPED (need --moving-labels and --ref-labels in target space)"
fi

# --- 4. Visuals (tools; each guarded so metrics still complete) ---
EDGE="${PREFIX}_edge.png"; JACPNG="${PREFIX}_jac.png"; MOSAIC="${PREFIX}_mosaic.png"
if command -v fsleyes >/dev/null 2>&1; then
  fsleyes render --outfile "$EDGE" "$MOVING_WARPED" "$FIXED" -ot edge -lw 2 -cm red \
    || echo "WARNING: edge overlay render failed"
  [[ -n "$WARP" ]] && fsleyes render --outfile "$JACPNG" "$FIXED" "${PREFIX}_jac.nii.gz" \
    -cm brain_colours_diverging -dr 0 2 -a 60 || true
elif command -v slices >/dev/null 2>&1; then
  slices "$MOVING_WARPED" "$FIXED" -o "$EDGE" || echo "WARNING: slices edge overlay failed"
fi
if command -v CreateTiledMosaic >/dev/null 2>&1 && command -v ConvertScalarImageToRGB >/dev/null 2>&1; then
  ConvertScalarImageToRGB 3 "$MOVING_WARPED" "${PREFIX}_rgb.nii.gz" none hot >/dev/null 2>&1 \
    && CreateTiledMosaic -i "$FIXED" -r "${PREFIX}_rgb.nii.gz" -o "$MOSAIC" -a 0.35 -t -1x-1 -d 2 \
       >/dev/null 2>&1 || echo "WARNING: mosaic failed"
fi

# --- 5. Report scaffold (criteria left for the agent/human to rate via rubric) ---
cat > "$REPORT" <<EOF
## Registration QC — ${SUBJECT} (${MOVING_WARPED} → ${FIXED})

**Verdict: <PASS | BORDERLINE | FAIL>  ·  Confidence: <HIGH | MEDIUM | LOW>**

### Quantitative
| Metric | Value | Reference / cohort |
|--------|-------|--------------------|
| Folding (Jacobian ≤0) | ${FOLD_PCT}% | 0% required |
| Jacobian min / max | ${JAC_MIN} / ${JAC_MAX} | strictly positive |
| log-Jacobian SD | ${LOGJAC_SD} | vs cohort |
| Similarity (${MODE}) | ${SIM} | expected range / cohort |
| Mean Dice | ${MEAN_DICE} | size-dependent |
| Worst ROI Dice | ${WORST_ROI}=${WORST_DICE} | flag if collapsed |

### Criteria  (rate per references/rubric.md; folding=${FOLDING} is a HARD-STOP if YES)
| Criterion | Rating | Notes |
|-----------|--------|-------|
| 1. Boundary / structural correspondence | <> | see ${EDGE} |
| 2. Deformation regularity (no folding) | <> | folding=${FOLDING} |
| 3. Label / tissue overlap | <> | meanDice=${MEAN_DICE} |
| 4. Intensity similarity | <> | ${SIM} |
| 5. Global alignment / no gross error | <> | check space/orientation/swap |

### Reasoning
<which criteria drove the verdict; dominant concern; why this confidence>

### Visuals
${EDGE}
$( [[ -n "$WARP" ]] && echo "${JACPNG}" )
${MOSAIC}

### Recommendation
<use as-is / use with caution in region X / re-run with changes Y / manual review>
EOF

echo "Metrics:  ${METRICS}"
echo "Report scaffold: ${REPORT}  (fill criteria/verdict via references/rubric.md)"
echo "Visuals:  ${QC}/${SUBJECT}_${TIMESTAMP}_*.png"
