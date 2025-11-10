# Option 1: Direct Replacement

## Tổng quan

Option 1 là phương pháp **đơn giản nhất**: thay thế trực tiếp MONAI model bằng external model mà **KHÔNG CẦN wrapper**.

## Khi nào dùng

- Model external đã là `torch.nn.Module`
- Input/output shape tương thích sẵn (1 channel cho CT, 3D spatial dims)
- Model đã được train trên medical data tương tự
- Muốn giải pháp đơn giản nhất với ít code nhất

## Ưu điểm

✅ Đơn giản nhất - chỉ **5 dòng code** thay đổi
✅ Không cần viết wrapper hoặc adapter
✅ Giữ nguyên 100% MONAI infrastructure
✅ Nhanh - không có overhead
✅ Easy to maintain

## Nhược điểm

⚠️ Yêu cầu model phải compatible sẵn (khó tìm)
⚠️ Input shape phải khớp (1 channel, 3D)
⚠️ Không tận dụng pretrained ImageNet weights (vì input shape khác)
⚠️ Model phải đã train trên medical data

## Files trong folder

- **`demo_baseline.py`** - BEFORE: MONAI DenseNet121 only
- **`demo_with_external.py`** - AFTER: External compatible model (có cải thiện)
- **`demo_external_direct.py`** - Full comparison BEFORE/AFTER trong 1 file

## Cách chạy

```bash
cd week4/option1

# Chạy từng file để thấy rõ sự khác biệt
python demo_baseline.py        # BEFORE: MONAI only
python demo_with_external.py   # AFTER: External model

# Hoặc chạy full comparison trong 1 file
python demo_external_direct.py # BEFORE + AFTER cùng lúc
```

## Code Example

### BEFORE: MONAI Model

```python
from monai.networks.nets import DenseNet121
from monai.inferers import SimpleInferer

# MONAI model
model = DenseNet121(
    spatial_dims=3,
    in_channels=1,
    out_channels=2
)

# Inference
inferer = SimpleInferer()
output = inferer(inputs=batch["image"], network=model)
```

### AFTER: External Model (Direct)

```python
# Load external compatible model
from your_research_paper import BetterCOVIDModel

model = BetterCOVIDModel()  # Already compatible!
model.load_state_dict(torch.load("weights_95acc.pth"))

# Same inferer, same transforms, same DataLoader
# ONLY CHANGE: the model!
inferer = SimpleInferer()  # Same!
output = inferer(inputs=batch["image"], network=model)  # Same!
```

**Chỉ 5 dòng code thay đổi!**

## Điều kiện cần

Model external phải thỏa mãn:

1. ✅ `isinstance(model, torch.nn.Module)` = True
2. ✅ Input shape: `(Batch, 1, Depth, Height, Width)` - 3D CT grayscale
3. ✅ Output shape: `(Batch, num_classes)` - Classification logits
4. ✅ Đã train trên medical CT data hoặc similar domain

Nếu KHÔNG thỏa mãn → Dùng **Option 2 (Wrapper)** hoặc **Option 3 (Ensemble)**

## So sánh với Options khác

| Tiêu chí | Option 1 | Option 2 | Option 3 |
|----------|----------|----------|----------|
| **Độ đơn giản** | ⭐⭐⭐⭐⭐ Rất đơn giản | ⭐⭐⭐ Trung bình | ⭐⭐ Phức tạp |
| **Code changes** | 5 dòng | 30 dòng | 50+ dòng |
| **Compatibility required** | Cao | Thấp | Rất thấp |
| **Pretrained ImageNet** | ❌ Không | ✅ Có | ✅ Có |
| **Accuracy** | Có cải thiện | Cải thiện tốt | Cải thiện cao nhất |
| **Inference speed** | Nhanh | Nhanh | Chậm (3x) |

## Khi nào KHÔNG dùng Option 1

❌ Model pretrained trên ImageNet (3 channels RGB) → **Dùng Option 2**
❌ Model input/output shape khác → **Dùng Option 2**
❌ Muốn accuracy tối đa → **Dùng Option 3**
❌ Không có external model compatible → **Dùng Option 2** hoặc train lại model

## Real-world Use Cases

**Khi bạn có:**
- Research paper model đã train trên medical CT
- Pretrained model từ medical imaging competition (Kaggle, Grand Challenge)
- Model từ collaborator đã train trên similar dataset
- Open-source medical imaging model với compatible architecture

**Example Sources:**
- Medical Segmentation Decathlon pretrained weights
- COVID-19 detection models từ research papers
- LUNA16 lung nodule detection models
- Models từ Grand Challenge leaderboards

## Expected Results

| Metric | Value |
|--------|-------|
| **Accuracy** | Có cải thiện |
| **Code changes** | ~5 dòng |
| **Inference time** | Same (~0.12s) |
| **Complexity** | Very low |
| **Recommended for** | Quick wins với compatible models |

## Next Steps

1. Chạy demo để hiểu cách hoạt động
2. Nếu có external compatible model → Use Option 1!
3. Nếu không → Xem Option 2 (Wrapper) hoặc Option 3 (Ensemble)
