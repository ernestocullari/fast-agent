import os
import sys

# Ensure the 'src' directory is in the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from mcp_agent.core.fastagent import FastAgent

if __name__ == "__main__":
    agent = FastAgent()
    agent.run()  # <-- Change to .start() if that's what your agent uses
