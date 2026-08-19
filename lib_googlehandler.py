"""This file is lib_googlehandler.py"""

from dataclasses import dataclass, field
from functools import cached_property
from datetime import datetime, timezone

import io 
import os
import shutil
import mimetypes
import time 
import json
import sys 

try:
    # Google Auth Imports
    # pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
    # pip install google-cloud-storage
    # pip install google-cloud-resource-manager 
    #       https://docs.cloud.google.com/resource-manager/reference/rest/v3/folders/list
    #       https://docs.cloud.google.com/python/docs/reference/cloudresourcemanager/latest
    # pip install google-cloud-service-usage
    # google-cloud-billing
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2 import service_account
    from google.cloud import storage
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
    from google.cloud import resourcemanager_v3 
    from google.cloud import service_usage_v1
    imports_google = True
except Exception as e:
     print(f"WARNING lib_googlevault: Cannot import Google SDK {e}")
     imports_google = False

import lib_helper_lib as helperlib 

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy import select
# Instead of: from itertools import batched
from lib_helper_lib import batched
from sqlalchemy import insert
import lib_sqlhandler
from sqlalchemy import delete
import sqlhandler_models as models


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
        'https://www.googleapis.com/auth/devstorage.read_only',   # Cloud Storage API
        'https://www.googleapis.com/auth/compute.readonly',       # Compute Engine read-only
        'https://www.googleapis.com/auth/cloud-platform.read-only', # GCP Resource Manager API, can't use this with workspace unless scope assigned
        ]
    # scopes are assigned under domain wide delegation in Google Worskpace admin.google.com
    SCOPES_GCP = ['https://www.googleapis.com/auth/cloud-platform.read-only', # GCP Resource Manager API, can't use this with workspace
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
            #print(f"        UPLOADING: {local_filename} to Drive... https://drive.google.com/drive/u/9/folders/{drive_folder_id}", end="", flush=True)
            print(f"        UPLOADING: {local_filename} to Drive... https://drive.google.com/drive/u/9/folders/{drive_folder_id}")
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
  
    def delegate_account(self, mastermailbox_email: str, clientaccount_email: str):
        """
        Delegates the mastermailbox (leaver) to the clientaccount (grantee).
        Because this uses Domain-Wide Delegation impersonating the leaver, 
        Google automatically forces the delegation to 'accepted', bypassing the invite email.
        """
        print(f"Delegating {mastermailbox_email}'s mailbox to {clientaccount_email}...")
        
        # 1. Impersonate the leaver's account
        impersonated_creds = self.base_creds.with_subject(mastermailbox_email)
        gmail_service = build('gmail', 'v1', credentials=impersonated_creds)
        
        delegate_body = {
            'delegateEmail': clientaccount_email
        }
        
        try:
            # 2. Create the delegate. userId='me' uses the impersonated subject.
            response = gmail_service.users().settings().delegates().create(
                userId='me',
                body=delegate_body
            ).execute()
            
            status = response.get('verificationStatus', 'unknown')
            print(f"  -> Success! Mailbox delegated. Status: {status}")
            return response
            
        except HttpError as e:
            if e.resp.status == 409:
                print(f"  -> {clientaccount_email} is already a delegate for {mastermailbox_email}.")
            else:
                print(f"  -> HTTP Error delegating mailbox: {e.resp.status} - {e}")
            return None
        except Exception as e:
            print(f"  -> Unknown Error delegating mailbox: {e}")
            return None

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
                suspend:bool = False,
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
        if suspend:
            body["suspended"] = True
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

    def deprovision_user(self, account_email: str):
        """
        Deprovisions a user by removing them from all groups, 
        revoking all OAuth tokens, and deleting App Specific Passwords (ASPs).
        """
        print(f"Starting deprovision process for {account_email}...")
        admin_service = self.get_serviceaccount_admin

        # 1. Remove from all groups
        print(f"Fetching groups for {account_email}...")
        groups = self.list_user_groups(account_email)
        
        if not groups:
            print(f"  - User {account_email} is not a member of any groups.")
        else:
            for group in groups:
                group_email = group.get('email')
                if group_email:
                    try:
                        admin_service.members().delete(
                            groupKey=group_email, 
                            memberKey=account_email
                        ).execute()
                        
                        print(f"  - Removed from group: {group_email}")
                    except Exception as e:
                        print(f"  - Error removing from {group_email}: {e}")

        # 2. Revoke OAuth Tokens
        print(f"Revoking OAuth tokens for {account_email}...")
        try:
            tokens_response = admin_service.tokens().list(userKey=account_email).execute()
            tokens = tokens_response.get('items', [])
            
            if not tokens:
                print("  - No OAuth tokens found.")
            else:
                for token in tokens:
                    client_id = token.get('clientId')
                    app_name = token.get('displayText', 'Unknown App')
                    if client_id:
                        admin_service.tokens().delete(
                            userKey=account_email, 
                            clientId=client_id
                        ).execute()
                        print(f"  - Revoked OAuth token for: {app_name} ({client_id})")
        except Exception as e:
            print(f"  - Error fetching/revoking OAuth tokens: {e}")

        # 3. Revoke Application Specific Passwords (ASPs)
        print(f"Revoking Application Specific Passwords for {account_email}...")
        try:
            asps_response = admin_service.asps().list(userKey=account_email).execute()
            asps = asps_response.get('items', [])
            
            if not asps:
                print("  - No ASPs found.")
            else:
                for asp in asps:
                    code_id = asp.get('codeId')
                    asp_name = asp.get('name', 'Unnamed ASP')
                    if code_id:
                        admin_service.asps().delete(
                            userKey=account_email, 
                            codeId=code_id
                        ).execute()
                        print(f"  - Revoked ASP: {asp_name} (ID: {code_id})")
        except Exception as e:
            print(f"  - Error fetching/revoking ASPs: {e}")
            
        print(f"Deprovisioning steps complete for {account_email}.")

    # Google Compute Platform
    def list_all_projects(self, query: str = "NOT id:sys-* AND NOT id:app-*", 
                          sqlh:lib_sqlhandler.SqlAService = None):
        #Google Cloud's Resource Manager API utilizes the AIP-160 filtering standard 
        print(f"Fetching accessible Google Cloud Projects Query={query}")
        engine = sqlh.engine
        sqlh.truncate_table("ccm_project_staging")
        sqlh.truncate_table('ccm_googleprojectapi_staging')
        # Initializes the Resource Manager client using your base Service Account credentials
        client = resourcemanager_v3.ProjectsClient(credentials=self.base_creds)
        
        try:
            # Searching without a query returns all accessible projects
            projects = client.search_projects(query=query)
        
            with Session(engine) as session:
                c = 0
                if query:
                    batch_size=2
                    chunkmessage=1
                else:
                    batch_size=5000
                    chunkmessage=100
                c_records = 0
                for chunk in batched(projects, batch_size):
                    batch_dicts = []
                    if False and c_records >= 10:
                        break
                    for chunki in chunk:
                        c_records +=1
                        if False and c_records >= 10:
                            break
                        if c_records % chunkmessage == 0:
                            #helperlib.print_flush(f"Appending record {c_records} with batch size {batch_size}. Done {c} batches")
                            print(f"Appending record {c_records} with batch size {batch_size} Current {chunki.project_id}. Done {c} batches")
                                                        
                        batch_dicts.append({
                            "project_id": chunki.project_id,
                            "api_lastseen": datetime.now(timezone.utc),
                            "name": chunki.name,
                            "parent": chunki.parent,
                            "display_name": chunki.display_name,
                            "state": chunki.state.name,
                            "create_time": chunki.create_time,
                            "etag": chunki.etag,
                            "api_data": type(chunki).to_dict(chunki)
                        })
                        if query:
                            self.list_enabled_apis(project_id=chunki.project_id, sqlh=sqlh)

                    session.execute(insert(models.CcmProjectStaging), batch_dicts)
                    session.commit()
                    c += len(batch_dicts)
                    print(f"\nInserted batch of {len(batch_dicts)} rows. Total so far: {c}")
            print(f"DONE. {c_records} Total records")
            
        except Exception as e:
            print(f"CRITICAL API ERROR: Failed to list GCP projects. {e}")
            return None
        sql = """MERGE INTO ccm_project AS Target
                USING ccm_project_staging AS Source
                ON Target.name = Source.name

                -- 1. If it exists in both tables, UPDATE the working table
                WHEN MATCHED THEN
                    UPDATE SET 
                        Target.api_lastseen = Source.api_lastseen,
                        Target.api_data = Source.api_data,
                        Target.parent = Source.parent,
                        Target.project_id = Source.project_id,
                        Target.state = Source.state,
                        Target.display_name = Source.display_name,
                        Target.create_time = Source.create_time,
                        Target.etag = Source.etag

                -- 2. If it is in Staging but NOT in Working, INSERT it
                WHEN NOT MATCHED BY TARGET THEN
                    INSERT (
                        api_lastseen, api_data, name, parent, 
                        project_id, state, display_name, create_time, etag
                    )
                    VALUES (
                        Source.api_lastseen, Source.api_data, Source.name, Source.parent, 
                        Source.project_id, Source.state, Source.display_name, Source.create_time, Source.etag
                    )
                """
        if query: 
            sql += " ; "
        else: 
            sql += """
                -- 3. If it is in Working but NOT in Staging, DELETE it
                -- (If you are doing a "partial stage", simply comment out or remove these next two lines!)
                WHEN NOT MATCHED BY SOURCE THEN
                    DELETE;
            """
        sqlh.execute_sql(sql)
        sql="""MERGE INTO ccm_googleprojectapi AS Target
                USING ccm_googleprojectapi_staging AS Source
                ON Target.name = Source.name AND Target.parent = Source.parent

                -- 1. If it exists in both tables (same API for the same project), UPDATE the working table.
                WHEN MATCHED THEN
                    UPDATE SET 
                        Target.api_lastseen = Source.api_lastseen,
                        Target.api_data = Source.api_data,
                        Target.state = Source.state

                -- 2. If it is in Staging but NOT in the main table, INSERT it.
                WHEN NOT MATCHED BY TARGET THEN
                    INSERT (
                        api_lastseen, api_data, name, state, parent
                    )
                    VALUES (
                        Source.api_lastseen, Source.api_data, Source.name, Source.state, Source.parent
                    )

                -- 3. If it is in the main table but NOT in Staging (for a project that WAS staged), DELETE it.
                WHEN NOT MATCHED BY SOURCE AND Target.parent IN (SELECT DISTINCT parent FROM ccm_googleprojectapi_staging) THEN
                    DELETE;"""
        sqlh.execute_sql(sql)
        sql="""INSERT INTO ccm_googleapi (api_lastseen, api_data,name,title,summary)
                SELECT distinct getdate(), cgs.config_api_data , cgs.config_name , cgs.config_title,cgs.config_summary  
                FROM ccm_googleprojectapi_staging AS cgs
                where not exists (select 1 from ccm_googleapi cg where cgs.config_name=cg.name );"""
        sqlh.execute_sql(sql)
        sql = """
            UPDATE gpa
            SET gpa.project_ccm_id = p.id
            FROM ccm_googleprojectapi AS gpa
            INNER JOIN ccm_project AS p ON gpa.parent = p.name;
        """
        sqlh.execute_sql(sql)
        sqlh.truncate_table("ccm_project_staging")
        sqlh.truncate_table('ccm_googleprojectapi_staging')
        
    def list_enabled_apis(self, project_id: str, 
                          sqlh:lib_sqlhandler.SqlAService = None, 
                          existing_api_names:list = None):
        """
        Lists all enabled APIs for a given project ID or Number.
        Returns a list of API names (e.g., ['compute.googleapis.com', 'storage-api.googleapis.com'])
        """
        print(f"Fetching enabled APIs for project: {project_id}...")
        existing_api_names = sqlh.get_all_google_api_names()
        # Initializes the Service Usage client using your base Service Account credentials
        client = service_usage_v1.ServiceUsageClient(credentials=self.base_creds)
        
        # The API expects the parent string formatted as 'projects/[PROJECT_ID_OR_NUMBER]'
        parent = f"projects/{project_id}"
        
        # We use the filter "state:ENABLED" to only get active APIs
        request = service_usage_v1.ListServicesRequest(
            parent=parent,
            filter="state:ENABLED"
        )
        
        project_apis_to_insert = []
        #new_apis_to_insert = []
        enabled_apis_count = 0

        try: # Using a single session for all checks in the loop
            with Session(sqlh.engine) as session:
                # 1. DELETE existing records for this project to ensure a clean slate.
                #print(f"Deleting existing API entries for project '{parent}'...")
                #delete_statement = delete(models.CcmGoogleProjectApi).where(models.CcmGoogleProjectApi.parent == parent)
                #result = session.execute(delete_statement)
                #session.commit()
                #print(f"Deleted {result.rowcount} old records.")

                # 2. COLLECT all enabled APIs from the Google API call.
                services = client.list_services(request=request)
                # Safely get the summary. If .documentation or .summary doesn't exist,
                # an AttributeError is caught and we default to an empty string.
                
                for service in services:
                    try:
                        summary = service.config.documentation.summary
                    except AttributeError:
                        summary = ""
                    enabled_apis_count += 1
                    project_apis_to_insert.append({
                        "name": service.name, # e.g., projects/123/services/compute.googleapis.com
                        "state": service.state.name,
                        "parent": service.parent, # e.g., projects/123
                        "api_lastseen": datetime.now(timezone.utc),
                        "api_data": type(service).to_dict(service),
                        "config_name": service.config.name,
                        "config_title": service.config.title,
                        "config_summary": summary,
                        "config_api_data": type(service.config).to_dict(service.config) 

                    })
                    #api_name = service.config.name
                    """
                    exists_statement = select(models.CcmGoogleApi.id).where(models.CcmGoogleApi.name == api_name).limit(1)
                    # 2. Execute it. .scalar() returns the single boolean result (True or False).
                    api_already_exists = session.scalar(exists_statement)
                    """
                    #api_already_exists = api_name in existing_api_names 
                    """# 3. Check the result before appending
                    if api_already_exists:
                        print(f"  - Skipping '{api_name}' (already in DB).")
                    else:
                        print(f"  + Adding new API '{api_name}' to insert list.")
                        

                        new_apis_to_insert.append({
                            "name": api_name,
                            "title": service.config.title,
                            "summary": summary,
                            "api_lastseen": datetime.now(timezone.utc),
                            "api_data": type(service).to_dict(service)
                        })
                        """
                        
                
                print(f"\nProcessed {enabled_apis_count} enabled APIs for project {project_id}.")

                """# 3. BULK INSERT all collected APIs into the linking table.
                if project_apis_to_insert:
                    #print(f"Bulk inserting {len(project_apis_to_insert)} project-api links...")
                    session.execute(insert(models.CcmGoogleProjectApiStaging), project_apis_to_insert)
                    #print("Bulk insert complete.")
                else:
                    print("No enabled APIs found to insert.")
                #if new_apis_to_insert:
                #    print(f"Bulk inserting {len(new_apis_to_insert)} new APIs into the database...")
                #    session.execute(insert(models.CcmGoogleApi), new_apis_to_insert)
                """
                session.execute(insert(models.CcmGoogleProjectApiStaging), project_apis_to_insert)
                session.commit()

            # 4. UPDATE FOREIGN KEY: Execute raw SQL to link to the ccm_project table.
            #print("Updating foreign key references to ccm_project table...")
            #update_sql = f"""
            #    UPDATE gpa
            #    SET gpa.project_ccm_id = p.id
            #    FROM ccm_googleprojectapi AS gpa
            #    INNER JOIN ccm_project AS p ON gpa.parent = p.name
            #    WHERE gpa.parent = '{parent}';
            #"""
            #sqlh.execute_sql(update_sql)
            #print("Foreign key update complete.")

        except Exception as e:
            print(f"CRITICAL API ERROR: Failed to list APIs for {project_id}. {e}")
            raise e 
            return None

    def list_all_instances(self, project_id: str,
                           sqlh:lib_sqlhandler.SqlAService = None):
        """
        Lists all Compute Engine VM instances across all zones for a given project.
        Prints the raw JSON output to stdout for inspection.
        """
        print(f"Fetching all VM instances for project: {project_id}...")

        try:
            # 1. Build the Compute Engine service object
            compute_service = build('compute', 'v1', credentials=self.base_creds)

            # 2. Use aggregatedList to get instances from all zones in one call
            request = compute_service.instances().aggregatedList(project=project_id)

            all_instances = []

            # 3. Handle pagination for the aggregated list
            while request is not None:
                response = request.execute()

                # The response is a dictionary where keys are 'zones/zone-name'
                # and values contain the list of instances for that zone.
                for name, instances_scoped_list in response['items'].items():
                    # The 'instances' key might be missing if a zone has no VMs
                    if 'instances' in instances_scoped_list:
                        all_instances.extend(instances_scoped_list['instances'])

                # Get the next page token to continue the loop
                request = compute_service.instances().aggregatedList_next(
                    previous_request=request, 
                    previous_response=response
                )

            print(f"Found a total of {len(all_instances)} instances across all zones.")

            # 4. Print the collected data as a pretty-printed JSON string
            # Using default=str handles non-serializable types like datetimes
            #print("\n--- RAW API JSON OUTPUT ---")
            #print(json.dumps(all_instances, indent=2, default=str))
            # 4. Process the raw instance data into a structured list for the database
            instances_to_insert = []
            

            for instance in all_instances:
                # --- Safely extract nested network information ---
                # This list will hold details for ALL network interfaces.
                processed_nics = []
                # Use .get() to avoid errors if 'networkInterfaces' is missing
                nics = instance.get('networkInterfaces', [])
                for nic in nics:
                    nic_data = {
                        'name': nic.get('name'),
                        'network': nic.get('network'),
                        'network_ip': nic.get('networkIP'),
                        'nat_ip': None # Default to None
                    }
                    # Use .get() again for accessConfigs, which might be missing
                    access_configs = nic.get('accessConfigs', [])
                    if access_configs:
                        # An interface can technically have multiple external IPs, but we'll grab the first one.
                        nic_data['nat_ip'] = access_configs[0].get('natIP')
                    processed_nics.append(nic_data)
                
                def parse_gcp_timestamp(ts_string):
                    """Safely parse GCP's ISO 8601 timestamp string."""
                    if not ts_string:
                        return None
                    try:
                        # fromisoformat handles the timezone offset correctly
                        return datetime.fromisoformat(ts_string)
                    except (ValueError, TypeError):
                        return None
                        
                # --- Safely extract disk and license information ---
                disk_licenses = []
                disks = instance.get('disks', [])
                if disks:
                    # This example collects licenses from ALL disks attached
                    for disk in disks:
                        disk_licenses.extend(disk.get('licenses', []))

                # --- Build the flat dictionary for insertion ---
                #print(json.dumps(instance.get('tags', {}))) 
                instances_to_insert.append({
                    'gcp_instance_id': instance.get('id'),
                    'creation_timestamp': parse_gcp_timestamp(instance.get('creationTimestamp')),
                    'name': instance.get('name'),
                    'status': instance.get('status'),
                    'zone': instance.get('zone', '').split('/')[-1], # Extract just the zone name
                    'machine_type': instance.get('machineType', '').split('/')[-1], # Extract just the machine type
                    'last_start_timestamp': parse_gcp_timestamp(instance.get('lastStartTimestamp')),
                    'last_stop_timestamp': parse_gcp_timestamp(instance.get('lastStopTimestamp')),
                    'last_suspended_timestamp': parse_gcp_timestamp(instance.get('lastSuspendedTimestamp')),
                    # Store complex types as JSON strings in the database
                    'tags_json': instance.get('tags', {}),
                    #'network_interfaces_json': json.dumps(processed_nics),
                    #'disks_licenses_json': json.dumps(disk_licenses),
                    # Keep the full raw data for future analysis or re-processing
                    'api_data': instance 
                })
                #print(f"{instance.get('name')} ")
            engine = sqlh.engine
            with Session(engine) as session:
                session.execute(insert(models.CcmGoogleInstanceStaging), instances_to_insert)
                session.commit()

            print(f"Processed {len(instances_to_insert)} instances for database staging.")

            # 5. Print the PROCESSED data for your review.
            # This is the data you will use for your bulk insert.
            #print("\n--- PROCESSED INSTANCE DATA (ready for DB insert) ---")
            #print(json.dumps(instances_to_insert, indent=2, default=str))

            # NEXT STEP: You would take 'instances_to_insert' and perform a bulk
            # insert into your new CcmInstanceStaging table.
            # with Session(sqlh.engine) as session:
            #     session.execute(insert(models.CcmInstanceStaging), instances_to_insert)
            #     session.commit()

        except HttpError as e:
            print(f"CRITICAL API ERROR: Failed to list instances for {project_id}. {e.resp.status} - {e.reason}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            print(f"An unexpected error occurred: {e}", file=sys.stderr)
            raise
        
    def list_all_organizations(self, sqlh:lib_sqlhandler.SqlAService = None):
        """
        Lists all accessible GCP Organizations.
        """
        print("Fetching accessible GCP Organizations...")
        #engine = create_engine(sqlh.db_url)
        engine = sqlh.engine

        # Initializes the Organizations client using your base Service Account credentials
        client = resourcemanager_v3.OrganizationsClient(credentials=self.base_creds)
        
        try:
            # Searching without a query returns all accessible organizations
            organizations = client.search_organizations()
            
            with Session(engine) as session:
                c = 0
                # itertools.batched
                batch_size=5000
                c_total = 0
                for chunk in batched(organizations, batch_size):
                    # org.name returns the string in the format "organizations/1234567890"
                    # org.display_name returns the human-readable name like "example.com"
                    #org_id = org.name.split('/')[-1] 
                    #https://googleapis.dev/python/protobuf/latest/google/protobuf/timestamp_pb2.html
                    #print(f"Organization ID: {org_id} | Name: {org.display_name} {type(org).to_json(org)} {type(org).to_dict(org)} ")
                    #{org.create_time.ToJsonString()}
                    #https://developers.google.com/workspace/admin/directory/reference/rest/v1/groups/
                    #https://docs.cloud.google.com/resource-manager/reference/rest/v3/organizations
                    #https://docs.cloud.google.com/python/docs/reference/cloudresourcemanager/latest/google.cloud.resourcemanager_v3.types.Organization
                    batch_dicts = []
                    
                    for org in chunk:
                        c_total +=1
                        if c_total % 500 == 0:
                            helperlib.print_flush(f"Appending item {c_total} with batch size {batch_size}. Done {c} batches")
                        org_dict = type(org).to_dict(org)
                        org_id = org.name.split('/')[-1]
                        batch_dicts.append({
                            "api_lastseen": datetime.now(timezone.utc),
                            "name": org.name,
                            "organisation_id": org_id,
                            "display_name": org.display_name,
                            "directory_customer_id": org.directory_customer_id,
                            "state": org.state.name,
                            "create_time": org.create_time,
                            "update_time": org.update_time,
                            "etag": org.etag,
                            "api_data": org_dict
                        })
                    session.execute(insert(models.CcmOrganisation), batch_dicts)
                    session.commit()
                    c += len(batch_dicts)
                    print(f"Inserted batch of {len(batch_dicts)} rows. Total so far: {c}")
                    """    
                    statement = select(models.CcmOrganisation).where(models.CcmOrganisation.name == org_name)
                    existing_org = session.scalars(statement).one_or_none()
                    if existing_org:
                        existing_org.api_lastseen = datetime.now(timezone.utc)
                        existing_org.display_name = org.display_name
                        existing_org.state = org.state.name
                        existing_org.update_time = org.update_time
                        existing_org.etag = org.etag
                        existing_org.api_data = org_dict
                        # (Notice we intentionally do NOT update created_time or directory_customer_id)
                        print(f"Updated existing org: {org_name}")
                    else:
                        # 3. INSERT: It does not exist. Create it and add to session.
                        new_org_record = models.CcmOrganisation(
                            api_lastseen=datetime.now(timezone.utc), 
                            name=org_name,
                            organisation_id=org_id,
                            display_name=org.display_name,
                            directory_customer_id=org.directory_customer_id,
                            state=org.state.name, 
                            create_time=org.create_time, 
                            update_time=org.update_time, 
                            etag=org.etag,
                            api_data=org_dict 
                        )
                        session.add(new_org_record)
                        print(f"Inserted new org: {org_name}")
                    """ 
                    """# 3. Create the Python object mapping to your table
                    new_org_record = models.CcmOrganisation(
                        api_lastseen=datetime.now(timezone.utc), 
                        name=org.name,
                        organisation_id=org_id,
                        display_name=org.display_name,
                        directory_customer_id=org.directory_customer_id,
                        state=org.state.name, 
                        create_time=org.create_time, 
                        update_time=org.update_time, 
                        etag=org.etag,
                        api_data=org_dict 
                    )
                    # 4. Add it to the session workspace (this does NOT hit the DB yet)
                    session.add(new_org_record)"""
                session.commit() 
            print(f"Total organizations returned: {c}")
            #return org_list
            
        except Exception as e:
            print(f"CRITICAL API ERROR: Failed to list GCP organizations. {e}")
            #return None
        
    def list_all_folders(self, sqlh:lib_sqlhandler.SqlAService = None):
        """
        Lists all GCP Folders the service account has access to.
        Sits between Organizations and Projects in the taxonomy.
        """
        print("Fetching accessible GCP Folders...")
        
        if not sqlh:
            print("CRITICAL ERROR: No SQL handler provided.")
            return

        engine = create_engine(sqlh.db_url)

        # Initialize the Folders client using your base Service Account credentials
        client = resourcemanager_v3.FoldersClient(credentials=self.base_creds)
        
        try:
            # Searching without a query returns all accessible folders across the org
            folders = client.search_folders()
            
            folder_list = []
            with Session(engine) as session:
                c = 0
                for folder in folders:
                    c += 1
                    # folder.name returns "folders/1234567890"
                    # folder.parent returns the parent resource, e.g., "organizations/123" or "folders/456"
                    folder_dict = type(folder).to_dict(folder)
                    folder_id = folder.name.split('/')[-1]
                    folder_name = folder.name
                    
                    # Look for existing folder to UPSERT
                    statement = select(models.CcmFolder).where(models.CcmFolder.name == folder_name)
                    existing_folder = session.scalars(statement).one_or_none()
                    
                    if existing_folder:
                        existing_folder.api_lastseen = datetime.now(timezone.utc)
                        existing_folder.display_name = folder.display_name
                        existing_folder.parent = folder.parent
                        existing_folder.state = folder.state.name
                        existing_folder.update_time = folder.update_time
                        existing_folder.etag = folder.etag
                        existing_folder.api_data = folder_dict
                        print(f"{c} Updated existing folder: {folder_name}")
                    else:
                        # INSERT: It does not exist. Create it and add to session.
                        new_folder_record = models.CcmFolder(
                            api_lastseen=datetime.now(timezone.utc), 
                            name=folder_name,
                            folder_id=folder_id,
                            display_name=folder.display_name,
                            parent=folder.parent,
                            state=folder.state.name, 
                            create_time=folder.create_time, 
                            update_time=folder.update_time, 
                            etag=folder.etag,
                            api_data=folder_dict 
                        )
                        session.add(new_folder_record)
                        print(f"{c} Inserted new folder: {folder_name}")
                        
                    folder_list.append(folder)
                
                # Commit all updates and inserts in one transaction
                session.commit() 
                
            print(f"Total folders returned: {len(folder_list)}")
            # update the ccm_organisation_id
            sql ="""WITH FolderTree AS (
                -- 1. Base Case: Find all folders that are directly under an Organization
                SELECT 
                    id AS folder_ccm_id,
                    name AS folder_name,
                    parent AS root_org_name -- e.g., 'organizations/123456789'
                FROM ccm_folder
                WHERE parent LIKE 'organizations/%'
                UNION ALL
                -- 2. Recursive Step: Find all child folders and inherit the root_org_name from their parent
                SELECT 
                    child.id AS folder_ccm_id,
                    child.name AS folder_name,
                    tree.root_org_name
                FROM ccm_folder child
                INNER JOIN FolderTree tree 
                    ON child.parent = tree.folder_name
            )
            -- 3. The Update Statement: Join the resolved tree to the organisation table to get the PK
            UPDATE f
            SET f.organisation_ccm_id = o.id
            FROM ccm_folder f
            INNER JOIN FolderTree ft 
                ON f.id = ft.folder_ccm_id
            INNER JOIN ccm_organisation o 
                ON ft.root_org_name = o.name;"""
            sqlh.execute_sql(sql) 
            return folder_list
            
        except Exception as e:
            print(f"CRITICAL API ERROR: Failed to list GCP folders. {e}")
            return None
    """Recursive CTE Common Table Expression
        WITH FolderTree AS (
        -- Base Case: Find all top-level folders (where the parent is an organization)
        SELECT 
            name AS folder_name,
            display_name,
            parent AS current_parent,
            parent AS root_organization -- This is the ultimate org!
        FROM ccm_folder
        WHERE parent LIKE 'organizations/%'

        UNION ALL

        -- Recursive Step: Find all sub-folders and inherit the root_organization from the parent
        SELECT 
            child.name,
            child.display_name,
            child.parent,
            tree.root_organization -- Passes the org down to the children
        FROM ccm_folder child
        INNER JOIN FolderTree tree 
            ON child.parent = tree.folder_name
    )
    -- See the final flat list!
    SELECT folder_name, display_name, root_organization 
    FROM FolderTree;"""
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
    
    