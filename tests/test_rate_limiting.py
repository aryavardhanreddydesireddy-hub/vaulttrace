from app import limiter


def test_login_rate_limit_blocks_sixth_attempt(client, app):
    flask_app, ids = app

    # Clear previous rate-limit counters for a clean test.
    limiter.storage.reset()

    # Enable rate limiting for this test.
    limiter.enabled = True

    try:
        responses = []

        # Send six login requests from the same test client.
        for _ in range(6):
            response = client.post(
                "/login",
                data={
                    "email": "wrong@test.local",
                    "password": "wrong-password"
                }
            )
            responses.append(response.status_code)

        # The first five requests should not be rate-limited.
        assert all(
            status != 429 for status in responses[:5]
        )

        # The sixth request should be rate-limited.
        assert responses[5] == 429

    finally:
        # Keep ordinary tests unaffected.
        limiter.enabled = False