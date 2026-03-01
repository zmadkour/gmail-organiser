"""TUI interface for Gmail Inbox Organizer using Textual."""

import asyncio
from datetime import datetime
import csv
import webbrowser

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    DataTable,
    Header,
    Footer,
    Static,
    ProgressBar,
    Label,
    Button,
    Input,
)
from textual.reactive import reactive
from rich.text import Text

from auth import authenticate_gmail
from gmail_analyzer import InboxAnalyzer, SenderInfo


class ProgressWidget(Static):
    """Widget to show analysis progress."""
    
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Ready to analyze inbox", id="status-label")
            yield ProgressBar(total=100, id="progress-bar")
            yield Label("", id="current-sender")


class SenderTable(DataTable):
    """DataTable for displaying sender information."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cursor_type = "row"
        self.show_cursor = True
        self.zebra_stripes = True


class InboxOrganizerApp(App):
    """Main TUI application for Gmail Inbox Organizer."""
    
    CSS = """
    Screen {
        align: center middle;
    }
    
    #progress-section {
        height: auto;
        padding: 1 2;
        border: solid green;
    }
    
    #table-section {
        height: 1fr;
        padding: 1 2;
    }
    
    #status-label {
        text-style: bold;
    }
    
    #current-sender {
        color: $text-muted;
        text-style: italic;
    }
    
    DataTable {
        height: 1fr;
        border: solid $primary;
    }
    
    #export-section {
        height: auto;
        padding: 1 2;
        border-top: solid $primary-darken-2;
    }
    
    #export-input {
        width: 60%;
    }
    
    .button-success {
        background: $success;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("e", "export", "Export CSV"),
        ("o", "open_unsubscribe", "Open Unsubscribe"),
    ]
    
    def __init__(self):
        super().__init__()
        self.service = None
        self.analyzer = None
        self.senders = []
        self.is_analyzing = False
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Vertical(id="main-container"):
            with Vertical(id="progress-section"):
                yield ProgressWidget()
                with Horizontal():
                    yield Button("Start Analysis", id="analyze-btn", variant="primary")
                    yield Button("Export to CSV", id="export-btn", variant="success", disabled=True)
            
            with Vertical(id="table-section"):
                table = SenderTable(id="sender-table")
                table.add_columns(
                    "#",
                    "Sender Email",
                    "Sender Name",
                    "Count",
                    "Unsubscribe",
                    "First Seen",
                    "Last Seen"
                )
                yield table
            
            with Horizontal(id="export-section"):
                yield Input(placeholder="Enter CSV filename (e.g., senders.csv)", id="export-input", value="senders.csv")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Called when app is mounted."""
        self.title = "Gmail Inbox Organizer"
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "analyze-btn":
            if not self.is_analyzing:
                await self.start_analysis()
        elif event.button.id == "export-btn":
            await self.export_csv()
    
    async def start_analysis(self) -> None:
        """Start the inbox analysis process."""
        self.is_analyzing = True
        
        # Update UI
        analyze_btn = self.query_one("#analyze-btn", Button)
        analyze_btn.disabled = True
        analyze_btn.label = "Analyzing..."
        
        status_label = self.query_one("#status-label", Label)
        status_label.update("Connecting to Gmail API...")
        
        try:
            # Authenticate
            if not self.service:
                self.service = await asyncio.get_event_loop().run_in_executor(
                    None, authenticate_gmail
                )
            
            # Create analyzer
            self.analyzer = InboxAnalyzer(self.service)
            
            # Update progress bar
            progress_bar = self.query_one("#progress-bar", ProgressBar)
            progress_bar.update(progress=0)
            
            # Define progress callback
            def progress_callback(current, total, message=""):
                if total and total > 0:
                    percentage = (current / total) * 100
                    progress_bar.update(progress=percentage)
                
                status_label.update(message if message else f"Processing {current}/{total} messages...")
                
                # Update current sender
                current_sender = self.query_one("#current-sender", Label)
                if message and "Processing:" in message:
                    current_sender.update(message.split(":", 1)[1].strip())
            
            # Run analysis
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.analyzer.analyze(progress_callback)
            )
            
            # Get sorted senders
            self.senders = self.analyzer.get_sorted_senders()
            
            # Update table
            await self.update_table()
            
            # Update status
            status_label.update(f"Analysis complete! Found {len(self.senders)} unique senders.")
            self.query_one("#current-sender", Label).update("")
            progress_bar.update(progress=100)
            
            # Enable export button
            self.query_one("#export-btn", Button).disabled = False
            
        except Exception as e:
            status_label.update(f"Error: {str(e)}")
            self.notify(f"Analysis failed: {str(e)}", severity="error")
        
        finally:
            self.is_analyzing = False
            analyze_btn.disabled = False
            analyze_btn.label = "Start Analysis"
    
    async def update_table(self) -> None:
        """Update the sender table with analysis results."""
        table = self.query_one("#sender-table", SenderTable)
        table.clear()
        
        for idx, (email, data) in enumerate(self.senders, 1):
            unsubscribe_text = "🔗 Link" if data.unsubscribe_url else "❌ None"
            first_seen = data.first_seen.strftime('%Y-%m-%d') if data.first_seen else 'N/A'
            last_seen = data.last_seen.strftime('%Y-%m-%d') if data.last_seen else 'N/A'
            
            table.add_row(
                str(idx),
                email,
                data.name or 'Unknown',
                str(data.count),
                unsubscribe_text,
                first_seen,
                last_seen,
                key=email
            )
    
    async def export_csv(self) -> None:
        """Export sender data to CSV file."""
        if not self.senders:
            self.notify("No data to export. Run analysis first.", severity="warning")
            return
        
        export_input = self.query_one("#export-input", Input)
        filename = export_input.value.strip()
        
        if not filename:
            filename = "senders.csv"
        
        if not filename.endswith('.csv'):
            filename += '.csv'
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([
                    'Rank',
                    'Sender Email',
                    'Sender Name',
                    'Message Count',
                    'Unsubscribe URL',
                    'First Seen',
                    'Last Seen'
                ])
                
                for idx, (email, data) in enumerate(self.senders, 1):
                    writer.writerow([
                        idx,
                        email,
                        data.name,
                        data.count,
                        data.unsubscribe_url or '',
                        data.first_seen.isoformat() if data.first_seen else '',
                        data.last_seen.isoformat() if data.last_seen else ''
                    ])
            
            self.notify(f"Exported to {filename}", severity="information")
            
        except Exception as e:
            self.notify(f"Export failed: {str(e)}", severity="error")
    
    async def action_export(self) -> None:
        """Export CSV action."""
        await self.export_csv()
    
    async def action_refresh(self) -> None:
        """Refresh analysis."""
        if not self.is_analyzing:
            await self.start_analysis()
    
    async def action_open_unsubscribe(self) -> None:
        """Open unsubscribe link for selected sender."""
        table = self.query_one("#sender-table", SenderTable)
        if table.cursor_row is None:
            self.notify("Select a sender first", severity="warning")
            return
        
        # Check if table has any rows
        if table.row_count == 0:
            self.notify("No data available. Run analysis first.", severity="warning")
            return
        
        # Get selected row data
        try:
            row_key = table.get_row_at(table.cursor_row)
        except Exception:
            self.notify("Please select a valid row", severity="warning")
            return
        if row_key:
            email = row_key[1]  # Email is in column 1
            
            # Find sender data
            for sender_email, data in self.senders:
                if sender_email == email:
                    if data.unsubscribe_url:
                        webbrowser.open(data.unsubscribe_url)
                        self.notify(f"Opening unsubscribe link for {email}")
                    else:
                        self.notify(f"No unsubscribe link found for {email}", severity="warning")
                    break
    
    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection."""
        pass  # Row selected, can add functionality here if needed


def main():
    """Main entry point."""
    app = InboxOrganizerApp()
    app.run()


if __name__ == "__main__":
    main()