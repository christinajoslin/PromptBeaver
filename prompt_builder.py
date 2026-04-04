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
    "Programming and Problem Solving (CS 180)": [
        "Control Flow",
        "Functions",
        "Recursion",
        "Debugging",
        "Code Tracing",
        "Object-Oriented Programming",
        "Classes and Objects",
        "Input and Output",
    ],
    "Foundations of Computer Science (CS 182)": [
        "Propositional Logic",
        "Predicates and Quantifiers",
        "Proof Techniques",
        "Sets and Functions",
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
        "Graph Algorithms",
        "Recursion",
        "Sorting",
        "Searching",
        "Asymptotic Analysis",
    ],
    "Data Mining & Machine Learning (CS 373)": [
        "Classification",
        "Regression",
        "Clustering",
        "Neural Networks",
        "Overfitting and Underfitting",
        "Model Evaluation Methods",
        "Optimization",
    ],
}


def build_user_prompt(
    question: str,
    question_intent: str,
    general_concept: str,
    specific_concept: str,
    interaction_mode: str,
    interaction_mode_description: str,
    supplemental_material_type: str | None = None,
    supplemental_material_file_name: str | None = None,
) -> str:
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

    prompt_lines = [
        "You are a Computer Science professor helping an undergraduate student with this question:",
        "",
        f"\"{question}\"",
        "",
        f"Intent: {question_intent}",
        f"Focus: {specific_concept} within {general_concept}",
        f"Your Role: {interaction_mode}",
        "",
        interaction_mode_description,
    ]

    if supplemental_material_prompt:
        prompt_lines.extend(["", supplemental_material_prompt])

    prompt_lines.extend(
        [
            "",
            "Rules",
            "",
            "- DO NOT provide direct answers to homework-style questions (e.g., MCQs).",
            "- DO NOT debug, modify, or rewrite code.",
            "- ALWAYS stay focused on the student’s exact question AND intent (do NOT introduce unrelated concepts).",
            "",
            "For the rest of this conversation, you MUST continue following these rules AND this role. "
            "Keep responses concise and easily scannable for an undergraduate student "
            "(NO long blocks of text or exhaustive lists).",
        ]
    )

    if supplemental_material_additional_rule:
        insert_idx = len(prompt_lines) - 1
        prompt_lines.insert(insert_idx, f"- {supplemental_material_additional_rule}")

    return "\n".join(prompt_lines).strip()