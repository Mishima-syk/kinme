#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, request, redirect,render_template, flash, url_for, session, abort
from werkzeug.utils import secure_filename
from model import db, Workflow, Tag, Node, User, workflows_nodes, workflows_tags
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired
from wtforms import TextField, PasswordField, SelectField, DateField, BooleanField, TextAreaField, FileField, validators
from sqlalchemy import func, text
import os
import string
import random
from zipfile import ZipFile
from io import BytesIO
from cairosvg import svg2png
import markdown
import json

database = os.path.join(os.path.dirname(__file__), 'kinme.db')
md = markdown.Markdown()

app = Flask(__name__)
app.config['SECRET_KEY'] = "kinme"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + database

login_manager = LoginManager()
login_manager.login_view =  "login"
login_manager.init_app(app)

db.init_app(app)
db.app = app

def flash_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            flash("Error in the %s field - %s" % (getattr(form, field).label.text, error))


### login form
class RegisterForm(FlaskForm):
    username = TextField('Username', validators=[validators.Required()])
    password = PasswordField('Password', validators=[validators.Required()])

class LoginForm(FlaskForm):
    username = TextField('Username', validators=[validators.Required()])
    password = PasswordField('Password', validators=[validators.Required()])

class NewWorkflow(FlaskForm):
    name = TextField(u'Workflow name', validators=[validators.Required()], render_kw={'placeholder': u"Simple name"})
    knwf = FileField(u'knwf file', validators=[FileRequired()])
    tag = TextField(u'tags', validators=[validators.Required()], render_kw={'placeholder': u"Space delimited tags"})
    content = TextAreaField('Username', validators=[validators.Required()], render_kw={'placeholder': u"Description (Markdown is available)"})


@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))


@app.route('/', methods=["GET", "POST"])
def index():
    tag_list = db.session.query(Tag, func.count(workflows_tags.c.workflow_id).label("total")).join(workflows_tags).group_by(Tag).order_by(text("total DESC"))
    node_list = db.session.query(Node, func.count(workflows_nodes.c.workflow_id).label("total")).join(workflows_nodes).group_by(Node).order_by(text("total DESC"))
    user_list = db.session.query(User, func.count(Workflow.user_id).label("total")).join(Workflow).group_by(User).order_by(text("total DESC"))
    workflows = Workflow.query.order_by(Workflow.id.desc()).all()
    return render_template("index.html", workflows=workflows, tags=tag_list, nodes=node_list, users=user_list)


@app.route('/tag/<int:tag_id>', methods=["GET", "POST"])
def tag_filter(tag_id):
    tag_list = db.session.query(Tag, func.count(workflows_tags.c.workflow_id).label("total")).join(workflows_tags).group_by(Tag).order_by(text("total DESC"))
    user_list = db.session.query(User, func.count(Workflow.user_id).label("total")).join(Workflow).group_by(User).order_by(text("total DESC"))
    node_list = db.session.query(Node, func.count(workflows_nodes.c.workflow_id).label("total")).join(workflows_nodes).group_by(Node).order_by(text("total DESC"))
    workflows = Workflow.query.filter(Workflow.tags.any(id=tag_id)).order_by(Workflow.id.desc()).all()
    return render_template("index.html", workflows=workflows, tags=tag_list, nodes=node_list, users=user_list)


@app.route('/node/<int:node_id>', methods=["GET", "POST"])
def node_filter(node_id):
    tag_list = db.session.query(Tag, func.count(workflows_tags.c.workflow_id).label("total")).join(workflows_tags).group_by(Tag).order_by(text("total DESC"))
    node_list = db.session.query(Node, func.count(workflows_nodes.c.workflow_id).label("total")).join(workflows_nodes).group_by(Node).order_by(text("total DESC"))
    user_list = db.session.query(User, func.count(Workflow.user_id).label("total")).join(Workflow).group_by(User).order_by(text("total DESC"))
    workflows = Workflow.query.filter(Workflow.nodes.any(id=node_id)).order_by(Workflow.id.desc()).all()
    return render_template("index.html", workflows=workflows, tags=tag_list, nodes=node_list, users=user_list)


@app.route('/user/<int:user_id>', methods=["GET", "POST"])
def user_filter(user_id):
    tag_list = db.session.query(Tag, func.count(workflows_tags.c.workflow_id).label("total")).join(workflows_tags).group_by(Tag).order_by(text("total DESC"))
    node_list = db.session.query(Node, func.count(workflows_nodes.c.workflow_id).label("total")).join(workflows_nodes).group_by(Node).order_by(text("total DESC"))
    user_list = db.session.query(User, func.count(Workflow.user_id).label("total")).join(Workflow).group_by(User).order_by(text("total DESC"))
    workflows = Workflow.query.filter_by(user_id=user_id).order_by(Workflow.id.desc()).all()
    return render_template("index.html", workflows=workflows, tags=tag_list, nodes=node_list, users=user_list)


@app.route('/workflow/<int:workflow_id>', methods=['GET', 'POST'])
def display_workflow(workflow_id):
    wf = Workflow.query.filter_by(id=workflow_id).first()
    if wf is None:
        abort(404)
    return render_template("workflow.html", workflow=wf)


@app.route('/new', methods=['GET', 'POST'])
@login_required
def new_workflow():
    form = NewWorkflow() # Don't pass request.form
    if form.validate_on_submit():
        tags = []
        for tag in form.tag.data.split(" "):
            tag_name = tag.strip()
            t = Tag.query.filter_by(name=tag_name).first()
            if t is None:
                t = Tag(tag_name)
                db.session.add(t)
                db.session.commit()
            tags.append(t)

        wf = Workflow(name=form.name.data, user_id=current_user.id, content=form.content.data)
        db.session.add(wf)
        db.session.commit()
        filename = secure_filename(form.knwf.data.filename)
        subdir = os.path.join("static", "workflows", str(wf.id))
        if not os.path.exists(subdir):
            os.mkdir(subdir)
        form.knwf.data.save(os.path.join(subdir, filename))
        zfile = ZipFile(form.knwf.data)
        node_list = []
        for name in zfile.namelist():
            if name.endswith("workflow.svg"):
                png_file = os.path.join(subdir, "workflow.png")
                s = zfile.read(name)
                svg2png(bytestring=s, write_to=png_file)
            tname = name.split("/")[1]
            node_name = tname.split("(")[0]
            if not node_name.startswith("workflow") and not node_name.startswith("."):
                node_name = node_name.rstrip()
                node_list.append(node_name)
        nl = list(set(node_list))
        nodes = []
        for node_name in nl:
            n = Node.query.filter_by(name=node_name).first()
            if n is None:
                n = Node(node_name)
                db.session.add(n)
                db.session.commit()
            nodes.append(n)            
        wf.workflow = filename
        wf.tags = tags
        wf.nodes = nodes
        db.session.commit()
        return redirect(url_for("index"))
    flash_errors(form)
    return render_template("new.html", form=form)


@app.route('/edit/<int:workflow_id>', methods=['GET', 'POST'])
@login_required
def edit_workflow(workflow_id):
    wf = Workflow.query.filter_by(id=workflow_id).first()
    if wf is None:
        abort(404)
    if wf.user_id != current_user.id:
        abort(403)

    if request.method == "GET":
        tag_str = " ".join([t.name for t in wf.tags])
        return render_template("edit.html", workflow=wf, tag_str=tag_str)
    elif request.method == "POST":
        form = NewWorkflow()
        tags = []
        for tag in form.tag.data.split(" "):
            tag_name = tag.strip()
            t = Tag.query.filter_by(name=tag_name).first()
            if t is None:
                t = Tag(tag_name)
                db.session.add(t)
                db.session.commit()
            tags.append(t)
        subdir = os.path.join("static", "workflows", str(wf.id))
        if form.knwf.data.filename:
            filename = secure_filename(form.knwf.data.filename)
            form.knwf.data.save(os.path.join(subdir, filename))
            zfile = ZipFile(form.knwf.data)
            node_list = []
            for name in zfile.namelist():
                if name.endswith("workflow.svg"):
                    png_file = os.path.join(subdir, "workflow.png")
                    s = zfile.read(name)
                    svg2png(bytestring=s, write_to=png_file)
                tname = name.split("/")[1]
                node_name = tname.split("(")[0]
                if not node_name.startswith("workflow") and not node_name.startswith("."):
                    node_name = node_name.rstrip()
                    node_list.append(node_name)
            nl = list(set(node_list))
            nodes = []
            for node_name in nl:
                n = Node.query.filter_by(name=node_name).first()
                if n is None:
                    n = Node(node_name)
                    db.session.add(n)
                    db.session.commit()
                nodes.append(n)            
            wf.workflow = filename
            wf.nodes = nodes
        wf.tags = tags
        wf.name = form.name.data
        wf.content = form.content.data
        wf.rendered_content = md.convert(wf.content)
        db.session.commit()
        return redirect(url_for("display_workflow", workflow_id=workflow_id))


@app.route('/delete/<int:workflow_id>', methods=['GET', 'POST'])
@login_required
def delete_workflow(workflow_id):
    wf = Workflow.query.filter_by(id=workflow_id).first()
    if wf is None:
        abort(404)
    if wf.user_id != current_user.id:
        abort(403)
    if request.method == "GET":
        return render_template("delete.html", workflow=wf)
    elif request.method == "POST":
        db.session.delete(wf)
        db.session.commit()
        return redirect("/")


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == "GET":
        return render_template("register.html", form=form)
    elif request.method == "POST":
        if form.validate_on_submit():
            user = User(request.form.get('username'), request.form.get('password'))
            db.session.add(user)
            db.session.commit()
        return redirect("/")


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    if form.validate_on_submit():
        user = User.query.filter_by(name=form.username.data).first()
        if user.password == form.password.data:
            login_user(user)
            next_url = request.form.get('next')
            #print next_url
            if len(next_url) > 0: 
                return redirect(next_url)
            else:
                return redirect('/')
        else:
            print('Login failed.')
    return render_template("login.html", form=form, next=request.args.get('next', ""))


@app.route("/logout")
def logout():
    logout_user()
    return redirect('/')


if __name__ == "__main__":
    app.run(debug=True)
