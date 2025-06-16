def calculate_enhanced_similarity(query_text, row_data):
    """DEBUG version to see what categories we actually have"""

    category = str(row_data.get("Category", "")).strip().lower()
    grouping = str(row_data.get("Grouping", "")).strip().lower()
    demographic = str(row_data.get("Demographic", "")).strip().lower()
    description = str(row_data.get("Description", "")).strip().lower()

    combined_text = f"{category} {grouping} {demographic} {description}"
    query_lower = query_text.lower().strip()

    # Block automotive unless explicitly requested
    wants_auto = is_automotive_query(query_text)
    if not wants_auto and is_automotive_content(combined_text):
        return 0.0

    score = 0.0

    # DEBUG: For wellness queries, heavily prioritize anything with "health" in category
    if "wellness" in query_lower or "health" in query_lower:
        if "health" in category:
            score += 20.0  # MASSIVE boost for health category
        elif "well" in category:
            score += 20.0  # MASSIVE boost for well being category
        elif "fitness" in category:
            score += 15.0  # High boost for fitness
        elif "wellness" in combined_text:
            score += 10.0
        elif "health" in combined_text:
            score += 10.0

    # Regular matching for other queries
    if query_lower in combined_text:
        score += 5.0

    query_words = query_lower.split()
    for word in query_words:
        if len(word) > 3:
            if word in combined_text:
                score += 1.0

    return score
