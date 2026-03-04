#!/bin/bash
# Format all frontend files with Prettier
set -e

FRONTEND_DIR="$(dirname "$0")/../frontend"

echo "Formatting frontend files..."
cd "$FRONTEND_DIR"

# Install deps if node_modules not present
if [ ! -d "node_modules" ]; then
    echo "Installing Prettier..."
    npm install
fi

npx prettier --write .
echo "Done! All frontend files formatted."
