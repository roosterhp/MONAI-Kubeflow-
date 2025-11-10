# Option 3: Ensemble (Two-Stage Pipeline)

## Tổng quan

Option 3 sử dụng **ensemble** của nhiều models để đạt **accuracy cao nhất**.

## Khi nào dùng

- Muốn **accuracy cao nhất** có thể
- External model rất khác biệt (không thể adapt trực tiếp)
- Muốn kết hợp strengths của nhiều models
- Production system với high-stakes decisions (medical diagnosis)
- Có nhiều pretrained models available

## Ưu điểm

✅ Accuracy cao nhất trong 3 options
✅ Giảm false positives và false negatives
✅ Robust hơn - không phụ thuộc vào 1 model
✅ Linh hoạt - có thể thêm/bớt models dễ dàng
✅ Kết hợp strengths của nhiều architectures

## Nhược điểm

⚠️ Tốn thời gian inference (chạy N models)
⚠️ Tốn memory (load N models cùng lúc)
⚠️ Phức tạp hơn về implementation
⚠️ Latency cao hơn (N x single model time)

## Files trong folder

- **`demo_baseline.py`** - BEFORE: Single MONAI model
- **`demo_with_ensemble.py`** - AFTER: Ensemble 3 models (accuracy cao nhất)
  - Strategy 1: Weighted Average
  - Strategy 2: Majority Voting

## Cách chạy

```bash
cd week4/option3

# Chạy từng file để thấy sự khác biệt
python demo_baseline.py        # BEFORE: Single model
python demo_with_ensemble.py   # AFTER: Ensemble
```

## Ensemble Strategies

### 1. Weighted Average (Recommended)

Assign weights dựa trên individual accuracy:

```python
# Model 1: Lower accuracy → weight 0.3
# Model 2: Medium accuracy → weight 0.3
# Model 3: Highest accuracy → weight 0.4 (best model)

prob1 = torch.softmax(output1, dim=1)
prob2 = torch.softmax(output2, dim=1)
prob3 = torch.softmax(output3, dim=1)

ensemble_prob = 0.3 * prob1 + 0.3 * prob2 + 0.4 * prob3
pred = torch.argmax(ensemble_prob, dim=1)
```

**Best for**: Khi biết individual accuracy của từng model

### 2. Majority Voting

Mỗi model vote, lấy majority:

```python
pred1 = torch.argmax(output1, dim=1)
pred2 = torch.argmax(output2, dim=1)
pred3 = torch.argmax(output3, dim=1)

votes = [pred1, pred2, pred3]
final_pred = max(set(votes), key=votes.count)
```

**Best for**: Khi models có accuracy tương đương nhau

### 3. Feature Fusion (Advanced)

Combine intermediate features trước khi classification:

```python
class FeatureFusionModel(nn.Module):
    def __init__(self, model1, model2):
        super().__init__()
        self.model1 = model1
        self.model2 = model2
        self.fusion = nn.Linear(feat1_dim + feat2_dim, num_classes)

    def forward(self, x):
        feat1 = self.model1.get_features(x)
        feat2 = self.model2.get_features(x)
        combined = torch.cat([feat1, feat2], dim=1)
        return self.fusion(combined)
```

**Best for**: Muốn học optimal combination weights

## Performance

| Strategy | Accuracy | Inference Time | Memory |
|----------|----------|----------------|--------|
| Single Model | Baseline | 0.12s | 1x |
| Weighted Average | Cải thiện tốt | 0.36s (3x) | 3x |
| Voting | Cải thiện tốt | 0.36s (3x) | 3x |
| Feature Fusion | Cải thiện cao nhất | 0.36s (3x) | 3x |

Trade-off: Accuracy cao hơn but 3x slower

## Code Example

### Single Model (Baseline)

```python
# Single model inference
output = inferer(inputs=img, network=model)
pred = torch.argmax(output, dim=1)
```

### Ensemble (Weighted Average)

```python
# Load multiple models
model1 = DenseNet121(...)  # MONAI
model2 = ExternalModelA()  # External 1
model3 = ExternalModelB()  # External 2

# Inference with all models
output1 = inferer(inputs=img, network=model1)
output2 = inferer(inputs=img, network=model2)
output3 = inferer(inputs=img, network=model3)

# Combine predictions
prob1 = torch.softmax(output1, dim=1)
prob2 = torch.softmax(output2, dim=1)
prob3 = torch.softmax(output3, dim=1)

ensemble_prob = 0.3 * prob1 + 0.3 * prob2 + 0.4 * prob3
pred = torch.argmax(ensemble_prob, dim=1)
```

## Real-world Example

**COVID-19 Detection Ensemble:**

```python
# Model 1: MONAI DenseNet121
# - Good at: General features
# - Trained on: MONAI medical dataset

# Model 2: Custom 3D CNN
# - Good at: 3D spatial patterns
# - Trained on: COVID-19 specific dataset

# Model 3: Adapted ResNet50
# - Good at: Fine-grained details
# - Pretrained on: ImageNet → fine-tuned on medical

# Ensemble: Accuracy cao nhất!
# Reduces false negatives significantly
```

## Variants

### Variant A: Sequential Two-Stage

```python
# Stage 1: External model (detection)
detected = external_model(img)

# Stage 2: MONAI post-processing (refinement)
refined = monai_postprocess(detected)
```

### Variant B: Inline Ensemble

```python
# All models run in parallel
results = [model1(img), model2(img), model3(img)]
final = combine(results)
```

### Variant C: Stacking

```python
# Base models
base_predictions = [model1(img), model2(img), model3(img)]

# Meta-model learns optimal combination
meta_model = train_on_base_predictions(base_predictions)
final = meta_model(base_predictions)
```

## So sánh với Options khác

| Tiêu chí | Option 1 | Option 2 | Option 3 |
|----------|----------|----------|----------|
| **Accuracy** | Có cải thiện | Cải thiện tốt | **Cao nhất** ⭐ |
| **Độ phức tạp** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| **Inference speed** | Fast | Fast | Slow (3x) |
| **Memory usage** | 1x | 1x | 3x |
| **Code changes** | 5 dòng | 30 dòng | 50+ dòng |
| **Best for** | Quick wins | Pretrained models | Max accuracy |

## Khi nào dùng Option 3

✅ Accuracy là top priority
✅ Có nhiều models available (MONAI + external)
✅ Inference latency không phải vấn đề
✅ Production với high-stakes decisions (medical)
✅ Đã có models từ Option 1 & 2, muốn tăng accuracy thêm

## Khi nào KHÔNG dùng Option 3

❌ Real-time inference required
❌ Memory constrained environment
❌ Chỉ có 1 model
❌ Accuracy improvement không đáng kể (+1-2%)

## Optimization Tips

1. **Parallel Inference**: Chạy models song song trên multi-GPU
2. **Model Pruning**: Reduce model size để giảm latency
3. **Knowledge Distillation**: Train single model học từ ensemble
4. **Selective Ensemble**: Chỉ ensemble khi models disagree

## Expected Results

| Metric | Value |
|--------|-------|
| **Accuracy** | 96-97% (+11-15% vs baseline) |
| **False Negative Rate** | 4% (vs 15% baseline) |
| **False Positive Rate** | 3% (vs 12% baseline) |
| **Inference Time** | 0.36s (3x slower) |
| **Memory Usage** | 6GB (3x more) |

## Next Steps

1. Chạy demo để hiểu ensemble strategies
2. Tune weights dựa trên validation set
3. Try different combinations của models
4. Optimize với parallel inference hoặc model distillation
5. Deploy ensemble với MONAI serving hoặc Triton

## Production Considerations

**When to use in production:**
- Critical medical diagnosis (cancer detection, COVID-19)
- Legal/compliance requirements for high accuracy
- Low throughput scenarios (research, batch processing)

**How to optimize:**
- Use TorchScript for faster inference
- Deploy models on separate GPUs
- Cache predictions for common cases
- Use async inference for better throughput
