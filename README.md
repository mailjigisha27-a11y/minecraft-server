# Minecraft Server Manager (Python)

A Python script that runs a Minecraft Java server and looks after it.

## Features

- Start the server from a simple menu
- Restarts the server automatically if it crashes
- Saves a world backup every 30 minutes while the server runs
- Saves a backup when the server stops
- Keeps only the newest backups
- Restore a backup from the menu (a safety backup is saved first)
- Writes a log file (`manager.log`) with the date and time of every backup, crash, and restore
- Settings in a simple `config.json` file, so you never need to edit the code

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
5. Show recent log
6. Quit
```

5. To stop the server safely, type `stop` in the terminal and press Enter.

## Settings

The first time you run the script, it creates a `config.json` file. Open it to change the settings:

```json
{
    "max_restarts": 3,
    "keep_backups": 10,
    "backup_every_minutes": 30,
    "max_memory": "2G",
    "min_memory": "1G",
    "server_jar": "server.jar"
}
```

| Setting | Meaning | Default |
|---|---|---|
| `max_restarts` | How many times to restart after a crash | 3 |
| `keep_backups` | How many backups to keep | 10 |
| `backup_every_minutes` | Time between automatic backups | 30 |
| `max_memory` | Most memory the server can use (like `2G` or `512M`) | 2G |
| `min_memory` | Memory the server starts with | 1G |
| `server_jar` | Name of the server file | server.jar |

If a value is not valid, the script tells you and uses the default value instead.

## Notes

- Backups are saved in the `backups` folder as zip files.
- Restore only works from the menu, when the server is stopped.
- The log file stays on your computer and is not uploaded to GitHub.
- Server files and player data are not uploaded to GitHub.

## Built with

Python, `subprocess`, `shutil`, `threading`, `json`