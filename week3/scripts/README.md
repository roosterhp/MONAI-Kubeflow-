# Utility Scripts

## prepare_data.py
Prepare and validate data for training

```bash
python prepare_data.py \
  --data-dir /path/to/raw/data \
  --output-dir /mnt/data/processed \
  --train-split 0.7 \
  --val-split 0.2 \
  --test-split 0.1
```

## build_images.sh
Build all Docker images for Kubeflow components

```bash
./build_images.sh --registry <registry> --tag v1
```

## deploy_pipeline.sh
Deploy complete Kubeflow pipeline

```bash
./deploy_pipeline.sh \
  --data-path /mnt/data/processed \
  --output-path /mnt/data/models/v1 \
  --num-classes 5
```

## test_inference.sh
Test inference endpoint with sample data

```bash
./test_inference.sh \
  --endpoint http://efficientnet-classifier.kubeflow.svc \
  --image test_images/sample.png
```
