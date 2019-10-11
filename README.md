# knimea

KNIME workflow file sharing service

# Setup

Install modules

    conda install -c conda-forge flask-sqlalchemy
    conda install -c conda-forge flask-login
    conda install -c conda-forge flask-wtf
    conda install -c conda-forge cairosvg
    conda install -c conda-forge markdown

clone or download this repository

setup database

    python refreshdb.py

launch flask server

    export FLASK_APP=app.py
    flask run



