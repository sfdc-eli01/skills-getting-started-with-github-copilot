import pytest
from fastapi.testclient import TestClient
from app import app, activities
import copy

# Create TestClient instance
client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities to original state after each test"""
    original_activities = copy.deepcopy(activities)
    yield
    activities.clear()
    activities.update(original_activities)


def test_root_redirect():
    """Test root endpoint redirects to static index"""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_get_activities():
    """Test getting all activities returns correct structure"""
    response = client.get("/activities")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert len(data) >= 9  # At least the pre-loaded activities

    # Check structure of one activity
    chess_club = data.get("Chess Club")
    assert chess_club is not None
    assert "description" in chess_club
    assert "schedule" in chess_club
    assert "max_participants" in chess_club
    assert "participants" in chess_club
    assert isinstance(chess_club["participants"], list)


def test_signup_success():
    """Test successful signup adds participant"""
    email = "newstudent@mergington.edu"
    activity = "Chess Club"

    # Initial count
    initial_response = client.get("/activities")
    initial_participants = len(initial_response.json()[activity]["participants"])

    # Signup
    response = client.post(f"/activities/{activity}/signup?email={email}")
    assert response.status_code == 200
    assert f"Signed up {email} for {activity}" in response.json()["message"]

    # Verify added
    final_response = client.get("/activities")
    final_participants = final_response.json()[activity]["participants"]
    assert email in final_participants
    assert len(final_participants) == initial_participants + 1


def test_signup_duplicate():
    """Test cannot signup twice for same activity"""
    email = "dupstudent@mergington.edu"
    activity = "Programming Class"

    # First signup
    response1 = client.post(f"/activities/{activity}/signup?email={email}")
    assert response1.status_code == 200

    # Second signup should fail
    response2 = client.post(f"/activities/{activity}/signup?email={email}")
    assert response2.status_code == 400
    assert "already signed up" in response2.json()["detail"]


def test_signup_invalid_activity():
    """Test signup with non-existent activity"""
    response = client.post("/activities/NonExistent/signup?email=test@mergington.edu")
    assert response.status_code == 404
    assert "Activity not found" in response.json()["detail"]


def test_signup_missing_email():
    """Test signup without email parameter"""
    response = client.post("/activities/Chess%20Club/signup")
    # FastAPI should handle missing query param
    assert response.status_code == 422  # Validation error


def test_unregister_success():
    """Test successful unregistration removes participant"""
    email = "removeme@mergington.edu"
    activity = "Gym Class"

    # First signup
    client.post(f"/activities/{activity}/signup?email={email}")

    # Initial count
    initial_response = client.get("/activities")
    initial_participants = len(initial_response.json()[activity]["participants"])

    # Unregister
    response = client.delete(f"/activities/{activity}/unregister?email={email}")
    assert response.status_code == 200
    assert f"Unregistered {email} from {activity}" in response.json()["message"]

    # Verify removed
    final_response = client.get("/activities")
    final_participants = final_response.json()[activity]["participants"]
    assert email not in final_participants
    assert len(final_participants) == initial_participants - 1


def test_unregister_not_signed_up():
    """Test cannot unregister if not signed up"""
    email = "notsigned@mergington.edu"
    activity = "Tennis Club"

    response = client.delete(f"/activities/{activity}/unregister?email={email}")
    assert response.status_code == 400
    assert "not signed up" in response.json()["detail"]


def test_unregister_invalid_activity():
    """Test unregister with non-existent activity"""
    response = client.delete("/activities/NonExistent/unregister?email=test@mergington.edu")
    assert response.status_code == 404
    assert "Activity not found" in response.json()["detail"]


def test_unregister_missing_email():
    """Test unregister without email parameter"""
    response = client.delete("/activities/Chess%20Club/unregister")
    assert response.status_code == 422  # Validation error


def test_full_workflow():
    """Test complete signup -> unregister -> signup cycle"""
    email = "workflow@mergington.edu"
    activity = "Art Studio"

    # Signup
    response1 = client.post(f"/activities/{activity}/signup?email={email}")
    assert response1.status_code == 200

    # Verify signed up
    response2 = client.get("/activities")
    assert email in response2.json()[activity]["participants"]

    # Unregister
    response3 = client.delete(f"/activities/{activity}/unregister?email={email}")
    assert response3.status_code == 200

    # Verify unregistered
    response4 = client.get("/activities")
    assert email not in response4.json()[activity]["participants"]

    # Can signup again
    response5 = client.post(f"/activities/{activity}/signup?email={email}")
    assert response5.status_code == 200