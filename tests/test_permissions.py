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
        db.session.add(DocumentPermission(document_id=ids["document_id"], user_id=ids["viewer_id"], level="read"))
        db.session.commit()
        from app import User, Document
        assert permission_for(db.session.get(Document, ids["document_id"]),
                              db.session.get(User, ids["viewer_id"])) == "read"

def test_revoked_permission_is_denied(app):
    flask_app, ids = app
    with flask_app.app_context():
        permission = DocumentPermission(document_id=ids["document_id"], user_id=ids["viewer_id"], level="read", active=False)
        db.session.add(permission)
        db.session.commit()
        from app import User, Document
        assert permission_for(db.session.get(Document, ids["document_id"]),
                              db.session.get(User, ids["viewer_id"])) is None

def test_expired_permission_is_denied(app):
    flask_app, ids = app
    with flask_app.app_context():
        permission = DocumentPermission(document_id=ids["document_id"], user_id=ids["viewer_id"],
                                        level="read", expires_at=datetime.utcnow() - timedelta(days=1))
        db.session.add(permission)
        db.session.commit()
        from app import User, Document
        assert permission_for(db.session.get(Document, ids["document_id"]),
                              db.session.get(User, ids["viewer_id"])) is None

def test_non_member_is_denied_even_with_permission_record(app):
    flask_app, ids = app
    with flask_app.app_context():
        db.session.add(DocumentPermission(document_id=ids["document_id"], user_id=ids["other_id"], level="read"))
        db.session.commit()
        from app import User, Document
        assert permission_for(db.session.get(Document, ids["document_id"]),
                              db.session.get(User, ids["other_id"])) is None

def test_owner_can_access_own_document(app):
    flask_app, ids = app
    with flask_app.app_context():
        from app import User, Document
        assert permission_for(db.session.get(Document, ids["document_id"]),
                              db.session.get(User, ids["owner_id"])) == "edit"

def test_inactive_owner_is_denied(app):
    flask_app, ids = app

    with flask_app.app_context():
        from app import User, Document

        owner = db.session.get(User, ids["owner_id"])
        doc = db.session.get(Document, ids["document_id"])

        owner.active = False
        db.session.commit()

        assert permission_for(doc, owner) is None
