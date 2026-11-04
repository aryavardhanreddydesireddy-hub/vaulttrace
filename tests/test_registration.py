from app import User


def test_public_registration_always_creates_viewer(app, client):
    response = client.post(
        "/register",
        data={
            "name": "Test User",
            "email": "newuser@test.local",
            "password": "strong-password-123",
            "role": "owner"
        },
        follow_redirects=True
    )

    assert response.status_code == 200

    with app[0].app_context():
        user = User.query.filter_by(
            email="newuser@test.local"
        ).first()

        assert user is not None
        assert user.role == "viewer"