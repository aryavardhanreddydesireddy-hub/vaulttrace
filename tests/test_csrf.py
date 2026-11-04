def test_post_without_csrf_token_is_rejected(app, client):
    flask_app, data = app

    original_setting = flask_app.config["WTF_CSRF_ENABLED"]
    flask_app.config["WTF_CSRF_ENABLED"] = True

    try:
        # Simulate an authenticated owner session.
        with client.session_transaction() as session:
            session["_user_id"] = str(data["owner_id"])
            session["_fresh"] = True

        # Submit a POST request without a CSRF token.
        response = client.post("/logout")

        assert response.status_code == 400

    finally:
        flask_app.config["WTF_CSRF_ENABLED"] = original_setting