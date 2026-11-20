
from tests.helpers import auth

ALICE = auth("alice", "thtax")
BOB = auth("bob", "other")


def test_other_tenant_cannot_read_research_history(client):
    """NV4: Tenant khac khong duoc doc lich su nghien cuu."""

    # Alice tao ho so
    response = client.post(
        "/api/v1/matters",
        json={
            "title": "NV4 - Regression Test",
            "client_name": "Cong ty ABC",
            "tax_types": ["VAT"],
            "tax_period": "2026",
        },
        headers=ALICE,
    )

    assert response.status_code == 201
    matter_id = response.json()["id"]

    # Alice luu lich su nghien cuu
    response = client.post(
        f"/api/v1/matters/{matter_id}/history",
        json={
            "question": "Thue GTGT la gi?",
            "tax_type": "VAT",
            "answer": "Noi dung nghien cuu noi bo",
        },
        headers=ALICE,
    )

    assert response.status_code == 201

    # Alice doc duoc lich su
    response = client.get(
        f"/api/v1/matters/{matter_id}/history",
        headers=ALICE,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1

    # Bob thu doc lich su cua Alice
    response = client.get(
        f"/api/v1/matters/{matter_id}/history",
        headers=BOB,
    )

    assert response.status_code == 404
    assert "Noi dung nghien cuu noi bo" not in response.text

def test_unauthenticated_user_cannot_read_research_history(client):
    """NV4: Nguoi dung chua dang nhap khong duoc doc lich su."""

    # Alice tao ho so
    response = client.post(
        "/api/v1/matters",
        json={
            "title": "NV4 - Authentication Test",
            "client_name": "Cong ty ABC",
            "tax_types": ["VAT"],
            "tax_period": "2026",
        },
        headers=ALICE,
    )

    assert response.status_code == 201
    matter_id = response.json()["id"]

    # Nguoi khong co token thu doc lich su
    response = client.get(
        f"/api/v1/matters/{matter_id}/history"
    )

    assert response.status_code == 401
