========================================
OUTPUT FOLDER
========================================

This folder will contain results after pipeline execution.

Expected Files (per patient):
------------------------------
full_comparison_lung_001.png  - Visualization for Patient 1
full_comparison_lung_002.png  - Visualization for Patient 2
full_comparison_lung_003.png  - Visualization for Patient 3
full_comparison_lung_004.png  - Visualization for Patient 4

covid_results_lung_001.json   - Detection results for Patient 1
covid_results_lung_002.json   - Detection results for Patient 2
covid_results_lung_003.json   - Detection results for Patient 3
covid_results_lung_004.json   - Detection results for Patient 4

Visualization Format (2x3 Grid):
--------------------------------
Row 1:
  - CT Scan (grayscale)
  - Lung Mask (colored overlay)
  - COVID Overlay (GGO=yellow, Consolidation=red)

Row 2:
  - Metrics (GGO%, Consolidation%, etc.)
  - Features (HU-based analysis)
  - Clinical Decision (Likelihood, Severity)

JSON Format:
------------
{
  "patient_id": "lung_001",
  "diagnosis": {
    "covid_likelihood": "HIGH/MODERATE/LOW",
    "covid_probability": 0-100,
    "severity": "SEVERE/MODERATE/MILD"
  },
  "features": {
    "ggo_percentage": ...,
    "consolidation_percentage": ...,
    ...
  }
}

Download Command:
-----------------
After pipeline completes in Kubeflow:
  > .\DOWNLOAD_OUTPUT.ps1

This will fetch all results from Minikube to this folder.

========================================
