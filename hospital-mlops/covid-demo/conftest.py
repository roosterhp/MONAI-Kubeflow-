"""Pytest configuration for COVID-19 pipeline tests"""
import sys
from pathlib import Path

# Add components directory to path
components_dir = Path(__file__).parent / "components"
sys.path.insert(0, str(components_dir))
