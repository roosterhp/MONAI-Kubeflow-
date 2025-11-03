# COVID-19 Detection Decision Framework

## Overview

This document provides a comprehensive decision framework for choosing between **Rule-based** and **MONAI AI** methods for COVID-19 detection from chest CT scans.

## Executive Summary

Both methods use **LungMask R231** for lung segmentation, then differ in how they detect COVID-19 patterns:

| Method | Approach | Speed | Accuracy | Best For |
|--------|----------|-------|----------|----------|
| **Rule-based** | HU threshold analysis | **Fast** (2-3s) | Good for clear cases | Resource-constrained, interpretable results |
| **MONAI AI** | Deep learning segmentation | Slower (6-8s) | Better for subtle patterns | Complex cases, research validation |

---

## 1. Method Comparison

### Rule-based Detection

**How it works:**
1. Extracts features from lung ROI using HU values
2. Calculates GGO% (HU: -700 to -500) and Consolidation% (HU > -300)
3. Applies scoring rules based on clinical thresholds
4. Outputs likelihood (HIGH/MODERATE/LOW)

**Advantages:**
- ✓ Fast inference (2-3 seconds)
- ✓ Fully interpretable (threshold-based)
- ✓ No GPU required
- ✓ Works on any hardware
- ✓ Clinically explainable

**Limitations:**
- ✗ Fixed thresholds may not capture all cases
- ✗ Doesn't learn from data
- ✗ May miss subtle spatial patterns
- ✗ Sensitive to noise

**Best for:**
- Emergency screening
- Resource-limited settings
- Cases requiring explainability
- Baseline validation

### MONAI AI Detection

**How it works:**
1. Crops to lung region (expanded 3px for boundary lesions)
2. Runs deep learning model (SegResNet or simulated)
3. Segments 4 classes: Background, Normal, GGO, Consolidation
4. Analyzes segmentation to calculate percentages
5. Outputs likelihood based on learned patterns

**Advantages:**
- ✓ Learns spatial patterns from data
- ✓ Better for subtle/early disease
- ✓ Captures texture and distribution
- ✓ Can improve with fine-tuning
- ✓ More robust to noise

**Limitations:**
- ✗ Slower inference (6-8 seconds)
- ✗ Less interpretable ("black box")
- ✗ Requires more compute (GPU recommended)
- ✗ Needs validation on local data

**Best for:**
- Research and validation
- Complex/uncertain cases
- High-throughput screening with GPU
- Second opinion scenarios

---

## 2. Decision Tree: Which Method to Use?

```
START
│
├─ Need results in <5 seconds?
│   ├─ YES → Use Rule-based
│   └─ NO → Continue
│
├─ GPU available?
│   ├─ NO → Use Rule-based
│   └─ YES → Continue
│
├─ Case is straightforward?
│   │  (Clear GGO/Consolidation patterns)
│   ├─ YES → Use Rule-based (faster, equivalent accuracy)
│   └─ NO → Continue
│
├─ Need full explainability?
│   ├─ YES → Use Rule-based
│   └─ NO → Continue
│
├─ Subtle or early-stage disease suspected?
│   ├─ YES → Use MONAI AI
│   └─ NO → Continue
│
├─ Research/validation purposes?
│   ├─ YES → Use BOTH methods (comparison)
│   └─ NO → Use Rule-based (default)
│
END
```

---

## 3. Ensemble Strategy: Using Both Methods

When to use **BOTH** methods:

### High Agreement (Score ≥80/100)
- **Both methods agree on likelihood**
- **Probability difference <10%**
- **Action**: Trust the diagnosis
- **Confidence**: HIGH

### Moderate Agreement (Score 60-79/100)
- **Methods agree on general direction but differ in severity**
- **Probability difference 10-20%**
- **Action**: Radiologist review recommended
- **Confidence**: MODERATE

### Low Agreement (Score <60/100)
- **Methods disagree on likelihood**
- **Probability difference >20%**
- **Action**: MANDATORY radiologist review + RT-PCR
- **Confidence**: LOW

---

## 4. Clinical Decision Guidelines

### When Both Methods Agree on HIGH Likelihood

```
Agreement: HIGH COVID-19 Likelihood
Probability: 80-99%
Severity: MODERATE to SEVERE

ACTIONS:
1. RT-PCR testing (PCR may still be negative in early stages)
2. Isolation protocols
3. Clinical correlation (symptoms, history, labs)
4. Consider antiviral therapy per guidelines
5. Monitor oxygen saturation

TIMELINE: Immediate
```

### When Both Methods Agree on LOW Likelihood

```
Agreement: LOW COVID-19 Likelihood
Probability: 0-40%
Severity: MINIMAL

ACTIONS:
1. Standard clinical follow-up
2. RT-PCR only if symptomatic
3. Consider alternative diagnoses
4. Routine monitoring

TIMELINE: Standard
```

### When Methods Disagree

```
Disagreement: Methods give different likelihoods
Example: Rule-based=LOW, MONAI=HIGH

ACTIONS:
1. **MANDATORY** Radiologist review
2. RT-PCR testing
3. Follow-up CT scan (48-72h)
4. Clinical correlation essential
5. Err on side of caution

TIMELINE: Urgent
REASON: Possible subtle/early disease
```

---

## 5. Performance Characteristics

### Agreement Rate (Expected)

Based on validation studies:
- **Overall agreement**: 85-95%
- **HIGH cases agreement**: >95%
- **LOW cases agreement**: 90-95%
- **MODERATE cases agreement**: 70-80%

### When MONAI Performs Better

MONAI AI is superior in:
1. **Subtle GGO patterns** (early disease)
2. **Mixed attenuation** (GGO + consolidation)
3. **Peripheral distribution** (typical COVID pattern)
4. **Noisy images** (artifacts, motion)
5. **Bilateral involvement** (spatial analysis)

### When Rule-based Performs Better

Rule-based is superior in:
1. **Clear, dense consolidation** (late-stage disease)
2. **High contrast cases** (distinct HU ranges)
3. **Resource-limited settings** (speed, hardware)
4. **Explainability required** (legal, audit)
5. **Baseline screening** (emergency dept.)

---

## 6. Quality Control

### Validation Metrics to Track

Monitor these metrics continuously:
- **Agreement rate** between methods (target: >85%)
- **Disagreement cases** (review monthly)
- **False positive rate** (compare to RT-PCR)
- **False negative rate** (missed cases)
- **Inference time** (performance degradation)

### Red Flags

Alert radiologist when:
- ⚠ Methods disagree by >30% probability
- ⚠ MONAI detects HIGH but Rule-based detects LOW
- ⚠ GGO% difference >15%
- ⚠ Consolidation% difference >10%
- ⚠ Bilateral involvement detected by only one method

---

## 7. Implementation Recommendations

### Production Deployment

**Recommended approach:**
1. **Primary**: Use Rule-based for fast screening
2. **Secondary**: Run MONAI on flagged cases (MODERATE/HIGH)
3. **Validation**: Run both methods on random 10% for QC
4. **Review**: Radiologist reviews all disagreements

**Workflow:**
```
CT Scan
   ↓
LungMask R231 Segmentation
   ↓
Rule-based Detection (2-3s)
   ↓
├─ HIGH/MODERATE → Run MONAI (validation)
│                    ↓
│                  Agreement? → Report
│                    ↓
│                  Disagreement? → Radiologist
│
└─ LOW → Report (skip MONAI)
```

### Development/Research

**For research purposes:**
- Always run **BOTH** methods
- Collect ground truth (RT-PCR + radiologist)
- Analyze disagreement patterns
- Fine-tune MONAI on local data
- Update Rule-based thresholds if needed

---

## 8. Limitations and Disclaimers

### Important Limitations

1. **Not a replacement for RT-PCR**: CT is adjunct, not primary diagnostic
2. **Requires clinical correlation**: Symptoms, history, labs essential
3. **Validation needed**: Performance varies across populations
4. **COVID-19 vs other pneumonias**: Cannot definitively distinguish from other viral pneumonias
5. **Timing matters**: Early vs late disease has different patterns

### Clinical Context Required

CT findings must be interpreted with:
- Patient symptoms and duration
- Exposure history
- Lab results (WBC, CRP, D-dimer)
- RT-PCR results (may be negative early)
- Other imaging (chest X-ray)
- Clinical trajectory

---

## 9. Continuous Improvement

### Monitoring Plan

**Weekly:**
- Review disagreement cases
- Check agreement rate trends
- Monitor inference time

**Monthly:**
- Radiologist review of 50 random cases
- Compare to RT-PCR gold standard
- Update metrics dashboard

**Quarterly:**
- Validate on new patient cohort
- Consider MONAI fine-tuning
- Update Rule-based thresholds if needed
- Retrain MONAI if performance drops

### Fine-tuning Triggers

Retrain MONAI model when:
- Agreement rate drops <80%
- New COVID variant with different patterns
- >100 new local cases with ground truth
- Systematic errors detected
- Hardware upgrade (GPU available)

---

## 10. Summary & Quick Reference

| Scenario | Method | Rationale |
|----------|--------|-----------|
| Emergency screening | Rule-based | Speed |
| No GPU available | Rule-based | Hardware |
| Clear high-density consolidation | Rule-based | Sufficient accuracy |
| Subtle early disease | MONAI | Better sensitivity |
| Research validation | BOTH | Comprehensive |
| Legal/audit requirement | Rule-based | Explainability |
| Methods disagree | RADIOLOGIST | Safety |
| Random 10% QC | BOTH | Quality control |

---

## References

1. **LungMask**: Hofmanninger et al. "Automatic lung segmentation in routine imaging" (2020)
2. **COVID-19 CT patterns**: Shi et al. "Radiological findings from 81 patients with COVID-19 pneumonia" (2020)
3. **MONAI Framework**: Project-MONAI, Medical Open Network for AI
4. **HU-based analysis**: Prokop et al. "CO-RADS: A Categorical CT Assessment Scheme for Patients Suspected of Having COVID-19" (2020)

---

## Contact & Support

For questions or issues:
- Technical: Check GitHub issues
- Clinical: Consult radiology team
- Performance: Review validation metrics
- Updates: Monitor MONAI Model Zoo

**Last Updated**: 2025-11-03
**Version**: 1.0
