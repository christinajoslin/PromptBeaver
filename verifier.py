"""
Script to verify and revise generated educational prompts. 

Author: Christina Joslin 
Date: 4/4/2026
Purpose: 
    - Evaluates generated educational prompts for alignment, clarity, 
      constraint adherence, and instructional accuracy.
    - Produces a single-turn behavior preview to assess how the prompt 
      actually guides model behavior on a student's question.
    - Normalizes verifier outputs and applies exact prompt-level edits 
      when revisions are recommended.
"""

# =========================================================
# Load Libraries 
# =========================================================
import json
import os
import random
import time
from typing import Any

import requests
from dotenv import load_dotenv

# =========================================================
# Configuration
# =========================================================
load_dotenv()

VERIFIER_MODEL = "gpt-oss:120b"
BACKUP_VERIFIER_MODEL = "llama4:latest"
BEHAVIOR_PREVIEW_MODEL = "gpt-oss:120b"
BACKUP_BEHAVIOR_PREVIEW_MODEL = "llama4:latest"
GENAI_CHAT_COMPLETIONS_URL = "https://genai.rcac.purdue.edu/api/chat/completions"

GENAI_KEY = os.getenv("GENAI_API_KEY")
if not GENAI_KEY:
    raise ValueError("GENAI_API_KEY not found in environment variables.")

# =========================================================
# System Prompts
# =========================================================
VERIFIER_SYSTEM_PROMPT = """
You are a strict educational prompt quality reviewer.
Return ONLY valid JSON that matches the requested schema.
Do not include markdown fences or extra commentary.
""".strip()

# =========================================================
# API Core 
# =========================================================
def _extract_content(data):
    """
    Extracts the assistant message content from the GenAI Studio response.
    """
    if isinstance(data, dict) and "choices" in data and isinstance(data["choices"], list) and data["choices"]:
        first = data["choices"][0]
        if isinstance(first, dict):
            message = first.get("message", {})
            if isinstance(message, dict):
                content = message.get("content", "")
                if isinstance(content, str):
                    return content

    raise ValueError("Could not parse model response from GenAI Studio chat completions API.")


def _call_chat_completions(model, prompt, messages, system, temperature, response_format, timeout= 120):
    """
    Delivers an input payload to the GenAI Studio chat completions endpoint.
    """
    headers = {
        "Authorization": f"Bearer {GENAI_KEY}",
        "Content-Type": "application/json",
    }

    if messages is not None:
        payload_messages = messages
    else:
        payload_messages = [
            {"role": "system", "content": system} if system else None,
            {"role": "user", "content": prompt or ""},
        ]
        payload_messages = [m for m in payload_messages if m]

    payload: dict[str, Any] = {
        "model": model,
        "messages": payload_messages,
        "temperature": temperature,
        "stream": False,
    }

    if response_format:
        payload["response_format"] = response_format

    try:
        response = requests.post(
            GENAI_CHAT_COMPLETIONS_URL,
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        return _extract_content(response.json())
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Error connecting to GenAI Studio: {exc}") from exc


def _should_fallback(exc):
    """
    Determines whether an exception qualifies for backup-model fallback.
    """
    message = str(exc).lower()
    fallback_signals = ["504", "503", "gateway", "time-out", "timeout", "timed out"]
    return any(signal in message for signal in fallback_signals)


def call_genai_studio_llm_with_retry(
    prompt = None,
    messages = None,
    system= "",
    primary_model=VERIFIER_MODEL,
    backup_model=BACKUP_VERIFIER_MODEL,
    temperature = 0.0,
    response_format = None,
    max_retries_primary = 3,
    max_retries_backup = 3,
    return_metadata = False,
):
    """
    Calls the primary model with retry logic, then falls back to a backup 
    model only for qualifying infrastructure-style failures.
    """
    last_exception: Exception | None = None

    for attempt in range(1, max_retries_primary + 1):
        try:
            result = _call_chat_completions(
                model=primary_model,
                prompt=prompt,
                messages=messages,
                system=system,
                temperature=temperature,
                response_format=response_format,
            )
            if return_metadata:
                return {
                    "content": result,
                    "api_retry_attempt_used": attempt,
                    "model_used": primary_model,
                    "used_backup_model": False,
                }
            return result
        except Exception as exc:
            last_exception = exc
            if attempt < max_retries_primary:
                time.sleep(0.3 * attempt + random.uniform(0, 0.2))

    if last_exception is None:
        raise RuntimeError("Model call failed before any attempt could complete.")

    if not _should_fallback(last_exception):
        raise RuntimeError(
            f"Primary model failed and error did not qualify for fallback: {last_exception}"
        ) from last_exception

    for attempt in range(1, max_retries_backup + 1):
        try:
            result = _call_chat_completions(
                model=backup_model,
                prompt=prompt,
                messages=messages,
                system=system,
                temperature=temperature,
                response_format=response_format,
            )
            if return_metadata:
                return {
                    "content": result,
                    "api_retry_attempt_used": attempt,
                    "model_used": backup_model,
                    "used_backup_model": True,
                }
            return result
        except Exception as exc:
            last_exception = exc
            if attempt < max_retries_backup:
                time.sleep(0.3 * attempt + random.uniform(0, 0.2))
            else:
                raise RuntimeError(
                    f"Both primary model '{primary_model}' and backup model '{backup_model}' failed"
                ) from last_exception

# =========================================================
# Prompt Builders
# =========================================================
def build_behavior_preview_messages(generated_prompt, student_question):
    """
    Formats a system/user message pair for single-turn behavior preview.
    """
    return [
        {"role": "system", "content": generated_prompt},
        {"role": "user", "content": student_question},
    ]


def build_static_verifier_prompt(
    generated_prompt,
    interaction_mode,
    question_intent,
    general_concept,
    specific_concept,
    has_supporting_material,
):
    """
    Builds the verifier prompt used when no student question is provided.
    """
    return f'''You are evaluating the quality of a generated educational prompt.

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

Prompt to evaluate:
"""
{generated_prompt}
"""

Return ONLY valid JSON in this exact schema:
{{
  "overall_rating": "strong",
  "overall_pass": true,
  "alignment_score": 1,
  "clarity_score": 1,
  "constraint_score": 1,
  "issues": ["issue 1"],
  "suggested_revision": "one concrete improvement"
}}

Scoring should be from 1 to 5.
If there are no issues, return an empty list for "issues".
Do not include markdown fences.'''.strip()


def build_behavior_verifier_prompt(
    generated_prompt,
    student_question,
    sample_response,
    interaction_mode,
    question_intent,
    general_concept,
    specific_concept,
    has_supporting_material,
):
    """
    Builds the verifier prompt used when judging both prompt quality and 
    single-turn model behavior.
    """
    return f'''You are evaluating the quality of a generated educational prompt AND the model behavior it produces.

Your job is to determine whether this prompt is genuinely useful for guiding a model's behavior, not merely whether it sounds well-written.

Important evaluation context:
- The sample response below is ONLY a single-turn preview.
- Treat it as the model's first response to the student's question.
- Do NOT assume you are seeing the entire conversation.
- For multi-turn interaction styles, judge whether this is an appropriate opening turn for the selected interaction mode.
- Accuracy must be judged in a way that respects the selected interaction mode. For example, a Socratic or guided opening turn may be accurate even if it does not fully explain everything immediately, as long as it appropriately advances the student toward the right understanding.
- You may use the sample response as evidence of how the prompt behaves, but any recommended_edits and any revised_prompt_draft must edit ONLY the prompt itself.
- Do NOT suggest edits to the sample response text, and do NOT quote sample-response wording as something to replace.

Score these dimensions separately and do not collapse them together:
1. Alignment = how well the prompt and sample response follow the selected interaction mode, question intent, and concept focus.
2. Clarity = how clear, specific, and easy the prompt is for the model to follow.
3. Constraint adherence = whether the prompt states the required rules and whether the sample response follows those rules.
4. Accuracy = how correct and instructionally appropriate the single-turn sample response is for the student's actual question, given the selected interaction mode.

Selected configuration:
- Interaction mode: {interaction_mode}
- Question intent: {question_intent}
- General concept: {general_concept}
- Specific concept: {specific_concept}
- Supporting material included: {has_supporting_material}

Student's actual question:
"""
{student_question}
"""

Generated prompt to evaluate:
"""
{generated_prompt}
"""

Single-turn sample model response produced using that generated prompt on the student's actual question:
"""
{sample_response}
"""

Important constraints to check:
- The prompt and response should reflect the selected interaction mode.
- The prompt and response should reflect the selected question intent.
- The prompt and response should clearly focus on the topic implied by the student's actual question.
- If the selected concept conflicts with the student's actual question, the student's actual question should take precedence.
- The prompt should instruct the model not to provide direct homework answers.
- The response should avoid giving away direct homework answers when that would violate the role or rules.
- The prompt should instruct the model not to debug, modify, or rewrite code.
- The response should avoid debugging, modifying, or rewriting code.
- The response should remain concise, focused, and scannable.
- The response should be accurate and appropriate as an opening turn for the selected instructional role.

Return ONLY valid JSON in this exact schema:
{{
  "overall_rating": "strong",
  "overall_pass": true,
  "alignment_score": 1,
  "clarity_score": 1,
  "constraint_score": 1,
  "accuracy_score": 1,
  "top_issues": [
    {{
      "type": "constraint_violation",
      "location": "response_behavior",
      "message": "specific issue"
    }}
  ],
  "recommended_edits": [
    {{
      "operation": "rewrite",
      "old_text": "exact text to replace",
      "new_text": "replacement text",
      "text": ""
    }},
    {{
      "operation": "add",
      "old_text": "",
      "new_text": "",
      "text": "exact sentence or phrase to add"
    }},
    {{
      "operation": "remove",
      "old_text": "exact text to remove",
      "new_text": "",
      "text": ""
    }}
  ],
  "revised_prompt_draft": "revised prompt text or empty string"
}}

Rules for the JSON fields:
- overall_rating must be one of: "strong", "acceptable", "needs_revision"
- recommended_edits and revised_prompt_draft must target the generated prompt only, not the sample response.
- If the problem appears in the sample response, convert that observation into a prompt-level edit that would reduce the chance of that behavior.
- Scores must be integers from 1 to 5.
- alignment_score must reflect match to mode, intent, and the true topic focus implied by the student's actual question.
- clarity_score must reflect prompt wording quality only.
- constraint_score must reflect rule-following in both the prompt and the single-turn sample response.
- accuracy_score must reflect whether the single-turn sample response is correct and instructionally appropriate for the student's actual question and the selected interaction mode.
- If there are no issues, return an empty list for "top_issues".
- If the prompt already looks strong and no meaningful changes are needed, return an empty list for recommended_edits and an empty string for revised_prompt_draft.
- revised_prompt_draft should be non-empty only if changes are clearly necessary and a materially better prompt can be produced.
- If you provide revised_prompt_draft, it must preserve the student's exact question, the selected concept focus, and the core instructional role while tightening weak instructions.
- Do not simply repeat the original prompt in revised_prompt_draft.
- Do not invent edits just to fill the schema. If no change is needed, leave recommended_edits empty.
- recommended_edits must be concrete and use ONLY these operations: "rewrite", "add", or "remove".
- For "rewrite", fill old_text and new_text.
- For "add", fill text only.
- For "remove", fill old_text only.
- Keep each edit short, specific, and directly usable in the UI.
- Do not include markdown fences.'''.strip()

# =========================================================
# Formatting Helpers 
# =========================================================
def _clean_revised_prompt_draft(revised_prompt_draft, generated_prompt):
    """
    Filters out empty, unchanged, or implausibly short revised drafts.
    """
    if not isinstance(revised_prompt_draft, str):
        return ""

    cleaned = revised_prompt_draft.strip()
    if not cleaned:
        return ""
    if cleaned == generated_prompt.strip():
        return ""
    if len(cleaned) < max(80, int(len(generated_prompt.strip()) * 0.45)):
        return ""
    return cleaned


def _edit_targets_prompt(edit, generated_prompt):
    """
    Confirms that a normalized edit can be applied directly to the prompt.
    """
    operation = edit.get("operation", "").strip().lower()
    old_text = edit.get("old_text", "").strip()
    new_text = edit.get("new_text", "").strip()
    text = edit.get("text", "").strip()

    if operation == "rewrite":
        return bool(old_text and new_text and old_text in generated_prompt)
    if operation == "remove":
        return bool(old_text and old_text in generated_prompt)
    if operation == "add":
        return bool(text)
    return False


def _normalize_recommended_edits(recommended_edits):
    """
    Converts raw model edits into a small, standardized list of exact edits.
    """
    normalized: list[dict[str, str]] = []
    if not isinstance(recommended_edits, list):
        return normalized

    for edit in recommended_edits:
        if not isinstance(edit, dict):
            continue

        operation = str(edit.get("operation", edit.get("action", "edit"))).strip().lower()
        old_text = str(edit.get("old_text", "")).strip()
        new_text = str(edit.get("new_text", "")).strip()
        text = str(edit.get("text", edit.get("recommendation", ""))).strip()

        if operation == "rewrite" and old_text and new_text:
            normalized.append(
                {"operation": "rewrite", "old_text": old_text, "new_text": new_text, "text": ""}
            )
        elif operation == "add" and text:
            normalized.append(
                {"operation": "add", "old_text": "", "new_text": "", "text": text}
            )
        elif operation == "remove" and old_text:
            normalized.append(
                {"operation": "remove", "old_text": old_text, "new_text": "", "text": ""}
            )
        elif text:
            normalized.append(
                {"operation": "add", "old_text": "", "new_text": "", "text": text}
            )

        if len(normalized) >= 5:
            break

    return normalized


def _normalize_behavior_output(parsed, generated_prompt):
    """
    Ensures the behavior-verifier output matches the expected downstream shape.
    """
    parsed.setdefault("overall_rating", "needs_revision")
    parsed.setdefault("overall_pass", False)
    parsed.setdefault("alignment_score", "N/A")
    parsed.setdefault("clarity_score", "N/A")
    parsed.setdefault("constraint_score", "N/A")
    parsed.setdefault("accuracy_score", parsed.get("behavior_score", "N/A"))
    parsed.setdefault("top_issues", [])
    parsed.setdefault("recommended_edits", [])
    parsed.setdefault("revised_prompt_draft", "")

    if not isinstance(parsed.get("top_issues"), list):
        parsed["top_issues"] = []

    normalized_edits = _normalize_recommended_edits(parsed.get("recommended_edits", []))
    parsed["recommended_edits"] = [
        edit for edit in normalized_edits if _edit_targets_prompt(edit, generated_prompt)
    ]

    cleaned_draft = _clean_revised_prompt_draft(
        parsed.get("revised_prompt_draft", ""),
        generated_prompt,
    )
    parsed["revised_prompt_draft"] = (
        cleaned_draft if cleaned_draft and cleaned_draft != generated_prompt.strip() else ""
    )

    return parsed

# =========================================================
# Verification 
# =========================================================
def generate_behavior_preview(generated_prompt, student_question):
    """
    Produces a one-turn sample response for behavior-based prompt review.
    """
    try:
        response = call_genai_studio_llm_with_retry(
            messages=build_behavior_preview_messages(generated_prompt, student_question),
            primary_model=BEHAVIOR_PREVIEW_MODEL,
            backup_model=BACKUP_BEHAVIOR_PREVIEW_MODEL,
            temperature=0.2,
            return_metadata=True,
        )
        assert isinstance(response, dict)
        return {
            "success": True,
            "sample_response": str(response["content"]).strip(),
            "model_used": response.get("model_used", BEHAVIOR_PREVIEW_MODEL),
            "used_backup_model": response.get("used_backup_model", False),
            "api_retry_attempt_used": response.get("api_retry_attempt_used", 1),
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def verify_prompt_with_llm(
    generated_prompt,
    interaction_mode,
    question_intent,
    general_concept,
    specific_concept,
    has_supporting_material,
    student_question= None,
):
    """
    Runs either static prompt verification or behavior-based verification, 
    depending on whether a student question is supplied.
    """
    try:
        if not student_question:
            verifier_prompt = build_static_verifier_prompt(
                generated_prompt=generated_prompt,
                interaction_mode=interaction_mode,
                question_intent=question_intent,
                general_concept=general_concept,
                specific_concept=specific_concept,
                has_supporting_material=has_supporting_material,
            )
            response = call_genai_studio_llm_with_retry(
                prompt=verifier_prompt,
                system=VERIFIER_SYSTEM_PROMPT,
                primary_model=VERIFIER_MODEL,
                backup_model=BACKUP_VERIFIER_MODEL,
                temperature=0.0,
                response_format={"type": "json_object"},
                return_metadata=True,
            )
            content = response["content"] if isinstance(response, dict) else response
            parsed = json.loads(content)
            return {"success": True, "data": parsed}

        preview_result = generate_behavior_preview(generated_prompt, student_question)
        if not preview_result.get("success"):
            return {
                "success": False,
                "error": f"Behavior preview failed: {preview_result.get('error', 'Unknown error')}",
            }

        verifier_prompt = build_behavior_verifier_prompt(
            generated_prompt=generated_prompt,
            student_question=student_question,
            sample_response=preview_result["sample_response"],
            interaction_mode=interaction_mode,
            question_intent=question_intent,
            general_concept=general_concept,
            specific_concept=specific_concept,
            has_supporting_material=has_supporting_material,
        )
        response = call_genai_studio_llm_with_retry(
            prompt=verifier_prompt,
            system=VERIFIER_SYSTEM_PROMPT,
            primary_model=VERIFIER_MODEL,
            backup_model=BACKUP_VERIFIER_MODEL,
            temperature=0.0,
            response_format={"type": "json_object"},
            return_metadata=True,
        )
        content = response["content"] if isinstance(response, dict) else response
        parsed = _normalize_behavior_output(json.loads(content), generated_prompt)
        parsed["behavior_preview"] = {
            "sample_response": preview_result.get("sample_response", ""),
            "model_used": preview_result.get("model_used", BEHAVIOR_PREVIEW_MODEL),
            "used_backup_model": preview_result.get("used_backup_model", False),
            "api_retry_attempt_used": preview_result.get("api_retry_attempt_used", 1),
        }

        if isinstance(response, dict):
            parsed["verifier_model_used"] = response.get("model_used", VERIFIER_MODEL)
            parsed["verifier_used_backup_model"] = response.get("used_backup_model", False)
            parsed["verifier_api_retry_attempt_used"] = response.get("api_retry_attempt_used", 1)

        return {"success": True, "data": parsed}
    except Exception as exc:
        return {"success": False, "error": str(exc)}

# =========================================================
# Revision Helpers 
# =========================================================
def _apply_exact_recommended_edits(generated_prompt,recommended_edits = None):
    """
    Applies only the exact normalized edits returned by the verifier.
    """
    prompt = generated_prompt
    notes: list[str] = []

    for edit in _normalize_recommended_edits(recommended_edits):
        operation = edit.get("operation", "").strip().lower()
        old_text = edit.get("old_text", "").strip()
        new_text = edit.get("new_text", "").strip()
        text = edit.get("text", "").strip()

        if operation == "rewrite" and old_text and new_text:
            if old_text in prompt:
                prompt = prompt.replace(old_text, new_text, 1)
                notes.append(f'Rewrote: "{old_text[:90]}"')
        elif operation == "remove" and old_text:
            if old_text in prompt:
                prompt = prompt.replace(old_text, "", 1)
                notes.append(f'Removed: "{old_text[:90]}"')
        elif operation == "add" and text:
            if text not in prompt:
                anchor = "For the rest of this conversation, you MUST continue following these rules, this role, and these setting expectations."
                if anchor in prompt:
                    prompt = prompt.replace(anchor, f"- {text}\n{anchor}", 1)
                else:
                    prompt = prompt.rstrip() + f"\n- {text}"
                notes.append(f'Added: "{text[:90]}"')

    prompt = "\n".join(line.rstrip() for line in prompt.splitlines())
    while "\n\n\n" in prompt:
        prompt = prompt.replace("\n\n\n", "\n\n")

    return prompt.strip(), notes[:5]

# =========================================================
# Revision 
# =========================================================
def revise_prompt_with_llm(
    generated_prompt,
    student_question,
    interaction_mode,
    question_intent,
    general_concept,
    specific_concept,
    has_supporting_material,
    top_issues = None,
    recommended_edits = None,
    fallback_revised_prompt_draft = None,
):
    """
    Revises a prompt by applying exact recommended edits, with an optional 
    fallback to a verified revised draft when the exact edits do not change 
    the prompt.
    """
    _ = (
        student_question,
        interaction_mode,
        question_intent,
        general_concept,
        specific_concept,
        has_supporting_material,
        top_issues,
    )

    try:
        normalized_edits = _normalize_recommended_edits(recommended_edits)
        if not normalized_edits:
            return {
                "success": True,
                "revised_prompt": generated_prompt.strip(),
                "revision_notes": [],
                "model_used": "exact_edit_applier",
                "used_backup_model": False,
                "api_retry_attempt_used": 1,
            }

        revised_prompt, revision_notes = _apply_exact_recommended_edits(
            generated_prompt=generated_prompt,
            recommended_edits=normalized_edits,
        )

        if revised_prompt.strip() == generated_prompt.strip():
            cleaned_fallback = _clean_revised_prompt_draft(
                fallback_revised_prompt_draft or "",
                generated_prompt,
            )
            if cleaned_fallback:
                return {
                    "success": True,
                    "revised_prompt": cleaned_fallback,
                    "revision_notes": [
                        "Used the verifier's revised draft because the exact edits did not change the prompt."
                    ],
                    "model_used": "fallback_revised_prompt_draft",
                    "used_backup_model": False,
                    "api_retry_attempt_used": 1,
                }
            return {
                "success": False,
                "error": "The exact suggested edits did not produce any change in the prompt.",
            }

        return {
            "success": True,
            "revised_prompt": revised_prompt,
            "revision_notes": revision_notes,
            "model_used": "exact_edit_applier",
            "used_backup_model": False,
            "api_retry_attempt_used": 1,
        }
    except Exception as exc:
        cleaned_fallback = _clean_revised_prompt_draft(
            fallback_revised_prompt_draft or "",
            generated_prompt,
        )
        if cleaned_fallback:
            return {
                "success": True,
                "revised_prompt": cleaned_fallback,
                "revision_notes": [
                    "Used the verifier's fallback revised draft because exact edit application failed."
                ],
                "model_used": "fallback_revised_prompt_draft",
                "used_backup_model": False,
                "api_retry_attempt_used": 1,
            }
        return {"success": False, "error": str(exc)}