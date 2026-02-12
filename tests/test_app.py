"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    # Store original state
    from src.app import activities
    original_activities = {
        name: {"participants": list(activity["participants"])}
        for name, activity in activities.items()
    }
    
    yield
    
    # Reset to original state
    for name, data in original_activities.items():
        activities[name]["participants"] = data["participants"]


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirect(self, client):
        """Test that root redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivitiesEndpoint:
    """Tests for the GET /activities endpoint"""
    
    def test_get_activities(self, client, reset_activities):
        """Test getting all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert "Tennis Club" in data
        assert "Basketball Team" in data
        assert "Art Club" in data
    
    def test_activities_structure(self, client, reset_activities):
        """Test that activities have correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        activity = data["Tennis Club"]
        assert "description" in activity
        assert "schedule" in activity
        assert "max_participants" in activity
        assert "participants" in activity
        assert isinstance(activity["participants"], list)
    
    def test_initial_participants(self, client, reset_activities):
        """Test that initial participants are loaded"""
        response = client.get("/activities")
        data = response.json()
        
        assert "alex@mergington.edu" in data["Tennis Club"]["participants"]
        assert "james@mergington.edu" in data["Basketball Team"]["participants"]


class TestSignupEndpoint:
    """Tests for the POST /activities/{activity_name}/signup endpoint"""
    
    def test_valid_signup(self, client, reset_activities):
        """Test successful signup"""
        response = client.post(
            "/activities/Tennis Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
    
    def test_duplicate_signup(self, client, reset_activities):
        """Test that duplicate signup is rejected"""
        # First signup should succeed
        response1 = client.post(
            "/activities/Tennis Club/signup?email=test@mergington.edu"
        )
        assert response1.status_code == 200
        
        # Second signup with same email should fail
        response2 = client.post(
            "/activities/Tennis Club/signup?email=test@mergington.edu"
        )
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"]
    
    def test_signup_nonexistent_activity(self, client, reset_activities):
        """Test signup for non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_signup_adds_participant(self, client, reset_activities):
        """Test that signup actually adds participant to activity"""
        client.post(
            "/activities/Chess Club/signup?email=newplayer@mergington.edu"
        )
        
        response = client.get("/activities")
        data = response.json()
        assert "newplayer@mergington.edu" in data["Chess Club"]["participants"]


class TestDeleteParticipantEndpoint:
    """Tests for the DELETE /activities/{activity_name}/participants/{email} endpoint"""
    
    def test_valid_delete(self, client, reset_activities):
        """Test successful participant deletion"""
        # First add a participant
        client.post(
            "/activities/Debate Team/signup?email=todelete@mergington.edu"
        )
        
        # Then delete them
        response = client.delete(
            "/activities/Debate Team/participants/todelete@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "todelete@mergington.edu" in data["message"]
    
    def test_delete_nonexistent_activity(self, client, reset_activities):
        """Test delete from non-existent activity"""
        response = client.delete(
            "/activities/Nonexistent Club/participants/test@mergington.edu"
        )
        assert response.status_code == 404
    
    def test_delete_nonexistent_participant(self, client, reset_activities):
        """Test delete non-existent participant from activity"""
        response = client.delete(
            "/activities/Tennis Club/participants/notasignup@mergington.edu"
        )
        assert response.status_code == 404
        assert "Student not found" in response.json()["detail"]
    
    def test_delete_removes_participant(self, client, reset_activities):
        """Test that delete actually removes participant"""
        email = "removal@mergington.edu"
        
        # Add participant
        client.post(f"/activities/Art Club/signup?email={email}")
        
        # Verify they're added
        response = client.get("/activities")
        assert email in response.json()["Art Club"]["participants"]
        
        # Delete participant
        client.delete(f"/activities/Art Club/participants/{email}")
        
        # Verify they're removed
        response = client.get("/activities")
        assert email not in response.json()["Art Club"]["participants"]
    
    def test_delete_existing_participant(self, client, reset_activities):
        """Test deleting an initially existing participant"""
        response = client.delete(
            "/activities/Theater Club/participants/ava@mergington.edu"
        )
        assert response.status_code == 200
        
        # Verify removal
        response = client.get("/activities")
        assert "ava@mergington.edu" not in response.json()["Theater Club"]["participants"]


class TestIntegrationScenarios:
    """Integration tests for complex scenarios"""
    
    def test_full_signup_and_delete_flow(self, client, reset_activities):
        """Test complete flow: signup, verify, delete, verify removal"""
        email = "integrationtest@mergington.edu"
        activity = "Programming Class"
        
        # Signup
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 200
        
        # Verify signup
        response = client.get("/activities")
        assert email in response.json()[activity]["participants"]
        
        # Delete
        response = client.delete(f"/activities/{activity}/participants/{email}")
        assert response.status_code == 200
        
        # Verify deletion
        response = client.get("/activities")
        assert email not in response.json()[activity]["participants"]
    
    def test_multiple_participants_signup(self, client, reset_activities):
        """Test multiple participants signing up for same activity"""
        activity = "Robotics Club"
        emails = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu",
        ]
        
        # Sign up multiple students
        for email in emails:
            response = client.post(f"/activities/{activity}/signup?email={email}")
            assert response.status_code == 200
        
        # Verify all are registered
        response = client.get("/activities")
        participants = response.json()[activity]["participants"]
        for email in emails:
            assert email in participants


class TestURLEncoding:
    """Tests for proper URL encoding handling"""
    
    def test_signup_with_special_characters_in_email(self, client, reset_activities):
        """Test signup with URL-encoded email"""
        email = "test+special@mergington.edu"
        response = client.post(
            f"/activities/Gym%20Class/signup?email={email}"
        )
        assert response.status_code == 200
    
    def test_delete_with_activity_spaces(self, client, reset_activities):
        """Test delete with activity name containing spaces"""
        client.post("/activities/Gym%20Class/signup?email=space@mergington.edu")
        
        response = client.delete(
            "/activities/Gym%20Class/participants/space@mergington.edu"
        )
        assert response.status_code == 200
