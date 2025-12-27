"""
Path utility for local execution
Maps absolute paths to relative paths for local development
"""

from pathlib import Path

def get_data_path():
    """Get the base data path for local execution"""
    return Path(__file__).parent.parent / "mnt/data"

def get_hospital_output_path():
    """Get the hospital output path for local execution"""
    return get_data_path() / "hospital_output"