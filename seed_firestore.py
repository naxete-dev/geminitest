"""Seed script to populate Firestore with sample workout routines for FitCoach AI."""

from google.cloud import firestore

# Hardcode project ID as string - DO NOT use GOOGLE_CLOUD_PROJECT or google.auth.default()
FIRESTORE_PROJECT = "qwiklabs-gcp-02-7d4210420334"

INITIAL_ROUTINES = [
    {
        "id": "chest-triceps-hypertrophy",
        "name": "Chest & Triceps Hypertrophy",
        "category": "Strength",
        "difficulty": "Intermediate",
        "duration_minutes": 45,
        "target_muscle_group": "Chest, Triceps",
        "description": "High-volume chest and triceps workout focused on muscle growth.",
        "exercises": [
            {"name": "Barbell Bench Press", "sets": 4, "reps": "8-10"},
            {"name": "Incline Dumbbell Press", "sets": 3, "reps": "10-12"},
            {"name": "Cable Chest Flyes", "sets": 3, "reps": "12-15"},
            {"name": "Triceps Pushdowns", "sets": 4, "reps": "12-15"},
            {"name": "Skull Crushers", "sets": 3, "reps": "10-12"}
        ]
    },
    {
        "id": "full-body-hiit-burn",
        "name": "Full Body HIIT Conditioning",
        "category": "HIIT",
        "difficulty": "Beginner",
        "duration_minutes": 30,
        "target_muscle_group": "Full Body",
        "description": "Fast-paced bodyweight and dumbbell circuit designed to burn calories.",
        "exercises": [
            {"name": "Jumping Jacks", "sets": 4, "reps": "45 sec"},
            {"name": "Dumbbell Goblet Squats", "sets": 4, "reps": "15"},
            {"name": "Push-Ups", "sets": 4, "reps": "12"},
            {"name": "Mountain Climbers", "sets": 4, "reps": "45 sec"},
            {"name": "Dumbbell Renegade Rows", "sets": 3, "reps": "10 per side"}
        ]
    },
    {
        "id": "back-biceps-builder",
        "name": "Back & Biceps Power Builder",
        "category": "Strength",
        "difficulty": "Advanced",
        "duration_minutes": 50,
        "target_muscle_group": "Back, Biceps",
        "description": "Heavy pulling session for back thickness, width, and arm strength.",
        "exercises": [
            {"name": "Conventional Deadlifts", "sets": 4, "reps": "5"},
            {"name": "Lat Pulldowns / Pull-Ups", "sets": 4, "reps": "8-10"},
            {"name": "Bent-Over Barbell Rows", "sets": 3, "reps": "8-10"},
            {"name": "Face Pulls", "sets": 4, "reps": "15"},
            {"name": "Barbell Bicep Curls", "sets": 3, "reps": "10-12"}
        ]
    },
    {
        "id": "leg-day-strength",
        "name": "Lower Body Strength & Core",
        "category": "Strength",
        "difficulty": "Intermediate",
        "duration_minutes": 50,
        "target_muscle_group": "Legs, Core",
        "description": "Comprehensive lower body routine targeting quads, hamstrings, and glutes.",
        "exercises": [
            {"name": "Barbell Back Squats", "sets": 4, "reps": "6-8"},
            {"name": "Romanian Deadlifts", "sets": 3, "reps": "8-10"},
            {"name": "Walking Dumbbell Lunges", "sets": 3, "reps": "12 per leg"},
            {"name": "Calf Raises", "sets": 4, "reps": "15"},
            {"name": "Hanging Leg Raises", "sets": 3, "reps": "15"}
        ]
    }
]


def seed_database():
    print(f"Connecting to Firestore for project: {FIRESTORE_PROJECT}...")
    db = firestore.Client(project=FIRESTORE_PROJECT)
    collection_ref = db.collection("workout_routines")

    for routine in INITIAL_ROUTINES:
        doc_id = routine["id"]
        doc_ref = collection_ref.document(doc_id)
        doc_ref.set(routine)
        print(f"✅ Seeded routine: {routine['name']} (id: {doc_id})")

    print("\n🎉 Firestore database successfully seeded with initial workout routines!")


if __name__ == "__main__":
    seed_database()
