"""
Script for generating descriptive statistics and SUS scores from survey results. 

Author: Joseph Hsin 
Date: 4/24/2026
"""
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("results.csv")
print(df.head())


major_map = {
    "1": "Computer Science",
    "2": "Data Science",
    "3": "Artificial Intelligence",
    "4": "Other"
}

year_map = {
    1: "1st year",
    2: "2nd year",
    3: "3rd year",
    4: "4th year",
    5: "5th+ year"
}

exp_map = {
    1: "Novice",
    2: "Beginner",
    3: "Intermediate",
    4: "Advanced"
}

feature_map = {
    "1": "Build a Prompt",
    "2": "Analyze My Prompt"
}

df['year_label'] = df['year'].map(year_map)
df['genai_label'] = df['genai_experience'].map(exp_map)


majors_split = df['majors'].dropna().astype(str).str.split(',')
majors_exploded = majors_split.explode().str.strip()
majors_labeled = majors_exploded.map(major_map)

majors_counts = majors_labeled.value_counts()
majors_percent = majors_labeled.value_counts(normalize=True) * 100

majors_summary = pd.DataFrame({
    'count': majors_counts,
    'percentage': majors_percent
})

print("\n=== Majors ===")
print(majors_summary)


features_split = df['features_used'].dropna().astype(str).str.split(',')
features_exploded = features_split.explode().str.strip()
features_labeled = features_exploded.map(feature_map)

features_summary = pd.DataFrame({
    'count': features_labeled.value_counts(),
    'percentage': features_labeled.value_counts(normalize=True) * 100
})

print("\n=== Features Used ===")
print(features_summary)


def summarize(col):
    counts = col.value_counts(dropna=False)
    perc = col.value_counts(normalize=True, dropna=False) * 100
    return pd.DataFrame({'count': counts, 'percentage': perc})

print("\n=== Year ===")
print(summarize(df['year_label']))

print("\n=== GenAI Experience ===")
print(summarize(df['genai_label']))

counts = df['year_label'].value_counts().sort_index()

plt.figure()
counts.plot(kind='bar')

plt.title("Distribution of Student Year")
plt.xlabel("Year")
plt.ylabel("Count")

plt.xticks(rotation=45)
plt.tight_layout()
plt.show()


plt.figure()
majors_counts.plot(kind='pie', autopct='%1.1f%%')

plt.title("Distribution of Majors")
plt.ylabel("")
plt.show()

sus_cols = [f'sus_{i}' for i in range(1, 11)]

def compute_sus(row):
    score = 0
    for i in range(1, 11):
        val = row[f'sus_{i}']
        if i % 2 == 1:
            score += (val - 1)
        else:
            score += (5 - val)
    return score * 2.5

df['sus_score'] = df.apply(compute_sus, axis=1)

print(df[['sus_score']].head())


print(df[['sus_score']])


avg_sus = df['sus_score'].mean()
print("Average SUS score:", avg_sus)


scores = df['sus_score']

plt.figure()
plt.boxplot(scores, labels=["SUS Scores"])

plt.title("Box and Whisker Plot of SUS Scores")
plt.ylabel("Score")

plt.grid(True)

plt.show()


