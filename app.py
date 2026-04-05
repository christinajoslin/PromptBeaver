"""
Streamlit app for building and evaluating educational cs prompts. 

Author: Christina Joslin
Date: 4/4/2026
Purpose:
    - Lets a user configure an instructional interaction mode, concept focus,
      and question intent to generate a structured prompt.
    - Runs an LLM behavior preview via Purdue GenAI Studio and verifier pass to assess prompt quality.
    - Supports exact-edit prompt revision and re-verification inside the UI.
"""

# =========================================================
# Load Libraries 
# =========================================================
import html
import markdown
import streamlit as st

from prompt_builder import (
    CONCEPT_MAP,
    INTERACTION_MODES,
    QUESTION_INTENTS,
    SUPPORTING_MATERIALS,
    build_user_prompt,
)
from verifier import revise_prompt_with_llm, verify_prompt_with_llm

# =========================================================
# Configuration
# =========================================================
PAGE_TITLE = "PromptBeaver"
PAGE_ICON = "🦫"
LAYOUT = "wide"
MAX_QUESTION_WORDS = 150
DOWNLOAD_FILENAME = "promptbeaver_prompt.txt"

DEFAULT_SESSION_STATE = {
    "final_prompt": None,
    "original_prompt": None,
    "final_prompt_source": "original",
    "verification_result": None,
    "last_revision_notes": [],
    "interaction_mode_select": None,
    "question_intent_select": None,
    "general_concept_select": None,
    "specific_concept_select": None,
    "student_question_input": "",
    "supporting_material_type_select": None,
}

APP_STYLES = """
<style>
.pb-card {
    padding: 1rem 1.15rem;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    margin-bottom: 0.9rem;
    background: #ffffff;
}
.pb-title {
    font-size: 1.02rem;
    font-weight: 700;
    margin-bottom: 0.2rem;
}
.pb-chip {
    display: inline-block;
    padding: 0.22rem 0.55rem;
    margin: 0.15rem 0.35rem 0.15rem 0;
    border-radius: 999px;
    background: #f3f4f6;
    border: 1px solid #e5e7eb;
    font-size: 0.88rem;
}
.pb-focus-card {
    padding: 0.95rem 1.05rem;
    border: 1px solid #dbe4f0;
    border-radius: 18px;
    margin: 1.1rem 0 0.95rem 0;
    background: #f8fbff;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.pb-focus-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 0.6rem;
    margin-top: 0.55rem;
}
.pb-focus-item {
    padding: 0.72rem 0.8rem;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    background: #ffffff;
}
.pb-focus-label {
    font-size: 0.8rem;
    font-weight: 700;
    color: #475569;
    margin-bottom: 0.2rem;
    text-transform: uppercase;
    letter-spacing: 0.02em;
}
.pb-focus-value {
    font-size: 0.95rem;
    font-weight: 600;
    color: #111827;
    line-height: 1.35;
}
.pb-section-label {
    font-size: 0.92rem;
    font-weight: 650;
    margin-top: 0.9rem;
    margin-bottom: 0.35rem;
    color: #111827;
}
.pb-edit-card {
    padding: 0.85rem 0.95rem;
    border: 1px solid #e5e7eb;
    border-radius: 16px;
    background: #fcfcfc;
    margin-bottom: 0.6rem;
}
.pb-edit-badge {
    display: inline-block;
    padding: 0.18rem 0.55rem;
    border-radius: 999px;
    background: #eef2ff;
    border: 1px solid #dbe4ff;
    font-size: 0.78rem;
    font-weight: 700;
    color: #334155;
    margin-bottom: 0.45rem;
}
.pb-metric-card {
    border: 1px solid #e5e7eb;
    border-radius: 22px;
    padding: 1rem 1rem 1.05rem 1rem;
    background: #ffffff;
    min-height: 170px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    gap: 0.8rem;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.pb-metric-top {
    display: flex;
    flex-direction: column;
    gap: 0.32rem;
}
.pb-metric-label {
    font-size: 1rem;
    font-weight: 700;
    color: #374151;
    line-height: 1.25;
    margin: 0;
}
.pb-metric-subtext {
    font-size: 0.88rem;
    color: #6b7280;
    line-height: 1.4;
    margin: 0;
}
.pb-issue-card {
    padding: 0.82rem 0.95rem;
    border: 1px solid #e5e7eb;
    border-radius: 16px;
    background: #ffffff;
    margin-bottom: 0.55rem;
}
.pb-issue-meta {
    font-size: 0.8rem;
    font-weight: 700;
    color: #475569;
    margin-bottom: 0.2rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}
.pb-issue-text {
    font-size: 0.94rem;
    color: #111827;
    line-height: 1.45;
    margin: 0;
}
.pb-behavior-card {
    padding: 1rem 1.05rem;
    border: 1px solid #dbe4f0;
    border-radius: 18px;
    background: #f8fbff;
    margin: 0.9rem 0 1rem 0;
}
.pb-behavior-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    margin-bottom: 0.65rem;
    flex-wrap: wrap;
}
.pb-behavior-title {
    font-size: 0.98rem;
    font-weight: 700;
    color: #111827;
    margin: 0;
}
.pb-model-badge {
    display: inline-block;
    padding: 0.22rem 0.6rem;
    border-radius: 999px;
    background: #eef2ff;
    border: 1px solid #dbe4ff;
    font-size: 0.8rem;
    font-weight: 700;
    color: #334155;
}
.pb-score-row {
    display: flex;
    align-items: center;
    gap: 0.42rem;
    flex-wrap: wrap;
    margin-top: 0.15rem;
}
.pb-score-pill {
    min-width: 2.1rem;
    height: 2.1rem;
    padding: 0 0.72rem;
    border-radius: 999px;
    border: 1px solid #d1d5db;
    background: #f9fafb;
    color: #4b5563;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.9rem;
    font-weight: 700;
    line-height: 1;
}
.pb-score-pill-selected {
    background: #eef2ff;
    border: 1px solid #c7d2fe;
    color: #312e81;
    box-shadow: 0 1px 2px rgba(79, 70, 229, 0.10);
}
.pb-score-label {
    font-size: 0.82rem;
    font-weight: 600;
    color: #9ca3af;
    margin-right: 0.1rem;
}
.pb-score-label-right {
    font-size: 0.82rem;
    font-weight: 600;
    color: #9ca3af;
    margin-left: 0.1rem;
}
.pb-behavior-body {
    padding: 0.9rem 1rem;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    background: #ffffff;
    color: #111827;
    font-size: 0.95rem;
    line-height: 1.55;
    overflow-x: auto;
}
.pb-behavior-body p {
    margin-top: 0;
    margin-bottom: 1rem;
}
.pb-behavior-body table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 0.75rem;
}
.pb-behavior-body th,
.pb-behavior-body td {
    border: 1px solid #e5e7eb;
    padding: 0.6rem 0.75rem;
    text-align: left;
    vertical-align: top;
}
.pb-behavior-body th {
    background: #f9fafb;
    font-weight: 700;
}
</style>
"""

# =========================================================
# UI Setup
# =========================================================
st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout=LAYOUT)
st.title(f"{PAGE_ICON} {PAGE_TITLE}")
st.caption("Generate a ready-to-copy user prompt for conceptual computer science questions.")
st.markdown(APP_STYLES, unsafe_allow_html=True)

# =========================================================
# Session State Helpers
# =========================================================
def initialize_session_state():
    """
    Sets default Streamlit session state values on first load.
    """
    for key, default in DEFAULT_SESSION_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = default


def reset_generation_state():
    """
    Clears generated output when validation fails or a new run begins.
    """
    st.session_state.final_prompt = None
    st.session_state.original_prompt = None
    st.session_state.final_prompt_source = "original"
    st.session_state.verification_result = None
    st.session_state.last_revision_notes = []


initialize_session_state()

# =========================================================
# Rendering Helpers
# =========================================================
def summarize_selection(label, value, description=None):
    """
    Shows a compact summary chip beneath a selected UI control.
    """
    if not value:
        return

    st.markdown(
        f"<span class='pb-chip'><strong>{label}:</strong> {html.escape(value)}</span>",
        unsafe_allow_html=True,
    )

    if description:
        st.caption(description)


def render_focus_preview(interaction_mode, question_intent, general_concept, specific_concept, supporting_material_type, uploaded_file):
    """
    Displays a card summarizing the current prompt configuration.
    """
    st.markdown("<div class='pb-focus-card'>", unsafe_allow_html=True)
    st.markdown("<div class='pb-title'>5) Review customizations</div>", unsafe_allow_html=True)

    items: list[tuple[str, str]] = []
    if interaction_mode:
        items.append(("Interaction mode", interaction_mode))
    if question_intent:
        items.append(("Question intent", question_intent))
    if general_concept:
        items.append(("General concept", general_concept))
    if specific_concept:
        items.append(("Specific concept", specific_concept))
    if supporting_material_type:
        items.append(("Supporting material", supporting_material_type))
    if uploaded_file is not None:
        items.append(("Attached file", uploaded_file.name))

    if items:
        st.markdown("<div class='pb-focus-grid'>", unsafe_allow_html=True)
        for label, value in items:
            st.markdown(
                f"""
                <div class='pb-focus-item'>
                    <div class='pb-focus-label'>{html.escape(label)}</div>
                    <div class='pb-focus-value'>{html.escape(value)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.write("Make selections to see what the prompt will focus on.")

    st.markdown("</div>", unsafe_allow_html=True)


def render_metric_with_info(title, score, explanation):
    """
    Renders a 1-5 score card with an expandable explanation.
    """
    try:
        score_value = int(score)
    except (TypeError, ValueError):
        score_value = None

    pills_html = "<div class='pb-score-row'><span class='pb-score-label'>Low</span>"
    for value in [1, 2, 3, 4, 5]:
        selected_class = " pb-score-pill-selected" if score_value == value else ""
        pills_html += f"<span class='pb-score-pill{selected_class}'>{value}</span>"
    pills_html += "<span class='pb-score-label-right'>High</span></div>"

    if score_value not in {1, 2, 3, 4, 5}:
        pills_html = f"<div class='pb-metric-subtext'>Score: {html.escape(str(score))}</div>"

    st.markdown(
        f"""
        <div class='pb-metric-card'>
            <div class='pb-metric-top'>
                <div class='pb-metric-label'>{html.escape(title)}</div>
            </div>
            {pills_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("ⓘ Details", expanded=False):
        st.markdown(
            f"<div class='pb-metric-subtext'>{html.escape(explanation)}</div>",
            unsafe_allow_html=True,
        )


def render_issue_list(top_issues):
    """
    Lists verifier-identified issues.
    """
    if not top_issues:
        st.success("No major issues reported.")
        return

    for issue in top_issues:
        issue_type = str(issue.get("type", "issue")).replace("_", " ").title()
        location = str(issue.get("location", "prompt")).replace("_", " ").title()
        message = str(issue.get("message", "")).strip() or "Review this area of the prompt."

        st.markdown(
            f"""
            <div class='pb-issue-card'>
                <div class='pb-issue-meta'>{html.escape(issue_type)} · {html.escape(location)}</div>
                <p class='pb-issue-text'>{html.escape(message)}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_recommended_edits(recommended_edits):
    """
    Displays concrete prompt edits suggested by the verifier.
    """
    if not recommended_edits:
        st.success("No prompt edits suggested.")
        return

    for i, edit in enumerate(recommended_edits, 1):
        operation = str(edit.get("operation", "edit")).strip().lower()
        old_text = str(edit.get("old_text", "")).strip()
        new_text = str(edit.get("new_text", "")).strip()
        text = str(edit.get("text", "")).strip()

        label = {
            "rewrite": "Rewrite prompt text",
            "remove": "Remove prompt text",
            "add": "Add prompt text",
        }.get(operation, "Edit prompt text")

        st.markdown("<div class='pb-edit-card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='pb-edit-badge'>Edit {i}</div>", unsafe_allow_html=True)
        st.markdown(f"**{label}**")

        if operation == "rewrite" and old_text and new_text:
            st.markdown(
                f"""
**Replace this prompt text**
`{old_text}`

**With this**
`{new_text}`
"""
            )
        elif operation == "remove" and old_text:
            st.markdown(
                f"""
**Remove this prompt text**
`{old_text}`
"""
            )
        elif operation == "add" and text:
            st.markdown(
                f"""
**Add this to the prompt**
`{text}`
"""
            )
        else:
            fallback = text or new_text or old_text or "Review this part of the prompt."
            st.markdown(f"`{fallback}`")

        st.markdown("</div>", unsafe_allow_html=True)


def render_behavior_preview(sample_response, behavior_model_used):
    """
    Shows the first-turn response produced during the behavior preview.
    """
    st.markdown("<div class='pb-section-label'>Preview of first-turn behavior</div>", unsafe_allow_html=True)

    safe_model = html.escape(behavior_model_used or "unknown model")
    rendered_response = markdown.markdown(sample_response)

    st.markdown(
        f"""
        <div class='pb-behavior-card'>
            <div class='pb-behavior-header'>
                <div class='pb-behavior-title'>Sample opening response</div>
                <div class='pb-model-badge'>Model: {safe_model}</div>
            </div>
            <div class='pb-behavior-body'>
                {rendered_response}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# =========================================================
# Verification Helpers
# =========================================================
def rerun_verification_for_prompt(prompt, question, interaction_mode, question_intent, general_concept, specific_concept, has_supporting_material):
    """
    Re-runs verifier logic on the current prompt.
    """
    return verify_prompt_with_llm(
        generated_prompt=prompt,
        student_question=question.strip(),
        interaction_mode=interaction_mode,
        question_intent=question_intent,
        general_concept=general_concept,
        specific_concept=specific_concept,
        has_supporting_material=has_supporting_material,
    )


def collect_input_errors(
    interaction_mode,
    general_concept,
    specific_concept,
    question_intent,
    question,
    word_count,
    supporting_material_type,
    uploaded_file,
):
    """
    Validates required UI inputs before generation.
    """
    errors = []

    if interaction_mode is None:
        errors.append("Please select an interaction mode.")
    if general_concept is None:
        errors.append("Please select a general concept.")
    if specific_concept is None:
        errors.append("Please select a specific concept.")
    if question_intent is None:
        errors.append("Please select a question intent.")
    if not question.strip():
        errors.append("Please enter a student question.")
    if word_count > MAX_QUESTION_WORDS:
        errors.append(f"The student question must be {MAX_QUESTION_WORDS} words or fewer.")
    if supporting_material_type is not None and uploaded_file is None:
        errors.append("You selected a supporting material type but did not upload a file.")
    if supporting_material_type is None and uploaded_file is not None:
        errors.append("You uploaded a file but did not select a supporting material type.")

    return errors

# =========================================================
# Main Layout 
# =========================================================
left_col, right_col = st.columns([1.05, 1], gap="large")

with left_col:

    # Prompt setup controls
    st.markdown("<div class='pb-card'>", unsafe_allow_html=True)
    st.markdown("<div class='pb-title'>1) Prompt setup</div>", unsafe_allow_html=True)

    interaction_mode = st.selectbox(
        "Interaction mode",
        options=list(INTERACTION_MODES.keys()),
        index=None,
        placeholder="Choose an interaction mode...",
        key="interaction_mode_select",
    )
    if interaction_mode:
        summarize_selection("Mode", interaction_mode, INTERACTION_MODES[interaction_mode]["ui_explanation"])

    question_intent = st.selectbox(
        "Question intent",
        options=list(QUESTION_INTENTS.keys()),
        index=None,
        placeholder="Choose a question intent...",
        key="question_intent_select",
    )
    if question_intent:
        summarize_selection("Intent", question_intent, QUESTION_INTENTS[question_intent])

    st.markdown("</div>", unsafe_allow_html=True)

    # Concept selection controls
    st.markdown("<div class='pb-card'>", unsafe_allow_html=True)
    st.markdown("<div class='pb-title'>2) Concept selection</div>", unsafe_allow_html=True)

    general_concept = st.selectbox(
        "General concept",
        options=list(CONCEPT_MAP.keys()),
        index=None,
        placeholder="Choose a general concept...",
        key="general_concept_select",
    )

    if general_concept is None:
        st.session_state.specific_concept_select = None

    specific_concept = st.selectbox(
        "Specific concept",
        options=CONCEPT_MAP[general_concept] if general_concept else [],
        index=None,
        placeholder="Choose a specific concept..." if general_concept else "Choose a general concept first...",
        disabled=general_concept is None,
        key="specific_concept_select",
    )

    if general_concept:
        summarize_selection("General", general_concept)
    if specific_concept:
        summarize_selection("Specific", specific_concept)

    st.markdown("</div>", unsafe_allow_html=True)

with right_col:

    # Student question input
    st.markdown("<div class='pb-card'>", unsafe_allow_html=True)
    st.markdown("<div class='pb-title'>3) Your question</div>", unsafe_allow_html=True)

    question = st.text_area(
        f"({MAX_QUESTION_WORDS} words max)",
        height=220,
        placeholder="Type the conceptual question here...",
        help="Enter the conceptual question you want an LLM to respond to.",
        key="student_question_input",
    )
    word_count = len(question.split()) if question.strip() else 0
    st.caption(f"Word count: {word_count}/{MAX_QUESTION_WORDS}")
    st.markdown("</div>", unsafe_allow_html=True)

    # Optional supporting materials
    st.markdown("<div class='pb-card'>", unsafe_allow_html=True)
    st.markdown("<div class='pb-title'>4) Optional supporting materials</div>", unsafe_allow_html=True)

    supporting_material_type = st.selectbox(
        "Supporting material type",
        options=list(SUPPORTING_MATERIALS.keys()),
        index=None,
        placeholder="Choose a supporting material type...",
        help="Upload materials to prioritize course-specific terminology and examples in the prompt.",
        key="supporting_material_type_select",
    )

    uploaded_file = st.file_uploader("Upload supporting file", type=["pdf", "txt", "md", "docx"])

    if supporting_material_type:
        summarize_selection("Material", supporting_material_type, SUPPORTING_MATERIALS[supporting_material_type])
    if uploaded_file is not None:
        st.caption(f"Attached file: {uploaded_file.name}")

    st.markdown("</div>", unsafe_allow_html=True)

render_focus_preview(
    interaction_mode,
    question_intent,
    general_concept,
    specific_concept,
    supporting_material_type,
    uploaded_file,
)

submit_clicked = st.button("Generate Prompt", use_container_width=True, type="primary")

if submit_clicked:
    errors = collect_input_errors(
        interaction_mode=interaction_mode,
        general_concept=general_concept,
        specific_concept=specific_concept,
        question_intent=question_intent,
        question=question,
        word_count=word_count,
        supporting_material_type=supporting_material_type,
        uploaded_file=uploaded_file,
    )

    if errors:
        reset_generation_state()
        for error in errors:
            st.error(error)
    else:
        generated_prompt = build_user_prompt(
            question=question.strip(),
            question_intent=question_intent,
            general_concept=general_concept,
            specific_concept=specific_concept,
            interaction_mode=interaction_mode,
            interaction_mode_description=INTERACTION_MODES[interaction_mode]["instruction_description"],
            supplemental_material_type=supporting_material_type if uploaded_file else None,
            supplemental_material_file_name=uploaded_file.name if uploaded_file else None,
        )

        st.session_state.final_prompt = generated_prompt
        st.session_state.original_prompt = generated_prompt
        st.session_state.final_prompt_source = "original"
        st.session_state.last_revision_notes = []

        with st.spinner("Running behavior preview and prompt evaluation..."):
            st.session_state.verification_result = rerun_verification_for_prompt(
                prompt=generated_prompt,
                question=question,
                interaction_mode=interaction_mode,
                question_intent=question_intent,
                general_concept=general_concept,
                specific_concept=specific_concept,
                has_supporting_material=uploaded_file is not None,
            )

if st.session_state.final_prompt:
    result_tabs = ["Generated prompt"]
    if st.session_state.verification_result is not None:
        result_tabs.append("Verification")

    tabs = st.tabs(result_tabs)

    with tabs[0]:

        # Generated prompt output
        if st.session_state.final_prompt_source == "revised":
            st.info("You are viewing the revised prompt.")

        st.code(st.session_state.final_prompt, language="text")

        download_col, restore_col = st.columns(2)
        with download_col:
            st.download_button(
                label="Download TXT",
                data=st.session_state.final_prompt,
                file_name=DOWNLOAD_FILENAME,
                mime="text/plain",
                use_container_width=True,
            )

        with restore_col:
            if st.session_state.final_prompt_source != "original" and st.session_state.original_prompt:
                if st.button(
                    "Restore original generated prompt",
                    key="restore_original_prompt_inline",
                    use_container_width=True,
                ):
                    st.session_state.final_prompt = st.session_state.original_prompt
                    st.session_state.final_prompt_source = "original"
                    st.session_state.last_revision_notes = []
                    st.rerun()
            else:
                st.button(
                    "Restore original generated prompt",
                    key="restore_original_prompt_inline_disabled",
                    use_container_width=True,
                    disabled=True,
                )

    if st.session_state.verification_result is not None:
        with tabs[1]:
            result = st.session_state.verification_result

            if result.get("success"):
                parsed = result["data"]
                overall_rating = parsed.get("overall_rating", "needs_revision")
                overall_pass = parsed.get("overall_pass", False)
                alignment_score = parsed.get("alignment_score", "N/A")
                clarity_score = parsed.get("clarity_score", "N/A")
                constraint_score = parsed.get("constraint_score", "N/A")
                accuracy_score = parsed.get("accuracy_score", parsed.get("behavior_score", "N/A"))
                top_issues = parsed.get("top_issues", [])
                recommended_edits = parsed.get("recommended_edits", [])
                behavior_preview = parsed.get("behavior_preview", {})
                behavior_model_used = behavior_preview.get("model_used", "unknown model")

                if overall_rating == "strong" and overall_pass:
                    st.success("Strong overall: the prompt and previewed behavior look well aligned.")
                elif overall_rating == "acceptable":
                    st.info("Acceptable overall: usable, but there are a few areas you may want to tighten.")
                else:
                    st.warning("Needs revision: the previewed behavior suggests this prompt should be tightened before use.")

                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    render_metric_with_info(
                        "Alignment",
                        alignment_score,
                        "How well the prompt and response match the selected mode, intent, and concept.",
                    )
                with c2:
                    render_metric_with_info(
                        "Clarity",
                        clarity_score,
                        "How clear, specific, and unambiguous the prompt is.",
                    )
                with c3:
                    render_metric_with_info(
                        "Constraint adherence",
                        constraint_score,
                        "Whether the prompt sets clear rules and the response follows them.",
                    )
                with c4:
                    render_metric_with_info(
                        "Accuracy",
                        accuracy_score,
                        "How correctly the response answers the question for the chosen interaction mode.",
                    )

                sample_response = behavior_preview.get("sample_response", "")
                render_behavior_preview(sample_response, behavior_model_used)

                st.markdown("<div class='pb-section-label'>Issues identified</div>", unsafe_allow_html=True)
                render_issue_list(top_issues)

                st.markdown("<div class='pb-section-label'>Suggested prompt edits</div>", unsafe_allow_html=True)
                render_recommended_edits(recommended_edits)

                if st.session_state.last_revision_notes:
                    st.markdown("<div class='pb-section-label'>Last applied changes</div>", unsafe_allow_html=True)
                    for note in st.session_state.last_revision_notes:
                        st.caption(f"• {note}")

                auto_apply_clicked = st.button(
                    "Auto-apply prompt edits",
                    key="auto_apply_suggested_edits",
                    type="primary",
                    use_container_width=True,
                    disabled=not recommended_edits,
                )

                if auto_apply_clicked:
                    with st.spinner("Applying suggested prompt edits and re-running verification..."):
                        revision_result = revise_prompt_with_llm(
                            generated_prompt=st.session_state.final_prompt,
                            student_question=question.strip(),
                            interaction_mode=interaction_mode,
                            question_intent=question_intent,
                            general_concept=general_concept,
                            specific_concept=specific_concept,
                            has_supporting_material=uploaded_file is not None,
                            top_issues=top_issues,
                            recommended_edits=recommended_edits,
                            fallback_revised_prompt_draft=parsed.get("revised_prompt_draft", ""),
                        )

                    if revision_result.get("success"):
                        st.session_state.final_prompt = revision_result["revised_prompt"]
                        st.session_state.final_prompt_source = "revised"
                        st.session_state.last_revision_notes = revision_result.get("revision_notes", [])

                        with st.spinner("Re-running verification..."):
                            st.session_state.verification_result = rerun_verification_for_prompt(
                                prompt=st.session_state.final_prompt,
                                question=question,
                                interaction_mode=interaction_mode,
                                question_intent=question_intent,
                                general_concept=general_concept,
                                specific_concept=specific_concept,
                                has_supporting_material=uploaded_file is not None,
                            )
                        st.rerun()
                    else:
                        st.error(revision_result.get("error", "Could not build a revised prompt."))
            else:
                st.error("Verification failed.")
                st.code(result.get("error", "Unknown error"))
