import subprocess
import sys
import os
import shutil
import time
import threading
from datetime import datetime

# Always run from the folder this script is in
os.chdir(os.path.dirname(os.path.abspath(__file__)))

MAX_RESTARTS = 3          # how many times to restart after a crash
KEEP_BACKUPS = 10         # how many backup zips to keep
BACKUP_EVERY_MINUTES = 30 # automatic backup while the server runs

command = [
    "java",
    "-Xmx2G",        # max memory: 2 GB
    "-Xms1G",        # starting memory: 1 GB
    "-jar", "server.jar",
    "nogui",
]

# Makes sure two backups never run at the same time
backup_lock = threading.Lock()


def backup_world():
    """Save a zip copy of the world folder into the backups folder."""
    with backup_lock:
        if not os.path.isdir("world"):
            print("No 'world' folder found, skipping backup.")
            return

        os.makedirs("backups", exist_ok=True)
        name = datetime.now().strftime("world_%Y-%m-%d_%H-%M-%S")
        temp_copy = os.path.join("backups", "_temp_copy")

        try:
            # Copy first, skipping session.lock (Windows locks it while the server runs)
            shutil.rmtree(temp_copy, ignore_errors=True)
            shutil.copytree("world", temp_copy, ignore=shutil.ignore_patterns("session.lock"))
            shutil.make_archive(os.path.join("backups", name), "zip", temp_copy)
            print(f"Backup saved: backups/{name}.zip")
        except Exception as error:
            print(f"Backup failed: {error}")
            return
        finally:
            shutil.rmtree(temp_copy, ignore_errors=True)

        # Delete the oldest backups, keep only the newest ones
        zips = sorted(f for f in os.listdir("backups") if f.endswith(".zip"))
        for old in zips[:-KEEP_BACKUPS]:
            os.remove(os.path.join("backups", old))
            print(f"Deleted old backup: {old}")


def backup_loop(stop_event):
    """Runs in the background and backs up the world every few minutes."""
    while not stop_event.wait(BACKUP_EVERY_MINUTES * 60):
        print("\nAutomatic backup...")
        backup_world()


def list_backups():
    """Show all backup files."""
    if not os.path.isdir("backups"):
        print("No backups yet.")
        return
    zips = sorted(f for f in os.listdir("backups") if f.endswith(".zip"))
    if not zips:
        print("No backups yet.")
        return
    for z in zips:
        size_mb = os.path.getsize(os.path.join("backups", z)) / (1024 * 1024)
        print(f"  {z}  ({size_mb:.1f} MB)")


def start_server():
    """Run the server. Restart it if it crashes. Back up every 30 minutes and when it stops."""
    print("Starting server. Type 'stop' here to stop it safely.")
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
                print("Java was not found. Install Java, then run `java -version` to check.")
                return
            except KeyboardInterrupt:
                print("Stopping server...")
                if server:
                    server.terminate()
                    server.wait()
                backup_world()
                return

            backup_world()

            if server.returncode == 0:
                print("Server stopped normally.")
                return

            restarts += 1
            if restarts > MAX_RESTARTS:
                print("Server crashed too many times. Stopping.")
                return

            print(f"Server crashed. Restarting in 5 seconds ({restarts}/{MAX_RESTARTS})...")
            time.sleep(5)
    finally:
        stop_event.set()  # stop the automatic backups when the server is done


def main():
    while True:
        print("\n=== Minecraft Server Manager ===")
        print("1. Start server")
        print("2. Make a backup now")
        print("3. Show backups")
        print("4. Quit")
        choice = input("Choose 1-4: ").strip()

        if choice == "1":
            start_server()
        elif choice == "2":
            backup_world()
        elif choice == "3":
            list_backups()
        elif choice == "4":
            print("Goodbye!")
            break
        else:
            print("Please type 1, 2, 3, or 4.")


if __name__ == "__main__":
    main()