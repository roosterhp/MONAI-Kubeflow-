"""
Download MedicalNet pretrained weights for Option 1 (Direct Replacement).

This helper pulls the public Hugging Face snapshot of the 3D ResNet-50 model
that was pre-trained on the 23-dataset MedicalNet collection, converts the
Safetensors checkpoint into the Torch `.pth` format expected by
`models/medicalnet_resnet.py`, and stores the result inside:
    `pretrained_weights/medicalnet/resnet_50_23dataset.pth`

If the Hugging Face download fails, the script falls back to the original
Google Drive mirror (much bigger, ~2.8 GB compared to 185 MB).
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Dict, Optional

import torch

from models.medicalnet_resnet import MedicalNet3DResNet50

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
HF_REPO_ID = "nwirandx/medicalnet-resnet3d50-23datasets"
HF_REVISION = "8598c5b72112e36f382b76b5ff9c95f4585e1d99"
HF_FILENAME = "model.safetensors"
HF_SIZE_BYTES = 184_892_056  # ~176.4 MB
HF_SHA256 = "cd44e149879827510edb70f9f341ab603501a72e95072491268e56076394db38"

GDRIVE_FILE_ID = "13tnSvXY7oDIEloNFiGTsjUIYfS3g3BfG"

TARGET_FILENAME = "resnet_50_23dataset.pth"
META_FILENAME = "resnet_50_23dataset.meta.json"

MIN_VALID_SIZE = 150_000_000  # bytes, sanity check for .pth file

# --------------------------------------------------------------------------- #


def ensure_module(module_name: str, pip_name: Optional[str] = None):
    """Import a module, installing it via pip if needed."""

    pip_name = pip_name or module_name
    try:
        return importlib.import_module(module_name)
    except ImportError:
        print(f"[INFO] Installing dependency: {pip_name}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name, "-q"])
        return importlib.import_module(module_name)


def sha256sum(path: Path) -> str:
    """Compute SHA256 hash of a file."""

    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_meta(meta_path: Path) -> Optional[Dict[str, str]]:
    if not meta_path.exists():
        return None
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def write_meta(meta_path: Path, **kwargs) -> None:
    meta_path.write_text(json.dumps(kwargs, indent=2), encoding="utf-8")


def looks_like_torch_checkpoint(weights_file: Path) -> bool:
    """
    Quick structural sanity checks so that HTML pages or generic zip archives
    don't masquerade as Torch checkpoints.
    """

    try:
        with weights_file.open("rb") as f:
            header = f.read(64)
    except OSError:
        return False

    lower_header = header.lower()
    html_markers = (b"<!doctype html", b"<html", b"<?xml")
    if any(marker in lower_header for marker in html_markers):
        print("[WARN] Existing weights look like an HTML/XML error page.")
        return False

    if header.startswith(b"{") and b"error" in lower_header:
        print("[WARN] Existing weights look like a JSON error response.")
        return False

    if header.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(weights_file) as archive:
                if "version" not in archive.namelist():
                    print("[WARN] Zip archive missing Torch 'version' record.")
                    return False
        except zipfile.BadZipFile:
            print("[WARN] Existing weights archive is a corrupt ZIP file.")
            return False

    return True


def validate_existing_file(weights_file: Path, meta_path: Path, verify_hash: bool = False) -> bool:
    """Return True if an existing weights file looks valid."""

    if not weights_file.exists():
        return False

    size = weights_file.stat().st_size
    if size < MIN_VALID_SIZE:
        print(f"[WARN] Existing file is too small ({size} bytes). Re-downloading.")
        return False

    if not looks_like_torch_checkpoint(weights_file):
        print("[INFO] Forcing re-download because existing file failed integrity heuristics.")
        if meta_path.exists():
            try:
                meta_path.unlink()
            except OSError:
                pass
        return False

    meta = load_meta(meta_path)
    if not meta:
        if verify_hash:
            sha = sha256sum(weights_file)
            print(f"[INFO] SHA256: {sha}")
        print(f"[OK] Found existing weights ({size / 1e6:.1f} MB)")
        return True

    expected_sha = meta.get("sha256")
    if verify_hash and expected_sha:
        actual_sha = sha256sum(weights_file)
        if actual_sha.lower() != expected_sha.lower():
            print("[WARN] Stored SHA256 mismatches disk copy. Re-downloading.")
            return False
        print(f"[OK] Existing weights verified (SHA256={actual_sha})")
        return True

    print(f"[OK] Found existing weights ({size / 1e6:.1f} MB)")
    return True


def convert_hf_state_dict(hf_state: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
    """Convert Hugging Face ResNet3D keys to our MedicalNet backbone keys."""

    converted: Dict[str, torch.Tensor] = {}

    def copy_bn(dst_prefix: str, src_prefix: str) -> None:
        for attr in ("weight", "bias", "running_mean", "running_var", "num_batches_tracked"):
            src_key = f"{src_prefix}.{attr}"
            if src_key in hf_state:
                converted[f"{dst_prefix}.{attr}"] = hf_state[src_key]

    # Stem
    converted["conv1.weight"] = hf_state["resnet3d.embedder.embedder.convolution.weight"]
    copy_bn("bn1", "resnet3d.embedder.embedder.normalization")

    # Residual stages
    stage_to_layer = ["layer1", "layer2", "layer3", "layer4"]
    stage_blocks = [3, 4, 6, 3]  # ResNet-50 layout
    for stage_idx, layer_name in enumerate(stage_to_layer):
        num_blocks = stage_blocks[stage_idx]
        for block_idx in range(num_blocks):
            block_prefix = f"resnet3d.encoder.stages.{stage_idx}.layers.{block_idx}"
            local_prefix = f"{layer_name}.{block_idx}"

            for conv_id, (conv_name, bn_name) in enumerate(
                (("conv1", "bn1"), ("conv2", "bn2"), ("conv3", "bn3"))
            ):
                src = f"{block_prefix}.layer.{conv_id}"
                converted[f"{local_prefix}.{conv_name}.weight"] = hf_state[f"{src}.convolution.weight"]
                copy_bn(f"{local_prefix}.{bn_name}", f"{src}.normalization")

            shortcut_key = f"{block_prefix}.shortcut.convolution.weight"
            if shortcut_key in hf_state:
                converted[f"{local_prefix}.downsample.0.weight"] = hf_state[shortcut_key]
                copy_bn(f"{local_prefix}.downsample.1", f"{block_prefix}.shortcut.normalization")

    # Classification head (identical shape, even if we reinitialize later)
    if "classifier.1.weight" in hf_state and "classifier.1.bias" in hf_state:
        converted["classifier.weight"] = hf_state["classifier.1.weight"]
        converted["classifier.bias"] = hf_state["classifier.1.bias"]

    # Validate against our architecture to catch mapping mistakes
    reference_keys = set(MedicalNet3DResNet50(pretrained_path=None).state_dict().keys())
    missing = reference_keys - set(converted.keys())
    if missing:
        raise RuntimeError(f"Converted state_dict missing keys: {sorted(missing)[:10]}")

    return converted


def download_from_huggingface(weights_file: Path, meta_path: Path) -> None:
    """Download + convert Hugging Face Safetensors checkpoint."""

    hf_hub = ensure_module("huggingface_hub")
    safetensors_module = ensure_module("safetensors.torch", "safetensors")
    hf_hub_download = hf_hub.hf_hub_download
    safetensors_torch = safetensors_module

    print("\n" + "=" * 70)
    print("Downloading MedicalNet weights from Hugging Face (preferred)")
    print("=" * 70)
    print(f"Repo ID : {HF_REPO_ID}")
    print(f"Revision: {HF_REVISION}")
    print(f"File    : {HF_FILENAME}")

    hf_path = Path(
        hf_hub_download(
            repo_id=HF_REPO_ID,
            filename=HF_FILENAME,
            revision=HF_REVISION,
            resume_download=True,
        )
    )

    size = hf_path.stat().st_size
    print(f"[OK] Downloaded Safetensors checkpoint ({size / 1e6:.1f} MB)")
    if size != HF_SIZE_BYTES:
        print(f"[WARN] Expected {HF_SIZE_BYTES} bytes but received {size}. Continuing anyway.")

    if HF_SHA256:
        sha = sha256sum(hf_path)
        if sha != HF_SHA256:
            raise RuntimeError(
                f"Hugging Face file SHA256 mismatch.\nExpected: {HF_SHA256}\nGot     : {sha}"
            )
        print(f"[OK] Verified Safetensors SHA256: {sha}")

    hf_state = safetensors_torch.load_file(str(hf_path))
    converted = convert_hf_state_dict(hf_state)

    checkpoint = {
        "state_dict": converted,
        "source": "huggingface",
        "repo_id": HF_REPO_ID,
        "revision": HF_REVISION,
        "converted_from": HF_FILENAME,
    }
    torch.save(checkpoint, weights_file)

    sha_pth = sha256sum(weights_file)
    meta = {
        "source": "huggingface",
        "repo_id": HF_REPO_ID,
        "revision": HF_REVISION,
        "filename": HF_FILENAME,
        "size_bytes": weights_file.stat().st_size,
        "sha256": sha_pth,
    }
    write_meta(meta_path, **meta)
    print(f"[OK] Saved Torch checkpoint ({weights_file.relative_to(Path(__file__).parent)})")
    print(f"[OK] SHA256: {sha_pth}")


def download_from_google_drive(weights_file: Path, meta_path: Path) -> None:
    """Fallback: download original 2.8 GB checkpoint from Google Drive."""

    gdown = ensure_module("gdown")
    url = f"https://drive.google.com/uc?id={GDRIVE_FILE_ID}"

    print("\n" + "=" * 70)
    print("Fallback: Downloading MedicalNet weights from Google Drive")
    print("=" * 70)
    print("NOTE: This file is ~2.8 GB and may take a while.")
    print(f"URL: {url}")

    gdown.download(url, str(weights_file), quiet=False)

    sha = sha256sum(weights_file)
    meta = {
        "source": "google-drive",
        "file_id": GDRIVE_FILE_ID,
        "size_bytes": weights_file.stat().st_size,
        "sha256": sha,
    }
    write_meta(meta_path, **meta)
    print(f"[OK] Google Drive download complete ({weights_file.stat().st_size / 1e9:.2f} GB)")
    print(f"[OK] SHA256: {sha}")


def pick_strategies(preference: str):
    if preference == "hf":
        return [download_from_huggingface, download_from_google_drive]
    if preference == "gdrive":
        return [download_from_google_drive]
    return [download_from_huggingface, download_from_google_drive]


def download_medicalnet_weights(force: bool = False, source: str = "auto", verify: bool = False) -> Optional[str]:
    """Public API called by other scripts."""

    base_dir = Path(__file__).parent
    weights_dir = base_dir / "pretrained_weights" / "medicalnet"
    weights_dir.mkdir(parents=True, exist_ok=True)

    weights_file = weights_dir / TARGET_FILENAME
    meta_path = weights_dir / META_FILENAME

    if not force and validate_existing_file(weights_file, meta_path, verify_hash=verify):
        return str(weights_file)

    for strategy in pick_strategies(source):
        try:
            strategy(weights_file, meta_path)
            if validate_existing_file(weights_file, meta_path, verify_hash=True):
                return str(weights_file)
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] {strategy.__name__} failed: {exc}")

    print("[ERROR] Unable to download MedicalNet weights automatically.")
    print("Please download manually from https://github.com/Tencent/MedicalNet and place the file at:")
    print(f"  {weights_file}")
    return None


def main():
    parser = argparse.ArgumentParser(description="Download MedicalNet pretrained weights.")
    parser.add_argument(
        "--source",
        choices=["auto", "hf", "gdrive"],
        default="auto",
        help="Preferred download backend (default: auto)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore cached files and re-download.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Force SHA256 verification of existing weights.",
    )
    args = parser.parse_args()

    result = download_medicalnet_weights(force=args.force, source=args.source, verify=args.verify)
    if result:
        print("\nReady to use MedicalNet!")
        print(f"  Weights: {result}")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
