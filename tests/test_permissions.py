
from datetime import datetime, timedelta
from app import db, DocumentPermission, Membership, permission_for


def test_viewer_without_permission_is_denied(app):
    flask_app, ids = app
    with flask_app.app_context():
        from app import User, Document
        viewer = db.session.get(User, ids["viewer_id"])
        doc = db.session.get(Document, ids["document_id"])
        assert permission_for(doc, viewer) is None


def test_read_permission_is_allowed(app):
    flask_app, ids = app
    with flask_app.app_context():
        db.session.add(DocumentPermission(
            document_id=ids["document_id"],
            user_id=ids["viewer_id"],
            level="read"
        ))
        db.session.commit()
        from app import User, Document
        assert permission_for(
            db.session.get(Document, ids["document_id"]),
            db.session.get(User, ids["viewer_id"])
        ) == "read"


def test_revoked_permission_is_denied(app):
    flask_app, ids = app
    with flask_app.app_context():
        permission = DocumentPermission(
            document_id=ids["document_id"],
            user_id=ids["viewer_id"],
            level="read",
            active=False
        )
        db.session.add(permission)
        db.session.commit()
        from app import User, Document
        assert permission_for(
            db.session.get(Document, ids["document_id"]),
            db.session.get(User, ids["viewer_id"])
        ) is None


def test_expired_permission_is_denied(app):
    flask_app, ids = app
    with flask_app.app_context():
        permission = DocumentPermission(
            document_id=ids["document_id"],
            user_id=ids["viewer_id"],
            level="read",
            expires_at=datetime.utcnow() - timedelta(days=1)
        )
        db.session.add(permission)
        db.session.commit()
        from app import User, Document
        assert permission_for(
            db.session.get(Document, ids["document_id"]),
            db.session.get(User, ids["viewer_id"])
        ) is None


def test_non_member_is_denied_even_with_permission_record(app):
    flask_app, ids = app
    with flask_app.app_context():
        db.session.add(DocumentPermission(
            document_id=ids["document_id"],
            user_id=ids["other_id"],
            level="read"
        ))
        db.session.commit()
        from app import User, Document
        assert permission_for(
            db.session.get(Document, ids["document_id"]),
            db.session.get(User, ids["other_id"])
        ) is None


def test_owner_can_access_own_document(app):
    flask_app, ids = app
    with flask_app.app_context():
        from app import User, Document
        assert permission_for(
            db.session.get(Document, ids["document_id"]),
            db.session.get(User, ids["owner_id"])
        ) == "edit"


def test_inactive_owner_is_denied(app):
    flask_app, ids = app
    with flask_app.app_context():
        from app import User, Document

        owner = db.session.get(User, ids["owner_id"])
        doc = db.session.get(Document, ids["document_id"])

        owner.active = False
        db.session.commit()

        assert permission_for(doc, owner) is None


def test_viewer_cannot_grant_document_permission(client, app):
    flask_app, ids = app

    response = client.post("/login", data={
        "email": "viewer@test.local",
        "password": "viewer-password-123"
    })
    assert response.status_code == 302

    response = client.post(
        f"/documents/{ids['document_id']}/permissions",
        data={
            "user_id": ids["other_id"],
            "level": "read",
            "days": "0"
        }
    )
    assert response.status_code == 403


def test_other_owner_cannot_grant_document_permission(client, app):
    flask_app, ids = app

    response = client.post("/login", data={
        "email": "other@test.local",
        "password": "other-password-123"
    })
    assert response.status_code == 302

    response = client.post(
        f"/documents/{ids['document_id']}/permissions",
        data={
            "user_id": ids["viewer_id"],
            "level": "read",
            "days": "0"
        }
    )
    assert response.status_code == 403


def test_other_owner_cannot_revoke_document_permission(client, app):
    flask_app, ids = app

    client.post("/login", data={
        "email": "other@test.local",
        "password": "other-password-123"
    })

    response = client.post(
        f"/documents/{ids['document_id']}/revoke/{ids['viewer_id']}"
    )
    assert response.status_code == 403


def test_other_owner_cannot_approve_access_request(client, app):
    flask_app, ids = app
    from app import AccessRequest

    with flask_app.app_context():
        access_request = AccessRequest(
            document_id=ids["document_id"],
            requester_id=ids["viewer_id"],
            requested_level="read",
            reason="Testing authorization"
        )
        db.session.add(access_request)
        db.session.commit()
        request_id = access_request.id

    client.post("/login", data={
        "email": "other@test.local",
        "password": "other-password-123"
    })

    response = client.post(f"/requests/{request_id}/approve")
    assert response.status_code == 403


def test_other_owner_cannot_reject_access_request(client, app):
    flask_app, ids = app
    from app import AccessRequest

    with flask_app.app_context():
        access_request = AccessRequest(
            document_id=ids["document_id"],
            requester_id=ids["viewer_id"],
            requested_level="read",
            reason="Testing rejection authorization"
        )
        db.session.add(access_request)
        db.session.commit()
        request_id = access_request.id

    client.post("/login", data={
        "email": "other@test.local",
        "password": "other-password-123"
    })

    response = client.post(f"/requests/{request_id}/reject")
    assert response.status_code == 403


def test_password_is_stored_as_hash_not_plaintext(app):
    flask_app, ids = app

    with flask_app.app_context():
        from app import User

        viewer = db.session.get(User, ids["viewer_id"])

        assert viewer.password_hash != "viewer-password-123"
        assert viewer.check_password("viewer-password-123")
        assert not viewer.check_password("wrong-password")


def test_audit_tampering_is_detected(client, app):
    flask_app, ids = app
    from app import AuditEvent, User

    # Create a test admin account
    with flask_app.app_context():
        admin = User(
            name="Test Admin",
            email="admin-test@test.local",
            role="admin"
        )
        admin.set_password("admin-password-123")
        db.session.add(admin)
        db.session.commit()

    # Log in and create a login audit event
    response = client.post("/login", data={
        "email": "admin-test@test.local",
        "password": "admin-password-123"
    })
    assert response.status_code == 302

    # Identify the latest audit event
    with flask_app.app_context():
        event = AuditEvent.query.order_by(
            AuditEvent.id.desc()
        ).first()
        event_id = event.id

    # Original audit chain should be consistent
    response = client.get("/admin/audit/verify")
    assert response.status_code == 200
    assert b"chain links are consistent" in response.data.lower()

    # Change the event without updating its hash
    with flask_app.app_context():
        event = db.session.get(AuditEvent, event_id)
        event.details = "Modified audit details"
        db.session.commit()

    # Verification must detect the tampering
    response = client.get("/admin/audit/verify")
    assert response.status_code == 200
    assert b"chain verification failed" in response.data.lower()


def test_unsupported_file_extension_is_rejected(client, app):
    from io import BytesIO
    from app import Document

    flask_app, data = app

    client.post("/login", data={
        "email": "owner@test.local",
        "password": "owner-password-123"
    })

    with flask_app.app_context():
        before_count = Document.query.count()

    response = client.post(
        f"/projects/{data['project_id']}/upload",
        data={
            "file": (BytesIO(b"not a real executable"), "malware.exe")
        },
        content_type="multipart/form-data"
    )

    assert response.status_code == 302

    with flask_app.app_context():
        after_count = Document.query.count()
        assert after_count == before_count

def test_uploaded_filename_is_sanitized(client, app):
    from io import BytesIO
    from app import Document
    from werkzeug.utils import secure_filename

    flask_app, data = app

    client.post("/login", data={
        "email": "owner@test.local",
        "password": "owner-password-123"
    })

    response = client.post(
        f"/projects/{data['project_id']}/upload",
        data={
            "file": (BytesIO(b"safe test content"), "../../unsafe name.txt")
        },
        content_type="multipart/form-data"
    )

    assert response.status_code == 302

    with flask_app.app_context():
        doc = Document.query.filter_by(
            project_id=data["project_id"],
            original_name=secure_filename("../../unsafe name.txt")
        ).first()

        assert doc is not None
        assert doc.stored_name != "../../unsafe name.txt"
        assert len(doc.stored_name) == 32

def test_oversized_file_upload_is_rejected(client, app):
    from io import BytesIO
    from app import Document, MAX_FILE_SIZE

    flask_app, data = app

    client.post("/login", data={
        "email": "owner@test.local",
        "password": "owner-password-123"
    })

    with flask_app.app_context():
        before_count = Document.query.count()

    response = client.post(
        f"/projects/{data['project_id']}/upload",
        data={
            "file": (
                BytesIO(b"A" * (MAX_FILE_SIZE + 1)),
                "large_file.txt"
            )
        },
        content_type="multipart/form-data"
    )

    assert response.status_code == 413
    assert b"larger than 10 MB" in response.data

    with flask_app.app_context():
        after_count = Document.query.count()
        assert after_count == before_count

def test_viewer_cannot_upload_document(client, app):
    from io import BytesIO
    from app import Document

    flask_app, data = app

    client.post("/login", data={
        "email": "viewer@test.local",
        "password": "viewer-password-123"
    })

    with flask_app.app_context():
        before_count = Document.query.count()

    response = client.post(
        f"/projects/{data['project_id']}/upload",
        data={
            "file": (BytesIO(b"unauthorized upload"), "test.txt")
        },
        content_type="multipart/form-data"
    )

    assert response.status_code == 403

    with flask_app.app_context():
        after_count = Document.query.count()
        assert after_count == before_count