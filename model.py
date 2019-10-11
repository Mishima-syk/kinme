from flask_sqlalchemy import SQLAlchemy
import markdown
from datetime import datetime

db = SQLAlchemy()
md = markdown.Markdown()

workflows_tags = db.Table('workflows_tags',
                    db.Column('workflow_id', db.Integer, db.ForeignKey('workflow.id')),
                    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'))
                )

workflows_nodes = db.Table('workflows_nodes',
                    db.Column('workflow_id', db.Integer, db.ForeignKey('workflow.id')),
                    db.Column('node_id', db.Integer, db.ForeignKey('node.id'))
                )

class Workflow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    workflow  = db.Column(db.Text)
    created_time = db.Column(db.DateTime)
    updated_time = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref='workflows')
    content = db.Column(db.Text, nullable=False)
    rendered_content = db.Column(db.Text, nullable=False)
    tags = db.relationship('Tag', secondary=workflows_tags, back_populates='workflows')
    nodes = db.relationship('Node', secondary=workflows_nodes, back_populates='workflows')

    def __init__(self, **k):
        self.name = k["name"]
        if "workflow" in k:
            self.workflow = k["workflow"]
        self.created_time = datetime.now()
        self.user_id = k["user_id"]
        self.content = k["content"]
        self.rendered_content = md.convert(k["content"])

    def __repr__(self):
        return '<({}) {}>'.format(self.name, self.created_time)


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    workflows = db.relationship('Workflow', secondary=workflows_tags, back_populates='tags')
    def __init__(self, name):
        self.name = name


class Node(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    workflows = db.relationship('Workflow', secondary=workflows_nodes, back_populates='nodes')
    def __init__(self, name):
        self.name = name


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30))
    password = db.Column(db.String(30))

    def __init__(self, name, password):
        self.name = name
        self.password = password

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    @classmethod
    def auth(cls, name, password):        
        u = User.query.filter_by(name=name).first()
        if u.password == password:
            return u

    def __repr__(self):
        return '<User:{}({})>'.format(self.name, self.id)
