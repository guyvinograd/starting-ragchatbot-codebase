#!/bin/bash
# Check frontend formatting without modifying files
set -e

FRONTEND_DIR="$(dirname "$0")/../frontend"

echo "Checking frontend formatting..."
cd "$FRONTEND_DIR"

# Install deps if node_modules not present
if [ ! -d "node_modules" ]; then
    echo "Installing Prettier..."
    npm install
fi

npx prettier --check .
echo "All frontend formatting checks passed!"
