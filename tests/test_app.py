"""
Tests for the Mergington High School API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    activities.clear()
    activities.update({
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
        },
        "Gym Class": {
            "description": "Physical education and sports activities",
            "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
            "max_participants": 30,
            "participants": ["john@mergington.edu", "olivia@mergington.edu"]
        }
    })


class TestRootEndpoint:
    """Tests for the root endpoint"""

    def test_root_redirects_to_static_index(self, client):
        """Test that the root endpoint redirects to the static index page"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for the GET /activities endpoint"""

    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data

    def test_get_activities_includes_participant_data(self, client):
        """Test that activities include participant information"""
        response = client.get("/activities")
        data = response.json()
        chess_club = data["Chess Club"]
        assert "participants" in chess_club
        assert "michael@mergington.edu" in chess_club["participants"]
        assert "daniel@mergington.edu" in chess_club["participants"]
        assert chess_club["max_participants"] == 12


class TestSignupForActivity:
    """Tests for the POST /activities/{activity_name}/signup endpoint"""

    def test_signup_for_activity_success(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess%20Club/signup?email=new.student@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Signed up" in data["message"]
        assert "new.student@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]

    def test_signup_adds_participant_to_activity(self, client):
        """Test that signup actually adds the participant to the activity"""
        email = "new.student@mergington.edu"
        client.post(f"/activities/Chess%20Club/signup?email={email}")
        
        # Verify participant was added
        response = client.get("/activities")
        data = response.json()
        assert email in data["Chess Club"]["participants"]

    def test_signup_for_nonexistent_activity_returns_404(self, client):
        """Test that signing up for a non-existent activity returns 404"""
        response = client.post(
            "/activities/Nonexistent%20Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_signup_when_already_registered_returns_400(self, client):
        """Test that signing up when already registered returns 400"""
        email = "michael@mergington.edu"  # Already in Chess Club
        response = client.post(f"/activities/Chess%20Club/signup?email={email}")
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_signup_multiple_students_to_same_activity(self, client):
        """Test that multiple students can sign up for the same activity"""
        students = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]
        
        for student in students:
            response = client.post(f"/activities/Programming%20Class/signup?email={student}")
            assert response.status_code == 200
        
        # Verify all students were added
        response = client.get("/activities")
        data = response.json()
        for student in students:
            assert student in data["Programming Class"]["participants"]


class TestUnregisterFromActivity:
    """Tests for the DELETE /activities/{activity_name}/unregister endpoint"""

    def test_unregister_from_activity_success(self, client):
        """Test successful unregister from an activity"""
        email = "michael@mergington.edu"
        response = client.delete(
            f"/activities/Chess%20Club/unregister?email={email}"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]
        assert email in data["message"]
        assert "Chess Club" in data["message"]

    def test_unregister_removes_participant_from_activity(self, client):
        """Test that unregister actually removes the participant from the activity"""
        email = "michael@mergington.edu"
        client.delete(f"/activities/Chess%20Club/unregister?email={email}")
        
        # Verify participant was removed
        response = client.get("/activities")
        data = response.json()
        assert email not in data["Chess Club"]["participants"]

    def test_unregister_from_nonexistent_activity_returns_404(self, client):
        """Test that unregistering from a non-existent activity returns 404"""
        response = client.delete(
            "/activities/Nonexistent%20Club/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_unregister_when_not_registered_returns_400(self, client):
        """Test that unregistering when not registered returns 400"""
        email = "notregistered@mergington.edu"
        response = client.delete(f"/activities/Chess%20Club/unregister?email={email}")
        assert response.status_code == 400
        assert "not registered" in response.json()["detail"]

    def test_signup_and_unregister_flow(self, client):
        """Test the complete flow of signing up and then unregistering"""
        email = "test.student@mergington.edu"
        activity = "Gym Class"
        
        # Sign up
        signup_response = client.post(f"/activities/{activity}/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Verify registration
        activities_response = client.get("/activities")
        assert email in activities_response.json()[activity]["participants"]
        
        # Unregister
        unregister_response = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert unregister_response.status_code == 200
        
        # Verify unregistration
        final_response = client.get("/activities")
        assert email not in final_response.json()[activity]["participants"]


class TestActivityCapacity:
    """Tests for activity participant capacity"""

    def test_activity_has_available_spots(self, client):
        """Test that activities show available spots correctly"""
        response = client.get("/activities")
        data = response.json()
        chess_club = data["Chess Club"]
        current_participants = len(chess_club["participants"])
        max_participants = chess_club["max_participants"]
        assert current_participants < max_participants

    def test_can_fill_activity_to_capacity(self, client):
        """Test that an activity can be filled to capacity"""
        response = client.get("/activities")
        data = response.json()
        chess_club = data["Chess Club"]
        
        current_count = len(chess_club["participants"])
        max_count = chess_club["max_participants"]
        spots_available = max_count - current_count
        
        # Sign up students until capacity
        for i in range(spots_available):
            email = f"student{i}@mergington.edu"
            response = client.post(f"/activities/Chess%20Club/signup?email={email}")
            assert response.status_code == 200
        
        # Verify activity is now at capacity
        response = client.get("/activities")
        data = response.json()
        assert len(data["Chess Club"]["participants"]) == max_count
