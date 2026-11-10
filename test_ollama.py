
import ollama
import json
import time

MODEL = "gemma4:31b-cloud"

question = """
Find engineering institutions in Karnataka that have:
1. Improved their overall NIRF rank between 2020 and 2025.
2. Increased their RPC score during the same period.
3. Decreased their TLR score during the same period.

Show the top 10 institutions with the largest ranking improvement.
Also explain the relationship between their research and teaching performance.
"""

prompt = f"""
You are an expert query planner for an NIRF analytics system.

Convert the user's question into a structured JSON analytical plan.

Return ONLY valid JSON:

{{
    "operation": "string",
    "filters": {{
        "category": null,
        "state": null,
        "start_year": null,
        "end_year": null
    }},
    "conditions": [
        {{
            "metric": "string",
            "comparison": "string",
            "period": "string"
        }}
    ],
    "metrics": [],
    "ranking": {{
        "metric": "string",
        "direction": "string",
        "limit": null
    }},
    "analysis_required": [],
    "visualization": {{
        "required": true,
        "chart_type": "string"
    }}
}}

Rules:
- Separate rank improvement from score improvement.
- Lower NIRF rank means better performance.
- Identify increases and decreases correctly.
- Preserve all requested conditions.
- Do not invent institution names or results.
- Do not calculate anything.
- Return JSON only.

USER QUESTION:
{question}
"""

start = time.time()

response = ollama.chat(
    model=MODEL,
    messages=[{"role": "user", "content": prompt}],
    format="json"
)

elapsed = time.time() - start
result = response["message"]["content"]

print("TIME:", round(elapsed, 2), "seconds")
print("\nOUTPUT:\n")

try:
    print(json.dumps(json.loads(result), indent=4))
except json.JSONDecodeError:
    print(result)
