# api/chat.py - Optimized MCP Server with FastAgent and Google Sheets Integration

from http.server import BaseHTTPRequestHandler
import json
import os
import sys
import asyncio
from datetime import datetime

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
src_path = os.path.join(parent_dir, "src")
if src_path not in sys.path:
    sys.path.append(src_path)

from mcp_agent.core.fastagent import FastAgent
from mcp_agent.tools.google_sheets_tool import google_sheets_tool

# Global agent instance
agent = None


def initialize_agent():
    """Initialize the FastAgent with Google Sheets tool and optimized system prompt."""
    global agent

    if agent is not None:
        return agent

    # Create FastAgent with proper configuration
    agent = FastAgent(
        name="artemis",
        parse_cli_args=False,  # Disable CLI parsing when running in Vercel
    )

    # Define the Artemis agent with Google Sheets tool
    @agent.agent(
        name="artemis",
        model="claude-3-5-sonnet-20241022",
        system_prompt="""
You are Artemis, a specialized geotargeting AI assistant helping users find exact ad targeting pathways.

SEARCH STRATEGY (in priority order):
1. Description column (most specific targeting pathways)
2. Demographic column (demographic criteria)
3. Grouping column (grouping categories)  
4. Category column (broad categories)
5. If no matches found, suggest trial/error or consultation

CORE FUNCTION:
- Match user's natural language audience descriptions to exact targeting pathways
- Always present results as: Category → Grouping → Demographic
- Use ONLY data from the Google Sheets database
- Never suggest targeting options not found in the database

RESPONSE REQUIREMENTS:
1. Always use fetch_geotargeting_tool for every targeting query
2. Present 1-3 complementary targeting pathways that work together
3. Show clean pathways without technical details
4. If weak matches, ask user for more detail
5. If no matches after multiple attempts, suggest:
   - Experimenting with the tool
   - Scheduling a consult with ernesto@artemistargeting.com

Keep responses focused on actionable Category → Grouping → Demographic pathways.
        """,
        tools=[
            {
                "name": "fetch_geotargeting_tool",
                "description": "Search geotargeting demographics database with 4-level priority search",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "User's plain language description of their target audience",
                        }
                    },
                    "required": ["query"],
                },
                "handler": lambda query: asyncio.run(google_sheets_tool.execute(query)),
            }
        ],
    )
    @agent.agent_main
    async def artemis_main():
        """Main agent function - this will be called by FastAgent"""
        pass

    return agent


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Health check endpoint"""
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

        response = {
            "success": True,
            "status": "healthy",
            "agent": "artemis",
            "message": "🚀 Optimized MCP Geotargeting Server with 4-level search is running!",
            "features": [
                "FastAgent with Claude integration",
                "Google Sheets with 4-level search priority",
                "Description → Demographic → Grouping → Category search",
                "Optimized targeting pathway recommendations",
            ],
            "timestamp": datetime.now().isoformat(),
        }

        self.wfile.write(json.dumps(response).encode())

    def do_POST(self):
        """Handle chat requests with optimized Artemis agent"""
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

        try:
            # Get POST data
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)

            # Parse JSON
            try:
                data = json.loads(post_data.decode("utf-8")) if post_data else {}
            except:
                data = {}

            user_input = data.get("message", "Hello")
            session_id = data.get("session_id", "default")

            # Initialize agent if not already done
            initialize_agent()

            # Run the agent with the user input
            async def run_agent():
                try:
                    async with agent.run() as agent_app:
                        result = await agent_app.send(user_input, agent_name="artemis")
                        return result
                except Exception as e:
                    return f"Agent error: {str(e)}"

            # Execute the async function
            result = asyncio.run(run_agent())

            response = {
                "success": True,
                "response": result,
                "session_id": session_id,
                "agent": "artemis",
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            response = {
                "success": False,
                "error": f"Server error: {str(e)}",
                "session_id": data.get("session_id", "default")
                if "data" in locals()
                else "unknown",
                "timestamp": datetime.now().isoformat(),
            }

        self.wfile.write(json.dumps(response).encode())

    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
