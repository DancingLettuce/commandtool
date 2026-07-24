"""This file is lib_googlevault.py"""

from dataclasses import dataclass, field
from functools import cached_property
import io 
import os
import shutil
import mimetypes
import time 
import sys 

try:
    # Google Auth Imports
    # pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
    # pip install google-cloud-storage
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2 import service_account
    from google.cloud import storage
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
    imports_google = True
except Exception as e:
     print(f"WARNING lib_googlevault: Cannot import Google SDK {e}")
     imports_google = False




import lib_helper_lib as helperlib 
 

@dataclass
class GoogleService():
    delegated_email: str=""
    SCOPES = [ 
        'https://www.googleapis.com/auth/admin.directory.user',
        'https://www.googleapis.com/auth/admin.directory.group',
        'https://www.googleapis.com/auth/gmail.settings.sharing',
        'https://www.googleapis.com/auth/gmail.settings.basic',
        'https://www.googleapis.com/auth/admin.reports.audit.readonly',
        'https://www.googleapis.com/auth/cloud-identity.devices',
        'https://www.googleapis.com/auth/admin.directory.user.security',
        'https://www.googleapis.com/auth/ediscovery',            # Vault API
        'https://www.googleapis.com/auth/drive',                 # Drive API
        'https://www.googleapis.com/auth/devstorage.read_only'   # Cloud Storage API
        ]
    service_account_file: str=""
    vault_matter_id: str="" 
    base_download_directory: str =""
    drive_parent_folder_id: str="" 
    drive_owner_email: str="" 
    google_group_highlight: list = field(default_factory=list)
    googleuser_account_password_default: str="" 
    #googleuser_default_hold_ou: list = field(
    #        default_factory=lambda: ['defaults']
    #        ) 
    # googleuser_default_hold_ou: list | None = None 
    googleuser_default_hold_ou: list = field(default_factory=list)

    def get_serviceaccount_service(self, 
        api_servicename:str=None,
        api_version:str=None,
        delegated_email: str=None):
        api_servicename = self.api_servicename if api_servicename is None else api_servicename
        api_version = self.api_servicename if api_version is None else api_version
        delegated_email = self.delegated_email if delegated_email is None else delegated_email 
        creds = service_account.Credentials.from_service_account_file(
                self.service_account_file, 
                scopes=self.SCOPES,
                subject=delegated_email
            )
        return build(api_servicename, api_version, credentials=creds)

    @cached_property
    def get_serviceaccount_gmailv1(self):
        creds = service_account.Credentials.from_service_account_file(
                self.service_account_file, 
                scopes=self.SCOPES,
                subject=self.delegated_email
            )
        return build('gmail', 'v1', credentials=creds)
    
    @cached_property
    def base_creds(self):
        return service_account.Credentials.from_service_account_file(
            self.service_account_file, 
            scopes=self.SCOPES )
        
    @cached_property
    def get_serviceaccount_admin(self):
        return build('admin', 'directory_v1', 
                    credentials=self.base_creds.with_subject(self.delegated_email))

    @cached_property
    def get_serviceaccount_docs(self):
        return build('docs', 'v1', 
            credentials=self.base_creds.with_subject(self.drive_owner_email))

    @cached_property
    def get_serviceaccount_drive(self):
        return build('drive', 'v3', 
            credentials=self.base_creds.with_subject(self.drive_owner_email))

    def pick_vault_export(self,
                        vault_matter_id:str=None):
        vault_matter_id = self.vault_matter_id if vault_matter_id is None else None
        print(f"Connecting to Google Vault Matter: {vault_matter_id}...")
        vault_service = self.get_serviceaccount_service(api_servicename="vault", 
                api_version="v1", delegated_email=self.delegated_email)
        # 1. List and sort exports
        try:
            response = vault_service.matters().exports().list(
                matterId=vault_matter_id,
                pageSize=100 
            ).execute()
        except Exception as e:
            print(f"CRITICAL API ERROR: Failed to list exports. {e}")
            return

        exports = response.get('exports', [])
        if not exports:
            print("No exports found in this matter.")
            return

        exports.sort(key=lambda x: x.get('createTime', ''), reverse=True)

        # 2. Build the Interactive Menu
        print("\n" + "="*50)
        print(f"FOUND {len(exports)} EXPORTS")
        print("="*50)
        
        for idx, export in enumerate(exports):
            status = export.get('status')
            name = export.get('name')
            create_time = export.get('createTime')
            print(f"[{idx}] {name} (Status: {status} | Created: {create_time})")
            
        print(f"[{len(exports)}] Quit / Cancel")
        print("="*50)

         # 3. Capture User Selection
        while True:
            choice_str = input(f"Select an export to process [0-{len(exports)}]: ").strip()
            if choice_str.lower() in ('q', 'quit', 'exit'):
                print("Exiting Vault Downloads!") 
                return 
            if not choice_str.isdigit():
                print("Invalid input.")
                continue
                
            choice = int(choice_str)
            if choice == len(exports):
                print("Exiting...")
                return
            if 0 <= choice < len(exports):
                selected_export = exports[choice]
                break
            else:
                print("Number out of range.")

        if selected_export.get('status') != 'COMPLETED':
            print(f"Cannot download. Export status is currently: {selected_export.get('status')}")
            return

        export_id = selected_export.get('id')
        export_name = selected_export.get('name', f'export_{export_id}')
        return export_id, export_name
    
    def get_human_readable_size(self, size_in_bytes):
        """Converts bytes to a human-readable format (KB, MB, GB)."""
        try:
            size = float(size_in_bytes)
        except (ValueError, TypeError):
            return "Unknown Size"
            
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
            
        return f"{size:.2f} PB"

    def upload_file_todrive(self,local_filename:str):
        print(f"Preparing Google Drive folder as {self.drive_owner_email}...")
        drive_service = self.get_serviceaccount_drive

        """folder_metadata = {
                    'name': safe_folder_name,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [self.drive_parent_folder_id]
                }
        try:
                    drive_folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
                    drive_folder_id = drive_folder.get('id')
        except Exception as e:
            print(f"CRITICAL ERROR: Failed to create Drive folder. {e}")
            return"""
        #print(f"        UPLOADING: {local_filename} to Drive... https://drive.google.com/drive/u/9/folders/{self.drive_parent_folder_id}", end="", flush=True)
        print(f"        UPLOADING: {local_filename} to Drive... https://drive.google.com/drive/u/9/folders/{self.drive_parent_folder_id}") 
        mime_type, _ = mimetypes.guess_type(local_filename)
        if mime_type is None:
            mime_type = 'application/octet-stream'
            
        file_metadata = {
            'name': local_filename,
            'parents': [self.drive_parent_folder_id]
        }
        
        media = MediaFileUpload(local_filename, mimetype=mime_type, resumable=True)
        print() 
        try:
            drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            print("DONEUPLOAD")
        except Exception as e:
            print(f"FAILED UPLOAD: {e}")
    def download_vault_export(self, 
        export_id:str=None, 
        export_name:str=None,
        base_download_directory:str=None):
        base_download_directory = self.base_download_directory if base_download_directory is None else base_download_directory
    
        vault_service = self.get_serviceaccount_service(
            api_servicename='vault', 
            api_version='v1', 
            delegated_email=self.delegated_email)
        # Create the local staging directory (MBOX files will remain here permanently)
        safe_folder_name = "".join(c for c in export_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_folder_name = safe_folder_name.replace(" ","_")
        download_path = os.path.join(base_download_directory, safe_folder_name)
        if os.path.exists(download_path) and os.path.isdir(download_path):
            shutil.rmtree(download_path)
            print(f"Deleted directory and all contents: {download_path}")
        else:
            print(f"Directory does not exist or is a file. {download_path}")
        os.makedirs(download_path, exist_ok=True)

        print(f"Fetching file list for export '{export_name}'...")
        try:
            export_details = vault_service.matters().exports().get(
                matterId=self.vault_matter_id,
                exportId=export_id 
            ).execute()
        except Exception as e:
            print(f"Failed to get export details: {e}")
            return

        cloud_storage_sink = export_details.get('cloudStorageSink', {})
        files = cloud_storage_sink.get('files', [])
        
        if not files:
            print("No files found in this export payload.")
            return

        print(f"Found {len(files)} files to process.")
        
         # 5. Pre-flight Setup: Storage & Drive Auth
        print(f"Building Storage API service as {self.delegated_email}...")
        storage_service = self.get_serviceaccount_service('storage', 'v1', delegated_email=self.delegated_email)
        
        print(f"Preparing Google Drive folder as {self.drive_owner_email}...")
        drive_service = self.get_serviceaccount_service('drive', 'v3', delegated_email=self.drive_owner_email)
        
        folder_metadata = {
            'name': safe_folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [self.drive_parent_folder_id]
        }
        try:
            drive_folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
            drive_folder_id = drive_folder.get('id')
        except Exception as e:
            print(f"CRITICAL ERROR: Failed to create Drive folder. {e}")
            return
        

        ##
            # 6. The Unified Pipeline (Download -> Upload -> Keep Local)
        print("\nStarting Unified Pipeline...")
        for idx, f in enumerate(files, 1):
            bucket_name = f.get('bucketName')
            object_name = f.get('objectName')
            raw_size = f.get('size')
            size = self.get_human_readable_size(raw_size) if raw_size else 'Unknown Size'
            
            local_filename = object_name.split('/')[-1]
            local_filepath = os.path.join(download_path, local_filename)
            file_root, file_extension = os.path.splitext(local_filename)    
            # --- A. DOWNLOAD (SDK NATIVE) ---
            print(f"[{idx}/{len(files)}] DOWNLOADING: {local_filename} (Size: {size})... ", end="", flush=True)
            try:
                request = storage_service.objects().get_media(
                    bucket=bucket_name,
                    object=object_name
                )
                
                fh = io.FileIO(local_filepath, 'wb')
                downloader = MediaIoBaseDownload(fh, request, chunksize=1024*1024*8) # 8MB chunks
                
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                    
                
                print("DOWNLOADED")

            except Exception as e:
                print(f"FAILED: {e}")
                continue # If download fails, skip upload for this file

            # --- B. UPLOAD ---
            print(f"        UPLOADING: {local_filename} to Drive... https://drive.google.com/drive/u/9/folders/{drive_folder_id}", end="", flush=True)
            mime_type, _ = mimetypes.guess_type(local_filepath)
            if mime_type is None:
                mime_type = 'application/octet-stream'
                
            file_metadata = {
                'name': local_filename,
                'parents': [drive_folder_id]
            }
            
            media = MediaFileUpload(local_filepath, mimetype=mime_type, resumable=True)
            
            try:
                drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                print("DONEUPLOAD")
            except Exception as e:
                print(f"FAILED UPLOAD: {e}")

    def evaluate_and_approve_device_user(self, service, device_user_name):
        """
        Evaluates business logic for a specific device user before approving them.
        Returns True if successfully approved, False if an error occurred or logic blocked it.
        """
        
        max_retries = 3
        retry_attempt = 0
        
        while retry_attempt < max_retries:
            try:
                # The Cloud Identity API requires a body payload for the approve method.
                # Using 'customers/my_customer' automatically targets the impersonated admin's tenant.
                request_body = {'customer': 'customers/my_customer'}
                
                service.devices().deviceUsers().approve(
                    name=device_user_name,
                    body=request_body
                ).execute()
                
                return True
                
            except HttpError as e:
                if e.resp.status in [503, 429, 500, 502, 504]:
                    retry_attempt += 1
                    time.sleep(2)
                else:
                    print(f"HTTP Error approving {device_user_name}: {e.resp.status} - {e}")
                    return False
            except Exception as e:
                print(f"Unknown Error approving {device_user_name}: {e}")
                return False
                
        print(f"Failed to approve {device_user_name} after {max_retries} attempts.")
        return False

    def delete_company_device(self, service, device_name):
        max_retries = 3
        retry_attempt = 0
        
        while retry_attempt < max_retries:
            try:
                # The Cloud Identity API requires a body payload for the approve method.
                # Using 'customers/my_customer' automatically targets the impersonated admin's tenant.
                request_body = {'customer': 'customers/my_customer'}
                
                service.devices().delete(
                    name=device_name,
                    #body=request_body
                ).execute()
                
                return True
                
            except HttpError as e:
                if e.resp.status in [503, 429, 500, 502, 504]:
                    retry_attempt += 1
                    time.sleep(2)
                else:
                    print(f"HTTP Error deleting {device_name}: {e.resp.status} - {e}")
                    return False
            except Exception as e:
                print(f"Unknown Error deleting {device_name}: {e}")
                return False
                
        print(f"Failed to delete {device_name} after {max_retries} attempts.")
        return False

    def delegate_account(self, service, mastermailbox_email, clientaccount_email):
        """Delegate mastermailbox to clientaccount"""
        pass 

    def list_delegates(self, account_email):
        print(f"getting delegates for {account_email}")
        impersonated_creds = self.base_creds.with_subject(account_email)
        service = build('gmail', 'v1', credentials=impersonated_creds)
        try:
            response = service.users().settings().delegates().list(userId='me').execute()
        except Exception as e:
            response = {'error':e} 
        #response = service.users().settings().delegates().list(userId=account_email).execute()
        return response

    def get_user(self,account_email):
        #print(f"Getting details for {account_email}")
        
        try:
            response = self.get_serviceaccount_admin.users().get(userKey=account_email).execute()
        except Exception as e:
            response = {'error':e}
        return response 

    def get_googleuser(self,account_email, profile=True, delegates=True, groups=True, google_group_highlight=[]):
        gu = GoogleUser(email=account_email, google_group_highlight=google_group_highlight)
        if profile:
            gu.read_user_response(self.get_user(account_email=account_email))
        if delegates:
            gu.read_delegates_response(self.list_delegates(account_email=account_email))
        if groups:
            gu.read_groups_response(self.list_user_groups(account_email=account_email))
        return gu 
    
    def list_user_groups(self, account_email):
        """
        Fetches all groups a user is a direct member of.
        Handles Google's pagination automatically.
        """
        groups = []
        # Initial request
        request = self.get_serviceaccount_admin.groups().list(userKey=account_email)
        while request is not None:
            response = request.execute()
            # Add this page of groups to our master list
            groups.extend(response.get('groups', []))
            # Get the next page (returns None if we are at the end)  
            request = self.get_serviceaccount_admin.groups().list_next(
                previous_request=request, 
                previous_response=response
            )  
        return groups

    def suspend_user(self, account_email):
        """Suspends a user account."""
        body = {"suspended": True}
        return self.get_serviceaccount_admin.users().update(userKey=account_email, body=body).execute()
    def reactivate_and_reset_user(self, account_email: str, new_password: str):
        """
        Unarchives, unsuspends, updates the user's password, 
        and turns off forced password change at next login.
        """
        body = {
            "archived": False,
            "suspended": False,
            "password": new_password,
            "changePasswordAtNextLogin": False
        }
        
        # Using .patch() is recommended for partial updates to avoid accidentally 
        # clearing or overwriting other unmentioned user fields.
        return self.get_serviceaccount_admin.users().patch(
            userKey=account_email, 
            body=body
        ).execute()
    def patch_user(self,account_email: str, 
                unsuspend:bool = False, 
                resetpassword:bool=False, 
                movetodefaultou:bool=False,
                ):
        body = {}  
        if unsuspend:
            body["archived"] =False
            body["suspended"] = False
        if resetpassword:
            body["password"] = self.googleuser_account_password_default
            body["changePasswordAtNextLogin"] = False
        if movetodefaultou:
            body["orgUnitPath"] = self.googleuser_default_hold_ou
        return self.get_serviceaccount_admin.users().patch(
                    userKey=account_email, 
                    body=body
                ).execute()
    def create_document(self,
                        parent_folder_id:str,
                        filename:str,
                        body_text:str):
        # creates in root drive
        doc_body = {'title': filename}
        doc = self.get_serviceaccount_docs.documents().create(body=doc_body).execute()
        doc_id = doc.get('documentId')
        body_text += f"\n\nDocument Link: https://docs.google.com/document/d/{doc_id}/edit {filename}"
        requests = [
        {
            'insertText': {
                'location': {'index': 1},
                'text': body_text
            }
        }
        ]
        self.get_serviceaccount_docs.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()

        # 3. Move the document to the specific folder using Drive API
        if parent_folder_id:
            drive_service = self.get_serviceaccount_drive
            
            # Retrieve the existing parents to remove (usually just the root folder)
            file = drive_service.files().get(fileId=doc_id, fields='parents').execute()
            previous_parents = ",".join(file.get('parents', []))
            
            # Move the file to the new folder
            drive_service.files().update(
                fileId=doc_id,
                addParents=parent_folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
            
        print("Success! Document created and populated.")
        print(f"Document Link: https://docs.google.com/document/d/{doc_id}/edit")
class GoogleUser:
    def __init__(self,
                 email=None,
                 orgunitpath=None,
                 lastlogintime=None,
                 creationtime=None,
                 archived=None,
                 suspended=None,
                 google_group_highlight=None 
                 ):
        self.email = email
        self.orgunitpath = orgunitpath
        self.lastlogintime = lastlogintime
        self.creationtime = creationtime
        self.archived = archived
        self.suspended=suspended
        self.delegates={}
        self.groups=[]
        self.google_group_highlight = google_group_highlight
        self.is_in_google_group_highlight = False
        self.error = None
    def read_user_response(self, response):
        if response.get('error',None):
            self.error = response.get('error',None)
        self.orgunitpath= response.get('orgUnitPath','')
        self.lastlogintime=response.get('lastLoginTime','')
        self.suspended=response.get('suspended','')
        self.archived=response.get('archived','')
        self.creationtime=response.get('creationTime','')
    def read_delegates_response(self,response):
        self.delegates = response.get('delegates',{})
    def read_groups_response(self,response):
        for group in response:
            email = group.get('email','')
            if email:
                self.groups.append(email)
                if not self.is_in_google_group_highlight:
                    if email in (self.google_group_highlight):
                        self.is_in_google_group_highlight = True    
    def is_active(self):
        return not (self.suspended or self.archived)  
    def to_str(self):
        if self.error:
            message = f"{self.email} ERROR {self.error}"
            return message
        message = f"{self.email} {'(Inactive)' if not self.is_active() else ''}"
        message += f"\n{self.orgunitpath}"
        message += f"\nCreated:{self.creationtime}"
        message += f"\nLogon:{self.lastlogintime}" 
        return message 
    def delegates_to_str(self):
        message = ""
        for delegate in self.delegates:
            if delegate:
                message += delegate.get('delegateEmail')
                if delegate.get('verificationStatus','') != 'accepted':
                    message += f"(*NotAccepted*)"
                message += "; "
        if message == "":
            message = "No delegates"
        else: 
            message = f"Delegates: {message}" 
        return message 
    def groups_to_str(self):
        message=""
        for group in self.groups:
            message += f"{group};"
        return message 
    