#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
COMMANDS=("pypi-fetcher" "env-finder" "library-loader")
GO_PROJECT_PATH="go-tools"
OUTPUT_BIN_PATH="bin"

echo "🧹 Clearing previous builds..."
rm -rf $OUTPUT_BIN_PATH/*

# --- Platform Detection ---
OS="$(uname -s)"
ARCH="$(uname -m)"

# --- Build Loop ---
for cmd in "${COMMANDS[@]}"; do
    echo "Building command: $cmd for this platform..."

    # Check the detected OS and Architecture and run the correct build command.
    if [[ "$OS" == "Darwin" && "$ARCH" == "arm64" ]]; then
        # Build for macOS Apple Silicon (M1/M2/M3/M4)
        echo "  -> Detected Apple Silicon Mac. Building for darwin/arm64..."
        go build -C "$GO_PROJECT_PATH" -o "../$OUTPUT_BIN_PATH/darwin/$cmd" "./cmd/$cmd"

    elif [[ "$OS" == "Darwin" && "$ARCH" == "x86_64" ]]; then
        # Build for macOS Intel
        echo "  -> Detected Intel Mac. Building for darwin/amd64..."
        go build -C "$GO_PROJECT_PATH" -o "../$OUTPUT_BIN_PATH/darwin/$cmd" "./cmd/$cmd"

    elif [[ "$OS" == "Linux" ]]; then
        # Build for Linux
        echo "  -> Detected Linux. Building for linux/amd64..."
        go build -C "$GO_PROJECT_PATH" -o "../$OUTPUT_BIN_PATH/linux/$cmd" "./cmd/$cmd"

    elif [[ "$OS" == "MINGW"* || "$OS" == "CYGWIN"* ]]; then
        # Build for Windows
        echo "  -> Detected Windows. Building for windows/amd64..."
        go build -C "$GO_PROJECT_PATH" -o "../$OUTPUT_BIN_PATH/win32/$cmd.exe" "./cmd/$cmd"

    else
        echo "❌ Error: Unsupported operating system '$OS'."
        exit 1
    fi
done

echo "✅ Build completed successfully for your platform!"
