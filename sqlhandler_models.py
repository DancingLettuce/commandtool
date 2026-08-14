"""This filename is sqlhandler_models.py"""

# setup alembic

"""In your terminal, run the initialization command. This creates an alembic.ini file and an alembic/ folder.
alembic init alembic
"""

from sqlalchemy import String, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# 1. Define the Base class (Your equivalent of models.Model in Django)
class Base(DeclarativeBase):
    pass

# 2. Define your actual table
class MyTable(Base):
    __tablename__ = "my_table"
    
    # SQLAlchemy requires a primary key on every model
    id: Mapped[int] = mapped_column(primary_key=True)
    my_field: Mapped[str] = mapped_column(String(100))

