#!/bin/bash
# Script to create a new release

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Create New Release ===${NC}"
echo ""

# Get version from argument or prompt
if [ -z "$1" ]; then
    echo -e "${GREEN}Enter version (e.g., v1.0.0):${NC}"
    read VERSION
else
    VERSION=$1
fi

# Validate version format
if [[ ! "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo -e "${RED}Error: Invalid version format. Use vX.Y.Z (e.g., v1.0.0)${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}Creating release: $VERSION${NC}"
echo ""

# Make sure we're on main branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo -e "${RED}Error: Must be on main branch to create release${NC}"
    exit 1
fi

# Make sure working directory is clean
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${RED}Error: Working directory not clean. Commit or stash changes first.${NC}"
    exit 1
fi

# Pull latest changes
echo -e "${BLUE}Pulling latest changes...${NC}"
git pull origin main

# Create and push tag
echo -e "${BLUE}Creating tag: $VERSION${NC}"
git tag -a "$VERSION" -m "Release $VERSION"

echo -e "${BLUE}Pushing tag to GitHub...${NC}"
git push origin "$VERSION"

echo ""
echo -e "${GREEN}✅ Release created successfully!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Check GitHub Actions: https://github.com/NT114DevSecOpsProject/MONAI-Kubeflow-/actions"
echo "2. Verify release: https://github.com/NT114DevSecOpsProject/MONAI-Kubeflow-/releases"
echo "3. Docker image will be available at: ghcr.io/nt114devsecopsproject/monai-kubeflow-/demo-app:$VERSION"
echo ""
