#!/bin/bash

echo "🔄 Backing up current requirements.txt..."
cp requirements.txt requirements.full.backup

echo "✍️  Writing slimmed-down requirements.txt..."
cat <<EOF > requirements.txt
Flask
anthropic
mcp_agent @ git+https://github.com/ernestocullari/fast-agent@4f22f3967f84daeff103b429b360cc6b4ffe2021#egg=mcp_agent&subdirectory=src
EOF

echo "🧼 Cleaning old Docker image (if any)..."
docker rmi -f fast-agent 2>/dev/null

echo "🐳 Rebuilding Docker image..."
docker build -t fast-agent .

echo "📦 Final Docker image size:"
docker images fast-agent --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
