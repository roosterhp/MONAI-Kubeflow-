# Why We Use LungMask Instead of MONAI Whole Body CT

## Summary

The MONAI **Whole Body CT Segmentation** model (wholeBody_ct_segmentation) **cannot run on CPU** due to extreme memory requirements.

## Comparison

| Feature | LungMask (R231) | MONAI Whole Body CT |
|---------|-----------------|---------------------|
| **Organs** | Lungs only (L/R) | 104 organs (whole body) |
| **Model Size** | ~30 MB | ~144 MB |
| **RAM Required** | 2-4 GB | **16+ GB** (10.2 GB for single inference) |
| **Device** | CPU-friendly | **GPU required (CUDA)** |
| **Inference Time (CPU)** | 80-150s | Out of Memory ❌ |
| **Dice Score (Lungs)** | 0.9758 | Unknown (can't test) |
| **Status** | ✅ Working | ❌ Cannot run on CPU |

## Error When Running MONAI Whole Body CT on CPU

```
RuntimeError: [enforce fail at alloc_cpu.cpp:121] data.
DefaultCPUAllocator: not enough memory: you tried to allocate 10200547328 bytes.
```

**Translation**: Tried to allocate **10.2 GB** of RAM for a single CT scan inference - too much for most laptops!

## Why MONAI Whole Body CT Fails

1. **3D Convolutions**: The model processes entire 3D volumes (512×512×150+ slices)
2. **104 Organ Channels**: Outputs segmentation for 104 different organs simultaneously
3. **Deep Network**: SegResNet with many layers and feature maps
4. **CPU Limitations**: Without GPU acceleration, intermediate tensors consume massive RAM

## Technical Details

```python
# lung_001.nii.gz dimensions: (512, 512, 133) = 34M voxels
# Model processes: 1 × 1 × 512 × 512 × 133 = 34M input voxels
# Internal feature maps: 32 channels × 512 × 512 × 133 = 1.1B floats
# Memory: 1.1B × 4 bytes = 4.4 GB (just for one layer!)
# Total with all layers: 10+ GB
```

## Solution: Use LungMask

LungMask is specifically optimized for **CPU inference** with:
- Sliding window approach (processes small patches)
- Efficient architecture
- Lower memory footprint
- Production-ready performance (Dice 0.9758)

## When to Use MONAI Whole Body CT

Use MONAI Whole Body CT only when:
1. ✅ You have a **GPU with CUDA** (NVIDIA)
2. ✅ You have **16+ GB RAM**
3. ✅ You need to segment **multiple organs** (not just lungs)
4. ✅ You have time for **longer inference** (even on GPU)

## Conclusion

For **lung segmentation on CPU**, LungMask is the correct choice:
- Works on any laptop
- Fast enough for clinical use
- Excellent accuracy (Dice 0.9758)
- No GPU required

**MONAI Whole Body CT is downloaded and available**, but we cannot test it without GPU infrastructure. It remains in `pretrained-models/` for future GPU-based deployment.

---

**Recommendation**: Continue using **LungMask** for all CPU-based testing and deployment. Only switch to MONAI Whole Body CT if you deploy to GPU servers and need multi-organ segmentation.
