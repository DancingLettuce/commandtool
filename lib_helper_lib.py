"""This file is helperlib.py"""

from datetime import datetime as dt_datetime, timedelta  , timezone as dt_timezone 
from dataclasses import dataclass, field
import tomllib 
from pathlib import Path

# git update
# for d in */ ; do if [ -d "$d.git" ]; then echo -e "\n--- Updating $d ---"; (cd "$d" && git pull); fi; done 
#b

class TimeDiff():
    def __init__(self,start_time=None, end_time=None):
        current_time = dt_datetime.now(dt_timezone.utc) # timezone.now()
        self.start_time = start_time or current_time
        self.end_time = end_time or current_time
        self.start_time_str = self.start_time.strftime('%H:%M:%S')
        """
        for k,v in kwargs.items():
            setattr(self,k,v) 
        """
    def convert_timediff(self, end_time=None, style='full'):
        current_time = dt_datetime.now(dt_timezone.utc) # timezone.now()
        if end_time:
            self.end_time = end_time
        else:
            self.end_time= current_time
        duration = self.end_time - self.start_time
        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        duration_parts = []
        if style == 'full':
            hh=' hours'
            mm=' minutes'
            ss=' seconds'
        elif style=='compact':
            hh=' h'
            mm=' m'
            ss=' s'
        elif style=='mini':
            hh='h'
            mm='m'
            ss='s'
        elif style=='hm':
            hh='h'
            mm='m'
            ss=None
        if hours > 0:
            duration_parts.append(f"{hours}{hh}")
        if minutes > 0:
            duration_parts.append(f"{minutes}{mm}")
        if ss is not None:
            duration_parts.append(f"{seconds}{ss}")
        if style =='hm':
            self.duration_str = "".join(duration_parts)
        else:    
            self.duration_str = ", ".join(duration_parts)
        return(self.duration_str)
    
def print_flush(message):
    """Print a string and do not move the cursor for progress-type displays"""
    message = message[:80]
    print ( f"{message } {' ' * 80 }", end= "\r", flush=True )

@dataclass 
class ScriptLog():
    summary: list = field(
        default_factory=lambda: []
        ) 
    filename: str = "log.txt"
    max_entries: int = 10
    def print_log_file(self,log_text: str, summary:bool = False):
        current_log = []
        # --- 1. Read existing log entries ---
        try:
            # 'r' mode opens the file for reading
            with open(self.filename, 'r') as f:
                # Read all lines and strip any trailing newline characters
                current_log = [line.strip() for line in f.readlines()]
        except FileNotFoundError:
            # If the file doesn't exist yet, current_log remains empty
            pass
        # --- 2. Remove oldest entries if capacity is reached ---
        # The list is indexed 0 (oldest) to 4 (newest).
        while len(current_log) >= self.max_entries:
            # Remove the first (oldest) item from the list
            current_log.pop(0)
        # --- 3. Create the new log entry ---
        # Format the timestamp as yyyy-mm-dd hh:mm
        timestamp = dt_datetime.now().strftime('%Y-%m-%d %H:%M')
        new_entry = f"{timestamp} {log_text}"
        if summary:
            self.summary.append(new_entry)
        # Append the new entry
        current_log.append(new_entry)

        # --- 4. Write the updated list back to the file ---
        # 'w' mode truncates (clears) the file and writes the new contents
        try:
            with open(self.filename, 'w') as f:
                # Write each entry on a new line
                for entry in current_log:
                    f.write(entry + '\n')
                
        except IOError as e:
            print(f"Error writing to log file {self.filename}: {e}")
            return False
            
        print(f"Log updated: {new_entry}")
        return True
    def print_summary(self):
        print("#" * 80)
        for i in self.summary:
            print(f"#{i}")
        print("#" * 80)

def print_log_file(log_text: str, filename: str = "log.txt", max_entries: int = 10):
    """
    Reads a log file into a list, maintains a maximum number of entries, 
    appends a new timestamped entry, and writes the list back to the file.
    """
    if filename is None:
        if args.logfile:
            filename = args.logfile
        else:
            filename = 'log.txt'

    current_log = []
    # --- 1. Read existing log entries ---
    try:
        # 'r' mode opens the file for reading
        with open(filename, 'r') as f:
            # Read all lines and strip any trailing newline characters
            current_log = [line.strip() for line in f.readlines()]
    except FileNotFoundError:
        # If the file doesn't exist yet, current_log remains empty
        pass
    # --- 2. Remove oldest entries if capacity is reached ---
    # The list is indexed 0 (oldest) to 4 (newest).
    while len(current_log) >= max_entries:
        # Remove the first (oldest) item from the list
        current_log.pop(0)
    # --- 3. Create the new log entry ---
    # Format the timestamp as yyyy-mm-dd hh:mm
    timestamp = dt_datetime.now().strftime('%Y-%m-%d %H:%M')
    new_entry = f"{timestamp} {log_text}"
    
    # Append the new entry
    current_log.append(new_entry)

    # --- 4. Write the updated list back to the file ---
    # 'w' mode truncates (clears) the file and writes the new contents
    try:
        with open(filename, 'w') as f:
            # Write each entry on a new line
            for entry in current_log:
                f.write(entry + '\n')
            
    except IOError as e:
        print(f"Error writing to log file {filename}: {e}")
        return False
        
    print(f"Log updated: {new_entry}")
    return True

def init_secrets(toml_string: str, filename: str="secrets.toml", unlink: bool = False):
    """Checks for the config file and creates it with defaults if missing."""
    config_file = Path(filename)
    if unlink:
        config_file.unlink(missing_ok=True)
    if not config_file.exists():
        # Create the file and write the defaults
        config_path = Path(config_file)
        # Create the directories
        config_path.parent.mkdir(parents=True, exist_ok=True)
        # Write the string and specify the encoding in one line
        config_path.write_text(toml_string, encoding="utf-8")
        print(f"Created {filename} with default configurations.")
    CONFIG = tomllib.loads(Path(filename).read_text(encoding="utf-8"))
    #with open(filename, "rb") as f:
    #    CONFIG = tomllib.load(f) 
    return CONFIG

def get_multiline_input(message :str="Enter your text (Type ':q' on a new line or hit Enter twice to finish):"):
    print(message)  
    lines = []
    blank_count = 0

    while True:
        try:
            line = input()
        except EOFError:
            # Engineers love using Ctrl+D (Linux/Mac) or Ctrl+Z (Windows) to send EOF.
            # This safely catches that standard terminal exit signal.
            break

        # Termination Condition 1: User types :q
        if line.strip() == ":q":
            break

        # Termination Condition 2: Two consecutive empty lines
        if line == "":
            blank_count += 1
            if blank_count == 2:
                # Remove the first blank line from the list so it doesn't pollute the final string
                if lines:
                    lines.pop()
                break
        else:
            # Reset the counter if they typed actual text
            blank_count = 0

        # Add the line to our list
        lines.append(line)

    # Stitch it all together with carriage returns
    return "\n".join(lines)


