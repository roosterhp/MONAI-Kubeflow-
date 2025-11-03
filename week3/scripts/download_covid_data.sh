#!/bin/bash

# Download and organize COVID-19 Radiography Database
# Usage: bash scripts/download_covid_data.sh

set -e  # Exit on error

echo "=================================================="
echo "COVID-19 Radiography Database Download Script"
echo "=================================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if kaggle is installed
if ! command -v kaggle &> /dev/null; then
    echo -e "${RED}❌ Error: Kaggle CLI not found${NC}"
    echo ""
    echo "Please install kaggle:"
    echo "  pip install kaggle"
    echo ""
    echo "Then setup API token:"
    echo "  1. Go to https://www.kaggle.com/settings"
    echo "  2. Create New API Token"
    echo "  3. Move kaggle.json to ~/.kaggle/"
    echo "     mkdir -p ~/.kaggle"
    echo "     mv ~/Downloads/kaggle.json ~/.kaggle/"
    echo "     chmod 600 ~/.kaggle/kaggle.json"
    exit 1
fi

# Check if kaggle API token exists
if [ ! -f ~/.kaggle/kaggle.json ]; then
    echo -e "${RED}❌ Error: Kaggle API token not found${NC}"
    echo ""
    echo "Please setup API token:"
    echo "  1. Go to https://www.kaggle.com/settings"
    echo "  2. Create New API Token"
    echo "  3. Move kaggle.json to ~/.kaggle/"
    echo "     mkdir -p ~/.kaggle"
    echo "     mv ~/Downloads/kaggle.json ~/.kaggle/"
    echo "     chmod 600 ~/.kaggle/kaggle.json"
    exit 1
fi

echo -e "${GREEN}✓${NC} Kaggle CLI found"
echo ""

# Create directories
echo "Creating directories..."
mkdir -p data/raw
mkdir -p data/organized
mkdir -p data/sample

# Download dataset
echo ""
echo "Downloading COVID-19 Radiography Database..."
echo "  Dataset: tawsifurrahman/covid19-radiography-database"
echo "  Size: ~1.2GB"
echo "  This may take 5-15 minutes..."
echo ""

cd data/raw

if [ -d "COVID-19_Radiography_Dataset" ]; then
    echo -e "${YELLOW}⚠️  Dataset already exists, skipping download${NC}"
else
    kaggle datasets download -d tawsifurrahman/covid19-radiography-database

    echo ""
    echo "Extracting dataset..."
    unzip -q covid19-radiography-database.zip

    # Clean up
    rm covid19-radiography-database.zip
    echo -e "${GREEN}✓${NC} Download complete"
fi

cd ../..

# Verify download
if [ -d "data/raw/COVID-19_Radiography_Dataset" ]; then
    echo ""
    echo "Verifying download..."
    echo ""
    echo "Found directories:"
    ls -d data/raw/COVID-19_Radiography_Dataset/*/
    echo ""
    echo -e "${GREEN}✓${NC} Dataset downloaded successfully"
else
    echo -e "${RED}❌ Error: Dataset directory not found${NC}"
    exit 1
fi

# Organize dataset
echo ""
echo "=================================================="
echo "Organizing dataset..."
echo "=================================================="
echo ""

python scripts/organize_covid_data.py

# Create sample dataset
echo ""
echo "=================================================="
echo "Creating sample dataset (100 images)..."
echo "=================================================="
echo ""

python scripts/create_sample_dataset.py --num-per-class 25

echo ""
echo "=================================================="
echo "✓ Setup Complete!"
echo "=================================================="
echo ""
echo "Data structure:"
echo "  data/"
echo "  ├── raw/                    # Raw downloaded data (~1.2GB)"
echo "  ├── organized/              # Organized full dataset (~1.2GB)"
echo "  └── sample/                 # Sample dataset (100 images, ~10MB)"
echo ""
echo "Next steps:"
echo ""
echo "1. Test with sample data (FAST):"
echo "   python components/preprocess/preprocess.py \\"
echo "     --raw-data-path data/sample \\"
echo "     --output-path data/processed_sample"
echo ""
echo "2. OR use full dataset (SLOW but better results):"
echo "   python components/preprocess/preprocess.py \\"
echo "     --raw-data-path data/organized \\"
echo "     --output-path data/processed"
echo ""
echo "=================================================="
