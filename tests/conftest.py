import os
import tempfile
import pytest
from app import app as flask_app, db, User, Project, Membership, Document, DocumentPermission

@pytest.fixture()
def app():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    upload_dir = tempfile.mkdtemp()
    flask_app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SQLALCHEMY_DATABASE_URI="sqlite:///" + db_path,
        UPLOAD_FOLDER=upload_dir,
        SECRET_KEY="test-secret"
    )
    with flask_app.app_context():
        db.drop_all()
        db.create_all()
        owner = User(name="Owner", email="owner@test.local", role="owner")
        owner.set_password("owner-password-123")
        viewer = User(name="Viewer", email="viewer@test.local", role="viewer")
        viewer.set_password("viewer-password-123")
        other = User(name="Other", email="other@test.local", role="viewer")
        other.set_password("other-password-123")
        db.session.add_all([owner, viewer, other])
        db.session.commit()
        project = Project(name="Test Project", owner_id=owner.id)
        db.session.add(project)
        db.session.commit()
        db.session.add(Membership(project_id=project.id, user_id=viewer.id, active=True))
        doc = Document(project_id=project.id, owner_id=owner.id, original_name="sample.txt",
                       stored_name="sample-stored", file_size=4)
        db.session.add(doc)
        db.session.commit()
        with open(os.path.join(upload_dir, "sample-stored"), "wb") as f:
            f.write(b"test")
        app_data = {"owner_id": owner.id, "viewer_id": viewer.id, "other_id": other.id,
                    "project_id": project.id, "document_id": doc.id}
    yield flask_app, app_data
    with flask_app.app_context():
        db.session.remove()
        db.drop_all()
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture()
def client(app):
    flask_app, _ = app
    return flask_app.test_client()
