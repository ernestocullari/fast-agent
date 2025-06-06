from flask import Flask, request, jsonify
from mcp_agent.core.fastagent import FastAgent
import os

app = Flask(__name__)

@app.route("/plan", methods=["POST"])
def generate_plan():
    user_input = request.json.get("prompt", "Plan my ad campaign")
    agent = FastAgent(config={
        "anthropic": {
            "api_key": os.environ["ANTHROPIC_API_KEY"]
        }
    })
    result = agent.run(user_input)
    return jsonify({"response": result})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
