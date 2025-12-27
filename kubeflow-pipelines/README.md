# Kubeflow Pipelines - Pipeline definitions

## 🎯 Mục đích

Folder này chứa **compiled pipeline YAML files** ready để upload lên Kubeflow UI.

## 📁 Nội dung

Các compiled pipelines (`.yaml` files) từ:
- `hospital-mlops/covid-demo/pipeline.py`
- `week5/pipeline.py`
- Và các pipelines khác

## 🚀 Cách sử dụng

### Upload pipeline lên Kubeflow UI

1. **Mở Kubeflow UI**: http://localhost:8080
2. **Click "Pipelines"** → "+ Upload pipeline"
3. **Chọn file `.yaml`** từ folder này
4. **Click "Create"**

### Hoặc dùng Python SDK

```python
import kfp

client = kfp.Client()
client.upload_pipeline(
    pipeline_file='covid_pipeline.yaml',
    pipeline_name='COVID-19 Detection Pipeline'
)
```

## 💡 Lưu ý

- Các file `.yaml` này được **compile** từ Python code (`pipeline.py`)
- **KHÔNG** edit trực tiếp file `.yaml` - thay vào đó edit `pipeline.py` và compile lại
- Để compile pipeline mới:
  ```bash
  cd hospital-mlops/covid-demo
  python pipeline.py  # Tạo file covid_pipeline.yaml
  ```
