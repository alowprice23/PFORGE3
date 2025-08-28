from fastapi.testclient import TestClient
import pytest

# We need to make sure the app object is created before running tests.
# A common pattern is to have a factory function or to import the app
# instance directly. We'll import it directly.
from pforge.server.app import app

@pytest.fixture(scope="module")
def test_client():
    """
    Creates a FastAPI TestClient instance for making simulated requests
    to the server. This fixture has module scope, so the client is
    created once per test file.
    """
    with TestClient(app) as client:
        yield client

def test_healthz_endpoint(test_client: TestClient):
    """
    Tests the /api/healthz endpoint to ensure the server is running and
    responsive.
    """
    response = test_client.get("/api/healthz")

    # Assert that the request was successful
    assert response.status_code == 200

    # Assert that the response body is as expected
    json_response = response.json()
    assert json_response["status"] == "ok"

def test_metrics_endpoint(test_client: TestClient):
    """
    Tests that the /api/metrics endpoint is available and returns a
    Prometheus-formatted response.
    """
    from pforge.metrics.metrics_collector import PFORGE_EFFICIENCY
    PFORGE_EFFICIENCY.set(0.75)
    response = test_client.get("/api/metrics")

    assert response.status_code == 200
    # Check for the correct content type for Prometheus
    assert "text/plain" in response.headers["content-type"]
    # Check that it contains our custom metric and its value
    assert "pforge_efficiency" in response.text
    assert "0.75" in response.text
