# Local Outlook Calendar

A lightweight local Windows calendar viewer for Outlook Classic.

Local Outlook Calendar reads your Outlook calendar through the local COM profile and shows a clean weekly view without Microsoft Graph, OAuth, Azure app registrations, or cloud sync.

## Why

Many Outlook calendar tools are sync engines, Graph API integrations, or cloud services. This project is intentionally smaller:

- local-first and read-only
- no Microsoft Graph permissions
- no extra login flow
- no external calendar sync
- simple weekly desktop view
- useful on locked-down corporate Windows machines where API access is difficult or unavailable

## Requirements

- Windows 10 or 11
- Outlook Classic installed and configured with a local profile
- Python 3.11+

New Outlook is not currently supported because it does not expose the same COM automation interface as Outlook Classic.

## Run From Source

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Build The Executable

```powershell
pip install -r requirements.txt
pyinstaller LocalOutlookCalendar.spec --noconfirm
```

The executable is generated at:

```text
dist\LocalOutlookCalendar.exe
```

## Features

- Weekly calendar view
- Local Outlook Classic calendar access through COM
- Recurring event expansion
- All-day event row
- Overlap-aware event columns
- Search by title or location
- Current-time indicator
- Weekend and off-hours shading
- Background loading to keep the UI responsive
- Custom application icon

## Limitations

- Windows only
- Requires Outlook Classic and a configured Outlook profile
- Read-only calendar view
- Default calendar only for now
- No reminders, notifications, edits, or meeting actions yet

## Project Status

Early local-first desktop app. The current goal is to provide a fast and reliable weekly calendar view for people who already have Outlook Classic configured but do not want a cloud/API-based integration.

## License

MIT
