"""
MongoDB database configuration and setup for Mergington High School API
"""

from pymongo import MongoClient
from argon2 import PasswordHasher

# Lazy-loaded database connections
_client = None
_db = None
activities_collection = None
teachers_collection = None

def hash_password(password):
    """Hash password using Argon2"""
    ph = PasswordHasher()
    return ph.hash(password)

def _init_db():
    """Initialize database collections - called lazily on first use"""
    global _client, _db, activities_collection, teachers_collection
    
    if _client is None:
        try:
            _client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=2000)
            _db = _client['mergington_high']
            activities_collection = _db['activities']
            teachers_collection = _db['teachers']
            # Test the connection
            _client.admin.command('ping')
        except Exception as e:
            print(f"Warning: Could not connect to MongoDB: {e}")
            print("The application will use in-memory storage instead")
            # Fall back to in-memory storage
            _setup_mock_db()
    
    return activities_collection, teachers_collection

def _setup_mock_db():
    """Set up mock in-memory database for development/testing"""
    global activities_collection, teachers_collection
    
    class MockCollection:
        def __init__(self):
            self.data = {}
        
        def find_one(self, query):
            for key, doc in self.data.items():
                if "_id" in query and doc.get("_id") == query["_id"]:
                    return doc
                for k, v in query.items():
                    if doc.get(k) != v:
                        break
                else:
                    return doc
            return None
        
        def find(self, query=None):
            if query is None:
                query = {}
            results = []
            for doc in self.data.values():
                matches = True
                for k, v in query.items():
                    if k == "schedule_details.days" and "$in" in v:
                        if "schedule_details" not in doc or doc["schedule_details"].get("days") is None:
                            matches = False
                            break
                        if not any(day in doc["schedule_details"]["days"] for day in v["$in"]):
                            matches = False
                            break
                    elif k == "schedule_details.start_time" and "$gte" in v:
                        if "schedule_details" not in doc or doc["schedule_details"].get("start_time") is None:
                            matches = False
                            break
                        if doc["schedule_details"]["start_time"] < v["$gte"]:
                            matches = False
                            break
                    elif k == "schedule_details.end_time" and "$lte" in v:
                        if "schedule_details" not in doc or doc["schedule_details"].get("end_time") is None:
                            matches = False
                            break
                        if doc["schedule_details"]["end_time"] > v["$lte"]:
                            matches = False
                            break
                    elif doc.get(k) != v:
                        matches = False
                        break
                if matches:
                    results.append(doc)
            return results
        
        def count_documents(self, query):
            return len(self.find(query))
        
        def insert_one(self, doc):
            self.data[doc.get("_id")] = doc
        
        def update_one(self, query, update):
            class Result:
                def __init__(self, modified):
                    self.modified_count = modified
            
            for key, doc in self.data.items():
                if doc.get("_id") == query.get("_id"):
                    if "$push" in update:
                        for k, v in update["$push"].items():
                            if k not in doc:
                                doc[k] = []
                            doc[k].append(v)
                    elif "$pull" in update:
                        for k, v in update["$pull"].items():
                            if k in doc and isinstance(doc[k], list):
                                doc[k] = [x for x in doc[k] if x != v]
                    return Result(1)
            return Result(0)
        
        def aggregate(self, pipeline):
            # Simplified aggregation for the days query
            if len(pipeline) >= 2 and pipeline[0].get("$unwind") and pipeline[1].get("$group"):
                days = set()
                for doc in self.data.values():
                    if "schedule_details" in doc and "days" in doc["schedule_details"]:
                        for day in doc["schedule_details"]["days"]:
                            days.add(day)
                return [{"_id": day} for day in sorted(days)]
            return []
    
    activities_collection = MockCollection()
    teachers_collection = MockCollection()

def init_database():
    """Initialize database if empty"""
    global activities_collection, teachers_collection
    
    # Ensure database is initialized
    if activities_collection is None or teachers_collection is None:
        _init_db()
    
    # Initialize activities if empty
    if activities_collection.count_documents({}) == 0:
        for name, details in _get_initial_activities().items():
            activities_collection.insert_one({"_id": name, **details})
            
    # Initialize teacher accounts if empty
    if teachers_collection.count_documents({}) == 0:
        for teacher in _get_initial_teachers():
            teachers_collection.insert_one({"_id": teacher["username"], **teacher})

def _get_initial_activities():
    return {
        "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Mondays and Fridays, 3:15 PM - 4:45 PM",
        "schedule_details": {
            "days": ["Monday", "Friday"],
            "start_time": "15:15",
            "end_time": "16:45"
        },
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 7:00 AM - 8:00 AM",
        "schedule_details": {
            "days": ["Tuesday", "Thursday"],
            "start_time": "07:00",
            "end_time": "08:00"
        },
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Morning Fitness": {
        "description": "Early morning physical training and exercises",
        "schedule": "Mondays, Wednesdays, Fridays, 6:30 AM - 7:45 AM",
        "schedule_details": {
            "days": ["Monday", "Wednesday", "Friday"],
            "start_time": "06:30",
            "end_time": "07:45"
        },
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 5:30 PM",
        "schedule_details": {
            "days": ["Tuesday", "Thursday"],
            "start_time": "15:30",
            "end_time": "17:30"
        },
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and compete in basketball tournaments",
        "schedule": "Wednesdays and Fridays, 3:15 PM - 5:00 PM",
        "schedule_details": {
            "days": ["Wednesday", "Friday"],
            "start_time": "15:15",
            "end_time": "17:00"
        },
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore various art techniques and create masterpieces",
        "schedule": "Thursdays, 3:15 PM - 5:00 PM",
        "schedule_details": {
            "days": ["Thursday"],
            "start_time": "15:15",
            "end_time": "17:00"
        },
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 3:30 PM - 5:30 PM",
        "schedule_details": {
            "days": ["Monday", "Wednesday"],
            "start_time": "15:30",
            "end_time": "17:30"
        },
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and prepare for math competitions",
        "schedule": "Tuesdays, 7:15 AM - 8:00 AM",
        "schedule_details": {
            "days": ["Tuesday"],
            "start_time": "07:15",
            "end_time": "08:00"
        },
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 3:30 PM - 5:30 PM",
        "schedule_details": {
            "days": ["Friday"],
            "start_time": "15:30",
            "end_time": "17:30"
        },
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "amelia@mergington.edu"]
    },
    "Weekend Robotics Workshop": {
        "description": "Build and program robots in our state-of-the-art workshop",
        "schedule": "Saturdays, 10:00 AM - 2:00 PM",
        "schedule_details": {
            "days": ["Saturday"],
            "start_time": "10:00",
            "end_time": "14:00"
        },
        "max_participants": 15,
        "participants": ["ethan@mergington.edu", "oliver@mergington.edu"]
    },
    "Science Olympiad": {
        "description": "Weekend science competition preparation for regional and state events",
        "schedule": "Saturdays, 1:00 PM - 4:00 PM",
        "schedule_details": {
            "days": ["Saturday"],
            "start_time": "13:00",
            "end_time": "16:00"
        },
        "max_participants": 18,
        "participants": ["isabella@mergington.edu", "lucas@mergington.edu"]
    },
    "Sunday Chess Tournament": {
        "description": "Weekly tournament for serious chess players with rankings",
        "schedule": "Sundays, 2:00 PM - 5:00 PM",
        "schedule_details": {
            "days": ["Sunday"],
            "start_time": "14:00",
            "end_time": "17:00"
        },
        "max_participants": 16,
        "participants": ["william@mergington.edu", "jacob@mergington.edu"]
    }
}

def _get_initial_teachers():
    """Get initial teacher data - passwords hashed on demand"""
    return [
        {
            "username": "mrodriguez",
            "display_name": "Ms. Rodriguez",
            "password": hash_password("art123"),
            "role": "teacher"
         },
        {
            "username": "mchen",
            "display_name": "Mr. Chen",
            "password": hash_password("chess456"),
            "role": "teacher"
        },
        {
            "username": "principal",
            "display_name": "Principal Martinez",
            "password": hash_password("admin789"),
            "role": "admin"
        }
    ]
