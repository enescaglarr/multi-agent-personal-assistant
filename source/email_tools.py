import asyncio
import base64
import re
from typing import List, Union
from autogen_ext.tools.langchain import LangChainToolAdapter
from autogen_core.tools import FunctionTool
from langchain_google_community import GmailToolkit
from langchain_google_community.gmail.utils import build_resource_service as build_gmail_resource_service
from source.log_records import logger
from source.google_utils import get_gmail_service

# LangChain's GmailSearch and GmailGetMessage tools return raw message dicts including the
# full email body (quoted threads, signatures, footers) -- unusable as a chat reply. We
# replace both with search_emails()/get_email() below, which ask the Gmail API directly
# and return clean, readable text.
_RAW_TOOL_NAMES = {"search_gmail", "get_gmail_message"}


def _get_header(headers: List[dict], name: str) -> str:
    """Pull a single header value (e.g. 'From', 'Subject', 'Date') out of a Gmail message payload."""
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")
    return ""


def _extract_plain_body(payload: dict) -> str:
    """Recursively find and decode the text/plain part of a Gmail message payload,
    falling back to text/html (tags stripped) if no plain-text part exists."""
    mime_type = payload.get("mimeType", "")
    data = payload.get("body", {}).get("data")

    if mime_type == "text/plain" and data:
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    for part in payload.get("parts", []) or []:
        text = _extract_plain_body(part)
        if text:
            return text

    if mime_type == "text/html" and data:
        html = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        return re.sub(r"<[^>]+>", " ", html)

    return ""


class GmailTools:
    """
    Class to handle Gmail tools creation using LangChain toolkit.

    Attributes:
        creds: Google API credentials
    """

    def __init__(self, creds):
        self.creds = creds
        self._gmail_service = None

    async def langchain_gmail_tools(self) -> List:
        """
        Create Gmail tools using LangChain toolkit.

        Returns:
            List of Gmail tools from LangChain toolkit
        """
        try:
            # Run in thread pool since build_resource_service might be blocking
            loop = asyncio.get_event_loop()
            api_resource = await loop.run_in_executor(
                None,
                build_gmail_resource_service,
                self.creds
            )
            self._gmail_service = api_resource
            gmail_toolkit = GmailToolkit(api_resource=api_resource)
            tools = [t for t in gmail_toolkit.get_tools() if t.name not in _RAW_TOOL_NAMES]
            logger.info(f"Created {len(tools)} Gmail tools from LangChain toolkit")
            return tools
        except Exception as e:
            logger.error(f"Error creating Gmail tools: {str(e)}")
            return []

    def _search_emails_sync(self, query: str, max_results: int) -> str:
        """Blocking Gmail API search, run off the event loop by search_emails()."""
        service = self._gmail_service
        results = service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()
        message_refs = results.get("messages", [])

        if not message_refs:
            return f"No emails found for query: {query}"

        lines = [f"Found {len(message_refs)} email(s) for '{query}':"]
        for i, ref in enumerate(message_refs, 1):
            msg = service.users().messages().get(
                userId="me",
                id=ref["id"],
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            ).execute()
            headers = msg.get("payload", {}).get("headers", [])
            sender = _get_header(headers, "From") or "Unknown sender"
            subject = _get_header(headers, "Subject") or "(no subject)"
            date = _get_header(headers, "Date") or ""
            snippet = msg.get("snippet", "")
            if len(snippet) > 150:
                snippet = snippet[:150] + "..."
            lines.append(
                f"\n{i}. {subject}\n   From: {sender}\n   Date: {date}\n   Id: {msg.get('id')}\n   Preview: {snippet}"
            )
        return "\n".join(lines)

    async def search_emails(self, query: str, max_results: int = 10) -> str:
        """Search Gmail and return a short, readable summary (subject/sender/date/preview) --
        not full email bodies."""
        try:
            if self._gmail_service is None:
                await self.langchain_gmail_tools()
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._search_emails_sync, query, max_results)
            logger.info(f"Searched Gmail for '{query}', found result")
            return result
        except Exception as e:
            logger.error(f"Error searching Gmail for '{query}': {str(e)}")
            return f"Error searching emails: {str(e)}"

    def _get_email_sync(self, message_id: str) -> str:
        """Blocking Gmail API message fetch, run off the event loop by get_email()."""
        service = self._gmail_service
        msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
        headers = msg.get("payload", {}).get("headers", [])
        sender = _get_header(headers, "From") or "Unknown sender"
        to = _get_header(headers, "To") or ""
        subject = _get_header(headers, "Subject") or "(no subject)"
        date = _get_header(headers, "Date") or ""

        body = _extract_plain_body(msg.get("payload", {})).strip()
        if len(body) > 3000:
            body = body[:3000] + "\n...[truncated]"

        return f"Subject: {subject}\nFrom: {sender}\nTo: {to}\nDate: {date}\n\n{body}"

    async def get_email(self, message_id: str) -> str:
        """Get one email's full content (headers + plain-text body) by message id --
        the id returned by search_emails for each result."""
        try:
            if self._gmail_service is None:
                await self.langchain_gmail_tools()
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._get_email_sync, message_id)
            logger.info(f"Retrieved email {message_id}")
            return result
        except Exception as e:
            logger.error(f"Error retrieving email {message_id}: {str(e)}")
            return f"Error retrieving email: {str(e)}"

    async def as_function_tools(self) -> List[Union[LangChainToolAdapter, FunctionTool]]:
        """
        Combine Gmail tools and utility tools for AutoGen agent.
        Gmail tools are wrapped in LangChainToolAdapter, utility functions use FunctionTool.

        Returns:
            List of tools for AutoGen (mix of LangChainToolAdapter and FunctionTool)
        """
        try:
            # Get Gmail tools and wrap them in LangChainToolAdapter
            gmail_tools = await self.langchain_gmail_tools()
            gmail_autogen_tools = [LangChainToolAdapter(tool) for tool in gmail_tools]
            
            search_tool = FunctionTool(
                self.search_emails,
                description=(
                    "Search Gmail and get a short, readable summary (subject, sender, date, "
                    "short preview, message id) -- not full email bodies. Use Gmail search "
                    "syntax in `query`, e.g. 'newer_than:7d' for the last week, "
                    "'from:someone@example.com', 'subject:invoice', 'is:unread'. "
                    "Call get_email afterwards (with the returned message id) if the user "
                    "needs the full content of one specific email."
                ),
            )

            get_email_tool = FunctionTool(
                self.get_email,
                description=(
                    "Get one email's full content (subject, from, to, date, plain-text body) "
                    "given a message id -- use the id returned by search_emails. Call this at "
                    "most once per request, even if search_emails found several matching "
                    "emails with similar subjects."
                ),
            )

            # Combine all tools
            all_tools = gmail_autogen_tools + [search_tool, get_email_tool]

            logger.info(f"Created {len(all_tools)} total tools for AutoGen agent ({len(gmail_autogen_tools)} Gmail tools + search_emails + get_email)")
            return all_tools
            
        except Exception as e:
            logger.error(f"Error creating Gmail tools for AutoGen: {str(e)}")
            return []


# Function to create Gmail tools outside the class
async def create_gmail_tools(creds) -> List[Union[LangChainToolAdapter, FunctionTool]]:
    """
    Factory function to create Gmail tools for use outside the class.
    
    Args:
        creds: Google API credentials
        
    Returns:
        List of tools for AutoGen (mix of LangChainToolAdapter and FunctionTool)
    """
    gmail_tools_instance = GmailTools(creds)
    return await gmail_tools_instance.as_function_tools()


# Example usage:
    """Main test function."""
async def main():
    email_creds = get_gmail_service()
    email_tools = await create_gmail_tools(email_creds)
    
    logger.info("Test completed")

if __name__ == "__main__":
    asyncio.run(main())
