import subprocess
import sys
import os
import shutil
import time
from datetime import datetime

# Always run from the folder this script is in
os.chdir(os.path.dirname(os.path.abspath(__file__)))

MAX_RESTARTS = 3   # how many times to restart after a crash
KEEP_BACKUPS = 5   # how many backup zips to keep

command = [
    "java",
    "-Xmx2G",        # max memory: 2 GB
    "-Xms1G",        # starting memory: 1 GB
    "-jar", "server.jar",
    "nogui",
]


def backup_world():
    """Save a zip copy of the world folder into the backups folder."""
    if not os.path.isdir("world"):
        print("No 'world' folder found, skipping backup.")
        return

    os.makedirs("backups", exist_ok=True)
    name = datetime.now().strftime("world_%Y-%m-%d_%H-%M-%S")
    shutil.make_archive(os.path.join("backups", name), "zip", "world")
    print(f"Backup saved: backups/{name}.zip")

    # Delete the oldest backups, keep only the newest ones
    zips = sorted(f for f in os.listdir("backups") if f.endswith(".zip"))
    for old in zips[:-KEEP_BACKUPS]:
        os.remove(os.path.join("backups", old))
        print(f"Deleted old backup: {old}")


def main():
    restarts = 0
    while True:
        try:
            server = subprocess.Popen(command)
            server.wait()
        except FileNotFoundError:
            print("Java was not found. Install Java, then run `java -version` to check.")
            sys.exit(1)
        except KeyboardInterrupt:
            print("Stopping server...")
            server.terminate()
            server.wait()
            backup_world()
            break

        # The server has stopped, so the world is saved. Make a backup.
        backup_world()

        if server.returncode == 0:
            print("Server stopped normally.")
            break

        restarts += 1
        if restarts > MAX_RESTARTS:
            print("Server crashed too many times. Stopping.")
            break

        print(f"Server crashed. Restarting in 5 seconds ({restarts}/{MAX_RESTARTS})...")
        time.sleep(5)


if __name__ == "__main__":
    main()