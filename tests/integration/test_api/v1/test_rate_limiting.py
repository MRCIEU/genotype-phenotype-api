from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_rate_limit_single_use():
    response = client.get(
        "v1/internal/rate-limiter",
        headers={"my_header": "hello"}
    )
    assert response.status_code == 200
    assert response.json() == {"success": True}


def test_rate_limit_catches_overuse():
    """
    Limiter set as '3/minute' will error if usage >=3 per minute, so the 3rd request should fail.
    """
    response_1 = client.get(
        "v1/internal/rate-limiter",
        headers={"my_header": "hello"}
    )
    response_2 = client.get(
        "v1/internal/rate-limiter",
        headers={"my_header": "hello"}
    )
    response_3 = client.get(
        "v1/internal/rate-limiter",
        headers={"my_header": "hello"}
    )
    assert response_1.status_code == 200
    assert response_2.status_code == 200
    assert response_3.status_code == 429
    assert response_3.json() == {"error": "Rate limit exceeded: 3 per 1 minute"}


def test_rate_limit_does_not_block_different_users():
    response_user_1 = client.get(
        "v1/internal/rate-limiter",
        headers={"first_user": "headers"}
    )
    response_user_2 = client.get(
        "v1/internal/rate-limiter",
        headers={"second_user": "different headers"}
    )
    response_user_3 = client.get(
        "v1/internal/rate-limiter",
        headers={"third user": "hello"}
    )
    assert response_user_1.status_code == 200
    assert response_user_2.status_code == 200
    assert response_user_3.status_code == 200
