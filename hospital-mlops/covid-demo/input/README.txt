========================================
INPUT FOLDER
========================================

This folder contains input CT scans for 4 patients.

Files:
------
lung_001.nii.gz   (115 MB)  - Patient 1
lung_002.nii.gz   ( 94 MB)  - Patient 2
lung_003.nii.gz   ( 94 MB)  - Patient 3
lung_004.nii.gz   (126 MB)  - Patient 4

Total: ~429 MB

Source:
-------
Medical Segmentation Decathlon - Task06_Lung
http://medicaldecathlon.com/

Format:
-------
NIfTI (.nii.gz) - Compressed 3D medical imaging format
Each file is a full chest CT scan

Usage:
------
These files will be uploaded to Minikube and processed
by the COVID-19 detection pipeline.

Upload Command:
  > .\UPLOAD_INPUT.ps1

Pipeline will:
  1. Segment lungs using LungMask
  2. Detect COVID-19 features (GGO, Consolidation)
  3. Generate visualization images
  4. Fine-tune model on detected cases

========================================
