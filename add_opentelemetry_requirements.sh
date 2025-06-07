#!/bin/bash

REQUIREMENTS_FILE="requirements.txt"

# Required packages for OpenTelemetry
REQUIRED_PACKAGES=(
  "opentelemetry-api"
  "opentelemetry-sdk"
  "opentelemetry-exporter-otlp"
)

# Create file if it doesn't exist
if [ ! -f "$REQUIREMENTS_FILE" ]; then
  touch "$REQUIREMENTS_FILE"
fi

# Add each package if not already listed
for pkg in "${REQUIRED_PACKAGES[@]}"; do
  if ! grep -q "^${pkg}\b" "$REQUIREMENTS_FILE"; then
    echo "$pkg" >> "$REQUIREMENTS_FILE"
    echo "✅ Added: $pkg"
  else
    echo "ℹ️  Already present: $pkg"
  fi
done
