import uuid

import pytest
import requests
from jsonschema import validate

from tests.api.schemas import UPDATE_LIST_SCHEMA, UPDATE_SCHEMA


def new_payload(**overrides):
    payload = {
        "title": f"API test update {uuid.uuid4().hex[:6]}",
        "jurisdiction": "EU",
        "category": "Guidance",
        "published_date": "2026-11-20",
        "summary": "Created by API test",
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def created_update(api_url, auth_headers):
    """Create a record before the test, delete it after (test cleans up its own data)."""
    response = requests.post(f"{api_url}/updates", json=new_payload(), headers=auth_headers)
    assert response.status_code == 201
    update = response.json()
    yield update
    requests.delete(f"{api_url}/updates/{update['id']}", headers=auth_headers)


# ---------------------------------------------------------------- positive tests
def test_health_check(api_url):
    response = requests.get(f"{api_url}/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_updates_matches_schema(api_url):
    response = requests.get(f"{api_url}/updates")
    assert response.status_code == 200
    validate(instance=response.json(), schema=UPDATE_LIST_SCHEMA)


def test_create_update_returns_201_and_saved_values(api_url, auth_headers):
    payload = new_payload(jurisdiction="SG", category="Rule change")
    response = requests.post(f"{api_url}/updates", json=payload, headers=auth_headers)

    assert response.status_code == 201
    body = response.json()
    validate(instance=body, schema=UPDATE_SCHEMA)
    assert body["title"] == payload["title"]
    assert body["jurisdiction"] == "SG"
    assert body["category"] == "Rule change"

    requests.delete(f"{api_url}/updates/{body['id']}", headers=auth_headers)  # cleanup


def test_get_update_by_id(api_url, created_update):
    response = requests.get(f"{api_url}/updates/{created_update['id']}")
    assert response.status_code == 200
    assert response.json() == created_update


def test_response_time_under_500ms(api_url):
    response = requests.get(f"{api_url}/updates")
    assert response.elapsed.total_seconds() < 0.5


# ---------------------------------------------------------------- negative tests
def test_create_without_api_key_returns_401(api_url):
    response = requests.post(f"{api_url}/updates", json=new_payload())
    assert response.status_code == 401


def test_create_with_wrong_api_key_returns_401(api_url):
    response = requests.post(f"{api_url}/updates", json=new_payload(), headers={"X-API-Key": "wrong"})
    assert response.status_code == 401


@pytest.mark.parametrize(
    "field, bad_value",
    [
        ("jurisdiction", "XX"),
        ("category", "Notice"),
        ("title", "ab"),
        ("published_date", "20-11-2026"),
        ("summary", ""),
    ],
)
def test_create_with_invalid_field_returns_422(api_url, auth_headers, field, bad_value):
    response = requests.post(
        f"{api_url}/updates", json=new_payload(**{field: bad_value}), headers=auth_headers
    )
    assert response.status_code == 422, f"{field}={bad_value!r} should be rejected"


def test_delete_update_then_get_returns_404(api_url, auth_headers):
    created = requests.post(f"{api_url}/updates", json=new_payload(), headers=auth_headers).json()

    delete_response = requests.delete(f"{api_url}/updates/{created['id']}", headers=auth_headers)
    assert delete_response.status_code == 204

    get_response = requests.get(f"{api_url}/updates/{created['id']}")
    assert get_response.status_code == 404


def test_get_nonexistent_update_returns_404(api_url):
    response = requests.get(f"{api_url}/updates/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Update not found"


def test_filter_by_jurisdiction_returns_only_that_jurisdiction(api_url):
    response = requests.get(f"{api_url}/updates", params={"jurisdiction": "UK"})

    assert response.status_code == 200
    updates = response.json()
    assert len(updates) > 0, "Expected at least one UK update"
    assert all(u["jurisdiction"] == "UK" for u in updates), \
        f"Non-UK items found: {[u for u in updates if u['jurisdiction'] != 'UK']}"