"""
High School Management System API

A FastAPI application that uses MongoDB for persistence. Activities are stored
in a MongoDB collection and seeded on first run. Endpoints are kept compatible
with the previous REST surface so the existing static UI continues to work.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path
from typing import Dict, Any
import pymongo


app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent, "static")), name="static")

# MongoDB setup
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "academy_db")
client = pymongo.MongoClient(MONGO_URL)
db = client[DB_NAME]
activities_col = db.get_collection("activities")


# Initial seed data (keeps the same content as the original in-memory store)
INITIAL_ACTIVITIES = [
    {
        "name": "Chess Club",
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    {
        "name": "Programming Class",
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    {
        "name": "Gym Class",
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    {
        "name": "Soccer Team",
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    {
        "name": "Basketball Team",
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    {
        "name": "Art Club",
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    {
        "name": "Drama Club",
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    {
        "name": "Math Club",
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    {
        "name": "Debate Team",
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
]


def seed_activities_if_empty() -> None:
    if activities_col.count_documents({}) == 0:
        activities_col.insert_many(INITIAL_ACTIVITIES)


@app.on_event("startup")
def on_startup():
    # Ensure DB is seeded on first run
    try:
        seed_activities_if_empty()
    except Exception:
        # In dev environments Mongo may not be available yet; swallow and let
        # requests return errors until DB is ready.
        pass


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities() -> Dict[str, Any]:
    docs = activities_col.find({})
    result = {}
    for d in docs:
        name = d.get("name")
        if not name:
            continue
        result[name] = {
            "description": d.get("description", ""),
            "schedule": d.get("schedule", ""),
            "max_participants": d.get("max_participants", 0),
            "participants": d.get("participants", []),
        }
    return result


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    # Validate activity exists
    activity = activities_col.find_one({"name": activity_name})
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    participants = activity.get("participants", [])
    if email in participants:
        raise HTTPException(status_code=400, detail="Student is already signed up")

    max_p = activity.get("max_participants", 0)
    if len(participants) >= max_p:
        raise HTTPException(status_code=400, detail="No spots available")

    activities_col.update_one({"name": activity_name}, {"$push": {"participants": email}})
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    activity = activities_col.find_one({"name": activity_name})
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    participants = activity.get("participants", [])
    if email not in participants:
        raise HTTPException(status_code=400, detail="Student is not signed up for this activity")

    activities_col.update_one({"name": activity_name}, {"$pull": {"participants": email}})
    return {"message": f"Unregistered {email} from {activity_name}"}

