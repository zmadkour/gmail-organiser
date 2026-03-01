# Gmail Inbox Organizer

A TUI application to analyze Gmail inbox, show sender frequency, and export data.

## Features
- Fetch and analyze Gmail inbox messages
- Display sender frequency ordered by message count
- Extract unsubscribe links from emails
- Interactive TUI with progress indicators
- Export sender data to CSV

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up Google Cloud project and enable Gmail API:
   - Go to https://console.cloud.google.com/
   - Create a new project
   - Enable Gmail API
   - Create OAuth 2.0 credentials
   - Download `credentials.json` and place in project root

3. Run the application:
```bash
python main.py
```

## Usage
- The app will authenticate with your Google account on first run
- It will analyze your inbox and display sender statistics
- Use arrow keys to navigate the TUI
- Press 'e' to export to CSV
- Press 'q' to quit
