"""
Utilities for constructing guided tutoring prompts and storing UI-facing
selection metadata for the tutoring interface.

Author: Christina Joslin
Date: 4/4/2026
Purpose:
    - Centralizes interaction modes, question intents, supporting materials,
      and concept mappings used by the tutoring app.
    - Builds a single user prompt that combines the student's question,
      instructional mode, concept focus, and optional uploaded materials.
    - Keeps prompt construction logic separate from the Streamlit interface
      so the app remains easier to maintain.
"""

# =========================================================
# Configuration
# =========================================================
INTERACTION_MODES = {
    "Socratic Coach": {
        "short_description": "Thought-Provoking Questions only",
        "ui_explanation": (
            "Engages the student exclusively through questions, prompting independent "
            "reasoning without providing direct answers."
        ),
        "instruction_description": (
            "Ask ONLY ONE guiding, thought-provoking question at a time. "
            "Do not explain concepts directly. If the student is stuck, provide hints "
            "using 'What if?' or similar prompts. If the student is incorrect, ask a "
            "question that helps them recognize the issue on their own."
        ),
        "setting_expectations": [
            "Ask exactly one guiding question at a time.",
            "Do not give a direct explanation or full answer.",
            "Use hints only to help the student reason for themself.",
        ],
    },
    "Guided Tutor": {
        "short_description": "Explanations + Guiding Questions",
        "ui_explanation": (
            "Supports learning through a combination of explanations and guiding "
            "questions, helping the student work through concepts step-by-step."
        ),
        "instruction_description": (
            "Give a brief, high-level explanation, then ask one guiding question. "
            "As the student responds, offer incremental clarifications or hints as "
            "needed, but do NOT solve the problem. ALWAYS check for understanding "
            "before introducing the next step."
        ),
        "setting_expectations": [
            "Start with a short high-level explanation.",
            "Then ask one guiding question.",
            "Support the student step by step without solving the problem for them.",
        ],
    },
    "Expert Explainer": {
        "short_description": "Explanations only",
        "ui_explanation": (
            "Provides clear, structured explanations of concepts in a direct and "
            "instructional manner."
        ),
        "instruction_description": (
            "Provide a clear, structured explanation focused only on what is needed "
            "to answer the question. Keep it concise and scannable."
        ),
        "setting_expectations": [
            "Provide a direct but concise explanation.",
            "Stay tightly focused on the asked concept.",
            "Do not wander into unrelated background or excessive detail.",
        ],
    },
    "Student Simulator": {
        "short_description": "Clarifying Questions Only",
        "ui_explanation": (
            "Acts as a novice learner, prompting the student to explain concepts and "
            "reinforce understanding through teaching."
        ),
        "instruction_description": (
            "Act as a confused high school student first learning the topic. "
            "Ask ONLY ONE clarifying question at a time and occasionally make a simple "
            "mistake to prompt the user to explain. Do NOT provide explanations."
        ),
        "setting_expectations": [
            "Stay in the role of a novice learner.",
            "Ask one clarifying question at a time.",
            "Do not give explanations or polished teaching answers.",
        ],
    },
}

QUESTION_INTENTS = {
    "Clarify a Concept": (
        "Focuses on understanding definitions, intuition, or core ideas."
    ),
    "Walk Through an Example": (
        "Focuses on step-by-step reasoning through a specific case or scenario."
    ),
    "Check My Reasoning": (
        "Focuses on validating or correcting the student’s thought process."
    ),
}

QUESTION_INTENT_EXPECTATIONS = {
    "Clarify a Concept": [
        "Prioritize definitions, intuition, and the key idea behind the concept.",
        "Do not drift into a full worked example unless it directly helps clarify the idea.",
    ],
    "Walk Through an Example": [
        "Anchor the response to the specific example or scenario in the student's question.",
        "Guide the reasoning step by step rather than jumping to the result.",
    ],
    "Check My Reasoning": [
        "Evaluate the student's logic or intermediate thinking.",
        "Point out what is correct, what needs adjustment, and why.",
    ],
}

SUPPORTING_MATERIALS = {
    "Lecture Slides": (
        "Use this if you want the model to prioritize terminology, examples, and "
        "definitions from your course slides."
    ),
    "Personal Notes": (
        "Use this if you want the model to follow your own notes and class-specific wording."
    ),
    "Textbook Excerpts": (
        "Use this if you want the model to ground the response in a textbook passage "
        "or assigned reading."
    ),
}

CONCEPT_MAP = {
    "Object-Oriented Programming (CS 180)": [
        "Variables and Data Types",
        "Control Flow",
        "Methods and Parameters",
        "Recursion",
        "Input and Output",
        "Classes and Objects",
        "Constructors",
        "Instance vs Static",
        "Encapsulation",
        "Inheritance",
        "Polymorphism",
        "Code Tracing",
    ],
     "Foundations of Computer Science (CS 182)": [
        "Propositional Logic",
        "Predicates and Quantifiers",
        "Proof Techniques",
        "Sets",
        "Functions",
        "Relations",
        "Combinatorics",
        "Recurrence Relations",
        "Boolean Algebra",
        "Finite State Machines",
        "Context-Free Languages",
    ],
    "Data Structures and Algorithms (CS 251/CS 253)": [
        "Array",
        "Linked List",
        "Stack",
        "Queue",
        "Hash Table",
        "Tree",
        "Heap",
        "Graph",
        "Recursion",
        "Sorting",
        "Searching",
        "Asymptotic Analysis",
    ],
    "Data Mining & Machine Learning (CS 373)": [
        "Feature Engineering",
        "Data Preprocessing",
        "Train Validation Test Split",
        "Classification",
        "Regression",
        "Decision Trees",
        "Nearest Neighbors",
        "Clustering",
        "Dimensionality Reduction",
        "Neural Networks",
        "Loss Functions",
        "Gradient Descent",
        "Regularization",
        "Overfitting",
        "Model Evaluation Metrics",
    ],
}

# =========================================================
# Prompt Builder
# =========================================================
def build_user_prompt(
    question,
    question_intent,
    general_concept,
    specific_concept,
    interaction_mode,
    interaction_mode_description,
    supplemental_material_type,
    supplemental_material_file_name,
):
    """
    Builds the final user prompt passed into the tutoring model.
    """
    supplemental_material_prompt = ""
    supplemental_material_additional_rule = ""

    if supplemental_material_type and supplemental_material_file_name:
        supplemental_material_prompt = (
            f"Ground your response strictly in the provided {supplemental_material_type} "
            f"(File: {supplemental_material_file_name}). If there is a conflict between "
            f"your internal training data and these materials, prioritize the uploaded "
            f"content to ensure consistency with the student's specific curriculum."
        )
        supplemental_material_additional_rule = (
            "Use the specific vocabulary and pedagogical style found in the uploaded materials."
        )

    mode_expectations = INTERACTION_MODES.get(interaction_mode, {}).get(
        "setting_expectations",
        []
    )
    intent_expectations = QUESTION_INTENT_EXPECTATIONS.get(question_intent, [])

    prompt_lines = [
        "You are a Computer Science professor helping an undergraduate student with this question:",
        "",
        f'"{question}"',
        "",
        f"Intent: {question_intent}",
        f"Focus: {specific_concept} within {general_concept}",
        f"Your Role: {interaction_mode}",
        "",
        "Role instructions",
        interaction_mode_description,
        "",
        "Selected setting expectations",
        f"- Interaction mode expectations for {interaction_mode}:",
    ]

    prompt_lines.extend([f"  - {item}" for item in mode_expectations])
    prompt_lines.append(f"- Question intent expectations for {question_intent}:")
    prompt_lines.extend([f"  - {item}" for item in intent_expectations])
    prompt_lines.extend(
        [
            "- Concept focus expectations:",
            f"  - Stay centered on {specific_concept} within {general_concept}.",
            "  - Address only what is needed for the student's actual question.",
        ]
    )

    if supplemental_material_prompt:
        prompt_lines.extend(["", supplemental_material_prompt])

    prompt_lines.extend(
        [
            "",
            "Rules",
            "",
            "- DO NOT provide direct answers to homework-style questions (for example, MCQs or graded work).",
            "- DO NOT debug, modify, or rewrite code.",
            "- ALWAYS stay focused on the student's exact question AND selected intent.",
            "- Keep the response concise, scannable, and free of unrelated concepts.",
            "",
            "For the rest of this conversation, you MUST continue following these rules, this role, and these setting expectations.",
        ]
    )

    if supplemental_material_additional_rule:
        insert_idx = len(prompt_lines) - 1
        prompt_lines.insert(insert_idx, f"- {supplemental_material_additional_rule}")

    return "\n".join(prompt_lines).strip()