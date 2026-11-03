# Minecraft Server Manager (Python)

A Python script that runs a Minecraft Java server and looks after it.

## Features

- Start the server from a simple menu
- Restarts the server automatically if it crashes (up to 3 times)
- Saves a world backup every 30 minutes while the server runs
- Saves a backup when the server stops
- Keeps only the 10 newest backups
- Restore a backup from the menu (a safety backup is saved first)
- Writes a log file (`manager.log`) with the date and time of every backup, crash, and restore

## What you need

- Python 3
- Java (check with `java -version`)
- A Minecraft Java `server.jar` in the same folder as `main.py`
- `eula.txt` set to `eula=true`

## How to use

1. Put `main.py` in your Minecraft server folder.
2. Open a terminal in that folder.
3. Run:

```
python main.py
```

4. Choose an option from the menu:

```
1. Start server
2. Make a backup now
3. Show backups
4. Restore a backup
5. Quit
```

5. To stop the server safely, type `stop` in the terminal and press Enter.

## Settings

You can change these lines at the top of `main.py`:

| Setting | Meaning | Default |
|---|---|---|
| `MAX_RESTARTS` | How many times to restart after a crash | 3 |
| `KEEP_BACKUPS` | How many backups to keep | 10 |
| `BACKUP_EVERY_MINUTES` | Time between automatic backups | 30 |

## Notes

- Backups are saved in the `backups` folder as zip files.
- The log file stays on your computer and is not uploaded to GitHub.
- Restore only works from the menu, when the server is stopped.
- Server files and player data are not uploaded to GitHub.

## Built with

Python, `subprocess`, `shutil`, `threading`