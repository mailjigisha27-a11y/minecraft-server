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
LOG_FILE = "manager.log"  # the log file

command = [
    "java",
    "-Xmx2G",        # max memory: 2 GB
    "-Xms1G",        # starting memory: 1 GB
    "-jar", "server.jar",
    "nogui",
]

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
    """Run the server. Restart it if it crashes. Back up every 30 minutes and when it stops."""
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
        print("5. Quit")
        choice = input("Choose 1-5: ").strip()

        if choice == "1":
            start_server()
        elif choice == "2":
            backup_world()
        elif choice == "3":
            list_backups()
        elif choice == "4":
            restore_backup()
        elif choice == "5":
            log("Manager closed.")
            print("Goodbye!")
            break
        else:
            print("Please type 1, 2, 3, 4, or 5.")


if __name__ == "__main__":
    main()