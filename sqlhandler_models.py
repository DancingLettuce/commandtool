"""This filename is sqlhandler_models.py"""

# setup alembic

"""In your terminal, run the initialization command. This creates an alembic.ini file and an alembic/ folder.
alembic init alembic

4. Create and Run the Migration
Now that Alembic knows about your model and your database credentials, let's create the table.
Generate the migration script (Django's makemigrations):
alembic revision --autogenerate -m "create my_table"

For critical existing databases, this is the safest workflow:
    Autogenerate the Python script (Online): alembic revision --autogenerate -m "create my_table" (This requires an online connection to compare your models to the DB).
    Review the Python script: Open alembic/versions/xxxx_create_my_table.py and ensure there are no drop_table commands.
    Generate the SQL (Offline): alembic upgrade head --sql > migration.sql
    Review the SQL: Open migration.sql and verify exactly what will happen.
    Execute: If the SQL is perfect, you can either run the migration.sql script manually via sqlcmd / DBeaver, OR you can safely run alembic upgrade head (Online) knowing exactly what it will do.

"""

from typing import Optional
from datetime import datetime
from sqlalchemy import BigInteger, String, JSON, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.mssql import DATETIMEOFFSET # Import the specific MS SQL type


# 1. Define the Base class (Your equivalent of models.Model in Django)
class Base(DeclarativeBase):
    pass

class CcmOrganisation(Base):
    __tablename__ = "ccm_organisation"
    # Primary Key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # Datetimes
    created_on: Mapped[Optional[datetime]] = mapped_column(
        DATETIMEOFFSET, server_default=text("getdate()")
    )
    api_lastseen: Mapped[Optional[datetime]] = mapped_column(DATETIMEOFFSET)
    create_time: Mapped[Optional[datetime]] = mapped_column(DATETIMEOFFSET)
    update_time: Mapped[Optional[datetime]] = mapped_column(DATETIMEOFFSET)
    # Strings with defaults
    name: Mapped[Optional[str]] = mapped_column(String(250), server_default="")
    organisation_id: Mapped[Optional[str]] = mapped_column(String(50), server_default="")
    display_name: Mapped[Optional[str]] = mapped_column(String(250), server_default="")
    directory_customer_id: Mapped[Optional[str]] = mapped_column(String(250), server_default="")
    state: Mapped[Optional[str]] = mapped_column(String(50), server_default="")
    etag: Mapped[Optional[str]] = mapped_column(String(50), server_default="")
    # JSON Data (Stored as NVARCHAR(MAX) in DB, handled as a Python dict in your code)
    api_data: Mapped[Optional[dict]] = mapped_column(JSON)

    """Key Design Details for this Model:
    BigInteger: Mapped to your bigint ID field.
    DATETIMEOFFSET: Imported directly from the mssql dialect to perfectly match your DDL and preserve UTC timezone offsets.
    JSON: Even though your database stores this as nvarchar(MAX), using SQLAlchemy's JSON 
    type means you can assign a raw Python dictionary to api_data, and SQLAlchemy will automatically convert 
    it to a JSON string during the INSERT/UPDATE statement to satisfy your ISJSON check constraint.
    server_default=text("getdate()"): This tells SQLAlchemy, "If I don't provide a created_on date in Python, 
    don't insert NULL. Let the SQL Server use its own default." """

class CcmFolder(Base):
    __tablename__ = "ccm_folder"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    created_on: Mapped[Optional[datetime]] = mapped_column(
        DATETIMEOFFSET, server_default=text("getdate()")
    )
    api_lastseen: Mapped[Optional[datetime]] = mapped_column(DATETIMEOFFSET)
    create_time: Mapped[Optional[datetime]] = mapped_column(DATETIMEOFFSET)
    update_time: Mapped[Optional[datetime]] = mapped_column(DATETIMEOFFSET)
    folder_id: Mapped[Optional[str]] = mapped_column(String(50), server_default="")
    parent: Mapped[Optional[str]] = mapped_column(String(50), server_default="")
    name: Mapped[Optional[str]] = mapped_column(String(250), server_default="")
    organisation_ccm_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    display_name: Mapped[Optional[str]] = mapped_column(String(250), server_default="")
    state: Mapped[Optional[str]] = mapped_column(String(50), server_default="")
    etag: Mapped[Optional[str]] = mapped_column(String(50), server_default="")
    # JSON Data (Stored as NVARCHAR(MAX) in DB, handled as a Python dict in your code)
    api_data: Mapped[Optional[dict]] = mapped_column(JSON)

class CcmProject(Base):
    __tablename__ = "ccm_project"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    created_on: Mapped[Optional[datetime]] = mapped_column(
        DATETIMEOFFSET, server_default=text("getdate()")
    )
    api_lastseen: Mapped[Optional[datetime]] = mapped_column(DATETIMEOFFSET)
    api_data: Mapped[Optional[dict]] = mapped_column(JSON)
    name: Mapped[Optional[str]] = mapped_column(String(250), server_default="")
    parent: Mapped[Optional[str]] = mapped_column(String(50), server_default="")
    project_id: Mapped[Optional[str]] = mapped_column(String(250), server_default="")
    state: Mapped[Optional[str]] = mapped_column(String(50), server_default="")
    display_name: Mapped[Optional[str]] = mapped_column(String(250), server_default="")
    create_time: Mapped[Optional[datetime]] = mapped_column(DATETIMEOFFSET)
    etag: Mapped[Optional[str]] = mapped_column(String(50), server_default="")

class CcmProjectStaging(Base):
    __tablename__ = "ccm_project_staging"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    created_on: Mapped[Optional[datetime]] = mapped_column(
        DATETIMEOFFSET, server_default=text("getdate()")
    )
    api_lastseen: Mapped[Optional[datetime]] = mapped_column(DATETIMEOFFSET)
    api_data: Mapped[Optional[dict]] = mapped_column(JSON)
    name: Mapped[Optional[str]] = mapped_column(String(250), server_default="")
    parent: Mapped[Optional[str]] = mapped_column(String(50), server_default="")
    project_id: Mapped[Optional[str]] = mapped_column(String(250), server_default="")
    state: Mapped[Optional[str]] = mapped_column(String(50), server_default="")
    display_name: Mapped[Optional[str]] = mapped_column(String(250), server_default="")
    create_time: Mapped[Optional[datetime]] = mapped_column(DATETIMEOFFSET)
    etag: Mapped[Optional[str]] = mapped_column(String(50), server_default="")