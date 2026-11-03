import subprocess
import sys
import os
import re
import json
import shutil
import time
import threading
from datetime import datetime

# Always run from the folder this script is in
os.chdir(os.path.dirname(os.path.abspath(__file__)))

LOG_FILE = "manager.log"       # the log file
CONFIG_FILE = "config.json"    # the settings file

# Used when config.json is missing, or when a value in it is not valid
DEFAULTS = {
    "max_restarts": 3,           # how many times to restart after a crash
    "keep_backups": 10,          # how many backup zips to keep
    "backup_every_minutes": 30,  # automatic backup while the server runs
    "max_memory": "2G",          # max memory for the server
    "min_memory": "1G",          # starting memory for the server
    "server_jar": "server.jar",  # name of the server file
}

# Smallest allowed number for each number setting
MIN_VALUES = {"max_restarts": 0, "keep_backups": 1, "backup_every_minutes": 1}

# Makes sure two backups never run at the same time
backup_lock = threading.Lock()
# Makes sure two messages are never written to the log at the same time
log_lock = threading.Lock()


def log(message):
    """Show a message on screen and also save it in manager.log with the time."""
    print(message)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with log_lock:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"[{stamp}] {message.strip()}\n")
    except OSError:
        pass  # if the log cannot be written, the script keeps working


def show_log(lines=20):
    """Show the last few lines of manager.log."""
    if not os.path.isfile(LOG_FILE):
        print("No log yet.")
        return
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            last = f.readlines()[-lines:]
    except OSError as error:
        print(f"Could not read the log: {error}")
        return
    if not last:
        print("The log is empty.")
        return
    print(f"\nLast {len(last)} log lines:")
    for line in last:
        print("  " + line.rstrip())


def load_config():
    """Read settings from config.json. Create it if missing. Bad values use the default."""
    config = dict(DEFAULTS)

    if not os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULTS, f, indent=4)
            log("Created config.json with the default settings.")
        except OSError as error:
            log(f"Could not create config.json ({error}). Using default settings.")
        return config

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            user = json.load(f)
        if not isinstance(user, dict):
            raise ValueError("the file must contain a JSON object")
    except (OSError, ValueError) as error:
        log(f"Could not read config.json ({error}). Using default settings.")
        return config

    for key, default in DEFAULTS.items():
        if key not in user:
            continue
        value = user[key]

        if key in MIN_VALUES:
            ok = isinstance(value, int) and not isinstance(value, bool) and value >= MIN_VALUES[key]
        elif key in ("max_memory", "min_memory"):
            ok = isinstance(value, str) and re.fullmatch(r"\d+[MmGg]", value) is not None
        else:
            ok = isinstance(value, str) and value.strip() != ""

        if ok:
            config[key] = value
        else:
            log(f"Setting '{key}' in config.json is not valid. Using {default!r} instead.")

    return config


config = load_config()
MAX_RESTARTS = config["max_restarts"]
KEEP_BACKUPS = config["keep_backups"]
BACKUP_EVERY_MINUTES = config["backup_every_minutes"]

command = [
    "java",
    f"-Xmx{config['max_memory']}",
    f"-Xms{config['min_memory']}",
    "-jar", config["server_jar"],
    "nogui",
]


def check_setup():
    """Check Java, the server file and the EULA. Returns True if all is ready."""
    problems = []

    if shutil.which("java") is None:
        problems.append("Java was not found. Install Java, then run `java -version` to check.")

    jar = config["server_jar"]
    if not os.path.isfile(jar):
        problems.append(f"The server file '{jar}' was not found in this folder.")

    # eula.txt is created by the server the first time it runs, so a missing file is fine
    if os.path.isfile("eula.txt"):
        try:
            with open("eula.txt", "r", encoding="utf-8") as f:
                text = f.read().lower().replace(" ", "")
            if "eula=true" not in text:
                problems.append("The EULA is not accepted. Open eula.txt and change eula=false to eula=true.")
        except OSError as error:
            problems.append(f"Could not read eula.txt ({error}).")

    if problems:
        log("The server cannot start yet:")
        for problem in problems:
            log(f"  - {problem}")
        return False
    return True


def backup_world():
    """Save a zip copy of the world folder. Returns True if it worked."""
    with backup_lock:
        if not os.path.isdir("world"):
            log("No 'world' folder found, skipping backup.")
            return True

        os.makedirs("backups", exist_ok=True)
        name = datetime.now().strftime("world_%Y-%m-%d_%H-%M-%S")
        temp_copy = os.path.join("backups", "_temp_copy")

        try:
            # Copy first, skipping session.lock (Windows locks it while the server runs)
            shutil.rmtree(temp_copy, ignore_errors=True)
            shutil.copytree("world", temp_copy, ignore=shutil.ignore_patterns("session.lock"))
            shutil.make_archive(os.path.join("backups", name), "zip", temp_copy)
            log(f"Backup saved: backups/{name}.zip")
        except Exception as error:
            log(f"Backup failed: {error}")
            return False
        finally:
            shutil.rmtree(temp_copy, ignore_errors=True)

        # Delete the oldest backups, keep only the newest ones
        zips = sorted(f for f in os.listdir("backups") if f.endswith(".zip"))
        for old in zips[:-KEEP_BACKUPS]:
            os.remove(os.path.join("backups", old))
            log(f"Deleted old backup: {old}")
        return True


def backup_loop(stop_event):
    """Runs in the background and backs up the world every few minutes."""
    while not stop_event.wait(BACKUP_EVERY_MINUTES * 60):
        log("Automatic backup...")
        backup_world()


def get_backups():
    """Return the backup file names, oldest first."""
    if not os.path.isdir("backups"):
        return []
    return sorted(f for f in os.listdir("backups") if f.endswith(".zip"))


def list_backups():
    """Show all backup files."""
    zips = get_backups()
    if not zips:
        print("No backups yet.")
        return
    for z in zips:
        size_mb = os.path.getsize(os.path.join("backups", z)) / (1024 * 1024)
        print(f"  {z}  ({size_mb:.1f} MB)")


def restore_backup():
    """Replace the current world with a chosen backup."""
    zips = get_backups()
    if not zips:
        print("No backups to restore.")
        return

    print("\nAvailable backups (newest at the bottom):")
    for number, z in enumerate(zips, start=1):
        size_mb = os.path.getsize(os.path.join("backups", z)) / (1024 * 1024)
        print(f"  {number}. {z}  ({size_mb:.1f} MB)")

    choice = input("Type the number of the backup to restore (or press Enter to cancel): ").strip()
    if not choice:
        print("Cancelled.")
        return
    if not choice.isdigit() or not 1 <= int(choice) <= len(zips):
        print("That is not a valid number. Nothing was changed.")
        return

    chosen = zips[int(choice) - 1]
    print(f"\nThis will REPLACE your current world with: {chosen}")
    print("A safety backup of your current world will be saved first.")
    if input("Type yes to continue: ").strip().lower() != "yes":
        print("Cancelled. Nothing was changed.")
        return

    zip_path = os.path.join("backups", chosen)
    temp_dir = "world_restore_temp"

    try:
        # 1. Unpack the chosen backup first, so a bad zip never touches your world
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.unpack_archive(zip_path, temp_dir)

        # 2. Save a safety backup of the current world
        print("Saving a safety backup of the current world...")
        if not backup_world():
            log("Safety backup failed, so the restore was stopped. Nothing was changed.")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return

        # 3. Swap the worlds
        if os.path.isdir("world"):
            shutil.rmtree("world")
        os.rename(temp_dir, "world")
        log(f"Restored: {chosen}")
        print("Choose 1 to start the server with the restored world.")
    except Exception as error:
        log(f"Restore failed: {error}")
        print("Your safety backup is in the backups folder.")
        shutil.rmtree(temp_dir, ignore_errors=True)


def start_server():
    """Check the setup, run the server, restart it if it crashes, and back up."""
    if not check_setup():
        return

    log("Starting server. Type 'stop' here to stop it safely.")
    print(f"A backup will be saved every {BACKUP_EVERY_MINUTES} minutes.")

    stop_event = threading.Event()
    threading.Thread(target=backup_loop, args=(stop_event,), daemon=True).start()

    restarts = 0
    try:
        while True:
            server = None
            try:
                server = subprocess.Popen(command)
                server.wait()
            except FileNotFoundError:
                log("Java was not found. Install Java, then run `java -version` to check.")
                return
            except KeyboardInterrupt:
                log("Stopping server...")
                if server:
                    server.terminate()
                    server.wait()
                backup_world()
                return

            backup_world()

            if server.returncode == 0:
                log("Server stopped normally.")
                return

            restarts += 1
            if restarts > MAX_RESTARTS:
                log("Server crashed too many times. Stopping.")
                return

            log(f"Server crashed. Restarting in 5 seconds ({restarts}/{MAX_RESTARTS})...")
            time.sleep(5)
    finally:
        stop_event.set()  # stop the automatic backups when the server is done


def main():
    log("Manager started.")
    while True:
        print("\n=== Minecraft Server Manager ===")
        print("1. Start server")
        print("2. Make a backup now")
        print("3. Show backups")
        print("4. Restore a backup")
        print("5. Show recent log")
        print("6. Quit")
        choice = input("Choose 1-6: ").strip()

        if choice == "1":
            start_server()
        elif choice == "2":
            backup_world()
        elif choice == "3":
            list_backups()
        elif choice == "4":
            restore_backup()
        elif choice == "5":
            show_log()
        elif choice == "6":
            log("Manager closed.")
            print("Goodbye!")
            break
        else:
            print("Please type 1, 2, 3, 4, 5, or 6.")


if __name__ == "__main__":
    main()