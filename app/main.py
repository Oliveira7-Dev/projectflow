from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from . import db, limiter
from .models import Project, Task, User

main_bp = Blueprint("main", __name__)

PROJECT_STATUSES = {"Em andamento", "Planejado", "Concluído"}
TASK_STATUSES = {"Pendente", "Em andamento", "Concluída"}
PRIORITIES = {"Baixa", "Média", "Alta"}

def clean_text(value, max_len):
    return (value or "").strip()[:max_len]

def parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None

def get_owned_project(project_id):
    project = db.session.get(Project, project_id)
    if not project or project.owner_id != current_user.id:
        abort(404)
    return project

@main_bp.route("/")
@login_required
def dashboard():
    projects = Project.query.filter_by(owner_id=current_user.id).order_by(Project.created_at.desc()).all()
    project_ids = [p.id for p in projects]
    tasks = Task.query.filter(Task.project_id.in_(project_ids)).all() if project_ids else []

    stats = {
        "projects": len(projects),
        "tasks": len(tasks),
        "pending": sum(1 for t in tasks if t.status != "Concluída"),
        "done": sum(1 for t in tasks if t.status == "Concluída"),
    }
    recent_tasks = sorted(tasks, key=lambda t: t.created_at, reverse=True)[:6]
    return render_template("dashboard.html", projects=projects[:4], stats=stats, recent_tasks=recent_tasks)

@main_bp.route("/projects")
@login_required
def projects():
    status = request.args.get("status", "")
    query = Project.query.filter_by(owner_id=current_user.id)
    if status in PROJECT_STATUSES:
        query = query.filter_by(status=status)
    else:
        status = ""
    return render_template("projects/list.html", projects=query.order_by(Project.created_at.desc()).all(), selected_status=status)

@main_bp.route("/projects/new", methods=["GET", "POST"])
@login_required
def project_new():
    if request.method == "POST":
        name = clean_text(request.form.get("name"), 140)
        description = clean_text(request.form.get("description"), 3000)
        status = request.form.get("status", "Em andamento")
        if status not in PROJECT_STATUSES:
            status = "Em andamento"

        if not name:
            flash("Informe o nome do projeto.", "warning")
        else:
            project = Project(name=name, description=description, status=status, owner_id=current_user.id)
            db.session.add(project)
            db.session.commit()
            flash("Projeto criado com sucesso.", "success")
            return redirect(url_for("main.projects"))
    return render_template("projects/form.html", project=None)

@main_bp.route("/projects/<int:project_id>")
@login_required
def project_detail(project_id):
    return render_template("projects/detail.html", project=get_owned_project(project_id))

@main_bp.route("/projects/<int:project_id>/edit", methods=["GET", "POST"])
@login_required
def project_edit(project_id):
    project = get_owned_project(project_id)
    if request.method == "POST":
        name = clean_text(request.form.get("name"), 140)
        if not name:
            flash("Informe o nome do projeto.", "warning")
        else:
            project.name = name
            project.description = clean_text(request.form.get("description"), 3000)
            status = request.form.get("status", "Em andamento")
            project.status = status if status in PROJECT_STATUSES else "Em andamento"
            db.session.commit()
            flash("Projeto atualizado.", "success")
            return redirect(url_for("main.project_detail", project_id=project.id))
    return render_template("projects/form.html", project=project)

@main_bp.route("/projects/<int:project_id>/delete", methods=["POST"])
@login_required
def project_delete(project_id):
    project = get_owned_project(project_id)
    db.session.delete(project)
    db.session.commit()
    flash("Projeto excluído.", "success")
    return redirect(url_for("main.projects"))

@main_bp.route("/projects/<int:project_id>/tasks/new", methods=["GET", "POST"])
@login_required
def task_new(project_id):
    project = get_owned_project(project_id)
    if request.method == "POST":
        title = clean_text(request.form.get("title"), 160)
        if not title:
            flash("Informe o título da tarefa.", "warning")
        else:
            priority = request.form.get("priority", "Média")
            status = request.form.get("status", "Pendente")
            task = Task(
                title=title,
                description=clean_text(request.form.get("description"), 3000),
                priority=priority if priority in PRIORITIES else "Média",
                status=status if status in TASK_STATUSES else "Pendente",
                due_date=parse_date(request.form.get("due_date", "").strip()),
                project_id=project.id,
                assignee_id=current_user.id,
            )
            db.session.add(task)
            db.session.commit()
            flash("Tarefa criada.", "success")
            return redirect(url_for("main.project_detail", project_id=project.id))
    return render_template("tasks/form.html", project=project, task=None)

@main_bp.route("/tasks/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def task_edit(task_id):
    task = db.session.get(Task, task_id)
    if not task or task.project.owner_id != current_user.id:
        abort(404)

    if request.method == "POST":
        title = clean_text(request.form.get("title"), 160)
        if not title:
            flash("Informe o título.", "warning")
        else:
            task.title = title
            task.description = clean_text(request.form.get("description"), 3000)
            priority = request.form.get("priority", "Média")
            status = request.form.get("status", "Pendente")
            task.priority = priority if priority in PRIORITIES else "Média"
            task.status = status if status in TASK_STATUSES else "Pendente"
            task.due_date = parse_date(request.form.get("due_date", "").strip())
            db.session.commit()
            flash("Tarefa atualizada.", "success")
            return redirect(url_for("main.project_detail", project_id=task.project_id))

    return render_template("tasks/form.html", project=task.project, task=task)

@main_bp.route("/tasks/<int:task_id>/delete", methods=["POST"])
@login_required
def task_delete(task_id):
    task = db.session.get(Task, task_id)
    if not task or task.project.owner_id != current_user.id:
        abort(404)
    project_id = task.project_id
    db.session.delete(task)
    db.session.commit()
    flash("Tarefa excluída.", "success")
    return redirect(url_for("main.project_detail", project_id=project_id))


@main_bp.route("/settings/profile", methods=["GET", "POST"])
@login_required
def profile_settings():
    if request.method == "POST":
        name = clean_text(request.form.get("name"), 120)
        email = clean_text(request.form.get("email"), 180).lower()

        if len(name) < 2:
            flash("Informe um nome válido.", "warning")
            return render_template("settings/profile.html")

        if not email or "@" not in email:
            flash("Informe um e-mail válido.", "warning")
            return render_template("settings/profile.html")

        existing = User.query.filter(User.email == email, User.id != current_user.id).first()
        if existing:
            flash("Este e-mail já está sendo usado por outra conta.", "warning")
            return render_template("settings/profile.html")

        current_user.name = name
        current_user.email = email
        db.session.commit()

        flash("Perfil atualizado com sucesso.", "success")
        return redirect(url_for("main.profile_settings"))

    return render_template("settings/profile.html")


@main_bp.route("/settings/security", methods=["GET", "POST"])
@login_required
@limiter.limit("5 per 10 minutes", methods=["POST"])
def security_settings():
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not current_user.check_password(current_password):
            flash("A senha atual está incorreta.", "danger")
            return render_template("settings/security.html")

        if new_password != confirm_password:
            flash("A confirmação da nova senha não confere.", "warning")
            return render_template("settings/security.html")

        # Mesmo padrão do cadastro/recuperação:
        # 10+ caracteres, maiúscula, minúscula, número e especial.
        if not (
            len(new_password) >= 10
            and any(c.isupper() for c in new_password)
            and any(c.islower() for c in new_password)
            and any(c.isdigit() for c in new_password)
            and any(not c.isalnum() for c in new_password)
        ):
            flash(
                "A nova senha precisa ter no mínimo 10 caracteres, "
                "com maiúscula, minúscula, número e caractere especial.",
                "warning",
            )
            return render_template("settings/security.html")

        if current_user.check_password(new_password):
            flash("A nova senha precisa ser diferente da senha atual.", "warning")
            return render_template("settings/security.html")

        current_user.set_password(new_password)
        db.session.commit()

        flash("Senha alterada com sucesso.", "success")
        return redirect(url_for("main.security_settings"))

    return render_template("settings/security.html")
