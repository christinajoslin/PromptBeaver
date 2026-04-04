import json
import requests


def build_verifier_prompt(
    generated_prompt: str,
    interaction_mode: str,
    question_intent: str,
    general_concept: str,
    specific_concept: str,
    has_supporting_material: bool,
) -> str:
    return f"""
You are evaluating the quality of a generated educational prompt.

Your job is to verify whether the prompt aligns with the intended instructional design.

Evaluate the prompt on these dimensions:
1. Alignment with selected interaction mode
2. Alignment with selected question intent
3. Constraint adherence
4. Clarity and completeness

Selected configuration:
- Interaction mode: {interaction_mode}
- Question intent: {question_intent}
- General concept: {general_concept}
- Specific concept: {specific_concept}
- Supporting material included: {has_supporting_material}

Generated prompt to evaluate:
\"\"\"
{generated_prompt}
\"\"\"

Important constraints to check:
- It should reflect the selected interaction mode.
- It should reflect the selected question intent.
- It should clearly focus on the selected concept.
- It should instruct the model not to provide direct homework answers.
- It should instruct the model not to debug, modify, or rewrite code.
- It should remain concise and focused.

Return ONLY valid JSON in this exact schema:
{{
  "overall_pass": true,
  "alignment_score": 1,
  "clarity_score": 1,
  "constraint_score": 1,
  "issues": ["issue 1"],
  "suggested_revision": "one concrete improvement"
}}

Scoring should be from 1 to 5.
Do not include markdown fences.
""".strip()


def call_genai_studio_llm(
    verifier_prompt: str,
    base_url: str,
    api_key: str,
    model: str = "llama4:latest",
    timeout: int = 60,
) -> str:
    """
    Boilerplate request function.
    You will likely need to adapt the endpoint path or response parsing
    to match your GenAI Studio environment exactly.
    """

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "prompt": verifier_prompt,
        "temperature": 0.0,
    }

    response = requests.post(
        base_url,
        headers=headers,
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()

    data = response.json()


    # Common fallback parsing patterns.
    # Adjust this once you confirm your actual API response schema.
    if isinstance(data, dict):
        if "response" in data and isinstance(data["response"], str):
            return data["response"]
        if "output" in data and isinstance(data["output"], str):
            return data["output"]
        if "text" in data and isinstance(data["text"], str):
            return data["text"]
        if "choices" in data and isinstance(data["choices"], list) and data["choices"]:
            first = data["choices"][0]
            if isinstance(first, dict):
                if "text" in first:
                    return first["text"]
                if "message" in first and isinstance(first["message"], dict):
                    return first["message"].get("content", "")

    raise ValueError("Could not parse model response from GenAI Studio API.")


def verify_prompt_with_llm(
    generated_prompt: str,
    interaction_mode: str,
    question_intent: str,
    general_concept: str,
    specific_concept: str,
    has_supporting_material: bool,
    base_url: str,
    api_key: str,
    model: str = "llama4:latest",
) -> dict:
    try:
        verifier_prompt = build_verifier_prompt(
            generated_prompt=generated_prompt,
            interaction_mode=interaction_mode,
            question_intent=question_intent,
            general_concept=general_concept,
            specific_concept=specific_concept,
            has_supporting_material=has_supporting_material,
        )

        raw_output = call_genai_studio_llm(
            verifier_prompt=verifier_prompt,
            base_url=base_url,
            api_key=api_key,
            model=model,
        )
        print(raw_output)

        cleaned_output = raw_output.strip()

        if cleaned_output.startswith("```"):
            cleaned_output = cleaned_output.strip("`")
            cleaned_output = cleaned_output.replace("json", "", 1).strip()

        parsed = json.loads(cleaned_output)

        return {
            "success": True,
            "data": parsed,
            "raw_output": raw_output,
        }

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }