import os
import sys

# Ensure the 'src' directory is in the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, "src")
if src_path not in sys.path:
    sys.path.append(src_path)

from flask import Flask, request, jsonify
from mcp_agent.core.fastagent import FastAgent

app = Flask(__name__)


@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message", "Hello")
    session_id = request.json.get("session_id", "default")

    agent = FastAgent(config={"anthropic": {"api_key": os.environ["ANTHROPIC_API_KEY"]}})

    result = agent.run(user_input)

    return jsonify({"response": result, "session_id": session_id, "status": "success"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
