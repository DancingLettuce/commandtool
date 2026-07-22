
"""This file is commandtool.py"""
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
            'param',
            type=str,
            nargs='?',
            help="The parameter for the command ."
        )
    parser.add_argument('--filename', help='filename to parse')
    parser.add_argument("--debug",  action="store_true",   help="Show the debug logs")
    parser.add_argument("--truncate",  action="store_true",   help="Truncate the target first")
    parser.add_argument("--testrun",  action="store_true",   help="This is a testrun")
    parser.add_argument("--interactive",  action="store_true",   help="Interactive to get input")
    parser.add_argument(
        "--configfile", 
        type=Path, # Argparse will automatically convert the string input to a Path object
        default=DEFAULT_CONFIG_PATH,
        help="Path to the TOML configuration file."
        )
    ARGS = parser.parse_args()
    known, unknown = parser.parse_known_args()
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
    """ 
SCRIPT_DIR = Path(__file__).resolve().parent 
#DEFAULT_CONFIG_PATH = SCRIPT_DIR / "secrets.toml" # for a local secrets or config file
DEFAULT_CONFIG_PATH = SCRIPT_DIR.parent / "secrets" / "secrets.toml"
DEFAULT_LOG_PATH = SCRIPT_DIR / "log.txt"
ARGS, ARBITRARY_ARGS = init_argparse()
import lib_helper_lib as helperlib 
CONFIG = helperlib.init_secrets(toml_string=TOML_STRING,filename=ARGS.configfile) 
 
from datetime import datetime as dt_datetime, timedelta  , timezone as dt_timezone 
import subprocess
import sys 
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
        if file_path.is_file() and file_path.suffix.lower() == filetype:
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
    meeting_data = transcribe.transcribe_audio(audio_file_path=file_to_transcribe) 
    #text_vector = transcribe.generate_text_vector(meeting_data['meeting_summary'])
    transcribe.insert_semantic_json(meeting_data)  
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
        print(f"ERROR renameing {file_to_transcribe} to {new_filename} {e}")   

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
    if ARGS.interactive:
        interactive_list = helperlib.get_multiline_input()
    elif ARGS.param:
        interactive_list = ARGS.param
    else:
        interactive_list = default_interactive
    if isinstance(interactive_list,str): 
        interactive_list = interactive_list.replace(" ",",").replace("\n",",")
        interactive_list = interactive_list.split(",")
    return interactive_list

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






def main():
    tdiff = helperlib.TimeDiff()
    fl = helperlib.ScriptLog()   
    args_command = ARGS.command 

    if (args_command == 'menu' or ARGS.command=='questionary') :
        if not imports_questionary:
            print(f"ERROR. Command line command {args_command} requires Questionary")
        else:
            pass # do menu  
    elif args_command == 'upload':
        folder_source = ''
        upload_recent_file(folder_path=CONFIG["MEDIA_SOURCE"], days=7)    
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
        print (lib_localtest.mytext )
        lib_localtest.localtest()
        

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
    elif args_command == 'unsuspendmoveouresetpassword':
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
            response = gh.patch_user(account_email=account_email, unsuspend=True,
                                     resetpassword=True, 
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
            print(f"ERROR renameing {file_to_transcribe} to {new_filename} {e}")   

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

    else:  
        print(f"No command passed {args_command}.") 
    fl.print_summary()  
    print(f"Started:{tdiff.start_time_str} Total Duration: {tdiff.convert_timediff()}")
    tdiff = helperlib.TimeDiff()
   
if __name__ == "__main__":
    main()  