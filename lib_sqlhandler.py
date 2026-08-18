"""This filename is lib_sqlhandler.py"""

#pip install sqlalchemy alembic pyodbc tomli
# check driver installed with cat /etc/odbcinst.ini



from dataclasses import dataclass, field
from datetime import datetime, timezone
import textwrap
import tomli
import urllib.parse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
import sqlhandler_models 

myvar = textwrap.dedent("""\
        This is a long multi-line string inside a function.
        The backslash after the opening quotes prevents an 
        initial blank line, and dedent removes leading indentation.
    """)


@dataclass
class SqlAService():
    cloud_cmdb_database_name: str=""
    cloud_cmdb_database_host: str=""
    cloud_cmdb_database_user: str=""
    cloud_cmdb_database_password: str=""
    cloud_cmdb_database_driver:str = ""

    @property
    def db_url(self):
        db_url = (f"mssql+pyodbc://{self.cloud_cmdb_database_user}:" 
                  f"{self.cloud_cmdb_database_password}@"
                  f"{self.cloud_cmdb_database_host}/{self.cloud_cmdb_database_name}?"
                  f"driver={self.cloud_cmdb_database_driver}")
        return db_url
    def execute_sql(self, sql:str):
        # command line version, comes with the ODBC driver
        # sqlcmd -S 1.2.3.4 -U sqlserver -P "your_password" -d my_database -Q "SELECT * FROM Mytable;"
        """
        # 2. Open a session (Transaction block)
        with Session(engine) as session:
            
            print("\n--- INSERTING DATA ---")
            # Instantiate your model
            new_record = MyTable(my_field="hello world")
            
            # Add to session and commit (Django's new_record.save())
            session.add(new_record)
            session.commit()
            print("Inserted successfully!")

            print("\n--- SELECTING DATA ---")
            # Build the query (Django's MyTable.objects.all())
            statement = select(MyTable)
            
            # Execute and get scalar results
            results = session.execute(statement).scalars().all()
            
            for row in results:
                print(f"ID: {row.id} | Field: {row.my_field}")
        """
        engine = create_engine(self.db_url)
        """with engine.connect() as connection:
            # Wrap your raw SQL string in the text() function
            result = connection.execute(text(sql))
            connection.commit()
        """  
        with engine.begin() as connection:
            result = connection.execute(text(sql)) 
            print(f"Affected {result.rowcount} rows.")
            # Check if the query actually returned data (like a SELECT) before looping
            if result.returns_rows:
                for row in result:
                    print(dict(row._mapping))

            
    def truncate_table(self, tablename:str):
        engine = create_engine(self.db_url)
        with Session(engine) as session:
            # 1. Execute the raw TRUNCATE statement using your table name
            session.execute(text(f"TRUNCATE TABLE {tablename};"))
            # 2. Commit the transaction
            session.commit()
            print(f"Table {tablename} truncated.")