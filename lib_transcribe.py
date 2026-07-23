"""This file is lib_transcribe.py"""

from dataclasses import dataclass, field
#2251
import os
import io
import sys   
import argparse    
import json
from datetime import datetime as dt_datetime, timedelta  , timezone as dt_timezone  
from functools import cached_property
import typing
from typing_extensions import TypedDict
typing.TypedDict = TypedDict # This intercepts and patches the bug in memory
#from typing import TypedDict

 
import lib_helper_lib as helperlib 
#
try:
    from google.oauth2 import service_account 
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload
    import_googleauth = True
except Exception as e:
    import_googleauth = False
    print(f"WARNING: Can not import Google Auth {e}")


# GenAI imports
try:
    from google import genai
    from google.genai import types
    import_googleai = True
except Exception as e:
    import_googleai = False
    print(f"WARNING: Can not import Google AI {e}")

try:
    from pydantic import BaseModel # pip install pydantic
    import_pydantic = True
except Exception as e:
    import_pydantic = False
    print(f"WARNING: Can not import Pydantic {e}")

try:
    import psycopg
    from pgvector.psycopg import register_vector
    import_postgres = True
except Exception as e:  
    print(f"WARNING: Can not import Postgres {e}")
    import_postgres = False
# progresql
# pip install "psycopg[binary]" pgvector

# This tells Gemini EXACTLY what keys to use and what data types they are.
#class MeetingRecord(BaseModel):
class MeetingRecord(TypedDict):
    attendees: list[str]
    meeting_summary: str
    dictated_preamble_notes: str
    verbatim_transcript: str
    timestamp: str
# You can pass this directly to the Gemini SDK:
# response = client.models.generate_content(
#     model='gemini-2.5-flash',
#     contents='Here is the audio transcript...',
#     config={
#         'response_mime_type': 'application/json',
#         'response_schema': MeetingRecord,
#     },
# )

class PresentationRecord(TypedDict):
    presentation_title: str
    presentation_summary: str
    dictated_preamble_notes: str
    verbatim_transcript: str
    timestamp: str

@dataclass
class Transcriber():
    # dataclass is the equivalent of init(arg=val)
    project_id: str = ""
    delegated_email: str = ""
    location: str = "global"
    service_account_file: str = ""
    semantic_database : str = ""
    semantic_user : str = ""
    semantic_password : str = ""
    semantic_ip : str = ""
    text_vector = None
    supplied_context: str = ""
    transcribe_prompt_additional_1: str = ""
    # Use field(default_factory=...) for lists and dictionaries
    vertex_scopes: list = field(
        default_factory=lambda: ['https://www.googleapis.com/auth/cloud-platform']
        ) 
  
    @property  
    def connection(self):
        # This acts like Visual Basic's "Property Get"
        if self._connection is None:
            print("Connecting to the database for the first time...")
            self._connection = "Connected Object!" # Do the expensive work here
        
        return self._connection
    
    @cached_property
    def vertex_creds(self):
        return service_account.Credentials.from_service_account_file(
            self.service_account_file, 
            scopes=self.vertex_scopes
            ) 
    
    @cached_property
    def ai_client(self):
        """Returns audio in JSON """
        return genai.Client(
            vertexai=True, 
            project=self.project_id, 
            location=self.location,
            credentials=self.vertex_creds
            )


    def transcribe_audio_lecture(self,
        audio_file_path: str, 
        ):
        with open(audio_file_path, "rb") as f:
                    audio_bytes = f.read()
        audio_part = types.Part.from_bytes(
            data=audio_bytes,
            mime_type="audio/mp3" # Update as needed for your file type
            )
        safety_settings = [
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=types.HarmBlockThreshold.BLOCK_NONE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=types.HarmBlockThreshold.BLOCK_NONE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=types.HarmBlockThreshold.BLOCK_NONE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
            ]
        print("Sending Lecture Audio To Gemini")
        prompt = """
                    You are an expert enterprise transcriptionist. I want you to perform a two-pass analysis of this audio file which is
                    a presentation or a lecture. 
                    """
        
        if self.supplied_context:
            prompt += "\n This is additional context for this specific transcription: "
            prompt += self.supplied_context    
        prompt +="""    
            PASS 1 (Analysis): 
            Analyze the first 5 minutes of the audio. Pay close attention to the pre-amble or initial introductions. 
            Identify the title of the lecture or presentation, 
            the purpose of the lecture, the identity of the speaker and the timestamp stated.  """
        
        prompt += """
            PASS 2 (Transcription):
            Using the identities and context you extracted in Pass 1, transcribe the entire audio file from the very beginning (00:00). 
            Use the correct speaker names to label the dialogue throughout. Provide a completely verbatim transcription, word-for-word.
            Ensure that swearing, offensive language and all inappropriate language is transcribed: the transcription must be good enough 
            to use as evidence
            in the case of disciplinary action.

            At the end of the transcription, provide a summary of the conversation with a summary in bullet list format.

            Extract the following :
            1. The title of the lecture or presentation.
            2. A concise summary of the lecture.
            3. The exact dictated preamble notes (if the speaker says 'these are the preamble notes').
            4. The complete verbatim transcript of the actual lecture or presentation. 

            Output Format:
            Meeting Metadata:
            - Date/Timestamp: [Extracted Timestamp]
            - Lecture Title: [Extracted Title]
            - Summary: [Extracted Summary]

            Transcript:
            [Speaker Name]: [Dialogue]
            """
        print(prompt)  
        response_stream = self.ai_client.models.generate_content_stream(
            model='gemini-3.5-flash',
            contents=[prompt, audio_part],
            config=types.GenerateContentConfig(
                    safety_settings=safety_settings
                ))
        print("\n--- Live Lecture Transcription Starting ---")
        transcript_text = f"Transcription of {audio_file_path}\n\n"

    
        # Loop through the stream and print it live   
        for chunk in response_stream:
            # Print the chunk to the terminal without a new line, and force it to display immediately
            print(chunk.text, end="", flush=True) 
            # Add the chunk to our master string
            transcript_text += chunk.text

        return transcript_text


    def transcribe_audio(self,
        audio_file_path: str, 
        ):
        """Returns audio in JSON """
        #ai_client = genai.Client(
        #    vertexai=True, 
        #    project=self.project_id, 
        #    location=self.location,
        #    credentials=self.vertex_creds
        #    )
        with open(audio_file_path, "rb") as f:
            audio_bytes = f.read()
        audio_part = types.Part.from_bytes(
            data=audio_bytes,
            mime_type="audio/mp3" # Update as needed for your file type
            )
        safety_settings = [
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=types.HarmBlockThreshold.BLOCK_NONE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=types.HarmBlockThreshold.BLOCK_NONE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=types.HarmBlockThreshold.BLOCK_NONE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.BLOCK_NONE,
                ),
            ]
        print("Sending Audio To Gemini")

        prompt = """
            You are an expert enterprise transcriptionist. I want you to perform a two-pass analysis of this audio file. 
            """

        if self.supplied_context:
            prompt += "\n This is additional context for this specific transcription: "
            prompt += self.supplied_context    
        prompt +="""    
            PASS 1 (Analysis): 
            Analyze the first 5 minutes of the audio. Pay close attention to the pre-amble or initial introductions. 
            Identify the names of all attendees, the purpose of the meeting, and the timestamp stated.  Generally the audio will 
            be introduced by an attendee
            of the meeting. They may list the attendees who are invited and may give the purpose of the meeting and the date time of
            the meeting.  """
        prompt += self.transcribe_prompt_additional_1 
        prompt += """
            PASS 2 (Transcription):
            Using the identities and context you extracted in Pass 1, transcribe the entire audio file from the very beginning (00:00). 
            Use the correct speaker names to label the dialogue throughout. Provide a completely verbatim transcription, word-for-word.
            Ensure that swearing, offensive language and all inappropriate language is transcribed: the transcription must be good enough to use as evidence
            in the case of disciplinary action.

            At the end of the transcription, provide a summary of the conversation with a bullet list of any action points or decisions.

            Extract the following into the provided JSON schema:
            1. A list of all attendees.
            2. A concise summary of the meeting's outcome.
            3. The exact dictated preamble notes (if the speaker says 'these are the preamble notes').
            4. The complete verbatim transcript of the actual meeting. 

            Output Format:
            Meeting Metadata:
            - Date/Timestamp: [Extracted Timestamp]
            - Purpose: [Extracted Purpose]
            - Attendees: [List of Names]

            Transcript:
            [Speaker Name]: [Dialogue]
            """
        print(prompt)  
        response_stream = self.ai_client.models.generate_content_stream(
            model='gemini-3.5-flash',
            contents=[prompt, audio_part],
            config=types.GenerateContentConfig(
                # safety_settings=safety_settings
                temperature=0.0,
                response_mime_type="application/json",
                response_schema=MeetingRecord,
                )
            )
        print("\n--- Live Transcription Starting ---")
         # We need a string to hold the final output for Google Drive
        timenow= dt_datetime.now(dt_timezone.utc)
        timeformat= timenow.strftime('%Y-%m-%d-%H%M')
        transcript_text = ""

        for chunk in response_stream:

            # Print the chunk to the terminal without a new line, and force it to display immediately
            print(chunk.text, end="", flush=True) 
            # Add the chunk to our master string
            transcript_text += chunk.text
        meeting_data = json.loads(transcript_text)


        with open('output.json', 'w') as f:
            # Use json.dump to write the data to the file
            json.dump(meeting_data, f, indent=4)
        return meeting_data   

    def transcribe_audio__2(self,
        audio_file_path: str, 
        source_type: str = "meeting",
        uploadtodrive: bool = False
        ):
        """Returns audio in JSON """
        #ai_client = genai.Client(
        #    vertexai=True, 
        #    project=self.project_id, 
        #    location=self.location,
        #    credentials=self.vertex_creds
        #    )
        with open(audio_file_path, "rb") as f:
            audio_bytes = f.read()
        audio_part = types.Part.from_bytes(
            data=audio_bytes,
            mime_type="audio/mp3" # Update as needed for your file type
            )
        safety_settings = [
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=types.HarmBlockThreshold.BLOCK_NONE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=types.HarmBlockThreshold.BLOCK_NONE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=types.HarmBlockThreshold.BLOCK_NONE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.BLOCK_NONE,
            ),
            ]
        print("Sending Audio To Gemini")

        
        prompt = """
            You are an expert enterprise transcriptionist. I want you to perform a two-pass analysis of this audio file. 
            """
            

        if self.supplied_context:
            prompt += "\n This is additional context for this specific transcription: "
            prompt += self.supplied_context    

        if source_type == "meeting":
            prompt +="""    
                PASS 1 (Analysis): 
                Analyze the first 5 minutes of the audio. Pay close attention to the pre-amble or initial introductions. 
                Identify the names of all attendees, the purpose of the meeting, and the timestamp stated.  
                Generally the audio will be introduced by an attendee who will state the date, time
                of the meeting. They may list the attendees who are invited and may give the purpose of the meeting. """
            prompt += self.transcribe_prompt_additional_1
            prompt += """
                PASS 2 (Transcription):
                Using the identities and context you extracted in Pass 1, transcribe the entire audio file from the very beginning (00:00). 
                Use the correct speaker names to label the dialogue throughout. Provide a completely verbatim transcription, word-for-word.
                Ensure that swearing, offensive language and all inappropriate language is transcribed: the transcription must be good enough to use as evidence 
                in the case of disciplinary action.

                At the end of the transcription, provide a summary of the conversation with a bullet list of any action points or decisions.

                Extract the following into the provided JSON schema:
                1. A list of all attendees.
                2. A concise summary of the meeting's outcome.
                3. The exact dictated preamble notes (if the speaker says 'these are the preamble notes').
                4. The complete verbatim transcript of the actual meeting. 
                
                Output Format:
                Meeting Metadata:
                - Date/Timestamp: [Extracted Timestamp]
                - Purpose: [Extracted Purpose]
                - Attendees: [List of Names]

                Transcript:
                [Speaker Name]: [Dialogue]
                """
            response_schema = MeetingRecord
        elif source_type == "presentation":
            prompt +="""    
                    PASS 1 (Analysis): 
                    Analyze the first 5 minutes of the audio. Pay close attention to the pre-amble which describes the course or presentation that is being recorded. 
                    Identify the name of the course and the module or session number.  The pre-amble may provide the names of the principal presenters or tutors in 
                    the course or the presentation.
                    
    
                    PASS 2 (Transcription):
                    Using the speaker identities and context you extracted in Pass 1, transcribe the entire audio file from the very beginning (00:00). 
                    Use the correct speaker names to label the dialogue throughout. Provide a completely verbatim transcription, word-for-word.
                    Ensure that swearing, offensive language and all inappropriate language is transcribed: the transcription must be good enough to use as evidence 
                    in the case of disciplinary action.
    
                    At the end of the transcription, provide a summary of the presentation.
    
                    Extract the following into the provided JSON schema:
                    1. The name of the course or presentation.
                    2. A concise summary of the course or presentation.
                    3. The exact dictated preamble notes (if the speaker says 'these are the preamble notes').
                    4. The complete verbatim transcript of the actual course or presentation. 
                    
                    Output Format:
                    Meeting Metadata:
                    - Date/Timestamp: [Extracted Timestamp]
                    - Presentation name: [Extracted Name]
                    - Summary: [Extracted Summary]
    
                    Transcript:
                    [Speaker Name]: [Dialogue]
                    """
            response_schema = PresentationRecord

        print(prompt)  
        response_stream = self.ai_client.models.generate_content_stream(
            model='gemini-3.5-flash',
            contents=[prompt, audio_part],
            config=types.GenerateContentConfig(
                # safety_settings=safety_settings
                temperature=0.0,
                response_mime_type="application/json",
                response_schema=response_schema,
                )
            )
        print("\n--- Live Transcription Starting ---")
         # We need a string to hold the final output for Google Drive
        timenow= dt_datetime.now(dt_timezone.utc)
        timeformat= timenow.strftime('%Y-%m-%d-%H%M')
        transcript_text = ""
        
        for chunk in response_stream:
            
            # Print the chunk to the terminal without a new line, and force it to display immediately
            print(chunk.text, end="", flush=True) 
            # Add the chunk to our master string
            transcript_text += chunk.text
        meeting_data = json.loads(transcript_text)

        
        with open('output.json', 'w') as f:
            # Use json.dump to write the data to the file
            json.dump(meeting_data, f, indent=4)
        return meeting_data   

    def generate_text_vector(self, text_to_embed: str):
        # ---------------------------------------------------------
        # Generate the Vector Embedding
        # ---------------------------------------------------------
        print("Generating vector embedding for semantic search...")
                
        # Call the dedicated embedding model
        embed_response = self.ai_client.models.embed_content(
            model='text-embedding-004', 
            contents=text_to_embed,
            # Optional: You can specify output dimensionality if your DB is strictly set (e.g., 768)
            # config=types.EmbedContentConfig(output_dimensionality=768) 
        )
        
        # Extract the native Python list of floats from the response
        text_vector = embed_response.embeddings[0].values
        """Because you did not specify a dimension limit (like vector(768)), pgvector will accept 
        whatever size array you hand it. By default, Google's text-embedding-004 outputs a 768-dimensional array. 
        Your Psycopg client will take the text_vector list we just generated and seamlessly insert it into that column!"""

        print(f"Successfully generated a {len(text_vector)}-dimension vector.")
        self.text_vector = text_vector
        return text_vector
    def insert_semantic_json(self, meeting_data: dict | None = None):
        if meeting_data is None:
            meeting_data = {}
        # pgvector allows you to pass standard Python lists of floats directly!
        # (Once you have real data, this will be the embedding array from Gemini)
        attendees = meeting_data['attendees']
        summary = meeting_data['meeting_summary']
        fulltext = meeting_data['verbatim_transcript']
        timestamp = meeting_data['timestamp']
        text_vector = self.generate_text_vector(meeting_data['meeting_summary'])

        # Capture the exact current time in UTC
        current_time = dt_datetime.now(dt_timezone.utc)

        # ---------------------------------------------------------
        # 3. Execution Block
        # ---------------------------------------------------------
        # Build the connection string 
        #conn_string = (f"dbname={CONFIG['SEMANTIC_DATABASE']} "
        #            f"user={CONFIG['SEMANTIC_USER']} "
        #            f"password={CONFIG['SEMANTIC_PASSWORD']} "
        #            f"host={CONFIG['SEMANTIC_IP']}")
        conn_string = (f"dbname={self.semantic_database} "
                    f"user={self.semantic_user} "
                    f"password={self.semantic_password} "
                    f"host={self.semantic_ip}")
    
        helperlib.print_log_file(f"Connecting to PostgreSQL... {self.semantic_ip}") 

        # Use a context manager (with) so the connection automatically closes when done
        with psycopg.connect(conn_string) as conn:
            
            # Register the pgvector extension so Psycopg knows how to format the float list
            register_vector(conn)

            with conn.cursor() as cur:
                # We use parameterized queries (%s) to completely prevent SQL Injection.
                # Never use f-strings to insert data directly into a SQL query!
                insert_query = """  
                    INSERT INTO public.meet (
                        tags, attendees, summary, full_text, 
                        text_vector, event_timestamp, created_on
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s
                    ) RETURNING id;
                """
                    
                helperlib.print_log_file(f"Executing INSERT statement...{insert_query}")
                cur.execute(insert_query, (
                    '',
                    attendees,
                    summary,
                    fulltext,
                    text_vector,
                    timestamp, # meet_timestamp
                    current_time  # created_on
                ))

                # Grab the brand new auto-incremented ID that PostgreSQL generated
                new_id = cur.fetchone()[0]
                
            # Commit the transaction to save it to the hard drive
            conn.commit()
            helperlib.print_log_file(f"Success! Meeting record inserted with ID: {new_id}") 
 