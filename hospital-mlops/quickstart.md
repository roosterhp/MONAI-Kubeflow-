# Quick Start - 30 Phút

## 🎯 Mục tiêu

Trong 30 phút, bạn sẽ:
1. ✅ Download pretrained model
2. ✅ Test trên 1 CT scan
3. ✅ Có kết quả segmentation với Dice 0.98

## 🚀 Bắt đầu

### Bước 1: Setup (5 phút)

```bash
# Clone project
git clone <repo-url>
cd hospital-mlops

# Install dependencies
pip install -r requirements.txt

# Verify MONAI
python -c "import monai; print(f'MONAI {monai.__version__}')"
```

### Bước 2: Download LungMask (5 phút) ⭐ RECOMMENDED

```bash
# Cách 1: Install package (easiest)
pip install git+https://github.com/JoHof/lungmask

# Cách 2: Download weights manually
cd pretrained-models
mkdir lungmask
wget https://github.com/JoHof/lungmask/releases/download/v0.2.5/unet_r231-d5d2fc3d.pth \
  -O lungmask/R231.pth
```

### Bước 3: Test Model (10 phút)

Tạo file `test_lungmask.py`:

```python
from lungmask import mask
import SimpleITK as sitk
import numpy as np

# Load CT scan (DICOM or NIFTI)
print("Loading CT scan...")
ct_scan = sitk.ReadImage("sample_ct.nii.gz")

# Apply LungMask
print("Segmenting lungs...")
lung_mask = mask.apply(ct_scan, model='R231')

# Save result
print("Saving result...")
sitk.WriteImage(lung_mask, "lung_segmentation.nii.gz")

# Calculate volume
spacing = ct_scan.GetSpacing()
voxel_volume = spacing[0] * spacing[1] * spacing[2]  # mm^3
lung_voxels = (sitk.GetArrayFromImage(lung_mask) > 0).sum()
lung_volume_ml = (lung_voxels * voxel_volume) / 1000

print(f"\n✓ Segmentation complete!")
print(f"  Lung volume: {lung_volume_ml:.1f} ml")
print(f"  Output: lung_segmentation.nii.gz")
```

Chạy:
```bash
python test_lungmask.py
```

**Output**:
```
Loading CT scan...
Segmenting lungs...
Saving result...

✓ Segmentation complete!
  Lung volume: 4523.8 ml
  Output: lung_segmentation.nii.gz
```

### Bước 4: Visualize (10 phút)

```python
# visualize.py
import matplotlib.pyplot as plt
import SimpleITK as sitk
import numpy as np

# Load original CT and segmentation
ct = sitk.GetArrayFromImage(sitk.ReadImage("sample_ct.nii.gz"))
mask_img = sitk.GetArrayFromImage(sitk.ReadImage("lung_segmentation.nii.gz"))

# Get middle slice
slice_idx = ct.shape[0] // 2

# Plot
fig, axes = plt.subplots(1, 3, figsize=(15, 5))

# Original CT
axes[0].imshow(ct[slice_idx], cmap='gray')
axes[0].set_title('Original CT')
axes[0].axis('off')

# Segmentation mask
axes[1].imshow(mask_img[slice_idx], cmap='jet')
axes[1].set_title('Lung Mask')
axes[1].axis('off')

# Overlay
axes[2].imshow(ct[slice_idx], cmap='gray')
axes[2].imshow(mask_img[slice_idx], cmap='jet', alpha=0.3)
axes[2].set_title('Overlay')
axes[2].axis('off')

plt.tight_layout()
plt.savefig('result.png', dpi=150, bbox_inches='tight')
print("✓ Saved to: result.png")
plt.show()
```

---

## 📊 Kết quả Mong đợi

- **Accuracy**: Dice 0.98 (excellent!)
- **Speed**: 5-10 giây/CT scan
- **Output**: NIFTI file với lung mask

---

## 🎯 Next Steps

### Option A: Sử dụng luôn (No fine-tuning needed!)

LungMask accuracy đã rất cao (0.98), có thể deploy ngay:

```python
# inference_service.py
from fastapi import FastAPI, File, UploadFile
from lungmask import mask
import SimpleITK as sitk
import tempfile

app = FastAPI()

@app.post("/segment")
async def segment_lung(file: UploadFile):
    # Save uploaded file
    with tempfile.NamedTemporaryFile(suffix=".nii.gz") as tmp:
        tmp.write(await file.read())
        tmp.flush()

        # Segment
        ct = sitk.ReadImage(tmp.name)
        lung_mask = mask.apply(ct, model='R231')

        # Calculate volume
        spacing = ct.GetSpacing()
        volume_ml = (sitk.GetArrayFromImage(lung_mask) > 0).sum() * \
                    spacing[0] * spacing[1] * spacing[2] / 1000

        return {
            "lung_volume_ml": float(volume_ml),
            "status": "success"
        }
```

Deploy:
```bash
pip install fastapi uvicorn
uvicorn inference_service:app --host 0.0.0.0 --port 8000
```

Test:
```bash
curl -X POST "http://localhost:8000/segment" \
  -F "file=@sample_ct.nii.gz"
```

### Option B: Fine-tune cho lesion segmentation

Nếu cần segment lesions BẰNG trong phổi:

1. Download MONAI COVID-19 model
2. Fine-tune với hospital data
3. Xem: [docs/FINE_TUNING_GUIDE.md](docs/FINE_TUNING_GUIDE.md)

---

## 🆘 Troubleshooting

### "No module named 'lungmask'"

```bash
pip install git+https://github.com/JoHof/lungmask
```

### "CUDA out of memory"

```python
# Use CPU instead
lung_mask = mask.apply(ct_scan, model='R231', batch_size=1, force_cpu=True)
```

### Model download fails

Download manually:
```bash
wget https://github.com/JoHof/lungmask/releases/download/v0.2.5/unet_r231-d5d2fc3d.pth
# Place in: ~/.torch/models/lungmask/
```

---

## ✅ Summary

✅ **30 phút** để có working lung segmentation
✅ **Dice 0.98** accuracy
✅ **Không cần training/fine-tuning**
✅ **Deploy ngay** cho production

**Nếu cần segment lesions** → Xem [FINE_TUNING_GUIDE.md](docs/FINE_TUNING_GUIDE.md)
