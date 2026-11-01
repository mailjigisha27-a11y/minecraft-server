# Minecraft Server Manager (Python)

A Python script that runs a Minecraft Java server and looks after it.

## Features
- Simple menu: start the server, make a backup, show backups, or quit
- Saves a zip backup of the `world` folder when the server stops
- Keeps only the last 5 backups
- Restarts the server automatically if it crashes (up to 3 times)

## Requirements
- Python 3
- Java (21 or newer)
- `server.jar` from minecraft.net, placed in the same folder as `main.py`

## How to run
1. Put `main.py` next to `server.jar`.
2. Open a terminal in that folder.
3. Run:

   python main.py

4. Type a number from the menu and press Enter.
5. To stop the server safely, type `stop` in the terminal.

## Note
Do not upload `server.jar`, the `world` folder, or player files to GitHub. The `.gitignore` file hides them.