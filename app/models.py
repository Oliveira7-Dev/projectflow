from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_verified = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    projects = db.relationship("Project", backref="owner", lazy=True, cascade="all, delete-orphan")
    tasks = db.relationship("Task", backref="assignee", lazy=True)

    def set_password(self, password):
        # O Werkzeug usa um KDF seguro; senha original nunca é armazenada.
        self.password_hash = generate_password_hash(password, method="scrypt")

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text, default="")
    status = db.Column(db.String(30), default="Em andamento")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)

    tasks = db.relationship("Task", backref="project", lazy=True, cascade="all, delete-orphan")

    @property
    def progress(self):
        if not self.tasks:
            return 0
        done = sum(1 for t in self.tasks if t.status == "Concluída")
        return round((done / len(self.tasks)) * 100)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, default="")
    priority = db.Column(db.String(20), default="Média")
    status = db.Column(db.String(30), default="Pendente")
    due_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False, index=True)
    assignee_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True, index=True)
