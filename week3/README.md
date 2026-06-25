# System Integration & Application

## Overview

## Project Setup

**install Docker Desktop on Windows, follow these steps:**

Download the Docker Desktop installer:

- For x86_64: [Docker Desktop for Windows - x86_64](https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe?utm_source=docker&utm_medium=webreferral&utm_campaign=docs-driven-download-win-amd64&_gl=1*98l6o2*_gcl_au*MTU2MjE4MTUxMC4xNzgyMjE0MTYx*_ga*MTcyNDM4MTAwNS4xNzgyMjE0MTYx*_ga_XJWPQMJYHQ*czE3ODIyMTQxNjEkbzEkZzEkdDE3ODIyMTQzMDckajIzJGwwJGgw)
- For ARM: [Docker Desktop for Windows - Arm (Early Access)](https://desktop.docker.com/win/main/arm64/Docker%20Desktop%20Installer.exe?utm_source=docker&utm_medium=webreferral&utm_campaign=docs-driven-download-win-arm64&_gl=1*98l6o2*_gcl_au*MTU2MjE4MTUxMC4xNzgyMjE0MTYx*_ga*MTcyNDM4MTAwNS4xNzgyMjE0MTYx*_ga_XJWPQMJYHQ*czE3ODIyMTQxNjEkbzEkZzEkdDE3ODIyMTQzMDckajIzJGwwJGgw)

Run the installer:

Double-click Docker Desktop Installer.exe to start the installation.
Choose the installation mode:
Per-user: Installs to %LOCALAPPDATA%\Programs\DockerDesktop (no admin required).
All users: Installs to C:\Program Files\Docker\Docker (requires admin privileges).
During installation, select your preferred backend (WSL 2 or Hyper-V) if prompted.

Follow the installation wizard to complete the setup.

Once installed, start Docker Desktop from the Windows Start menu.

You can also install from the command line:

Per-user installation (no admin required):

```bash
"Docker Desktop Installer.exe" install --user
```

All-users installation (run as administrator):

```bash
"Docker Desktop Installer.exe" install
```

### Note:

Windows containers are only supported in all-users installation mode.
If your administrator account is different from your user account, add your user to the docker-users group for elevated features.

### Running Locally

Install dependencies:
```bash
pip install fastapi "uvicorn[standard]" jinja2
```

Run the server from the **project root** (`frontend/`), not from inside `src/`:
```bash
uvicorn --app-dir src main:app --host 0.0.0.0 --port 8000
```

Then visit `http://localhost:8000` (or `http://127.0.0.1:8000`).

> **Note on paths:** `main.py` loads its HTML templates using a path built relative to the file itself (`Path(__file__).resolve().parent`), not relative to your terminal's current directory. This means the server will find `index.html` correctly no matter which folder you launch `uvicorn` from. If you ever see a `TemplateNotFound` error, check the working directory you ran the command from first.

### Running with Docker

Build the image:
```bash
docker build ./ -t frontend:1.0
```

Run the container:
```bash
docker run -p 8000:8000 frontend:1.0
```

Then visit `http://localhost:8000` in your browser.