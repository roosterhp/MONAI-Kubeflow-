# Kubeflow Install - Cài đặt Kubeflow

## 🎯 Mục đích

Folder này chứa **manifests** và **scripts** để cài đặt Kubeflow Pipelines trên Kubernetes cluster.

## 📁 Nội dung

- **manifests/** - YAML files để deploy Kubeflow components
- **manifests-1.8-branch/** - Kubeflow manifests version 1.8
- **kfctl_*.yaml** - Configuration files cho Kubeflow deployment

## 🚀 Cách sử dụng

### Cài đặt Kubeflow Pipelines

```bash
# Sử dụng kubectl để apply manifests
kubectl apply -k github.com/kubeflow/pipelines/manifests/kustomize/cluster-scoped-resources?ref=2.0.5

# Đợi 30 giây để CRDs được tạo
sleep 30

# Deploy Kubeflow Pipelines
kubectl apply -k github.com/kubeflow/pipelines/manifests/kustomize/env/platform-agnostic?ref=2.0.5
```

### Kiểm tra installation

```bash
# Check pods
kubectl get pods -n kubeflow

# Port forward để truy cập UI
kubectl port-forward -n kubeflow svc/ml-pipeline-ui 8080:80
```

## 📚 Tham khảo

Xem hướng dẫn chi tiết trong file `README.md` chính ở root folder (PHẦN 3: CÀI ĐẶT KUBEFLOW PIPELINES).

## 💡 Lưu ý

- Folder này chứa **installation manifests**, không phải pipeline code
- Sau khi cài xong Kubeflow, các pipeline sẽ được định nghĩa trong `hospital-mlops/`, `week5/`, etc.
