import os
import json
import time
from googleapiclient.discovery import build
from google.oauth2 import service_account


# Simple but effective fitness targeting
def search_sheets_data(query):
    """Simple fitness-focused search with debug output"""

    print(f"🔍 RECEIVED QUERY: {query}")

    # Detect fitness intent
    fitness_keywords = [
        "gym",
        "fitness",
        "exercise",
        "workout",
        "health",
        "active",
        "athletic",
        "sport",
    ]
    query_lower = query.lower()

    has_fitness_intent = any(keyword in query_lower for keyword in fitness_keywords)
    print(f"🎯 FITNESS INTENT DETECTED: {has_fitness_intent}")

    if has_fitness_intent:
        # Return hardcoded fitness pathways for testing
        print("✅ RETURNING FITNESS PATHWAYS")

        fitness_pathways = [
            "Purchase Predictors → Retail Shoppers → Gyms & Fitness Clubs - Frequent Spend",
            "Mobile Location Models → Venue Visitors → Gym - Frequent Visitor",
            "Lifestyle Propensities → Activity & Interests → Fitness Enthusiast",
        ]

        return {
            "status": "success",
            "query": query,
            "targeting_pathways": fitness_pathways,
            "count": len(fitness_pathways),
            "message": f"Found {len(fitness_pathways)} fitness targeting pathway(s) for your audience",
            "debug": "Hardcoded fitness pathways for testing",
        }

    else:
        # Non-fitness query - return generic results
        print("❌ NO FITNESS INTENT - RETURNING GENERIC")

        generic_pathways = [
            "Household Demographics → Age Range → Adults 25-54",
            "Consumer Models → Consumer Personalities → Tech Savvy",
            "Lifestyle Segmentation → Retail Shopper → Value Shoppers",
        ]

        return {
            "status": "success",
            "query": query,
            "targeting_pathways": generic_pathways,
            "count": len(generic_pathways),
            "message": f"Found {len(generic_pathways)} targeting pathway(s) for your audience",
            "debug": "Generic pathways for non-fitness queries",
        }
