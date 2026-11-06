import os
import uuid
import hashlib
import io
import zipfile
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import Flask, render_template, redirect, url_for, flash, request, send_file, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.engine import URL
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "txt", "csv", "xlsx", "png", "jpg", "jpeg"}
MAX_FILE_SIZE = 10 * 1024 * 1024

app = Flask(__name__)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://"
)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")

if not app.config["SECRET_KEY"]:
    raise RuntimeError("SECRET_KEY environment variable is required.")

database_path = os.path.join(BASE_DIR, "instance", "vaulttrace.db")

os.makedirs(os.path.dirname(database_path), exist_ok=True)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    os.environ.get("DATABASE_URL")
    or URL.create("sqlite", database=database_path)
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE
app.config["UPLOAD_FOLDER"] = os.environ.get("UPLOAD_FOLDER", os.path.join(BASE_DIR, "instance", "vault"))

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
csrf = CSRFProtect(app)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="viewer")
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text, default="")
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    owner = db.relationship("User", foreign_keys=[owner_id])


class Membership(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (db.UniqueConstraint("project_id", "user_id"),)
    project = db.relationship("Project")
    user = db.relationship("User")


class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(80), unique=True, nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    project = db.relationship("Project")
    owner = db.relationship("User")


class DocumentPermission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("document.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    level = db.Column(db.String(10), nullable=False)  # read or edit
    expires_at = db.Column(db.DateTime, nullable=True)
    active = db.Column(db.Boolean, default=True, nullable=False)
    __table_args__ = (db.UniqueConstraint("document_id", "user_id"),)
    document = db.relationship("Document")
    user = db.relationship("User")


class AccessRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("document.id"), nullable=False)
    requester_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    requested_level = db.Column(db.String(10), nullable=False)
    reason = db.Column(db.String(500), default="")
    status = db.Column(db.String(20), default="pending", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    document = db.relationship("Document")
    requester = db.relationship("User")


class AuditEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    action = db.Column(db.String(80), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey("document.id"), nullable=True)
    details = db.Column(db.String(500), default="")
    outcome = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    timestamp = db.Column(db.String(40), nullable=False)
    previous_hash = db.Column(db.String(64), nullable=False)
    event_hash = db.Column(db.String(64), nullable=False)
    actor = db.relationship("User")
    document = db.relationship("Document")


@login_manager.user_loader
def load_user(user_id):
    user = db.session.get(User, int(user_id))

    if user and user.active:
        return user

    return None


def audit(action, outcome="success", document_id=None, details=""):
    previous = AuditEvent.query.order_by(AuditEvent.id.desc()).first()
    previous_hash = previous.event_hash if previous else "0" * 64

    timestamp = datetime.now(timezone.utc).isoformat()
    actor_id = current_user.id if current_user.is_authenticated else None

    safe_details = details[:500]

    payload = (
        f"{actor_id if actor_id is not None else 'anonymous'}|"
        f"{action}|{outcome}|{document_id}|{safe_details}|"
        f"{timestamp}|{previous_hash}"
    )

    event_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    db.session.add(AuditEvent(
        actor_id=actor_id,
        action=action,
        outcome=outcome,
        document_id=document_id,
        details=safe_details,
        timestamp=timestamp,
        previous_hash=previous_hash,
        event_hash=event_hash
    ))

    db.session.commit()


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles or not current_user.active:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def is_project_owner(project):
    return current_user.is_authenticated and (current_user.role == "admin" or project.owner_id == current_user.id)


def active_membership(project_id, user_id):
    return Membership.query.filter_by(project_id=project_id, user_id=user_id, active=True).first()


def permission_for(document, user):
    if not user.active:
        return None

    if document.owner_id == user.id or user.role == "admin":
        return "edit"

    if not active_membership(document.project_id, user.id):
        return None

    permission = DocumentPermission.query.filter_by(
        document_id=document.id, user_id=user.id, active=True
    ).first()

    if not permission:
        return None

    if permission.expires_at and permission.expires_at <= datetime.utcnow():
        return None

    return permission.level


def can_read(document, user):
    return permission_for(document, user) in ("read", "edit")


def can_edit(document, user):
    return permission_for(document, user) == "edit"


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_file_content(filename, data):
    """
    Validate uploaded file content against its extension.
    Returns True if the content appears to match the expected type.
    """

    extension = filename.rsplit(".", 1)[1].lower()

    # PDF signature
    if extension == "pdf":
        return data.startswith(b"%PDF-")

    # PNG signature
    if extension == "png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")

    # JPEG signature
    if extension in ("jpg", "jpeg"):
        return data.startswith(b"\xff\xd8\xff")

    # Older Microsoft Word DOC signature
    if extension == "doc":
        return data.startswith(
            b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
        )

    # DOCX and XLSX are ZIP-based formats
    if extension in ("docx", "xlsx"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                names = set(archive.namelist())

                if extension == "docx":
                    return (
                        "[Content_Types].xml" in names
                        and "word/document.xml" in names
                    )

                if extension == "xlsx":
                    return (
                        "[Content_Types].xml" in names
                        and "xl/workbook.xml" in names
                    )

        except (zipfile.BadZipFile, OSError):
            return False

        return False

    # TXT and CSV: check that the content is valid UTF-8 text.
    if extension in ("txt", "csv"):
        if b"\x00" in data:
            return False

        try:
            data.decode("utf-8-sig")
            return True
        except UnicodeDecodeError:
            return False

    return False


@app.context_processor
def inject_globals():
    return {"now": datetime.utcnow}


@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or len(password) < 10:
            flash(
                "Enter your name and email. Password must be at least 10 characters.",
                "error"
            )

        elif User.query.filter_by(email=email).first():
            flash("That email is already registered.", "error")

        else:
            # Public registrations always receive viewer role.
            user = User(
                name=name,
                email=email,
                role="viewer"
            )

            user.set_password(password)

            db.session.add(user)
            db.session.commit()

            flash("Account created. You can now sign in.", "success")
            return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and user.active and user.check_password(password):
            login_user(user)
            audit("login", "success")
            return redirect(url_for("dashboard"))
        audit("login", "denied", details=f"email={email}")
        flash("Invalid credentials or inactive account.", "error")
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    audit("logout")
    logout_user()
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    if current_user.role == "admin":
        projects = Project.query.order_by(Project.created_at.desc()).all()
        documents = Document.query.order_by(Document.uploaded_at.desc()).limit(10).all()
    elif current_user.role == "owner":
        projects = Project.query.filter_by(owner_id=current_user.id).all()
        documents = Document.query.filter_by(owner_id=current_user.id).all()
    else:
        memberships = Membership.query.filter_by(user_id=current_user.id, active=True).all()
        project_ids = [m.project_id for m in memberships]
        projects = Project.query.filter(Project.id.in_(project_ids)).all() if project_ids else []
        documents = [d for d in Document.query.filter(Document.project_id.in_(project_ids)).all() if can_read(d, current_user)] if project_ids else []
    return render_template("dashboard.html", projects=projects, documents=documents)


@app.route("/projects/new", methods=["GET", "POST"])
@role_required("owner", "admin")
def new_project():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        if not name:
            flash("Project name is required.", "error")
        else:
            project = Project(name=name, description=description, owner_id=current_user.id)
            db.session.add(project)
            db.session.commit()
            audit("project_created", details=f"project_id={project.id}")
            flash("Project created.", "success")
            return redirect(url_for("project_detail", project_id=project.id))
    return render_template("project_new.html")


@app.route("/projects/<int:project_id>")
@login_required
def project_detail(project_id):
    project = db.get_or_404(Project, project_id)

    if not is_project_owner(project) and not active_membership(project.id, current_user.id):
        abort(403)

    documents = Document.query.filter_by(project_id=project.id).all()

    members = (
        Membership.query.filter_by(project_id=project.id).all()
        if is_project_owner(project) else []
    )

    # Project members can see document metadata so they can request access.
    visible_documents = documents

    permission_map = {}
    document_permissions = {}

    for document in documents:
        permission_map[document.id] = DocumentPermission.query.filter_by(
            document_id=document.id,
            user_id=current_user.id,
            active=True
        ).first()

        document_permissions[document.id] = DocumentPermission.query.filter_by(
            document_id=document.id,
            active=True
        ).all()

    return render_template(
        "project_detail.html",
        project=project,
        documents=visible_documents,
        members=members,
        permission_map=permission_map,
        document_permissions=document_permissions,
        users=User.query.filter_by(active=True).all()
        if is_project_owner(project) else []
    )


@app.route("/projects/<int:project_id>/members", methods=["POST"])
@role_required("owner", "admin")
def add_member(project_id):
    project = db.get_or_404(Project, project_id)

    if not is_project_owner(project):
        abort(403)

    email = request.form.get("email", "").strip().lower()
    user = User.query.filter_by(email=email, active=True).first()

    if not user:
        flash("No active user found with that email.", "error")
        return redirect(url_for("project_detail", project_id=project.id))

    if user.id == project.owner_id:
        flash("The project owner is already a member.", "error")
        return redirect(url_for("project_detail", project_id=project.id))

    membership = Membership.query.filter_by(
        project_id=project.id,
        user_id=user.id
    ).first()

    if membership:
        if membership.active:
            flash("This user is already a project member.", "error")
        else:
            membership.active = True
            db.session.commit()
            audit("member_added", details=f"project_id={project.id};user_id={user.id}")
            flash("Project membership reactivated.", "success")
    else:
        db.session.add(Membership(
            project_id=project.id,
            user_id=user.id,
            active=True
        ))
        db.session.commit()
        audit("member_added", details=f"project_id={project.id};user_id={user.id}")
        flash("Member added successfully.", "success")

    return redirect(url_for("project_detail", project_id=project.id))


@app.route("/projects/<int:project_id>/upload", methods=["POST"])
@role_required("owner", "admin")
def upload_document(project_id):
    project = db.get_or_404(Project, project_id)

    if not is_project_owner(project):
        abort(403)

    file = request.files.get("file")

    if not file or not file.filename:
        flash("Choose a file.", "error")
        return redirect(url_for("project_detail", project_id=project.id))

    if not allowed_file(file.filename):
        flash("File type not allowed.", "error")
        audit(
            "document_upload",
            "denied",
            details=f"project_id={project.id};invalid_extension"
        )
        return redirect(url_for("project_detail", project_id=project.id))

    data = file.read(MAX_FILE_SIZE + 1)

    if len(data) > MAX_FILE_SIZE:
        flash("File is too large (10 MB maximum).", "error")
        audit(
            "document_upload",
            "denied",
            details=f"project_id={project.id};file_too_large"
        )
        return redirect(url_for("project_detail", project_id=project.id))

    original = secure_filename(file.filename) or "uploaded_file"

    # Validate the actual file content.
    if not validate_file_content(original, data):
        flash(
            "File content does not match the selected file type.",
            "error"
        )
        audit(
            "document_upload",
            "denied",
            details=f"project_id={project.id};content_validation_failed"
        )
        return redirect(url_for("project_detail", project_id=project.id))

    stored = uuid.uuid4().hex
    storage_path = os.path.join(app.config["UPLOAD_FOLDER"], stored)

    try:
        with open(storage_path, "wb") as output:
            output.write(data)

        doc = Document(
            project_id=project.id,
            owner_id=current_user.id,
            original_name=original,
            stored_name=stored,
            file_size=len(data)
        )

        db.session.add(doc)
        db.session.commit()

    except Exception:
        db.session.rollback()

        if os.path.exists(storage_path):
            os.remove(storage_path)

        app.logger.exception("Document upload failed")
        flash(
            "Upload could not be completed. Please try again.",
            "error"
        )
        return redirect(url_for("project_detail", project_id=project.id))

    audit(
        "document_uploaded",
        document_id=doc.id,
        details=f"project_id={project.id};name={original}"
    )

    flash(
        "Document uploaded. No member can access it until you grant permission.",
        "success"
    )

    return redirect(url_for("project_detail", project_id=project.id))


@app.route("/documents/<int:document_id>/permissions", methods=["POST"])
@role_required("owner", "admin")
def grant_permission(document_id):
    doc = db.get_or_404(Document, document_id)
    if not is_project_owner(doc.project):
        abort(403)
    try:
        user_id = int(request.form.get("user_id", "0"))
        level = request.form.get("level", "read")
        days = int(request.form.get("days", "0"))
    except ValueError:
        abort(400)
    if level not in ("read", "edit") or days < 0 or days > 365:
        abort(400)
    if not active_membership(doc.project_id, user_id):
        flash("Add the user to the project before granting document access.", "error")
        return redirect(url_for("project_detail", project_id=doc.project_id))
    permission = DocumentPermission.query.filter_by(document_id=doc.id, user_id=user_id).first()
    expires = datetime.utcnow() + timedelta(days=days) if days else None
    if permission:
        permission.level, permission.expires_at, permission.active = level, expires, True
    else:
        db.session.add(DocumentPermission(document_id=doc.id, user_id=user_id, level=level, expires_at=expires))
    db.session.commit()
    audit("permission_granted", document_id=doc.id, details=f"user_id={user_id};level={level};days={days}")
    flash("Document permission saved.", "success")
    return redirect(url_for("project_detail", project_id=doc.project_id))


@app.route("/documents/<int:document_id>/revoke/<int:user_id>", methods=["POST"])
@role_required("owner", "admin")
def revoke_permission(document_id, user_id):
    doc = db.get_or_404(Document, document_id)

    if not is_project_owner(doc.project):
        abort(403)

    permission = DocumentPermission.query.filter_by(
        document_id=doc.id,
        user_id=user_id
    ).first()

    if not permission:
        flash("No permission record found.", "error")
    elif not Membership.query.filter_by(
        project_id=doc.project_id,
        user_id=user_id,
        active=True
    ).first():
        flash("The user is not an active project member.", "error")
    elif not permission.active:
        flash("Permission is already revoked.", "error")
    else:
        permission.active = False
        db.session.commit()

        audit(
            "permission_revoked",
            document_id=doc.id,
            details=f"user_id={user_id}"
        )

        flash("Permission revoked successfully.", "success")

    return redirect(url_for("project_detail", project_id=doc.project_id))


@app.route("/documents/<int:document_id>/download")
@login_required
def download_document(document_id):
    doc = db.get_or_404(Document, document_id)
    if not can_read(doc, current_user):
        audit("document_download", "denied", document_id=doc.id, details="authorization_failed")
        abort(403)
    path = os.path.join(app.config["UPLOAD_FOLDER"], doc.stored_name)
    if not os.path.isfile(path):
        audit("document_download", "denied", document_id=doc.id, details="file_missing")
        abort(404)
    audit("document_download", "success", document_id=doc.id, details="authorized_download")
    return send_file(path, as_attachment=True, download_name=doc.original_name)


@app.route("/documents/<int:document_id>/request", methods=["POST"])
@role_required("viewer")
def request_access(document_id):
    doc = db.get_or_404(Document, document_id)
    if not active_membership(doc.project_id, current_user.id):
        abort(403)
    level = request.form.get("level", "read")
    if level not in ("read", "edit"):
        abort(400)
    existing = AccessRequest.query.filter_by(document_id=doc.id, requester_id=current_user.id, status="pending").first()
    if existing:
        flash("You already have a pending request for this document.", "error")
    else:
        db.session.add(AccessRequest(document_id=doc.id, requester_id=current_user.id, requested_level=level,
                                     reason=request.form.get("reason", "")[:500]))
        db.session.commit()
        audit("access_requested", document_id=doc.id, details=f"level={level}")
        flash("Access request sent to the project owner.", "success")
    return redirect(url_for("dashboard"))


@app.route("/requests")
@login_required
def requests_page():
    if current_user.role in ("owner", "admin"):
        projects = Project.query.filter_by(owner_id=current_user.id).all() if current_user.role == "owner" else Project.query.all()
        pids = [p.id for p in projects]
        requests_list = AccessRequest.query.join(Document).filter(Document.project_id.in_(pids)).order_by(AccessRequest.created_at.desc()).all() if pids else []
    else:
        requests_list = AccessRequest.query.filter_by(requester_id=current_user.id).order_by(AccessRequest.created_at.desc()).all()
    return render_template("requests.html", requests_list=requests_list)


@app.route("/requests/<int:request_id>/<decision>", methods=["POST"])
@role_required("owner", "admin")
def decide_request(request_id, decision):
    access_request = db.get_or_404(AccessRequest, request_id)
    if decision not in ("approve", "reject") or not is_project_owner(access_request.document.project):
        abort(403)
    if access_request.status != "pending":
        flash("This request has already been reviewed.", "error")
    elif decision == "approve":
        if not active_membership(access_request.document.project_id, access_request.requester_id):
            flash("The requester is no longer an active project member.", "error")
        else:
            permission = DocumentPermission.query.filter_by(document_id=access_request.document_id,
                                                            user_id=access_request.requester_id).first()
            if permission:
                permission.level, permission.active = access_request.requested_level, True
            else:
                db.session.add(DocumentPermission(document_id=access_request.document_id,
                    user_id=access_request.requester_id, level=access_request.requested_level))
            access_request.status = "approved"
            db.session.commit()
            audit("access_request_approved", document_id=access_request.document_id,
                  details=f"request_id={request_id}")
            flash("Request approved and permission granted.", "success")
    else:
        access_request.status = "rejected"
        db.session.commit()
        audit("access_request_rejected", document_id=access_request.document_id,
              details=f"request_id={request_id}")
        flash("Request rejected.", "success")
    return redirect(url_for("requests_page"))


@app.route("/admin")
@role_required("admin")
def admin_panel():
    return render_template("admin.html", users=User.query.order_by(User.created_at.desc()).all(),
                           events=AuditEvent.query.order_by(AuditEvent.id.desc()).limit(100).all(),
                           projects=Project.query.all())


@app.route("/admin/users/<int:user_id>/toggle", methods=["POST"])
@role_required("admin")
def toggle_user(user_id):
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        flash("You cannot deactivate your own account.", "error")
    else:
        user.active = not user.active
        db.session.commit()
        audit("user_status_changed", details=f"user_id={user.id};active={user.active}")
        flash("User status updated.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/audit/verify")
@role_required("admin")
def verify_audit():
    events = AuditEvent.query.order_by(AuditEvent.id.asc()).all()

    previous = "0" * 64
    valid = True

    for event in events:

        if event.previous_hash != previous:
            valid = False
            break

        actor = event.actor_id if event.actor_id is not None else "anonymous"

        payload = (
            f"{actor}|{event.action}|{event.outcome}|"
            f"{event.document_id}|{event.details}|"
            f"{event.timestamp}|{event.previous_hash}"
        )

        expected_hash = hashlib.sha256(
            payload.encode("utf-8")
        ).hexdigest()

        if event.event_hash != expected_hash:
            valid = False
            break

        previous = event.event_hash

    return render_template(
        "verify.html",
        valid=valid,
        count=len(events)
    )


@app.errorhandler(403)
def forbidden(_error):
    return render_template("error.html", code=403, message="You do not have permission to perform this action."), 403


@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, message="The requested item could not be found."), 404


@app.errorhandler(413)
def too_large(_error):
    return render_template("error.html", code=413, message="The uploaded file is larger than 10 MB."), 413


def initialize_database():
    with app.app_context():
        db.create_all()

        if not User.query.filter_by(email="admin@vaulttrace.local").first():
            admin = User(
                name="VaultTrace Admin",
                email="admin@vaulttrace.local",
                role="admin"
            )

            admin_password = os.environ.get("ADMIN_PASSWORD")

            if not admin_password:
                raise RuntimeError(
                    "ADMIN_PASSWORD environment variable is required."
                )

            admin.set_password(admin_password)
            db.session.add(admin)
            db.session.commit()


if __name__ == "__main__":
    initialize_database()
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1")