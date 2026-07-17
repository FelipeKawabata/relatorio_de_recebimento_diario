import os
from urllib.parse import quote_plus
from sqlalchemy import create_engine

from app import db
from app import models  # noqa: F401 — registra as tabelas no db.metadata

odbc = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    f"SERVER={os.getenv('DB_SERVER')};"
    f"DATABASE={os.getenv('DB_DATABASE')};"
    f"UID={os.getenv('DB_DDL_USERNAME')};"
    f"PWD={os.getenv('DB_DDL_PASSWORD')};"
    "Encrypt=yes;TrustServerCertificate=yes;"
)
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc)}")

db.metadata.create_all(engine)
print("Tabelas criadas!")
