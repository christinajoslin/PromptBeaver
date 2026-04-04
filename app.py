import json
import streamlit as st

from prompt_builder import (
    INTERACTION_MODES,
    QUESTION_INTENTS,
    SUPPORTING_MATERIALS,
    CONCEPT_MAP,
    build_user_prompt,
)
from verifier import verify_prompt_with_llm

st.set_page_config(page_title="PromptBeaver", page_icon="🦫", layout="wide")

st.title("🦫 PromptBeaver")
st.write(
    "PromptBeaver helps students build a single ready-to-paste prompt for conceptual "
    "computer science questions."
)

# -----------------------------
# Styling
# -----------------------------
st.markdown(
    """
    <style>
    .pb-card {
        padding: 1rem 1.2rem;
        border: 1px solid #d9d9d9;
        border-radius: 12px;
        margin-bottom: 1rem;
        background-color: #fafafa;
    }
    .pb-section-title {
        font-size: 1.1rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
    }
    .pb-muted {
        color: #666666;
        font-size: 0.95rem;
        margin-bottom: 0.75rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Session state
# -----------------------------
if "final_prompt" not in st.session_state:
    st.session_state.final_prompt = None

if "verification_result" not in st.session_state:
    st.session_state.verification_result = None

left_col, right_col = st.columns([1.2, 1])

with left_col:
    st.markdown('<div class="pb-card">', unsafe_allow_html=True)
    st.markdown('<div class="pb-section-title">1) Interaction Mode</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="pb-muted">Choose the pedagogical style you want the model to use.</div>',
        unsafe_allow_html=True,
    )

    interaction_mode = st.selectbox(
        "Select an interaction mode",
        options=list(INTERACTION_MODES.keys()),
        index=None,
        placeholder="Choose an interaction mode...",
        key="interaction_mode",
    )

    if interaction_mode is None:
        st.info(
            "Default guidance text: Select how you want the AI to interact with the student. "
            "For example, you can choose a questioning-based role, an explanation-based role, "
            "or a simulated learner role."
        )
    else:
        st.markdown(
            f"**{interaction_mode}** — {INTERACTION_MODES[interaction_mode]['short_description']}"
        )
        st.write(INTERACTION_MODES[interaction_mode]["ui_explanation"])
        st.caption(
            f"Prompt behavior: {INTERACTION_MODES[interaction_mode]['instruction_description']}"
        )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="pb-card">', unsafe_allow_html=True)
    st.markdown('<div class="pb-section-title">2) Concept Selection</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="pb-muted">Choose the broad course area and the most dominant specific concept.</div>',
        unsafe_allow_html=True,
    )

    general_concept = st.selectbox(
        "Select a general concept",
        options=list(CONCEPT_MAP.keys()),
        index=None,
        placeholder="Choose a general concept...",
        key="general_concept",
    )

    if general_concept is None:
        st.info(
            "Default guidance text: First choose a broad course area such as CS 180, CS 182, "
            "CS 251/253, or CS 373. Then choose the specific concept that best matches your question."
        )

    specific_concept = None
    if general_concept is not None:
        specific_concept = st.selectbox(
            "Select a specific concept",
            options=CONCEPT_MAP[general_concept],
            index=None,
            placeholder="Choose a specific concept...",
            key="specific_concept",
        )
    else:
        st.selectbox(
            "Select a specific concept",
            options=[],
            index=None,
            placeholder="Choose a general concept first...",
            disabled=True,
            key="specific_concept_disabled",
        )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="pb-card">', unsafe_allow_html=True)
    st.markdown('<div class="pb-section-title">3) Question Intent</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="pb-muted">Choose the main purpose of the student’s question.</div>',
        unsafe_allow_html=True,
    )

    question_intent = st.selectbox(
        "Select a question intent",
        options=list(QUESTION_INTENTS.keys()),
        index=None,
        placeholder="Choose a question intent...",
        key="question_intent",
    )

    if question_intent is None:
        st.info(
            "Default guidance text: Select whether the student wants help understanding a concept, "
            "walking through an example, or checking their reasoning."
        )
    else:
        st.write(QUESTION_INTENTS[question_intent])
    st.markdown("</div>", unsafe_allow_html=True)

with right_col:
    st.markdown('<div class="pb-card">', unsafe_allow_html=True)
    st.markdown('<div class="pb-section-title">4) Student Question</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="pb-muted">Enter the conceptual question you want the model to respond to.</div>',
        unsafe_allow_html=True,
    )

    question = st.text_area(
        "Enter the student question (200 words max)",
        height=220,
        placeholder="Type the conceptual question here...",
        help="This becomes the main question embedded in the final prompt.",
    )

    word_count = len(question.split()) if question.strip() else 0
    st.caption(f"Current word count: {word_count}/200")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="pb-card">', unsafe_allow_html=True)
    st.markdown('<div class="pb-section-title">5) Supporting Materials</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="pb-muted">Optional: add course materials so the prompt prioritizes course-accurate terminology, definitions, and examples.</div>',
        unsafe_allow_html=True,
    )

    supporting_material_type = st.selectbox(
        "Select a supporting material type",
        options=list(SUPPORTING_MATERIALS.keys()),
        index=None,
        placeholder="Choose a supporting material type...",
        key="supporting_material_type",
    )

    if supporting_material_type is None:
        st.info(
            "Default guidance text: You may optionally add lecture slides, personal notes, or "
            "textbook excerpts. If you do, the generated prompt will tell the model to prioritize "
            "the terminology, definitions, and examples from that document."
        )
    else:
        st.write(SUPPORTING_MATERIALS[supporting_material_type])

    uploaded_file = st.file_uploader(
        "Upload an optional supporting file",
        type=["pdf", "txt", "md", "docx"],
    )
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("### Generate Prompt")

generate_clicked = st.button("Generate Prompt", use_container_width=True)

if generate_clicked:
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
    if word_count > 200:
        errors.append("The student question must be 200 words or fewer.")
    if supporting_material_type is not None and uploaded_file is None:
        errors.append("You selected a supporting material type but did not upload a file.")
    if supporting_material_type is None and uploaded_file is not None:
        errors.append("You uploaded a file but did not select a supporting material type.")

    if errors:
        st.session_state.final_prompt = None
        st.session_state.verification_result = None
        for error in errors:
            st.error(error)
    else:
        final_prompt = build_user_prompt(
            question=question.strip(),
            question_intent=question_intent,
            general_concept=general_concept,
            specific_concept=specific_concept,
            interaction_mode=interaction_mode,
            interaction_mode_description=INTERACTION_MODES[interaction_mode]["instruction_description"],
            supplemental_material_type=supporting_material_type if uploaded_file else None,
            supplemental_material_file_name=uploaded_file.name if uploaded_file else None,
        )

        st.session_state.final_prompt = final_prompt
        st.session_state.verification_result = None

if st.session_state.final_prompt:
    st.success("Your PromptBeaver prompt is ready.")
    st.markdown("### Final User Prompt")
    st.code(st.session_state.final_prompt, language="text")
    st.text_area("Copy/paste version", st.session_state.final_prompt, height=420)

    st.download_button(
        label="Download Prompt as TXT",
        data=st.session_state.final_prompt,
        file_name="promptbeaver_prompt.txt",
        mime="text/plain",
    )

    st.markdown("### Optional LLM Verification")
    run_verification = st.checkbox(
        "Enable LLM verification for this prompt",
        value=False,
        help="Runs an optional quality review using llama4:latest.",
    )

    with st.expander("Verification settings"):
        genai_base_url = st.text_input(
            "GenAI Studio base URL",
            value="",
            placeholder="https://your-genai-endpoint.example.com/...",
        )
        genai_api_key = st.text_input(
            "GenAI Studio API key / bearer token",
            value="",
            type="password",
        )
        model_name = st.text_input(
            "Model name",
            value="llama4:latest",
        )

    if run_verification:
        verify_clicked = st.button("Verify Prompt Quality", use_container_width=True)

        if verify_clicked:
            if not genai_base_url.strip():
                st.error("Please provide the GenAI Studio base URL.")
            elif not genai_api_key.strip():
                st.error("Please provide the GenAI Studio API key / bearer token.")
            else:
                with st.spinner("Running LLM verification..."):
                    result = verify_prompt_with_llm(
                        generated_prompt=st.session_state.final_prompt,
                        interaction_mode=interaction_mode,
                        question_intent=question_intent,
                        general_concept=general_concept,
                        specific_concept=specific_concept,
                        has_supporting_material=uploaded_file is not None,
                        base_url=genai_base_url.strip(),
                        api_key=genai_api_key.strip(),
                        model=model_name.strip(),
                    )
                    st.session_state.verification_result = result

if st.session_state.verification_result:
    result = st.session_state.verification_result

    st.markdown("### Verification Results")

    if result.get("success"):
        parsed = result["data"]

        overall_pass = parsed.get("overall_pass", False)
        alignment_score = parsed.get("alignment_score", "N/A")
        clarity_score = parsed.get("clarity_score", "N/A")
        constraint_score = parsed.get("constraint_score", "N/A")
        issues = parsed.get("issues", [])
        suggested_revision = parsed.get("suggested_revision", "")

        if overall_pass:
            st.success("The verifier marked this prompt as passing overall.")
        else:
            st.warning("The verifier found issues with the prompt.")

        c1, c2, c3 = st.columns(3)
        c1.metric("Alignment", alignment_score)
        c2.metric("Clarity", clarity_score)
        c3.metric("Constraint Adherence", constraint_score)

        st.markdown("**Issues identified**")
        if issues:
            for issue in issues:
                st.write(f"- {issue}")
        else:
            st.write("No issues reported.")

        st.markdown("**Suggested revision**")
        st.write(suggested_revision if suggested_revision else "No revision suggested.")
    else:
        st.error("Verification failed.")
        st.code(result.get("error", "Unknown error"))