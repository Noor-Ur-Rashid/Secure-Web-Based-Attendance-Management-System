import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = "supersecretkey123"
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "database", "users.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False