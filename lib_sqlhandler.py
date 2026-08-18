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

    @property 
    def engine(self):
        return create_engine(self.db_url, fast_executemany=True)
    
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
        # allow bulk inserts
        engine = self.engine
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

    """
    bulk data insert
    from sqlalchemy import insert
    from sqlalchemy import update

    # 1. Build a list of raw dictionaries (NO ORM objects)
    my_bulk_data = []
    for org in organizations:
        my_bulk_data.append({
            "name": org.name,
            "display_name": org.display_name,
            "state": org.state.name,
            # ... other fields ...
        })
        update_data = [
            {"id": 1, "state": "INACTIVE"},
            {"id": 2, "state": "ACTIVE"},
            # ... 249,998 more ...
        ]

    # 2. Execute the bulk insert
    with Session(engine) as session:
        session.execute(insert(CcmOrganisation), my_bulk_data)
        session.execute(update(CcmOrganisation), update_data)
        session.commit()
    
        from itertools import batched
        from sqlalchemy import insert

        with Session(engine) as session:
            # batched() automatically yields chunks of exactly 5000 items
            # and gracefully handles the smaller leftover chunk at the end!
            for chunk in batched(huge_list_of_items, 5000):
                
                # Convert the chunk into dictionaries
                batch_dicts = [{"name": item.name} for item in chunk]
                
                session.execute(insert(CcmOrganisation), batch_dicts)
                session.commit()
                
                print(f"Inserted batch of {len(batch_dicts)} rows..."

    def fetch_all_records_as_iterator(api_client):
    
    Wraps a paginated API into a seamless iterator.
    
    # Start with no page token
    next_page_token = None
    
    while True:
        # 1. Call the API, passing the token if we have one
        # (Adjust this to match your specific API's parameter names)
        response = api_client.get_data(page_token=next_page_token)
        
        # 2. Extract the list of records from this specific page
        records = response.get("data", [])
        
        # 3. Yield them one by one. This is what makes it an iterator!
        for record in records:
            yield record
            
        # 4. Check for the next page token
        next_page_token = response.get("next_page_token")
        
        # 5. Break the while loop if the API tells us there are no more pages
        if not next_page_token:
            break
    
        or
        # Yields every item in the list sequentially
        yield from response.get("data", [])


    """