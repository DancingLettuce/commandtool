
"""This filename is commandtool.py"""
# call with py -m commandtool.commandtool from parent

"""
Installation guide

rsync -avz -e "ssh -i path-to-cert" path-to-dev/pythondev/commandtool/*.py 
    user@ipaddress:path-to-dev/pythondev/commandtool/
sudo apt update && sudo apt install rsync -y

"""
#1832

import argparse   
from pathlib import Path
import sys  
import csv


def init_argparse():
    parser = argparse.ArgumentParser()
    epilog=""">>Command Tool"""
    description = ('cli')
    parser = argparse.ArgumentParser()
    parser = argparse.ArgumentParser(
            description=description,
            epilog=epilog,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            prog="commandtool.py"  # Explicitly set the program name for help messages
            )
    parser.add_argument(
            'command',
            type=str,
            nargs='?',
            help="""The command to execute (e.g. upload | transcribe | 
        """
        )
    parser.add_argument(
            'param1',
            type=str,
            nargs='?',
            help="The parameter for the command ."
        )
    parser.add_argument(
            'param2',
            type=str,
            nargs='?',
            help="The parameter for the command ."
        )
    parser.add_argument('--filename', help='filename to parse')
    parser.add_argument("--debug",  action="store_true",   help="Show the debug logs")
    parser.add_argument("--truncate",  action="store_true",   help="Truncate the target first")
    parser.add_argument("--testrun",  action="store_true",   help="This is a testrun")
    parser.add_argument("--interactive",  action="store_true",   help="Interactive to get input")
    parser.add_argument("--uselocallist",  action="store_true",   help="Use value of lib_localtest.locallist")
    parser.add_argument(
        "--configfile", 
        type=Path, # Argparse will automatically convert the string input to a Path object
        default=DEFAULT_CONFIG_PATH,
        help="Path to the TOML configuration file."
        )
    #ARGS = parser.parse_args()
    ARGS, unknown = parser.parse_known_args()
    # Convert the list of unknown args into a dictionary
    # This assumes the format is strictly --key value --key2 value2
    arbitrary_args = {}
    for i in range(0, len(unknown), 2):
        if unknown[i].startswith('--'):
            # Strip the '--' from the key
            key = unknown[i].lstrip('-')
            # Assign the next item as the value
            value = unknown[i+1] if (i + 1) < len(unknown) else True
            arbitrary_args[key] = value
    return ARGS,  arbitrary_args

TOML_STRING="""# Auto-generated default configuration
    SSH_CERTIFICATE_FILE=""
    MEDIA_SOURCE=""
    SCP_DESTINATION_PATH=""
    TRANSCRIBER_PROJECT_ID=""
    SERVICE_ACCOUNT_FILE=""
    SEMANTIC_DATABASE=""
    SEMANTIC_USER=""
    SEMANTIC_PASSWORD=""
    SEMANTIC_IP=""
    ADMIN_EMAIL = ""
    VAULT_MATTER_ID = ""
    BASE_DOWNLOAD_DIR="" 
    DRIVE_PARENT_FOLDER_ID=""
    DRIVE_OWNER_EMAIL=""
    DJANGO_ROOT=""
    DJANGO_SETTINGS_MODULE=""
    GOOGLE_GROUP_HIGHLIGHT=[] 
    GOOGLEUSER_ACCOUNT_PASSWORD_DEFAULT = ""
    GOOGLEUSER_DEFAULT_HOLD_OU = ""
    TRANSCRIBE_PROMPT_ADDITIONAL_1 = ""
    TRANSCRIBE_OWNER_EMAIL = ""
    TRANSCRIBE_FOLDER_ID = ""
    TRANSCRIBE_LECTURE_FOLDER_ID = ""
    CLOUD_CMDB_DATABASE_NAME = ""
    CLOUD_CMDB_DATABASE_HOST = ""
    CLOUD_CMDB_DATABASE_USER = ""
    CLOUD_CMDB_DATABASE_PASSWORD = ""
    CLOUD_CMDB_DATABASE_DRIVER = ""
    """ 
SCRIPT_DIR = Path(__file__).resolve().parent 
#DEFAULT_CONFIG_PATH = SCRIPT_DIR / "secrets.toml" # for a local secrets or config file
DEFAULT_CONFIG_PATH = SCRIPT_DIR.parent / "secrets" / "secrets.toml"
DEFAULT_LOG_PATH = SCRIPT_DIR / "log.txt"
ALLOWED_COMMANDS={
    'menu':"", 'questionary':"",'upload':"param1=folder location (default=.MP3)",'transcribe':"",
    'vault':"",'test':"",'approve_deviceuser':"",
    'delete_device':"",'list_delegates':"",'get_users':"",
    'list_user_groups':"",'delegate_sheet':"",
    'unsuspendmoveouresetpassword':"",'transcribe_lecture':"param1=folderid",
    'search_object':"",'moveou':"", "upload_file":"param1=folderid",
    "deprovision_user":"", "unsuspend_user":"", "suspend_user":"",
    "delegate_account":"param1=mailbox param2=userwithaccess",
    "listallprojects":"all | quick","listallorganisations":"","listallfolders":"",
    "listallinstances":"param1=project_id","listallloadbalancers":"param1=project_id",
    "listapis":"project_id",
    "ingesttenable": "file_path",
    "ingestdnszone": "file_path",
    "csvexplode":r"filepath col(default=4)",
    "securityreset":"Delete passkey, Force PW change, Reset backup codes, Delete oAuth",
    "accountreset": "userlist,options (p=reset pw, o=move ou, a=delete oauth," +
    "b=reset backup codes,u=unsuspend/unarchive," + 
    "r=reset sign in,u=unsuspend,s=suspend " +
    "g=delete groups) eg poabusg",
    "syncalldirectoryusers":"",
    "logoutstaleusers":""
    }
  
ARGS, ARBITRARY_ARGS = init_argparse()
import lib_helper_lib as helperlib 
CONFIG = helperlib.init_secrets(toml_string=TOML_STRING,filename=ARGS.configfile) 
 
from datetime import datetime as dt_datetime, timedelta  , timezone as dt_timezone 
import subprocess
import json 
import os  
 

try:
    import questionary #pip install questionary 
    imports_questionary = True
except Exception as e:
    print(f"WARNING: Can not import Questionary {e}")
    imports_questionary = False  

try:
    if CONFIG['DJANGO_ROOT'] not in sys.path:
        sys.path.insert(0, CONFIG['DJANGO_ROOT'])
    # 3. Tell Django where the settings module is
    os.environ.setdefault('DJANGO_SETTINGS_MODULE',CONFIG['DJANGO_SETTINGS_MODULE'])
    # 4. Boot up the Django engine
    import django
    django.setup()
    import_djangoapp = True
except Exception as e:
    import_djangoapp = False
    print(f"WARNING: Can not import DjangoApp {e}")

try:
    import lib_transcribe 
    import_lib_transcribe = True
except Exception as e:
    import_lib_transcribe = False
    print(f"WARNING: Can not import lib_transcribe {e}")
 
try:
    import lib_googlehandler
    import_lib_googlehandler = True
except Exception as e:
    import_lib_googlehandler = False
    print(f"WARNING: Can not import lib_googlehandler {e}")

try:
    import lib_localtest
    import_lib_localtest = True
except Exception as e:
    import_lib_localtest = False
    print(f"WARNING: Can not import lib_localtest {e}")

try:
    import lib_djangoapp
    import_lib_djangoapp = True
except Exception as e:
    import_lib_djangoapp = False
    print(f"WARNING: Can not import lib_djangoapp {e}")

try:
    import lib_sqlhandler 
    import_lib_sqlhandler = True
except Exception as e:
    import_lib_sqlhandler = False
    print(f"WARNING: Can not import lib_sqlhandler {e}")

def upload_recent_file(folder_path: str,filetype: str='.mp3', days=7):
    file_to_copy= get_file(folder_path=folder_path, filetype=filetype, days=7)


    print(f"\nInitiating transfer for: {file_to_copy} to {CONFIG['SCP_DESTINATION_PATH']}") 
     
    # Construct the scp command as a list of arguments
    scp_command = [
        "scp", 
        "-i", CONFIG["SSH_CERTIFICATE_FILE"], 
        file_to_copy,  
        CONFIG["SCP_DESTINATION_PATH"]
    ]
    
    # Execute the command
    try:
        # check=True will raise an exception if the scp command fails
        subprocess.run(scp_command, check=True)
        print("\nTransfer completed successfully!")
        new_filename = f"{file_to_copy}.bak"

        try:
            # Rename the file
            os.rename(file_to_copy, new_filename)
            print(f"Successfully renamed '{file_to_copy}' to '{new_filename}'")
        except FileNotFoundError:
            print(f"Error: The file '{file_to_copy}' could not be found in the current directory.")
        except PermissionError:
            print(f"Error: Insufficient permissions to rename '{file_to_copy}'.")
        except Exception as e:
            print(f"ERROR renameing {file_to_copy} to {new_filename} {e}")
    except subprocess.CalledProcessError as e:
        print(f"\nError: The transfer failed. {e}")

def get_file(folder_path: str,filetype: str='.mp3', days=7):
    folder = Path(folder_path)
    print(f"Searching folder {folder.resolve()}" )   
    # Verify the directory exists
    if not folder.exists() or not folder.is_dir():
        print(f"Error: The directory '{folder_path}' does not exist or is not a folder.")
        return

    # Calculate the timestamp for exactly 7 days ago
    one_week_ago = dt_datetime.now() - timedelta(days=days)
    one_week_ago_ts = one_week_ago.timestamp()

    # List to store the matching files  
    recent_files = []  

    # Iterate through files in the directory
    for file_path in folder.iterdir():
        # Check if it's a file and ends with .mp3 (handling both .mp3 and .MP3)
        if (file_path.is_file() and 
            file_path.suffix.lower() == (filetype if filetype else file_path.suffix.lower())
            and not file_path.name.startswith(".")
            ):
            file_stat = file_path.stat()
            mod_time = file_stat.st_mtime
            
            # Filter for files updated in the past week
            if mod_time >= one_week_ago_ts:
                size_bytes = file_stat.st_size
                size_mb = size_bytes / (1024 * 1024) # Convert bytes to Megabytes
                
                # Format the timestamp into a readable date/time string
                mod_date = dt_datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
                
                recent_files.append({
                    'name': file_path.name,
                    'full_path': file_path, # Store the full Path object for scp
                    'updated': mod_date,
                    'size_mb': size_mb,
                    'timestamp': mod_time
                })
                
    recent_files.sort(key=lambda x: x['timestamp'], reverse=True)  
    
    # Output the results and prompt user
    if not recent_files:
        print(f"No {filetype} files updated in the past {days} days were found.")
        return 

    print(f"{'No.':<4} | {'Filename':<35} | {'Date Updated':<20} | {'Size'}")
    print("-" * 75)
    
    # Enumerate adds a counter starting at 1
    for i, f in enumerate(recent_files, start=1):
        # Truncate filename if it's too long to keep the table neat
        display_name = f['name'] if len(f['name']) <= 35 else f['name'][:32] + "..."
        print(f"{i:<4} | {display_name:<35} | {f['updated']:<20} | {f['size_mb']:.2f} MB")

    # User Selection Loop
    while True:
        choice = input(f"\nEnter the number of the file to transfer (1-{len(recent_files)}) or 'q' to quit: ")
        
        if choice.lower() == 'q':
            print("Exiting...")
            return
            
        try:
            selected_index = int(choice)
            if 1 <= selected_index <= len(recent_files):
                break # Valid selection, break out of loop
            else:
                print(f"Invalid selection. Please choose a number between 1 and {len(recent_files)}.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    # Get the selected file's data
    selected_file = recent_files[selected_index - 1]
    file_to_copy = str(selected_file['full_path'])
    return(file_to_copy)

def transcribe_mp3():
    file_to_transcribe = get_file(folder_path='', filetype='.mp3', days=99)
    if not file_to_transcribe:
        print(f"No file")
        sys.exit()   
    print("Provide additional supplied context")
    supplied_context = helperlib.get_multiline_input()
    transcribe = lib_transcribe.Transcriber(project_id=CONFIG['TRANSCRIBER_PROJECT_ID'],
            service_account_file=CONFIG['SERVICE_ACCOUNT_FILE'],
            semantic_user=CONFIG['SEMANTIC_USER'],
            semantic_password=CONFIG['SEMANTIC_PASSWORD'],
            semantic_database=CONFIG['SEMANTIC_DATABASE'],
            semantic_ip=CONFIG['SEMANTIC_IP'],
            supplied_context=supplied_context, 
            )    
    meeting_data = transcribe.transcribe_audio_text(audio_file_path=file_to_transcribe) 
    #text_vector = transcribe.generate_text_vector(meeting_data['meeting_summary'])
    #transcribe.insert_semantic_json(meeting_data)  
    new_filename = f"{file_to_transcribe}.transcribed"

    try:
        # Rename the file
        os.rename(file_to_transcribe, new_filename)
        print(f"Successfully renamed '{file_to_transcribe}' to '{new_filename}'")
    except FileNotFoundError:
        print(f"Error: The file '{file_to_transcribe}' could not be found in the current directory.")
    except PermissionError:
        print(f"Error: Insufficient permissions to rename '{file_to_transcribe}'.")
    except Exception as e:
        print(f"ERROR renaming {file_to_transcribe} to {new_filename} {e}")   

def approve_deviceuser(delegated_email, service_account_file):
    gh = lib_googlehandler.GoogleService(
            delegated_email=delegated_email,
            service_account_file=service_account_file,
            )
    svc = gh.get_serviceaccount_service(api_servicename='cloudidentity', 
                                        api_version='v1')
    device_users_to_approve = [] 
    processed_count = 0 
    for device_user_name in device_users_to_approve:
        processed_count += 1  
        print(f'{processed_count}/{len(device_users_to_approve)} {device_user_name}')
        gh.evaluate_and_approve_device_user(service=svc,
                                        device_user_name=device_user_name)
    print("done")
    
def delete_devices(delegated_email, service_account_file):
    gh = lib_googlehandler.GoogleService(
            delegated_email=delegated_email,
            service_account_file=service_account_file,
            )
    svc = gh.get_serviceaccount_service(api_servicename='cloudidentity', 
                                        api_version='v1')
    device_to_delete = lib_localtest.devices_to_delete.splitlines() 
    processed_count = 0 
    for device_name in device_to_delete:
        processed_count += 1  
        print(f'{processed_count}/{len(device_to_delete)} {device_name}')
        gh.delete_company_device(service=svc, 
                                        device_name=device_name)
    print("done")
 
def get_interactive_list(default_interactive=None):
    """Returns list of entries"""
    interactive_list = []
    if ARGS.uselocallist:
        interactive_list = lib_localtest.locallist
    else:    
        if ARGS.interactive:
            interactive_list = helperlib.get_multiline_input()
        elif ARGS.param1:
            interactive_list = ARGS.param1
        else:
            interactive_list = default_interactive
    if isinstance(interactive_list, str):
        # Split the string by newlines or commas, strip whitespace from each item,
        # and filter out any empty entries that might result.
        return [item.strip() for item in interactive_list.replace(',', '\n').splitlines() if item.strip()]
    return interactive_list # Return as-is if it's already a list

def list_delegates(delegated_email, service_account_file):
    #account_emails = helperlib.get_multiline_input()
    account_emails = get_interactive_list(default_interactive=lib_localtest.delegateaccount)
    
    gh = lib_googlehandler.GoogleService(
            delegated_email=delegated_email,
            service_account_file=service_account_file,
            )
    #svc = gh.get_serviceaccount_service(api_servicename='gmail', 
    #                                    api_version='v1',
    #                                    delegated_email=account_emails 
    #                                    )
    message= ""
    for account_email in account_emails:
        if not account_email:
            continue
        delegates = gh.list_delegates(account_email)
        message += '\n' if message else '' 
        message += f"Delegates of {account_email}: "

        for delegate in delegates.get('delegates',{}):
            if delegate:
                message += delegate.get('delegateEmail')
                if delegate.get('verificationStatus','') != 'accepted':
                    message += f"(*NotAccepted*)"
                message += "; "

    print(f"{message}") 

def get_users(delegated_email, service_account_file):
    account_emails = get_interactive_list(default_interactive=lib_localtest.delegateaccount)
    message= ""
    gh = lib_googlehandler.GoogleService(
            delegated_email=delegated_email,
            service_account_file=service_account_file,
            )
    for account_email in account_emails:
        if not account_email:
            continue
        account = gh.get_user(account_email)
        message += '\n' if message else '' 
        message += f"User {account_email}: "
        message += f"\nOU:{account.get('orgUnitPath','')} "
        message += f"\nLogin:{account.get('lastLoginTime','')} "
        if account.get('suspended','') or account.get('archived',''):
            message += f" /Inactive ({'S' if account.get('suspended','') else ''}{'A' if account.get('archived','') else ''} )"
        message += f"\nCreated:{account.get('creationTime','')} "
        
    print(f"{message}") 

def get_google_users(delegated_email, service_account_file,google_group_highlight=[] ):
    account_emails = get_interactive_list(default_interactive=lib_localtest.delegateaccount)
    gh = lib_googlehandler.GoogleService(
            delegated_email=delegated_email,
            service_account_file=service_account_file,)
    message= ""
    for account_email in account_emails:
        if not account_email:
            continue
        gu = gh.get_googleuser(account_email=account_email, google_group_highlight=google_group_highlight) 
        print()
        print("*" * 80)
        print(gu.to_str())
        if gu.error:
            return  


        print(gu.delegates_to_str())  
        print(gu.groups_to_str())  
        if gu.is_in_google_group_highlight:
            print("Is found in control group")
        else:
            print("MISSING from control group") 
        cmi = lib_djangoapp.get_cmi(account_email)
        if cmi.description:
            print(cmi.description)
        
        print()

def list_user_groups(delegated_email, service_account_file):
    account_emails = get_interactive_list(default_interactive=lib_localtest.delegateaccount)
    gh = lib_googlehandler.GoogleService(
            delegated_email=delegated_email,
            service_account_file=service_account_file,)  
    for account_email in account_emails:
        if not account_email:
            continue
        groups = gh.list_user_groups(account_email=account_email)
    print(groups) 

def delegate_sheet():
    sheet_text = helperlib.get_multiline_input()
    gh = lib_googlehandler.GoogleService(
            delegated_email=CONFIG.get('ADMIN_EMAIL',None),
            service_account_file=CONFIG.get('SERVICE_ACCOUNT_FILE',None),
            )
    for line in sheet_text.splitlines():
        #account-to-delegate,delegate-to,notify
        line = line.replace(' ',',').replace("\t",",").split(",")
        ac_todelegate=line[1]
        gu = gh.get_googleuser(
            account_email=ac_todelegate, 
            google_group_highlight=CONFIG.get('GOOGLE_GROUP_HIGHLIGHT',[]) )
        print(gu.to_str() ) 
        
        print(line)

def sync_all_directory_users(delegated_email, service_account_file):
    """
    Fetches all Google Workspace users via the Directory API.
    Chunks 10 pages (up to 5,000 users) into memory before executing
    batch DB lookups and bulk operations to drastically reduce DB hits.
    """
    # quick import
    from gwa import models as gwa_models
    from django.db import connection
    from googleapiclient.errors import HttpError
    import time
    from django.utils import timezone
    from django.utils.dateparse import parse_datetime
    
    # Setup the Client
    gh = lib_googlehandler.GoogleService(
                delegated_email=delegated_email,
                service_account_file=service_account_file,)
    
    service = gh.get_serviceaccount_admin 
    
    table_name = gwa_models.StagingGoogleUser._meta.db_table
    print(f"Truncating staging table: {table_name}")
    with connection.cursor() as cursor:
        cursor.execute(f'TRUNCATE TABLE {table_name};')

    page_token = None
    page_count = 0
    total_processed = 0
    
    # --- Buffers for chunking ---
    chunk_users_payload = []
    pages_in_chunk = 0

    print("Querying Directory API... (Alphabetical order by email)")
    
    while True:
        page_count += 1
        pages_in_chunk += 1
        response = None
        max_retries = 5
        retry_attempt = 0
        
        # 1. Inner Retry Loop for API Limits
        while retry_attempt < max_retries:
            try:
                print(f"Calling API page {page_count}")
                response = service.users().list(
                    customer='my_customer',
                    maxResults=500,
                    pageToken=page_token
                ).execute()
                break  
                
            except HttpError as e:
                if e.resp.status in [503, 429, 500, 502, 504]:
                    retry_attempt += 1
                    print(f"[{e.resp.status}] Google backend busy. Sleeping 30s (Attempt {retry_attempt}/{max_retries})...")
                    time.sleep(30)
                else:
                    print(f"CRITICAL HTTP ERROR on page {page_count}: {e}")
                    raise e
            except Exception as e:
                print(f"CRITICAL UNKNOWN ERROR on page {page_count}: {e}")
                raise e
                
        if not response:
            print(f"Failed to fetch page {page_count}. Aborting sync.")
            break

        # 2. Add this page's users to our memory buffer
        users_on_page = response.get('users', [])
        chunk_users_payload.extend(users_on_page)
        
        page_token = response.get('nextPageToken')

        # 3. Process the chunk if we hit 10 pages OR if this is the very last page
        if pages_in_chunk == 10 or not page_token:
            if chunk_users_payload:
                print(f"Processing chunk of {len(chunk_users_payload)} users...")
                current_time = timezone.now()
                
                batch_emails = [u.get('primaryEmail') for u in chunk_users_payload if u.get('primaryEmail')]
                
                # One single database read for 5,000 emails
                existing_users_qs = gwa_models.GoogleUser.objects.filter(email__in=batch_emails)
                existing_users_map = {user.email: user for user in existing_users_qs}
                existing_users_qs = None
                existing_users_map = None
                
                to_create = []
                to_update = []
                
                for u in chunk_users_payload:
                    email = u.get('primaryEmail')
                    if not email:
                        continue
                        
                    created_str = u.get('creationTime')
                    login_str = u.get('lastLoginTime')
                    
                    parsed_created = parse_datetime(created_str) if created_str else None
                    parsed_login = parse_datetime(login_str) if login_str else None
                    
                    new_user = gwa_models.StagingGoogleUser(
                            email=email,
                            api_lastseen=current_time,
                            ou=u.get('orgUnitPath', ''),
                            suspended=u.get('suspended', False),
                            archived=u.get('archived', False),
                            account_created=parsed_created,
                            last_login=parsed_login,
                            isadmin=u.get('isAdmin', False),
                            isdelegatedadmin=u.get('isDelegatedAdmin', False),
                            api_data=u
                        )
                    to_create.append(new_user)
                        
                # 4. Execute the Bulk Operations safely with batch_size
                # 10 fields * 200 batch_size = 2000 parameters (safely under SQL Server's 2100 limit)
                if to_create:
                    gwa_models.StagingGoogleUser.objects.bulk_create(to_create, batch_size=200)
                    
                
                    
                total_processed += len(chunk_users_payload) 
                print(f"-> DB Flush Complete | Inserted: {len(to_create)} | Updated: {len(to_update)} | Cumulative Total: {total_processed} email {email}  ")

            # Reset the buffers for the next 10 pages
            chunk_users_payload = []
            pages_in_chunk = 0

        # Exit condition 
        if not page_token:
            break


    SQL="""truncate table gwa_googleuser;
    INSERT INTO gwa_googleuser(email, chit, api_lastseen, ou, suspended, archived, account_created, last_login, api_data, isadmin, isdelegatedadmin)
    SELECT email, chit, api_lastseen, ou, suspended, archived, account_created, last_login, api_data, isadmin, isdelegatedadmin
    FROM gwa_staginggoogleuser ;"""
    print(f"Truncating GoogleUser and inserting from staging.")
    with connection.cursor() as cursor:
        cursor.execute(SQL)   

    print(f"Sync complete! Total Users Processed: {total_processed}")
    
def logout_stale_users(delegated_email, service_account_file, days_stale=60):
    """
    Finds all active users who haven't logged in for 'days_stale' (default 90)
    and hits the Google Directory API to force a sign-out (revoke tokens).
    Uses .iterator() to process large datasets without memory crashes.
    """
    from gwa import models as gwa_models
    from django.db import connection
    from googleapiclient.errors import HttpError
    import time
    from django.utils import timezone
    from django.utils.dateparse import parse_datetime
    from django.db.models import Q
    
    # Setup the Client
    gh = lib_googlehandler.GoogleService(
                delegated_email=delegated_email,
                service_account_file=service_account_file,)
    
    service = gh.get_serviceaccount_admin 
    
    cutoff_date = timezone.now() - timedelta(days=days_stale)
    print(f"Starting stale user logout. Cutoff date: {cutoff_date.strftime('%Y-%m-%d')}")
    
    # Query: Not suspended, not archived.
    # AND (last_login is older than cutoff OR (last_login is NULL and account is older than cutoff))
    stale_users_qs = gwa_models.GoogleUser.objects.filter(
        suspended=False,
        archived=False
    ).filter(
        Q(last_login__lte=cutoff_date) | 
        Q(last_login__isnull=True, account_created__lte=cutoff_date)
    )
    
    total_stale = stale_users_qs.count()
    print(f"Found {total_stale} users matching criteria. Starting sign-out process...")
    
    if total_stale == 0:
        return
        
    success_count = 0
    error_count = 0
    processed_count = 0
    
    # Use .iterator(chunk_size) to safely stream the 80k users from SQL Server
    for user in stale_users_qs.iterator(chunk_size=2000):
        processed_count += 1                
        user_email = user.email
        
        # Inner Retry Loop for API Limits (429/503)
        max_retries = 3
        retry_attempt = 0
        while retry_attempt < max_retries:
            try:
                # Execute the sign-out command
                service.users().signOut(userKey=user_email).execute()
                success_count += 1
                break
                
            except HttpError as e:
                # Catch 503 (Unavailable) and 429 (Rate Limit)
                if e.resp.status in [503, 429, 500, 502, 504]:
                    retry_attempt += 1
                    time.sleep(2)  # Short sleep, signOut API recovers fast
                else:
                    # 404 (User not found) or 403 (Forbidden)
                    error_count += 1
                    print(f"[{processed_count}/{total_stale}] HTTP Error signing out {user_email}: {e.resp.status}")
                    break
            except Exception as e:
                error_count += 1
                print(f"[{processed_count}/{total_stale}] Unknown Error for {user_email}: {e}")
                break
                
        # Progress logging
        if processed_count % 10 == 0:
            print(
                f"Progress: {processed_count}/{total_stale} processed. "
                f"(Success: {success_count}, Errors: {error_count}) "
            )
            
    print(
        f"Stale User Logout Complete! "
        f"Processed: {processed_count}, Success: {success_count}, Errors: {error_count}. "
    )




def main():
    tdiff = helperlib.TimeDiff()
    fl = helperlib.ScriptLog()   
    args_command = ARGS.command 
    args_param1 = ARGS.param1
    args_param2 = ARGS.param2
    
    if args_command and args_command.startswith('*'):
        allowed_commands_str = '\n** '.join(
            f"{key} {value}" 
            for key, value in ALLOWED_COMMANDS.items()
            if args_command[1:].lower() in key.lower())

        print(f'Command filter on {args_command[1:]}')
        print(f"** {allowed_commands_str}")

    elif args_command not in ALLOWED_COMMANDS.keys(): 
        allowed_commands_str = '\n** '.join(f"{key} {value}" for key, value in ALLOWED_COMMANDS.items())
        print(f"Command {args_command} not found. The possible commands are: {allowed_commands_str}")
    if (args_command == 'menu' or ARGS.command=='questionary') :
        if not imports_questionary:
            print(f"ERROR. Command line command {args_command} requires Questionary")
        else:
            pass # do menu  
    elif args_command == 'upload':
        folder_source = ''
        if args_param1:
            folder_path = args_param1
            filetype = ''
        else:
            folder_path = CONFIG["MEDIA_SOURCE"]
            filetype = '.mp3'
        print(folder_path) 
        upload_recent_file(folder_path=folder_path, filetype=filetype,  days=7)    
        fl.print_log_file("jj", summary=True ) 
    elif args_command == 'transcribe':
        transcribe_mp3()
    elif args_command == 'vault':
        googlehandler = lib_googlehandler.GoogleService(
            delegated_email=CONFIG['ADMIN_EMAIL'],
            service_account_file=CONFIG['SERVICE_ACCOUNT_FILE'],
            vault_matter_id=CONFIG['VAULT_MATTER_ID'],
            base_download_directory=CONFIG['BASE_DOWNLOAD_DIR'],
            drive_parent_folder_id=CONFIG['DRIVE_PARENT_FOLDER_ID'],
            drive_owner_email=CONFIG['DRIVE_OWNER_EMAIL'],
            )
        export_id, export_name = googlehandler.pick_vault_export()
        googlehandler.download_vault_export(export_id=export_id, 
                                            export_name=export_name) 
    elif args_command == 'test':
        if not import_lib_localtest:
                    print("No local test, exiting")
                    return
        sqlh = lib_sqlhandler.SqlAService(
            cloud_cmdb_database_name =CONFIG.get('CLOUD_CMDB_DATABASE_NAME',''), 
            cloud_cmdb_database_host = CONFIG.get('CLOUD_CMDB_DATABASE_HOST',''),
            cloud_cmdb_database_user = CONFIG.get('CLOUD_CMDB_DATABASE_USER',''),
            cloud_cmdb_database_password = CONFIG.get('CLOUD_CMDB_DATABASE_PASSWORD',''),
            cloud_cmdb_database_driver = CONFIG.get('CLOUD_CMDB_DATABASE_DRIVER',''),
        )
        sqlh.execute_sql(lib_localtest.mysql)
        """
        if not import_lib_localtest:
            print("No local test, exiting")
            return
        transcribe_owner_email = CONFIG.get('TRANSCRIBE_OWNER_EMAIL',"")
        print(f"Creating document in {transcribe_owner_email}'s account...")

        gh = lib_googlehandler.GoogleService(
                drive_owner_email=transcribe_owner_email,
                service_account_file=CONFIG.get('SERVICE_ACCOUNT_FILE',""),
                )
        print("created gh")
        print(CONFIG.get('SERVICE_ACCOUNT_FILE',""))
        gh.create_document(
            parent_folder_id=CONFIG.get('TRANSCRIBE_FOLDER_ID',""),
            filename="myfile",
            body_text="mytext"
            )
        print("done")
        """
    elif args_command == 'approve_deviceuser':
        approve_deviceuser(
                delegated_email=CONFIG['ADMIN_EMAIL'],
                service_account_file=CONFIG['SERVICE_ACCOUNT_FILE'],)
    elif args_command == 'delete_device':
        delete_devices( 
            delegated_email=CONFIG['ADMIN_EMAIL'],
            service_account_file=CONFIG['SERVICE_ACCOUNT_FILE'],)
    elif args_command == 'list_delegates' :
        list_delegates(
            delegated_email=CONFIG['ADMIN_EMAIL'],
            service_account_file=CONFIG['SERVICE_ACCOUNT_FILE'],)
    elif args_command == 'get_users':
        get_google_users( 
            delegated_email=CONFIG.get('ADMIN_EMAIL',''), 
            service_account_file=CONFIG.get('SERVICE_ACCOUNT_FILE',''),
            google_group_highlight=CONFIG.get('GOOGLE_GROUP_HIGHLIGHT',[])) 
    elif args_command == 'list_user_groups':
        list_user_groups(  
            delegated_email=CONFIG['ADMIN_EMAIL'], 
            service_account_file=CONFIG['SERVICE_ACCOUNT_FILE'],)
    elif args_command == 'delegate_sheet':
        delegate_sheet() 
    elif args_command in ('unsuspendmoveouresetpassword','suspend_user',
                            'unsuspend_user'):
        unsuspend=False
        resetpassword=False
        movetodefaultou = False
        suspend = False
        if args_command == 'unsuspendmoveouresetpassword':
            unsuspend=True
            resetpassword=True
            movetodefaultou = True
        elif args_command == 'suspend_user':
            suspend = True
        elif args_command == 'unsuspend_user':
            unsuspend=True
        else:
            print("ERROR IN COMMAND")
            return 
        gh = lib_googlehandler.GoogleService(
                        delegated_email=CONFIG.get('ADMIN_EMAIL',""),
                        service_account_file=CONFIG.get('SERVICE_ACCOUNT_FILE',""),
                        google_group_highlight=CONFIG.get('GOOGLE_GROUP_HIGHLIGHT',[]) ,
                        googleuser_account_password_default=CONFIG.get('GOOGLEUSER_ACCOUNT_PASSWORD_DEFAULT',""),
                        googleuser_default_hold_ou=CONFIG.get('GOOGLEUSER_DEFAULT_HOLD_OU',""),
                        )
        account_emails = get_interactive_list()
        message= ""
        for account_email in account_emails:
            if not account_email:
                continue
            response = gh.patch_user(account_email=account_email, unsuspend=unsuspend,
                                     resetpassword=resetpassword, 
                                     movetodefaultou=movetodefaultou,
                                     suspend=suspend,)
            print(f"{account_email} {response}")
    elif args_command == 'moveou':
            gh = lib_googlehandler.GoogleService(
                            delegated_email=CONFIG.get('ADMIN_EMAIL',""),
                            service_account_file=CONFIG.get('SERVICE_ACCOUNT_FILE',""),
                            google_group_highlight=CONFIG.get('GOOGLE_GROUP_HIGHLIGHT',[]) ,
                            googleuser_account_password_default=CONFIG.get('GOOGLEUSER_ACCOUNT_PASSWORD_DEFAULT',""),
                            googleuser_default_hold_ou=CONFIG.get('GOOGLEUSER_DEFAULT_HOLD_OU',""),
                            )
            account_emails = get_interactive_list()
            for account_email in account_emails:
                if not account_email:
                    continue
                response = gh.patch_user(account_email=account_email, unsuspend=False,
                                         resetpassword=False, 
                                         movetodefaultou=True)
                print(f"{account_email} {response}")
    elif args_command == 'transcribe_lecture':
        file_to_transcribe = get_file(folder_path='', filetype='.mp3', days=99)
        if not file_to_transcribe:
            print(f"No file")
            sys.exit()   
        print("Provide additional supplied context")
        supplied_context = helperlib.get_multiline_input()
        transcribe = lib_transcribe.Transcriber(
                project_id=CONFIG.get('TRANSCRIBER_PROJECT_ID',""),
                service_account_file=CONFIG.get('SERVICE_ACCOUNT_FILE',""),
                supplied_context=supplied_context, 
                )    
        transcript_text = transcribe.transcribe_audio_lecture(audio_file_path=file_to_transcribe) 
        new_filename = f"{file_to_transcribe}.transcribed"   
        try:
            # Rename the file
            os.rename(file_to_transcribe, new_filename)
            print(f"Successfully renamed '{file_to_transcribe}' to '{new_filename}'")
        except FileNotFoundError:
            print(f"Error: The file '{file_to_transcribe}' could not be found in the current directory.")
        except PermissionError:
            print(f"Error: Insufficient permissions to rename '{file_to_transcribe}'.")
        except Exception as e:
            print(f"ERROR renaming {file_to_transcribe} to {new_filename} {e}")   
        timenow= dt_datetime.now(dt_timezone.utc)
        timeformat= timenow.strftime('%Y-%m-%d-%H%M')
        filename = f"transcript_{timeformat}.txt"
        with open(filename, 'w') as f:
            f.write(transcript_text)
        print(f"Success! File saved. {filename}")
         # ---------------------------------------------------------
        # 5. Create Document & Insert Text
        # ---------------------------------------------------------
        transcribe_owner_email = CONFIG.get('TRANSCRIBE_OWNER_EMAIL',"")
        print(f"Creating document in {transcribe_owner_email}'s account...")

        gh = lib_googlehandler.GoogleService(
                drive_owner_email=transcribe_owner_email,
                service_account_file=CONFIG.get('SERVICE_ACCOUNT_FILE',""),
                )
        gh.create_document(
            parent_folder_id=CONFIG.get('TRANSCRIBE_FOLDER_ID',""),
            filename=filename,
            body_text=transcript_text
            )
    elif args_command == "search_object":
        account_emails = get_interactive_list(default_interactive=lib_localtest.delegateaccount)
        #gh = lib_googlehandler.GoogleService(
        #        delegated_email=CONFIG.get('ADMIN_EMAIL',""),
        #        service_account_file=CONFIG.get('SERVICE_ACCOUNT_FILE',""),)
        message= ""
        for account_email in account_emails:
            if not account_email:
                continue
            dto=lib_djangoapp.search_object(search=account_email)
            print()
            for item, value in dto.items() :
                print(item)
                for item1 in value:
                    print(f"{item1.get('name','')} {item1.get('description','')}")
            print("*" * 80)
    elif args_command=="upload_file": 
        filename = get_file(folder_path='', filetype=None, days=7)
        if not filename:
            print(f"No file selected {filename}")
            return
        gh = lib_googlehandler.GoogleService(
                        drive_owner_email=CONFIG.get('TRANSCRIBE_OWNER_EMAIL',""),
                        service_account_file=CONFIG.get('SERVICE_ACCOUNT_FILE',""),
                        drive_parent_folder_id=args_param1 if args_param1 else CONFIG.get('TRANSCRIBE_LECTURE_FOLDER_ID',"")
                        )
        gh.upload_file_todrive(local_filename=filename,)
    elif args_command == "deprovision_user":
        gh = lib_googlehandler.GoogleService(
                                delegated_email=CONFIG.get('ADMIN_EMAIL',""),
                                service_account_file=CONFIG.get('SERVICE_ACCOUNT_FILE',""),
                                google_group_highlight=CONFIG.get('GOOGLE_GROUP_HIGHLIGHT',[]) ,
                                googleuser_account_password_default=CONFIG.get('GOOGLEUSER_ACCOUNT_PASSWORD_DEFAULT',""),
                                googleuser_default_hold_ou=CONFIG.get('GOOGLEUSER_DEFAULT_HOLD_OU',""),
                                )
        account_emails = get_interactive_list()
        for account_email in account_emails:
            if not account_email:
                continue
            gh.deprovision_user(account_email=account_email)
            print(f"{account_email} Done") 
    elif args_command == "delegate_account":
        gh = lib_googlehandler.GoogleService(
                                        delegated_email=CONFIG.get('ADMIN_EMAIL',""),
                                        service_account_file=CONFIG.get('SERVICE_ACCOUNT_FILE',""),
                                        google_group_highlight=CONFIG.get('GOOGLE_GROUP_HIGHLIGHT',[]) ,
                                        googleuser_account_password_default=CONFIG.get('GOOGLEUSER_ACCOUNT_PASSWORD_DEFAULT',""),
                                        googleuser_default_hold_ou=CONFIG.get('GOOGLEUSER_DEFAULT_HOLD_OU',""),
                                        )
        gh.delegate_account(mastermailbox_email=args_param1, 
                            clientaccount_email=args_param2)
    elif args_command == "listallprojects":
        """args_param1 = all | quick"""
        gh = lib_googlehandler.GoogleService(
                                        delegated_email=CONFIG.get('ADMIN_EMAIL',""),
                                        service_account_file=CONFIG.get('SERVICE_ACCOUNT_FILE',""),
                                        )
        sqlh = lib_sqlhandler.SqlAService(
                            cloud_cmdb_database_name =CONFIG.get('CLOUD_CMDB_DATABASE_NAME',''), 
                            cloud_cmdb_database_host = CONFIG.get('CLOUD_CMDB_DATABASE_HOST',''),
                            cloud_cmdb_database_user = CONFIG.get('CLOUD_CMDB_DATABASE_USER',''),
                            cloud_cmdb_database_password = CONFIG.get('CLOUD_CMDB_DATABASE_PASSWORD',''),
                            cloud_cmdb_database_driver = CONFIG.get('CLOUD_CMDB_DATABASE_DRIVER',''),
                        )
        if not args_param1 or args_param1=="all":
            query=""
        elif args_param1 == 'quick': 
            query="NOT id:sys-* AND NOT id:app-*"
        else:
            print(f"Invalid args_param1 {args_param1}")
        gh.list_all_projects(query=query, sqlh=sqlh) 
    elif args_command == "listallorganisations":
        sqlh = lib_sqlhandler.SqlAService(
                    cloud_cmdb_database_name =CONFIG.get('CLOUD_CMDB_DATABASE_NAME',''), 
                    cloud_cmdb_database_host = CONFIG.get('CLOUD_CMDB_DATABASE_HOST',''),
                    cloud_cmdb_database_user = CONFIG.get('CLOUD_CMDB_DATABASE_USER',''),
                    cloud_cmdb_database_password = CONFIG.get('CLOUD_CMDB_DATABASE_PASSWORD',''),
                    cloud_cmdb_database_driver = CONFIG.get('CLOUD_CMDB_DATABASE_DRIVER',''),
                )
        ##sqlh.truncate_table('ccm_organisation')
        gh = lib_googlehandler.GoogleService(
                                        delegated_email=CONFIG.get('ADMIN_EMAIL',""),
                                        service_account_file=CONFIG.get('SERVICE_ACCOUNT_FILE',""),
                                        )
        gh.list_all_organizations(sqlh=sqlh)
    elif args_command == "listallfolders":
        sqlh = lib_sqlhandler.SqlAService(
                    cloud_cmdb_database_name =CONFIG.get('CLOUD_CMDB_DATABASE_NAME',''), 
                    cloud_cmdb_database_host = CONFIG.get('CLOUD_CMDB_DATABASE_HOST',''),
                    cloud_cmdb_database_user = CONFIG.get('CLOUD_CMDB_DATABASE_USER',''),
                    cloud_cmdb_database_password = CONFIG.get('CLOUD_CMDB_DATABASE_PASSWORD',''),
                    cloud_cmdb_database_driver = CONFIG.get('CLOUD_CMDB_DATABASE_DRIVER',''),
                )
        ##sqlh.truncate_table('ccm_folder')
        gh = lib_googlehandler.GoogleService(
                                        delegated_email=CONFIG.get('ADMIN_EMAIL',""),
                                        service_account_file=CONFIG.get('SERVICE_ACCOUNT_FILE',""),
                                        )
        gh.list_all_folders(sqlh=sqlh)
    elif args_command == "listapis":
        """Pass the proect_id as args_param1"""
        """-- Select all projects that have the Compute Engine API enabled
                SELECT
                    p.project_id,
                    p.display_name,
                    p.state
                FROM
                    ccm_project AS p
                INNER JOIN
                    ccm_googleprojectapi AS gpa ON p.name = gpa.parent
                WHERE
                    -- The 'name' in the API table is the full resource name, 
                    -- so we use LIKE to find the service
                    gpa.name LIKE '%/compute.googleapis.com';
"""
        sqlh = lib_sqlhandler.SqlAService(
            cloud_cmdb_database_name=CONFIG.get('CLOUD_CMDB_DATABASE_NAME',''), 
            cloud_cmdb_database_host=CONFIG.get('CLOUD_CMDB_DATABASE_HOST',''),
            cloud_cmdb_database_user=CONFIG.get('CLOUD_CMDB_DATABASE_USER',''),
            cloud_cmdb_database_password=CONFIG.get('CLOUD_CMDB_DATABASE_PASSWORD',''),
            cloud_cmdb_database_driver=CONFIG.get('CLOUD_CMDB_DATABASE_DRIVER',''),
        )
        #existing_api_names = sqlh.get_all_google_api_names()
        gh = lib_googlehandler.GoogleService(
                delegated_email=CONFIG.get('ADMIN_EMAIL',""),
                service_account_file=CONFIG.get('SERVICE_ACCOUNT_FILE',""),
                )
        sqlh.truncate_table('ccm_googleprojectapi_staging')
        gh.list_enabled_apis(project_id=args_param1,sqlh=sqlh)
    elif args_command == "listallinstances":
        """Pass the project_id as args_param1"""
        gh = lib_googlehandler.GoogleService(
                delegated_email=CONFIG.get('ADMIN_EMAIL',""),
                service_account_file=CONFIG.get('SERVICE_ACCOUNT_FILE',""),
                )
        sqlh = lib_sqlhandler.SqlAService(
                    cloud_cmdb_database_name=CONFIG.get('CLOUD_CMDB_DATABASE_NAME',''), 
                    cloud_cmdb_database_host=CONFIG.get('CLOUD_CMDB_DATABASE_HOST',''),
                    cloud_cmdb_database_user=CONFIG.get('CLOUD_CMDB_DATABASE_USER',''),
                    cloud_cmdb_database_password=CONFIG.get('CLOUD_CMDB_DATABASE_PASSWORD',''),
                    cloud_cmdb_database_driver=CONFIG.get('CLOUD_CMDB_DATABASE_DRIVER',''),
                )
        sqlh.truncate_table('ccm_googleinstance_staging')
        sqlh.truncate_table('ccm_googleinstance_network_staging') 
        sqlh.truncate_table('ccm_googleinstance_disklicence_staging')
        gh.list_all_instances(project_id=args_param1, sqlh=sqlh)
    elif args_command == "listallloadbalancers":
        """Pass the project_id as args_param1"""
        gh = lib_googlehandler.GoogleService(
                delegated_email=CONFIG.get('ADMIN_EMAIL',""),
                service_account_file=CONFIG.get('SERVICE_ACCOUNT_FILE',""),
                )
        sqlh = lib_sqlhandler.SqlAService(
                    cloud_cmdb_database_name=CONFIG.get('CLOUD_CMDB_DATABASE_NAME',''), 
                    cloud_cmdb_database_host=CONFIG.get('CLOUD_CMDB_DATABASE_HOST',''),
                    cloud_cmdb_database_user=CONFIG.get('CLOUD_CMDB_DATABASE_USER',''),
                    cloud_cmdb_database_password=CONFIG.get('CLOUD_CMDB_DATABASE_PASSWORD',''),
                    cloud_cmdb_database_driver=CONFIG.get('CLOUD_CMDB_DATABASE_DRIVER',''),
                )
        sqlh.truncate_table('ccm_googleloadbalancer_staging')
        gh.list_all_load_balancers(project_id=args_param1, sqlh=sqlh)
    elif args_command == "ingesttenable":
        if not args_param1:
            filepath = get_file(folder_path='', filetype='.csv', days=10)
        else:
            filepath = args_param1
        if not filepath:
            print(f"No file selected {filepath}")
            return 
        sqlh = lib_sqlhandler.SqlAService(
                            cloud_cmdb_database_name=CONFIG.get('CLOUD_CMDB_DATABASE_NAME',''), 
                            cloud_cmdb_database_host=CONFIG.get('CLOUD_CMDB_DATABASE_HOST',''),
                            cloud_cmdb_database_user=CONFIG.get('CLOUD_CMDB_DATABASE_USER',''),
                            cloud_cmdb_database_password=CONFIG.get('CLOUD_CMDB_DATABASE_PASSWORD',''),
                            cloud_cmdb_database_driver=CONFIG.get('CLOUD_CMDB_DATABASE_DRIVER',''),
                        )
        sqlh.truncate_table('ccm_tenable_staging') 
        sqlh.readcsv_tenable(filepath=filepath)
        print(f"Success! File saved. {filepath}")
    elif args_command == "ingestdnszone":
            if not args_param1:
                filepath = get_file(folder_path='', filetype='.csv', days=10)
            else:
                filepath = args_param1
            if not filepath:
                print(f"No file selected {filepath}")
                return 
            sqlh = lib_sqlhandler.SqlAService(
                                cloud_cmdb_database_name=CONFIG.get('CLOUD_CMDB_DATABASE_NAME',''), 
                                cloud_cmdb_database_host=CONFIG.get('CLOUD_CMDB_DATABASE_HOST',''),
                                cloud_cmdb_database_user=CONFIG.get('CLOUD_CMDB_DATABASE_USER',''),
                                cloud_cmdb_database_password=CONFIG.get('CLOUD_CMDB_DATABASE_PASSWORD',''),
                                cloud_cmdb_database_driver=CONFIG.get('CLOUD_CMDB_DATABASE_DRIVER',''),
                            )
            sqlh.truncate_table('ccm_dnszone_staging') 
            sqlh.readcsv_dnszone(filepath=filepath)
            print(f"Success! File saved. {filepath}")
    elif args_command == "csvexplode":
        if not args_param1:
            print("No file passed as param1")
            filepath = get_file(folder_path='', filetype='.csv', days=10)
        else:
            filepath = args_param1
        if not args_param2:
            print("No column passed as param2 using 4")
            col = 4
        else:
            col = int(args_param2)  
        if not filepath:
            print(f"No file selected {filepath}")
            return 
        fileout = Path(filepath).stem + '_exploded.csv'
        with open (filepath,'r') as fin, open(fileout, 'w') as fout:
            reader = csv.reader(fin)
            writer = csv.writer(fout)
            for row in reader:
                field = row[col-1]
                values = row[col-1].split(",")
                for value in values:
                    writer.writerow(row + [value.strip()])
        print(f"Success! File saved. {fileout}")
    elif args_command == "securityreset":
        gh = lib_googlehandler.GoogleService(
                        delegated_email=CONFIG.get('ADMIN_EMAIL',""),
                        service_account_file=CONFIG.get('SERVICE_ACCOUNT_FILE',""),
                        google_group_highlight=CONFIG.get('GOOGLE_GROUP_HIGHLIGHT',[]) ,
                        googleuser_account_password_default=CONFIG.get('GOOGLEUSER_ACCOUNT_PASSWORD_DEFAULT',""),
                        googleuser_default_hold_ou=CONFIG.get('GOOGLEUSER_DEFAULT_HOLD_OU',""),
                        )
        account_emails = get_interactive_list()
        print(f"Resetting accounts {account_emails}")
        
        for account_email in account_emails:
            account_email = account_email.strip() 
            if not account_email or account_email =="":
                continue
            print(f"Processing {account_email}")
            try:
                # force password change on next logon
                response = gh.patch_user(account_email=account_email, unsuspend=False,
                                            resetpassword=False, 
                                            movetodefaultou=False,
                                            suspend=False,
                                            pwresetnextlogin=True)
                response = gh.revoke_oauthapplicationpwd_user(account_email=account_email)
                #response = gh.reset_verificationcodes(account_email=account_email)
                response = gh.reset_signincookies(account_email=account_email)
            except Exception as e:
                print(f"ERROR {account_email} {e}")            
    elif args_command == "accountreset":
        #userlist,options 
        # (p=reset pw, o=move ou, a=delete oauth,b=reset backup codes,u=unsuspend/unarchive) 
        # eg poabu"
        if not args_param2 or args_param2=='':
            print("Must have param2 ")
            return 
        gh = lib_googlehandler.GoogleService(
                                delegated_email=CONFIG.get('ADMIN_EMAIL',""),
                                service_account_file=CONFIG.get('SERVICE_ACCOUNT_FILE',""),
                                google_group_highlight=CONFIG.get('GOOGLE_GROUP_HIGHLIGHT',[]) ,
                                googleuser_account_password_default=CONFIG.get('GOOGLEUSER_ACCOUNT_PASSWORD_DEFAULT',""),
                                googleuser_default_hold_ou=CONFIG.get('GOOGLEUSER_DEFAULT_HOLD_OU',""),
                                )
        account_emails = get_interactive_list()
        print(f"Resetting accounts {account_emails}")

        for account_email in account_emails:
            account_email = account_email.strip() 
            if not account_email or account_email =="":
                continue
            print(f"Processing {account_email}")
            suspend = None
            unsuspend = None
            if 'u' in args_param2:
                unsuspend = True
            if 's' in args_param2:
                suspend = True
            
            try:
                # force password change on next logon
                if 'u' in args_param2 or 's' in args_param2 or 'p' in args_param2 or 'o' in args_param2:
                    response = gh.patch_user(account_email=account_email, 
                        unsuspend=unsuspend,
                        resetpassword='p' in args_param2,  
                        movetodefaultou='o' in args_param2,
                        suspend=suspend,
                        pwresetnextlogin=False)
                if 'a' in args_param2:
                    response = gh.revoke_oauthapplicationpwd_user(account_email=account_email)
                if 'b' in args_param2:
                    response = gh.reset_verificationcodes(account_email=account_email)
                if 'r' in args_param2:
                    response = gh.reset_signincookies(account_email=account_email)
                if 'g' in args_param2:
                    response = gh.remove_usergroups(account_email=account_email)
            except Exception as e:
                print(f"ERROR {account_email} {e}")
    elif args_command == "syncalldirectoryusers":
        sync_all_directory_users(delegated_email=CONFIG.get('ADMIN_EMAIL',''), 
                    service_account_file=CONFIG.get('SERVICE_ACCOUNT_FILE','') )

    elif args_command == "logoutstaleusers":
        logout_stale_users(delegated_email=CONFIG.get('ADMIN_EMAIL',''), 
                    service_account_file=CONFIG.get('SERVICE_ACCOUNT_FILE','') )
    else:  
        print(f"No command passed {args_command}.") 
    fl.print_summary()  
    print(f"Started:{tdiff.start_time_str} Total Duration: {tdiff.convert_timediff()}")
    tdiff = helperlib.TimeDiff()
   
if __name__ == "__main__":
    main()  