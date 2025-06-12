import os
import sys

# Ensure the 'src' directory is in the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, "src")
if src_path not in sys.path:
    sys.path.append(src_path)

from flask import Flask, request, jsonify
from mcp_agent.core.fastagent import FastAgent
from mcp_agent.tools.google_sheets_tool import google_sheets_tool
import asyncio

app = Flask(__name__)

# Initialize FastAgent once at startup with Google Sheets tool
agent = None

def initialize_agent():
    """Initialize the FastAgent with Google Sheets tool and optimized system prompt."""
    global agent
    
    # Create FastAgent with proper configuration
    agent = FastAgent(
        name="artemis",
        parse_cli_args=False  # Disable CLI parsing when running in Flask
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
                            "description": "User's plain language description of their target audience"
                        }
                    },
                    "required": ["query"]
                },
                "handler": lambda query: asyncio.run(google_sheets_tool.execute(query))
            }
        ]
    )
    
    @agent.agent_main
    async def artemis_main():
        """Main agent function - this will be called by FastAgent"""
        pass
    
    return artemis_main

# Initialize agent at startup
artemis_main = initialize_agent()

@app.route("/chat", methods=["POST"])
def chat():
    """Handle chat requests with the optimized Artemis agent."""
    try:
        user_input = request.json.get("message", "Hello")
        session_id = request.json.get("session_id", "default")
        
        # Run the agent with the user input
        async def run_agent():
            async with agent.run() as agent_app:
                result = await agent_app.send(user_input, agent_name="artemis")
                return result
        
        # Execute the async function
        result = asyncio.run(run_agent())
        
        return jsonify({
            "response": result,
            "session_id": session_id,
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({
            "response": f"Error: {str(e)}",
            "session_id": request.json.get("session_id", "default"),
            "status": "error"
        }), 500

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "agent": "artemis"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
