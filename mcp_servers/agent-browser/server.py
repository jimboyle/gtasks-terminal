#!/usr/bin/env python3
"""
MCP Server for Vercel agent-browser CLI
Provides browser automation tools compatible with agent-browser CLI commands.
"""

import asyncio
import json
import subprocess
import sys
from typing import Any, Optional
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

app = Server("agent-browser-mcp")

def run_agent_browser(args: list[str], session_id: Optional[str] = None) -> str:
    """Execute agent-browser CLI command and return result."""
    cmd = ["agent-browser"]
    if session_id:
        cmd.extend(["--session", session_id])
    cmd.extend(args)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode != 0:
            return f"Error: {result.stderr}"
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "Error: Command timed out"
    except FileNotFoundError:
        return "Error: agent-browser CLI not found. Install with: npm install -g agent-browser"

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available browser automation tools."""
    return [
        Tool(
            name="browser_navigate",
            description="Navigate to a URL in the browser",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to navigate to"},
                    "sessionId": {"type": "string", "description": "Browser session ID for isolation"}
                },
                "required": ["url"]
            }
        ),
        Tool(
            name="browser_snapshot",
            description="Get an accessibility tree snapshot of the page for AI-friendly element references",
            inputSchema={
                "type": "object",
                "properties": {
                    "sessionId": {"type": "string", "description": "Browser session ID"},
                    "interactive": {"type": "boolean", "description": "Only interactive elements", "default": False},
                    "compact": {"type": "boolean", "description": "Remove empty structural elements", "default": False}
                }
            }
        ),
        Tool(
            name="browser_click",
            description="Click on an element identified by selector or accessibility properties",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector, text content, or accessibility locator"},
                    "sessionId": {"type": "string", "description": "Browser session ID"}
                },
                "required": ["selector"]
            }
        ),
        Tool(
            name="browser_type",
            description="Type text character by character (useful for triggering key events)",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "Selector for the input element"},
                    "text": {"type": "string", "description": "Text to type"},
                    "sessionId": {"type": "string", "description": "Browser session ID"}
                },
                "required": ["selector", "text"]
            }
        ),
        Tool(
            name="browser_fill",
            description="Fill a text input field with the specified value",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "Selector for the input element"},
                    "value": {"type": "string", "description": "Text value to fill in"},
                    "sessionId": {"type": "string", "description": "Browser session ID"}
                },
                "required": ["selector", "value"]
            }
        ),
        Tool(
            name="browser_press",
            description="Press a keyboard key",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Key to press (e.g., 'Enter', 'Escape', 'Tab')"},
                    "sessionId": {"type": "string", "description": "Browser session ID"}
                },
                "required": ["key"]
            }
        ),
        Tool(
            name="browser_get_text",
            description="Get text content from an element or the entire page",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "Selector for the element (gets full page text if not provided)"},
                    "sessionId": {"type": "string", "description": "Browser session ID"}
                }
            }
        ),
        Tool(
            name="browser_screenshot",
            description="Take a screenshot of the page or an element",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to save the screenshot"},
                    "fullPage": {"type": "boolean", "description": "Capture the full scrollable page"},
                    "selector": {"type": "string", "description": "Selector for element to screenshot"},
                    "sessionId": {"type": "string", "description": "Browser session ID"}
                }
            }
        ),
        Tool(
            name="browser_scroll",
            description="Scroll the page or an element",
            inputSchema={
                "type": "object",
                "properties": {
                    "direction": {"type": "string", "enum": ["up", "down", "left", "right"], "description": "Scroll direction"},
                    "amount": {"type": "number", "description": "Scroll amount in pixels"},
                    "selector": {"type": "string", "description": "Selector for element to scroll (scrolls page if not provided)"},
                    "sessionId": {"type": "string", "description": "Browser session ID"}
                },
                "required": ["direction"]
            }
        ),
        Tool(
            name="browser_go_back",
            description="Navigate back in browser history",
            inputSchema={
                "type": "object",
                "properties": {
                    "sessionId": {"type": "string", "description": "Browser session ID"}
                }
            }
        ),
        Tool(
            name="browser_go_forward",
            description="Navigate forward in browser history",
            inputSchema={
                "type": "object",
                "properties": {
                    "sessionId": {"type": "string", "description": "Browser session ID"}
                }
            }
        ),
        Tool(
            name="browser_reload",
            description="Reload the current page",
            inputSchema={
                "type": "object",
                "properties": {
                    "sessionId": {"type": "string", "description": "Browser session ID"}
                }
            }
        ),
        Tool(
            name="browser_close_session",
            description="Close a browser session",
            inputSchema={
                "type": "object",
                "properties": {
                    "sessionId": {"type": "string", "description": "Session ID to close"}
                }
            }
        ),
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls by executing agent-browser commands."""
    session_id = arguments.get("sessionId")
    
    if name == "browser_navigate":
        url = arguments.get("url")
        if not url:
            return [TextContent(type="text", text="Error: URL is required")]
        result = run_agent_browser(["open", url], session_id)
        return [TextContent(type="text", text=result)]
    
    elif name == "browser_snapshot":
        args = ["snapshot"]
        if arguments.get("interactive"):
            args.append("-i")
        if arguments.get("compact"):
            args.append("-c")
        result = run_agent_browser(args, session_id)
        return [TextContent(type="text", text=result)]
    
    elif name == "browser_click":
        selector = arguments.get("selector")
        result = run_agent_browser(["click", selector], session_id)
        return [TextContent(type="text", text=result)]
    
    elif name == "browser_type":
        selector = arguments.get("selector")
        text = arguments.get("text")
        result = run_agent_browser(["type", selector, text], session_id)
        return [TextContent(type="text", text=result)]
    
    elif name == "browser_fill":
        selector = arguments.get("selector")
        value = arguments.get("value")
        result = run_agent_browser(["fill", selector, value], session_id)
        return [TextContent(type="text", text=result)]
    
    elif name == "browser_press":
        key = arguments.get("key")
        result = run_agent_browser(["press", key], session_id)
        return [TextContent(type="text", text=result)]
    
    elif name == "browser_get_text":
        selector = arguments.get("selector")
        if selector:
            result = run_agent_browser(["get", "text", selector], session_id)
        else:
            result = run_agent_browser(["get", "text", "body"], session_id)
        return [TextContent(type="text", text=result)]
    
    elif name == "browser_screenshot":
        args = ["screenshot"]
        if arguments.get("fullPage"):
            args.append("--full")
        path = arguments.get("path")
        if path:
            args.append(path)
        result = run_agent_browser(args, session_id)
        return [TextContent(type="text", text=result)]
    
    elif name == "browser_scroll":
        direction = arguments.get("direction")
        amount = arguments.get("amount", 300)
        result = run_agent_browser(["scroll", direction, str(amount)], session_id)
        return [TextContent(type="text", text=result)]
    
    elif name == "browser_go_back":
        result = run_agent_browser(["back"], session_id)
        return [TextContent(type="text", text=result)]
    
    elif name == "browser_go_forward":
        result = run_agent_browser(["forward"], session_id)
        return [TextContent(type="text", text=result)]
    
    elif name == "browser_reload":
        result = run_agent_browser(["reload"], session_id)
        return [TextContent(type="text", text=result)]
    
    elif name == "browser_close_session":
        # agent-browser doesn't have a close_session command
        # Sessions are automatically closed when the process ends
        return [TextContent(type="text", text="Session closed (agent-browser uses auto-cleanup)")]
    
    return [TextContent(type="text", text=f"Error: Unknown tool {name}")]

async def main():
    """Main entry point for the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
