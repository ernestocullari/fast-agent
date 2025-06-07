#!/bin/bash
echo "Replacing 'mcp_agent.mcp' imports with 'mcp_agent._mcp_local_backup'..."

find ./src/mcp_agent -type f -name "*.py" \
  -exec sed -i 's/from mcp_agent\.mcp\./from mcp_agent._mcp_local_backup./g' {} +

echo "✅ Replacement complete."
