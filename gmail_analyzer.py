"""Gmail message fetching and analysis module."""

import base64
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Dict, Any, List, Tuple, Optional, Callable


@dataclass
class SenderInfo:
    """Data class for sender information."""
    count: int = 0
    name: str = ""
    unsubscribe_url: Optional[str] = None
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None


def extract_sender_info(headers):
    """
    Extract sender email and name from headers.
    
    Returns:
        tuple: (sender_email, sender_name)
    """
    for header in headers:
        if header['name'] == 'From':
            from_value = header['value']
            # Extract email from "Name <email@domain.com>" format
            email_match = re.search(r'<([^>]+)>', from_value)
            if email_match:
                sender_email = email_match.group(1).lower()
                sender_name = from_value.split('<')[0].strip().strip('"')
            else:
                sender_email = from_value.lower()
                sender_name = sender_email
            return sender_email, sender_name
    return None, None


def extract_unsubscribe_link(payload):
    """
    Extract unsubscribe link from email payload.
    
    Returns:
        str: Unsubscribe URL or None
    """
    unsubscribe_url = None
    
    # Check headers for List-Unsubscribe header
    headers = payload.get('headers', [])
    for header in headers:
        if header['name'] == 'List-Unsubscribe':
            value = header['value']
            # Extract URL from <http://...> format
            url_match = re.search(r'<(https?://[^>]+)>', value)
            if url_match:
                unsubscribe_url = url_match.group(1)
                break
    
    # If not found in headers, search in body
    if not unsubscribe_url:
        unsubscribe_url = find_unsubscribe_in_body(payload)
    
    return unsubscribe_url


def find_unsubscribe_in_body(payload):
    """
    Search email body for unsubscribe links.
    
    Returns:
        str: Unsubscribe URL or None
    """
    text_content = extract_text_from_payload(payload)
    if not text_content:
        return None
    
    # Common unsubscribe URL patterns
    patterns = [
        r'https?://[^\s"<>]+unsubscribe[^\s"<>]*',
        r'https?://[^\s"<>]+opt-out[^\s"<>]*',
        r'https?://[^\s"<>]+preferences[^\s"<>]*',
        r'<a[^>]*href="(https?://[^"]*unsubscribe[^"]*)"',
        r'href="(https?://[^"]*opt-out[^"]*)"',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text_content, re.IGNORECASE)
        if matches:
            return matches[0]
    
    return None


def extract_text_from_payload(payload):
    """
    Extract text content from email payload.
    
    Returns:
        str: Text content
    """
    text_content = ""
    
    if 'parts' in payload:
        for part in payload['parts']:
            mime_type = part.get('mimeType', '')
            if mime_type == 'text/plain' or mime_type == 'text/html':
                data = part.get('body', {}).get('data', '')
                if data:
                    try:
                        text = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        text_content += text + " "
                    except Exception:
                        pass
            elif 'parts' in part:
                text_content += extract_text_from_payload(part)
    else:
        data = payload.get('body', {}).get('data', '')
        if data:
            try:
                text_content = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            except Exception:
                pass
    
    return text_content


def fetch_inbox_messages(service, progress_callback=None):
    """
    Fetch all messages from Gmail inbox.
    
    Args:
        service: Gmail API service object
        progress_callback: Optional callback function(current, total)
    
    Returns:
        list: List of message metadata
    """
    messages = []
    page_token = None
    
    while True:
        results = service.users().messages().list(
            userId='me',
            labelIds=['INBOX'],
            pageToken=page_token
        ).execute()
        
        batch = results.get('messages', [])
        messages.extend(batch)
        
        if progress_callback:
            progress_callback(len(messages), None)
        
        page_token = results.get('nextPageToken')
        if not page_token:
            break
    
    return messages


def fetch_message_details(service, message_id):
    """
    Fetch full message details.
    
    Returns:
        dict: Message data with headers and payload
    """
    return service.users().messages().get(
        userId='me',
        id=message_id,
        format='full'
    ).execute()


class InboxAnalyzer:
    """Analyzes Gmail inbox and builds sender frequency map."""
    
    def __init__(self, service):
        self.service = service
        self.sender_data: Dict[str, SenderInfo] = defaultdict(SenderInfo)
    
    def analyze(self, progress_callback=None):
        """
        Analyze inbox and build sender frequency map.
        
        Args:
            progress_callback: Optional callback function(current, total, message)
        
        Returns:
            dict: Sender data with frequency and unsubscribe links
        """
        # Fetch all message IDs
        if progress_callback:
            progress_callback(0, 0, "Fetching message list...")
        
        message_list = fetch_inbox_messages(self.service)
        total_messages = len(message_list)
        
        if progress_callback:
            progress_callback(0, total_messages, f"Found {total_messages} messages")
        
        # Process each message
        for i, message_ref in enumerate(message_list):
            message_id = message_ref['id']
            
            try:
                message = fetch_message_details(self.service, message_id)
                headers = message.get('payload', {}).get('headers', [])
                
                # Extract sender info
                sender_email, sender_name = extract_sender_info(headers)
                
                if sender_email:
                    sender_info = self.sender_data[sender_email]
                    sender_info.count += 1
                    if sender_name and not sender_info.name:
                        sender_info.name = sender_name
                    
                    # Extract date
                    for header in headers:
                        if header['name'] == 'Date':
                            try:
                                date = parsedate_to_datetime(header['value'])
                                if not sender_info.first_seen:
                                    sender_info.first_seen = date
                                sender_info.last_seen = date
                            except Exception:
                                pass
                            break
                    
                    # Extract unsubscribe link if not already found
                    if not sender_info.unsubscribe_url:
                        payload = message.get('payload', {})
                        unsubscribe_url = extract_unsubscribe_link(payload)
                        if unsubscribe_url:
                            sender_info.unsubscribe_url = unsubscribe_url
                
                if progress_callback:
                    progress_callback(i + 1, total_messages, f"Processing: {sender_email or 'Unknown'}")
                    
            except Exception as e:
                if progress_callback:
                    progress_callback(i + 1, total_messages, f"Error processing message: {e}")
        
        return dict(self.sender_data)
    
    def get_sorted_senders(self):
        """
        Get senders sorted by message count (descending).
        
        Returns:
            list: Tuples of (email, SenderInfo) sorted by count
        """
        return sorted(
            self.sender_data.items(),
            key=lambda x: x[1].count,
            reverse=True
        )