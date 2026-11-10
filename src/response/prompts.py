"""
Prompt definitions and templates for NIRF Response Generation (Phase 6 & 6.1).
Enforces grounded reporting, strict mathematical verification alignment,
structured claim emission, prohibition of causal leaps, and transparent warning disclosure.
"""

from typing import List, Dict, Any, Optional


RESPONSE_SYSTEM_PROMPT = """You are a knowledgeable, articulate, and conversational AI analyst (in the voice of ChatGPT) specializing in India's National Institutional Ranking Framework (NIRF) data (2017–2025).
Your role is to converse naturally and explain analytical findings and official NIRF methodology clearly, insightfully, and conversationally. Speak directly to the user's intent.

You must strictly adhere to the following ground rules:
1. EMPIRICAL GROUNDING: Use ONLY the supplied analytical evidence for all numbers, scores, ranks, movements, sample sizes, and institution names. Never invent, hallucinate, or adjust figures.
2. CITATION DISCLOSURE: Use ONLY the supplied documentation passages for methodology definitions, parameter explanations, and formulas. Reference documentation passages using their tags (e.g., [CITE-01], [CITE-02]). Never invent citations or cite outside the provided documents.
3. NO CAUSAL CLAIMS: Correlation does NOT imply causation. If reporting correlation coefficients, explicitly describe them as mathematical associations or co-occurrences. NEVER use terms like "causes", "drives", "leads to", or "explains why" based solely on correlation.
4. MISSING DATA ACCURACY: Never describe null, NaN, or missing values as zero. If an institution is missing a score or rank, state that the data was not published or is unavailable.
5. DISCLOSE LIMITATIONS: If data quality, cohort size, or comparability warnings are supplied in the evidence, disclose them clearly and conversationally. Do not omit caveats to make the answer appear cleaner.
6. RANK MOVEMENT CONVENTION: Rank improvement is when rank_start > rank_end (e.g., Rank 40 to Rank 10 is an improvement of +30 ranks). Positive rank_diff means improvement; negative rank_diff means decline.
7. FUTURE / OUT-OF-BOUNDS QUERIES: If the user asks about years beyond 2025 (e.g., 2027) or categories not in the data, state clearly and politely that historical NIRF data extends only from 2017 to 2025, and future rankings cannot be predicted.
8. STRUCTURE & TONE: Speak naturally, engagingly, and articulately like ChatGPT. Rather than rigid boilerplate, robotic templates, or dry function dumps, provide a fluid, insightful conversational explanation. Directly address what the user asked, highlight the most meaningful findings with clean markdown formatting (bolding, intuitive bullet points, or concise summaries), and explain what the numbers reveal in human terms.
9. VISUALIZATION COORDINATION: The NIRF analytics platform automatically renders rich interactive Plotly figures (including Box & Whisker plots, Histograms, Lollipop charts, Scatter plots, Line charts, Bar charts, and Maps) right below your response. NEVER say "While I cannot render a visual image/chart..." or apologize for visualization limitations. Refer to the chart smoothly (e.g., "As illustrated in the box plot below...", "The distribution graph below shows...").
10. OUTPUT FORMAT: You must output a valid JSON object with two fields:
   - "answer": A markdown string containing your complete natural-language explanation.
   - "claims": A list of structured factual claims made in the answer. Each claim has:
     {
       "statement": "<exact clause or sentence from answer>",
       "claim_type": "<METRIC_VALUE | RANK_VALUE | RANK_CHANGE | CORRELATION | COUNT | AGGREGATE_STATISTIC | INSTITUTION_COMPARISON>",
       "institution_name": "<name of institution if applicable, or null>",
       "institution_uid": "<uid if provided in evidence, or null>",
       "metric": "<score | rpc | tlr | go | oi | perception | rank | rank_improvement, or null>",
       "value": <numeric value as float or int>,
       "year": <assessment year as int, or null>,
       "state": "<state name if aggregate or state comparison, or null>",
       "statistic_type": "<mean | median | count | change | total, or null>"
     }
"""


def build_generation_prompt(
    user_question: str,
    evidence_context: str,
    response_type: str,
    custom_instructions: Optional[str] = None,
) -> str:
    """
    Constructs the user generation prompt including evidence and response framing.
    """
    prompt_lines = [
        f"USER QUESTION: {user_question}",
        f"EVIDENCE CLASSIFICATION: {response_type}",
        "",
        "AVAILABLE EVIDENCE:",
        evidence_context,
        "",
        "RESPONSE INSTRUCTIONS:",
        "- Provide a natural, conversational, and direct answer in the 'answer' field of your JSON response (sounding articulate and insightful like ChatGPT).",
        "- Highlight the key insights and direct takeaways clearly.",
        "- Reference specific institutions, years, categories, and metrics exactly as given in the evidence.",
        "- If reporting rank changes, explicitly state the starting rank, ending rank, and magnitude of change.",
        "- If documentation evidence is present, cite the relevant [CITE-XX] tags smoothly in your explanation.",
        "- If warnings or limitations are present in the evidence, weave a brief 'Data Notes & Limitations' note at the end.",
        "- Enumerate all numerical and factual claims in the 'claims' array of your JSON output.",
    ]

    if custom_instructions:
        prompt_lines.append(f"- Specific Note: {custom_instructions}")

    prompt_lines.append('\nReturn ONLY a valid JSON object with "answer" and "claims" fields:')
    return "\n".join(prompt_lines)


def build_regeneration_prompt(
    user_question: str,
    evidence_context: str,
    previous_response: str,
    failed_claims: List[Dict[str, Any]],
    verification_feedback: str,
) -> str:
    """
    Constructs a targeted regeneration prompt informing the LLM of verification discrepancies.
    """
    failed_bullets = []
    for fc in failed_claims:
        failed_bullets.append(
            f"- Statement: \"{fc.get('statement') or fc.get('claim_text')}\" | Issue: {fc.get('verification_notes')} "
            f"(Expected: {fc.get('actual_value')}, Got: {fc.get('value') or fc.get('claimed_value')})"
        )

    prompt = f"""USER QUESTION: {user_question}

A previous draft of your response failed automated numerical verification against the empirical dataset.

VERIFICATION FEEDBACK:
{verification_feedback}

FAILED OR DISCREPANT CLAIMS:
{chr(10).join(failed_bullets)}

PREVIOUS DRAFT:
\"\"\"
{previous_response}
\"\"\"

GROUNDED EVIDENCE:
{evidence_context}

CORRECTION REQUIREMENTS:
1. Correct every discrepant numerical value, institution name, rank direction, or correlation coefficient listed above to strictly match the empirical evidence.
2. Remove any unsupported causal statements or ungrounded claims.
3. Preserve all verified findings, citations, and data quality warnings.
4. Output a valid JSON object with corrected "answer" and "claims" fields.

Return ONLY the corrected JSON object now:"""
    return prompt
