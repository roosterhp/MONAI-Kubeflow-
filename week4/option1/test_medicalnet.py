"""
Test MedicalNet model loading and forward pass
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import torch
from models.medicalnet_resnet import resnet50_medicalnet

print("\n" + "="*70)
print("TESTING MEDICALNET 3D-RESNET50")
print("="*70)

# Test 1: Model loading
print("\n[Test 1] Loading model...")
try:
    model = resnet50_medicalnet(num_classes=2, pretrained=True)
    print("[OK] Model loaded successfully")
    print(f"    Parameters: {sum(p.numel() for p in model.parameters()):,}")
except Exception as e:
    print(f"[FAIL] {e}")
    sys.exit(1)

# Test 2: Forward pass
print("\n[Test 2] Testing forward pass...")
try:
    model.eval()

    # Create dummy input: (B, 1, D, H, W)
    dummy_input = torch.randn(1, 1, 96, 96, 96)
    print(f"    Input shape: {dummy_input.shape}")

    with torch.no_grad():
        output = model(dummy_input)

    print(f"    Output shape: {output.shape}")

    if output.shape == (1, 2):
        print("[OK] Forward pass successful!")
        print(f"    Output logits: {output[0].tolist()}")
    else:
        print(f"[FAIL] Expected (1, 2), got {output.shape}")
        sys.exit(1)
except Exception as e:
    print(f"[FAIL] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: MONAI SimpleInferer compatibility
print("\n[Test 3] Testing MONAI inferer compatibility...")
try:
    from monai.inferers import SimpleInferer

    inferer = SimpleInferer()
    dummy_input = torch.randn(1, 1, 96, 96, 96)

    with torch.no_grad():
        output = inferer(inputs=dummy_input, network=model)

    if output.shape == (1, 2):
        print("[OK] MONAI inferer compatible!")
        print(f"    Output shape: {output.shape}")
    else:
        print(f"[FAIL] Expected (1, 2), got {output.shape}")
        sys.exit(1)
except Exception as e:
    print(f"[FAIL] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Confidence scores
print("\n[Test 4] Testing confidence scores...")
try:
    probs = torch.softmax(output, dim=1)
    pred = torch.argmax(probs, dim=1).item()
    conf = probs.max().item()

    print(f"    Prediction: {pred}")
    print(f"    Confidence: {conf:.3f}")
    print(f"    Probabilities: {probs[0].tolist()}")
    print("[OK] Confidence scores valid!")
except Exception as e:
    print(f"[FAIL] {e}")
    sys.exit(1)

print("\n" + "="*70)
print("[SUCCESS] ALL TESTS PASSED!")
print("="*70)
print("\nMedicalNet 3D-ResNet50 is ready to use!")
print("Run: python demo_with_external.py")
print("="*70)
