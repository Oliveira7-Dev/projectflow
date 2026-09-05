from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from . import db
from .models import Project, Task

main_bp = Blueprint("main", __name__)

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
    if status:
        query = query.filter_by(status=status)
    return render_template("projects/list.html", projects=query.order_by(Project.created_at.desc()).all(), selected_status=status)

@main_bp.route("/projects/new", methods=["GET", "POST"])
@login_required
def project_new():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        status = request.form.get("status", "Em andamento")

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
    project = get_owned_project(project_id)
    return render_template("projects/detail.html", project=project)

@main_bp.route("/projects/<int:project_id>/edit", methods=["GET", "POST"])
@login_required
def project_edit(project_id):
    project = get_owned_project(project_id)

    if request.method == "POST":
        project.name = request.form.get("name", "").strip()
        project.description = request.form.get("description", "").strip()
        project.status = request.form.get("status", "Em andamento")
        if not project.name:
            flash("Informe o nome do projeto.", "warning")
        else:
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
        title = request.form.get("title", "").strip()
        due = request.form.get("due_date", "").strip()
        due_date = datetime.strptime(due, "%Y-%m-%d").date() if due else None

        if not title:
            flash("Informe o título da tarefa.", "warning")
        else:
            task = Task(
                title=title,
                description=request.form.get("description", "").strip(),
                priority=request.form.get("priority", "Média"),
                status=request.form.get("status", "Pendente"),
                due_date=due_date,
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
        task.title = request.form.get("title", "").strip()
        task.description = request.form.get("description", "").strip()
        task.priority = request.form.get("priority", "Média")
        task.status = request.form.get("status", "Pendente")
        due = request.form.get("due_date", "").strip()
        task.due_date = datetime.strptime(due, "%Y-%m-%d").date() if due else None

        if not task.title:
            flash("Informe o título.", "warning")
        else:
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
