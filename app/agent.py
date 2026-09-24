# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os
import re
import time
import urllib.parse
import urllib.request
from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google import genai
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.cloud import firestore, storage
from google.genai import types

from .a2ui_utils import a2ui_callback




# Hardcode project ID string for Firestore client and GCS bucket name as required
FIRESTORE_PROJECT = "qwiklabs-gcp-02-7d4210420334"
GCS_BUCKET_NAME = "fitcoach-ai-assets-qwiklabs-gcp-02-7d4210420334"



def _get_firestore_client():
    return firestore.Client(project=FIRESTORE_PROJECT)


def list_workout_routines(category: str = None, difficulty: str = None) -> str:
    """Lists available workout routines from the Firestore database.

    Args:
        category: Optional filter by workout category (e.g. 'Strength', 'HIIT', 'Full Body').
        difficulty: Optional filter by difficulty level (e.g. 'Beginner', 'Intermediate', 'Advanced').

    Returns:
        JSON string containing matching workout routines.
    """
    db = _get_firestore_client()
    query = db.collection("workout_routines")

    if category:
        query = query.where("category", "==", category)
    if difficulty:
        query = query.where("difficulty", "==", difficulty)

    docs = query.stream()
    routines = []
    for doc in docs:
        data = doc.to_dict()
        routines.append({
            "id": doc.id,
            "name": data.get("name"),
            "category": data.get("category"),
            "difficulty": data.get("difficulty"),
            "duration_minutes": data.get("duration_minutes"),
            "target_muscle_group": data.get("target_muscle_group"),
            "description": data.get("description"),
        })

    if not routines:
        return "No workout routines found matching criteria."
    return json.dumps(routines, indent=2)


def get_workout_routine_details(routine_id: str) -> str:
    """Gets complete details and exercises for a specific workout routine.

    Args:
        routine_id: The ID of the workout routine to retrieve (e.g. 'chest-triceps-hypertrophy').

    Returns:
        JSON string with complete workout details and exercises.
    """
    db = _get_firestore_client()
    doc_ref = db.collection("workout_routines").document(routine_id)
    doc = doc_ref.get()

    if not doc.exists:
        return f"Workout routine with ID '{routine_id}' not found."

    return json.dumps(doc.to_dict(), indent=2)


def add_workout_routine(
    name: str,
    category: str,
    difficulty: str,
    duration_minutes: int,
    target_muscle_group: str,
    description: str,
) -> str:
    """Adds a new workout routine to the Firestore database.

    Args:
        name: Name of the workout routine (e.g. 'Core & Ab Blast').
        category: Category (e.g. 'Strength', 'HIIT', 'Core').
        difficulty: Difficulty level ('Beginner', 'Intermediate', 'Advanced').
        duration_minutes: Estimated duration in minutes.
        target_muscle_group: Targeted muscle groups (e.g. 'Abs, Obliques').
        description: Short overview of the routine.

    Returns:
        Status message with created routine ID.
    """
    db = _get_firestore_client()
    routine_id = name.lower().replace(" ", "-").replace("&", "and")

    routine_data = {
        "id": routine_id,
        "name": name,
        "category": category,
        "difficulty": difficulty,
        "duration_minutes": duration_minutes,
        "target_muscle_group": target_muscle_group,
        "description": description,
        "exercises": []
    }

    db.collection("workout_routines").document(routine_id).set(routine_data)
    return f"Successfully added routine '{name}' with ID '{routine_id}' to Firestore database."


def calculate_fitness_metrics(
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: str = "male",
    activity_level: str = "moderate",
    goal: str = "maintenance",
) -> str:
    """Calculates BMR (Basal Metabolic Rate), TDEE (Total Daily Energy Expenditure),
    target daily calories, macro breakdown (protein, carbs, fats), and target heart rate zones.

    Args:
        weight_kg: Weight in kilograms (e.g. 75.0).
        height_cm: Height in centimeters (e.g. 175.0).
        age: Age in years (e.g. 28).
        gender: 'male' or 'female'.
        activity_level: 'sedentary', 'light', 'moderate', 'active', or 'very_active'.
        goal: 'weight_loss', 'maintenance', or 'muscle_gain'.

    Returns:
        JSON string containing BMR, TDEE, target calories, macro distribution, and heart rate zones.
    """
    if gender.lower() == "female":
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5

    activity_multipliers = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9,
    }
    multiplier = activity_multipliers.get(activity_level.lower(), 1.55)
    tdee = bmr * multiplier

    if goal.lower() == "weight_loss":
        target_calories = tdee - 500
    elif goal.lower() == "muscle_gain":
        target_calories = tdee + 300
    else:
        target_calories = tdee

    protein_g = (target_calories * 0.30) / 4
    carbs_g = (target_calories * 0.40) / 4
    fats_g = (target_calories * 0.30) / 9

    max_hr = 220 - age
    target_hr_zones = {
        "fat_burn": f"{int(max_hr * 0.60)}-{int(max_hr * 0.70)} bpm",
        "cardio": f"{int(max_hr * 0.70)}-{int(max_hr * 0.85)} bpm",
        "peak": f"{int(max_hr * 0.85)}-{int(max_hr * 0.95)} bpm",
    }

    result = {
        "bmr_kcal": round(bmr, 1),
        "tdee_kcal": round(tdee, 1),
        "target_daily_calories_kcal": round(target_calories, 1),
        "macro_breakdown_grams": {
            "protein": round(protein_g, 1),
            "carbs": round(carbs_g, 1),
            "fats": round(fats_g, 1),
        },
        "max_heart_rate_bpm": max_hr,
        "target_heart_rate_zones": target_hr_zones,
    }
    return json.dumps(result, indent=2)


def search_public_exercise_db(category: str = None, name_query: str = None) -> str:
    """Searches the free public WGER Exercise Database for exercise instructions, target muscles, and equipment.

    Args:
        category: Optional category filter (e.g. 'Chest', 'Arms', 'Legs', 'Abs', 'Back', 'Shoulders').
        name_query: Optional search keyword in exercise name (e.g. 'Bench Press', 'Squat', 'Curl').

    Returns:
        JSON string containing matching public exercises, targeted muscles, equipment, and form instructions.
    """
    api_key = os.environ.get("WGER_API_KEY")
    url = "https://wger.de/api/v2/exerciseinfo/?limit=50"
    headers = {"User-Agent": "FitCoachAI/1.0", "Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Token {api_key}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        return f"Error fetching from WGER Public Exercise API: {str(e)}"

    results = []
    for item in data.get("results", []):
        cat_name = item.get("category", {}).get("name", "General") if item.get("category") else "General"
        en_trans = [t for t in item.get("translations", []) if t.get("language") == 2]
        if not en_trans:
            continue
        ex_name = en_trans[0].get("name", "")
        raw_desc = en_trans[0].get("description", "")
        ex_desc = re.sub(r"<[^>]+>", " ", raw_desc).replace("&nbsp;", " ").strip()

        if category and category.lower() not in cat_name.lower():
            continue
        if name_query and name_query.lower() not in ex_name.lower():
            continue

        muscles = [m.get("name_en") or m.get("name") for m in item.get("muscles", [])]
        equipment = [eq.get("name") for eq in item.get("equipment", [])]

        results.append({
            "name": ex_name,
            "category": cat_name,
            "target_muscles": muscles,
            "equipment": equipment,
            "instructions": ex_desc[:400]
        })
        if len(results) >= 5:
            break

    if not results:
        return "No public exercises found matching search criteria."
    return json.dumps(results, indent=2)


def geocode_address(address: str) -> str:
    """Converts a street address or city name into geographic coordinates (latitude, longitude) using Google Geocoding API.

    Args:
        address: Street address, city, or location description (e.g. 'San Francisco, CA').

    Returns:
        JSON string containing formatted address, latitude, and longitude.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not set."

    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={urllib.parse.quote(address)}&key={api_key}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        return f"Geocoding API error: {str(e)}"

    if data.get("status") != "OK" or not data.get("results"):
        return f"Geocoding failed for address: {address}"

    result = data["results"][0]
    loc = result.get("geometry", {}).get("location", {})
    return json.dumps({
        "formatted_address": result.get("formatted_address"),
        "latitude": loc.get("lat"),
        "longitude": loc.get("lng")
    }, indent=2)


def find_nearby_places(latitude: float, longitude: float, place_type: str = "gym", radius_meters: float = 5000.0) -> str:
    """Finds nearby places of a specific type (e.g. 'gym', 'fitness_center', 'park') using Google Places API (New).

    Args:
        latitude: Latitude of the center location.
        longitude: Longitude of the center location.
        place_type: Type of place to search for (e.g. 'gym', 'fitness_center', 'park').
        radius_meters: Search radius in meters (default 5000.0).

    Returns:
        JSON string containing key fields (name, address, location) for nearby places.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not set."

    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location"
    }
    body = {
        "includedTypes": [place_type],
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "radius": radius_meters
            }
        },
        "maxResultCount": 5
    }

    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        return f"Places API error: {str(e)}"

    places_list = []
    for place in data.get("places", []):
        display = place.get("displayName", {})
        name = display.get("text") if isinstance(display, dict) else str(display)
        places_list.append({
            "name": name,
            "address": place.get("formattedAddress"),
            "location": place.get("location")
        })

    if not places_list:
        return "No nearby places found."
    return json.dumps(places_list, indent=2)


async def generate_fitness_image(prompt: str, tool_context: ToolContext = None) -> str:
    """Generates an image for a fitness item, meal, or exercise using gemini-3.1-flash-lite-image in the global region.

    Saves the image bytes to session artifacts via tool_context and uploads directly to public Cloud Storage.

    Args:
        prompt: Description of the fitness meal, exercise, or routine item to generate an image for.
        tool_context: ADK ToolContext injected automatically by the framework.

    Returns:
        Public HTTPS URL of the uploaded image (https://storage.googleapis.com/<bucket>/images/<filename>).
    """
    client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT, location="global")
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=f"High quality fitness photo: {prompt}",
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        ),
    )

    img_bytes = None
    if response.candidates and response.candidates[0].content:
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                img_bytes = part.inline_data.data
                break

    if not img_bytes:
        return "Error: Failed to generate image bytes."

    filename = f"fitness_{int(time.time())}.jpg"

    if tool_context:
        part_artifact = types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
        await tool_context.save_artifact(filename=filename, artifact=part_artifact)

    storage_client = storage.Client(project=FIRESTORE_PROJECT)
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(f"images/{filename}")
    blob.upload_from_string(img_bytes, content_type="image/jpeg")

    public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/images/{filename}"
    return public_url



async def generate_exercise_video(prompt: str, tool_context: ToolContext = None) -> str:
    """Generates a short video clip for a workout exercise or form demonstration using gemini-omni-flash-preview in global region.

    Saves the video bytes to session artifacts via tool_context and uploads directly to public Cloud Storage.

    Args:
        prompt: Description of the exercise or movement to generate a video for (e.g. 'proper form for pushups').
        tool_context: ADK ToolContext injected automatically by the framework.

    Returns:
        Public HTTPS URL of the uploaded video (https://storage.googleapis.com/<bucket>/videos/<filename>).
    """
    client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT, location="global")
    interaction = client.interactions.create(
        model="gemini-omni-flash-preview",
        input=f"Generate a short video clip demonstrating: {prompt}",
        generation_config={
            "response_modalities": ["VIDEO"],
        },
    )

    video_bytes = None
    mime_type = "video/mp4"

    if hasattr(interaction, "output_video") and interaction.output_video:
        if hasattr(interaction.output_video, "data") and interaction.output_video.data:
            video_bytes = interaction.output_video.data
            if hasattr(interaction.output_video, "mime_type") and interaction.output_video.mime_type:
                mime_type = interaction.output_video.mime_type

    if not video_bytes:
        return "Error: Failed to generate video bytes."

    filename = f"exercise_{int(time.time())}.mp4"

    if tool_context:
        part_artifact = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
        await tool_context.save_artifact(filename=filename, artifact=part_artifact)

    storage_client = storage.Client(project=FIRESTORE_PROJECT)
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(f"videos/{filename}")
    blob.upload_from_string(video_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/videos/{filename}"
    return public_url


def _get_code_executor():
    """Reads deployment metadata and returns an AgentEngineSandboxCodeExecutor instance.

    Uses existing sandbox_resource_name if available; otherwise creates a new sandbox
    from remote_agent_runtime_id (Agent Engine ID).
    """
    metadata_path = os.path.join(os.path.dirname(__file__), "..", "deployment_metadata.json")
    if os.path.exists(metadata_path):
        with open(metadata_path) as f:
            meta = json.load(f)
        sandbox_id = meta.get("sandbox_resource_name")
        runtime_id = meta.get("remote_agent_runtime_id")
        if sandbox_id:
            return AgentEngineSandboxCodeExecutor(sandbox_resource_name=sandbox_id)
        elif runtime_id:
            return AgentEngineSandboxCodeExecutor(agent_engine_resource_name=runtime_id)
    return None


# Memory Bank ID (reusing deployed Reasoning Engine ID)
MEMORY_BANK_ID = "7952998501145640960"


def memory_bank_service_builder():
    """Returns VertexAiMemoryBankService instance for Agent Runtime deployment."""
    return VertexAiMemoryBankService(
        project=FIRESTORE_PROJECT,
        location="us-east1",
        agent_engine_id=MEMORY_BANK_ID,
    )


async def generate_memories_callback(callback_context: CallbackContext):
    """WRITE: After each turn, send the session to Memory Bank for durable memory extraction."""
    await callback_context.add_session_to_memory()
    return None


a2ui_schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_instruction = a2ui_schema_manager.generate_system_prompt(
    role_description=(
        "You are FitCoach AI, an intelligent fitness assistant. You help users discover, "
        "customize, and manage workout routines stored in a Firestore database. "
        "You remember user preferences, goals, and restrictions across sessions. "
        "You can calculate personalized fitness metrics (BMR, TDEE, macros), search the "
        "public WGER exercise database, geocode locations, find nearby gyms/fitness centers, "
        "generate high-quality fitness/nutrition images, generate exercise video demonstrations, "
        "and safely execute Python code in a sandbox."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=a2ui_instruction,
    code_executor=_get_code_executor(),
    tools=[
        PreloadMemoryTool(),
        list_workout_routines,
        get_workout_routine_details,
        add_workout_routine,
        calculate_fitness_metrics,
        search_public_exercise_db,
        geocode_address,
        find_nearby_places,
        generate_fitness_image,
        generate_exercise_video,
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)







