import os
import json
import time
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

MODEL = "gemini-3.6-flash"

question = """
Find engineering institutions in Karnataka that have:

1. Improved their overall NIRF rank between 2020 and 2025.
2. Increased their RPC score during the same period.
3. Decreased their TLR score during the same period.

Show the top 10 institutions with the largest ranking improvement.

Also explain the relationship between research and teaching performance.
"""

prompt = f"""
You are an advanced analytical query planner for a NIRF dashboard.

Convert the user's question into a structured JSON analysis plan.

USER QUESTION:
{question}

Return ONLY valid JSON with exactly these keys:

{{
    "operation": "",
    "filters": {{
        "category": "",
        "state": "",
        "start_year": null,
        "end_year": null
    }},
    "conditions": [
        {{
            "metric": "",
            "comparison": "",
            "period": ""
        }}
    ],
    "metrics": [],
    "ranking": {{
        "metric": "",
        "direction": "",
        "limit": null
    }},
    "analysis_required": [],
    "visualization": {{
        "required": true,
        "chart_type": ""
    }}
}}

RULES:
1. Identify every condition in the question.
2. Do not omit any requested metric.
3. Ranking improvement means the institution's numerical rank
   decreases from the start year to the end year.
4. A larger ranking improvement means a larger positive value
   of (start_year_rank - end_year_rank).
5. The ranking direction must reflect the largest improvement first.
6. Include an appropriate analysis for the relationship between RPC
   and TLR. Do not assume correlation proves causation.
7. Do not invent filters or conditions.
8. Return JSON only. No Markdown or explanation.
"""

start = time.time()

response = client.models.generate_content(
    model=MODEL,
    contents=prompt,
    config={
        "response_mime_type": "application/json"
    }
)

elapsed = time.time() - start

print("MODEL:", MODEL)
print(f"TIME: {elapsed:.2f} seconds")
print("\nMODEL OUTPUT:\n")
print(response.text)

try:
    parsed = json.loads(response.text)
    print("\nJSON VALIDATION: PASSED")
except json.JSONDecodeError:
    print("\nJSON VALIDATION: FAILED")