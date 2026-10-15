"""This filename is lib_sqlhandler.py"""

#pip install sqlalchemy alembic pyodbc tomli
# check driver installed with cat /etc/odbcinst.ini



from dataclasses import dataclass, field
from datetime import datetime, timezone
import textwrap
import csv
import tomli
import urllib.parse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy import insert
import sqlhandler_models 
from lib_helper_lib import batched


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
            return result 
            if result.returns_rows:
                for row in result:
                    print(dict(row._mapping))

    def get_dataset(self, sql:str):
        with Session(self.engine) as session:
            # Execute the query and immediately fetch all results into a list.
            # The list of Row objects is detached from the session.
            result = session.execute(text(sql))
            # .all() returns a list of Row objects, which behave like tuples.
            # This list can be safely returned and used after the session is closed.
            return result.all()
            
    def truncate_table(self, tablename:str):
        engine = create_engine(self.db_url)
        with Session(engine) as session:
            # 1. Execute the raw TRUNCATE statement using your table name
            session.execute(text(f"TRUNCATE TABLE {tablename};"))
            # 2. Commit the transaction
            session.commit()
            print(f"Table {tablename} truncated.")

    def get_all_google_api_names(self) -> set[str]:
        """
        Fetches all 'name' values from the ccm_googleapi table into a set for efficient lookups.
        
        Returns:
            A set containing all API names from the database.
        """
        engine = self.engine
        with Session(engine) as session:
            statement = select(sqlhandler_models.CcmGoogleApi.name)
            # .scalars() fetches the first column of each row.
            # .all() gets all results into a list.
            # We convert to a set for O(1) average time complexity for lookups.
            api_names_list = session.execute(statement).scalars().all()
            return set(api_names_list)


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
    def import_file(self):
        
        fieldmapping = {
            'Plugin ID':'plugin_id',
            'CVE':'cve',
            'CVSS':'cvss',
            'Risk':'risk',
            'Host':'host',
            'Protocol':'protocol',
            'Port':'port',
            'Name':'name',
            'Synopsis':'synopsis',
            'Description':'description',
            'Solution':'solution',
            'See Also':'see_also',
            'Plugin Output':'plugin_output',
            'Asset UUID':'asset_uuid',
            #'Vulnerability State':'vulnerability_state',
            'IP Address':'ip_address',
            'FQDN':'fqdn',
            'NetBios':'netbios',
            'OS':'os',
            'MAC Address':'mac_address',
            'Plugin Family':'plugin_family',
            #'CVSS Base Score':'cvss_base_score',
            #'CVSS Temporal Score':'cvss_temporal_score',
            #'CVSS Temporal Vector':'cvss_temporal_vector',
            #'CVSS Vector':'cvss_vector',
            #'CVSS3 Base Score':'cvss3_base_score',
            #'CVSS3 Temporal Score':'cvss3_temporal_score',
            #'CVSS3 Temporal Vector':'cvss3_temporal_vector',
            #'CVSS3 Vector':'cvss3_vector',
            #'System Type':'system_type',
            'Host Start':'host_start',
            'Host End':'host_end',
            #'Vulnerability Priority Rating (VPR)':'vulnerability_priority_rating_vpr',
            'First Found':'first_found',
            'Last Found':'last_found',
            'Host Scan Schedule ID':'host_scan_schedule_id',
            'Host Scan ID':'host_scan_id',
            #'Indexed At':'indexed_at',
            #'Last Authenticated Results Date':'last_authenticated_results_date',
            #'Last Unauthenticated Results Date':'last_unauthenticated_results_date',
            #'Tracked':'tracked',
            #'Risk Factor':'risk_factor',
            #'Severity':'severity',
            #'Original Severity':'original_severity',
            #'Modification':'modification',
            #'Plugin Family ID':'plugin_family_id',
            #'Plugin Type':'plugin_type',
            #'Plugin Version':'plugin_version',
            #'Service':'service',
            #'Plugin Modification Date':'plugin_modification_date',
            #'Plugin Publication Date':'plugin_publication_date',
            #'Checks for Malware':'checks_for_malware',
            #'Exploit Available':'exploit_available',
            #'Exploited by Malware':'exploited_by_malware',
            #'Exploited by Nessus':'exploited_by_nessus',
            #'CANVAS':'canvas',
            #'D2 Elliot':'d2_elliot',
            #'Metasploit':'metasploit',
            #'Core Exploits':'core_exploits',
            #'ExploitHub':'exploithub',
            #'Default Account':'default_account',
            #'Patch Available':'patch_available',
            #'In The News':'in_the_news',
            #'Unsupported By Vendor':'unsupported_by_vendor',
            'Last Fixed':'last_fixed'
        }
        pass

    def readcsv_tenable(self, filepath:str):
        # =SUBSTITUTE(lower(G1)," ", "_")
        # =="""" &H1& """:row['" & G1 &"']," 
        with open( filepath,'r', encoding='utf-8') as f:
            csv_reader = csv.DictReader(f,skipinitialspace=True)
            c_records =0
            with Session(self.engine) as session:
                for chunk in batched(csv_reader, 500):
                    batch_dicts = []
                    for row in chunk:
                        c_records +=1
                        
                        batch_dicts.append({
                                "etl_filename": filepath,
                                "plugin_id": row['Plugin ID'],
                                "risk": row['Risk'],
                                "host": row['Host'],
                                "protocol": row['Protocol'],
                                "port": row['Port'],
                                "name": row['Name'],
                                "synopsis": row['Synopsis'],
                                "description": row['Description'],
                                "solution": row['Solution'],
                                "see_also": row['See Also'],
                                "plugin_output": row['Plugin Output'],    
                                "ip_address": row['IP Address'],
                                'host_start':row['Host Start'],
                                'host_end':row['Host End'],
                                "os":row["OS"],
                                'host_scan_schedule_id':row['Host Scan Schedule ID'],
                                'host_scan_id':row['Host Scan ID'],
                        })
                    print(f"Appending {c_records}")
                    session.execute(insert(sqlhandler_models.CcmTenableStaging), batch_dicts)
                    session.commit()

    def readcsv_dnszone(self, filepath:str):
        with open( filepath,'r', encoding='utf-8') as f:
            csv_reader = csv.DictReader(f,skipinitialspace=True)
            c_records =0
            with Session(self.engine) as session:
                for chunk in batched(csv_reader, 500):
                    batch_dicts = []
                    for row in chunk:
                        c_records +=1
                        
                        batch_dicts.append({
                            "etl_filename": filepath,
                            "rrid":row.get('rrid',None),
                            "owner":row.get('Owner',None),
                            "created":row.get('Created',None),
                            "encoding":row.get('Encoding',None),
                            "zone":row.get('Zone',None),
                            "dname":row.get('Dname',None),
                            "dname_clean":row.get('Dname','').removesuffix("."), 
                            "type":row.get('Type',None),
                            "class":row.get('Class',None),
                            "ttl":row.get('TTL',None),
                            "lname":row.get('Lname',None),
                            "info1":row.get('Info1',None),
                            "info2":row.get('Info2',None),
                            "info3":row.get('Info3',None),
                            "info4":row.get('Info4',None),
                            "info5":row.get('Info5',None),
                            "info6":row.get('Info6',None),
                            "info7":row.get('Info7',None),
                            "info8":row.get('Info8',None),
                            "reference":row.get('Reference',None),
                            "server_mask":row.get('Server Mask',None),
                            "timemask":row.get('Timemask',None),
                            "restrict_access":row.get('Restrict Access',None),
                            "monitor":row.get('Monitor',None),
                            "dead":row.get('Dead',None),
                            "suspended":row.get('Suspended',None),
                            "countflag":row.get('Countflag',None),
                            "modified":row.get('Modified',None),
                        })
                    print(f"Appending {c_records}")
                    session.execute(insert(sqlhandler_models.CcmDnsZoneStaging), batch_dicts)
                    session.commit()
        """
        TRUNCATE TABLE ccm_dnszone;
        INSERT INTO RPA_Reporting.dbo.ccm_dnszone
                    (created, [zone], dname_clean, [type], 
                    info1, info2, info3, info4, info5, info6, info7, info8, 
                    reference, modified)
                    SELECT DISTINCT created, [zone], dname_clean, [type], 
                        info1, info2, info3, info4, info5, info6, info7, info8, 
                        reference, modified 
                    FROM ccm_dnszone_staging;

        UPDATE dz 
            SET cmi_configurationitem_id = ci.id 
            FROM ccm_dnszone dz
            INNER JOIN cmi_configurationitem ci ON dz.dname_clean = ci.name; 
        
        """
        sql = r"""
            
            MERGE INTO cmi_configurationitem AS Target
                        USING 
                        (SELECT DISTINCT dname_clean 
                            FROM ccm_dnszone_staging 
                            WHERE dname_clean !='' AND dname_clean IS NOT NULL)
                        AS Source
                        ON Target.name = Source.dname_clean
                        WHEN MATCHED THEN
                            UPDATE SET
                                Target.lastseen = GETUTCDATE(),
                                Target.updated_on = GETUTCDATE()
                        WHEN NOT MATCHED BY TARGET THEN
                            INSERT (
                                lastseen, name, firstseen, activelabel, status_class
                            )
                            VALUES (
                                GETUTCDATE(), Source.dname_clean, GETUTCDATE(), 'dnszone', 'is-dnszone'
                            );
            UPDATE cmi_configurationitem 
            SET status_class = concat(status_class, ' is-dnszone')
            WHERE name in (SELECT dname_clean FROM ccm_dnszone_staging )
            AND status_class not like '%is-dnszone%';

        """       
        print(f"Merging configuration item data")
        self.execute_sql(sql)
        sql = """insert into cmi_itemlog (event, eventsource, eventsourceresource,description, configurationitem_id)
        select distinct 'itemlink', 'itemlink', 'dnszone', ds.info1 , cc1.id
        from ccm_dnszone_staging ds
        inner join cmi_configurationitem cc1 on ds.dname_clean = cc1.name 
        where not exists (select 1 from cmi_itemlog il 
        inner join cmi_configurationitem cc on il.configurationitem_id = cc.id 
        where il.description = ds.info1 and cc.name = ds.dname_clean and il.event='itemlink')
        and ds.type='a';"""
        print(f"Adding ItemLog records (CI->IP)")
        self.execute_sql(sql)
        sql="""MERGE INTO cmi_configurationitem AS Target
                        USING 
                        (SELECT DISTINCT info1 
                            FROM ccm_dnszone_staging 
                            WHERE info1 !='' AND info1 IS NOT NULL and type='a')
                        AS Source
                        ON Target.name = Source.info1
                        WHEN MATCHED THEN
                            UPDATE SET
                                Target.lastseen = GETUTCDATE(),
                                Target.updated_on = GETUTCDATE()
                        WHEN NOT MATCHED BY TARGET THEN
                            INSERT (
                                lastseen, name, firstseen, activelabel, status_class
                            )
                            VALUES (
                                GETUTCDATE(), Source.info1, GETUTCDATE(), 'ipaddress', 'is-ipaddress'
                            );"""        
        print(f"Adding IP Address as configuration item")
        self.execute_sql(sql)




