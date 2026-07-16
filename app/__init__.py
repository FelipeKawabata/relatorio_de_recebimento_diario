from flask import Flask, jsonify
import os
from urllib.parse import quote_plus
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from datetime import timedelta

load_dotenv(override=True)

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

servidor = os.getenv("DB_SERVER")
banco = os.getenv("DB_DATABASE")
usuario = os.getenv("DB_USERNAME")
senha = os.getenv("DB_PASSWORD")
driver = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")

if not all([servidor, banco, usuario, senha]):
    raise RuntimeError(
        "As varáveis DB_SERVER, DB_DATABASE, DB_USERNAME e DB_PASSWORD precisam estar corretamente configuradas."
    )

odbc_connection_string = (
    f"DRIVER={{{driver}}};"
    f"SERVER={servidor};"
    f"DATABASE={banco};"
    f"UID={usuario};"
    f"PWD={senha};"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)

connection_params = quote_plus(odbc_connection_string)

app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mssql+pyodbc:///?odbc_connect={connection_params}")

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 1800
}

db = SQLAlchemy(app)

from app.routes import homepage  # noqa: E402
