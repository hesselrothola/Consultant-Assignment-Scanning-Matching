"""
PlaywrightMCPClient - Client wrapper for Playwright MCP server.
Handles SSE communication with the containerized browser automation server.
"""

import asyncio
import logging
import json
from typing import Any, Dict, List, Optional
import httpx
import aiohttp
import sseclient
from uuid import uuid4

logger = logging.getLogger(__name__)


class PlaywrightMCPClient:
    """
    Client for communicating with Playwright MCP server via SSE.
    Manages browser automation through MCP protocol.
    """
    
    def __init__(self, mcp_url: str = "http://playwright_mcp:8931/sse"):
        self.mcp_url = mcp_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.tools_cache: Dict[str, Any] = {}
        self.connected = False
    
    async def __aenter__(self):
        """Initialize client session."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up client session."""
        await self.disconnect()
    
    async def connect(self):
        """Establish connection to MCP server and load available tools."""
        if self.connected:
            return
        
        try:
            self.session = aiohttp.ClientSession()
            
            # Get available tools from MCP server
            await self._load_tools()
            
            self.connected = True
            logger.info(f"Connected to Playwright MCP server at {self.mcp_url}")
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            if self.session:
                await self.session.close()
            raise
    
    async def disconnect(self):
        """Close connection to MCP server."""
        if self.session:
            await self.session.close()
            self.session = None
        self.connected = False
        logger.info("Disconnected from Playwright MCP server")
    
    async def _load_tools(self):
        """Load available tools from MCP server."""
        try:
            # MCP servers expose tools through SSE endpoint
            # Send initial request to get tools listing
            async with self.session.post(
                self.mcp_url.replace('/sse', '/tools/list'),
                json={"jsonrpc": "2.0", "method": "tools/list", "id": str(uuid4())}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if "result" in data and "tools" in data["result"]:
                        for tool in data["result"]["tools"]:
                            self.tools_cache[tool["name"]] = tool
                        logger.info(f"Loaded {len(self.tools_cache)} tools from MCP server")
                    else:
                        # Fallback: assume standard Playwright tools are available
                        self._load_default_tools()
                else:
                    # If tools endpoint doesn't exist, use defaults
                    self._load_default_tools()
        except Exception as e:
            logger.warning(f"Could not load tools from server, using defaults: {e}")
            self._load_default_tools()
    
    def _load_default_tools(self):
        """Load default Playwright MCP tools."""
        default_tools = [
            "browser_navigate",
            "browser_snapshot",
            "browser_click",
            "browser_type",
            "browser_evaluate",
            "browser_wait_for",
            "browser_navigate_back",
            "browser_take_screenshot",
            "browser_file_upload",
            "browser_fill_form",
            "browser_select_option",
            "browser_hover",
            "browser_drag",
            "browser_press_key",
            "browser_handle_dialog",
            "browser_tabs",
            "browser_close",
            "browser_resize",
            "browser_console_messages",
            "browser_network_requests"
        ]
        
        for tool_name in default_tools:
            self.tools_cache[tool_name] = {"name": tool_name}
    
    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a tool on the MCP server.
        
        Args:
            tool_name: Name of the tool to execute (e.g., "browser_navigate")
            parameters: Parameters for the tool
        
        Returns:
            Tool execution result
        """
        if not self.connected:
            await self.connect()
        
        if tool_name not in self.tools_cache:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        request_id = str(uuid4())
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": parameters
            },
            "id": request_id
        }
        
        try:
            # Send request via SSE
            response = await self._send_sse_request(request)
            
            if "error" in response:
                raise Exception(f"Tool execution failed: {response['error']}")
            
            return response.get("result", {})
            
        except Exception as e:
            logger.error(f"Failed to execute tool {tool_name}: {e}")
            raise
    
    async def _send_sse_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send request to MCP server via SSE and wait for response.
        """
        try:
            async with self.session.post(
                self.mcp_url,
                json=request,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"SSE request failed with status {response.status}: {error_text}")
                
                # Read SSE stream for response
                result = None
                async for line in response.content:
                    decoded_line = line.decode('utf-8').strip()
                    
                    if decoded_line.startswith("data: "):
                        data_str = decoded_line[6:]  # Remove "data: " prefix
                        
                        if data_str == "[DONE]":
                            break
                        
                        try:
                            data = json.loads(data_str)
                            if data.get("id") == request["id"]:
                                result = data
                                break
                        except json.JSONDecodeError:
                            continue
                
                if result is None:
                    raise Exception("No response received from MCP server")
                
                return result
                
        except Exception as e:
            logger.error(f"SSE request failed: {e}")
            raise
    
    async def navigate(self, url: str) -> bool:
        """Convenience method for navigation."""
        result = await self.execute_tool("browser_navigate", {"url": url})
        return result.get("success", False)
    
    async def click(self, ref: str, element_description: str) -> bool:
        """Convenience method for clicking elements."""
        result = await self.execute_tool(
            "browser_click",
            {"ref": ref, "element": element_description}
        )
        return result.get("success", False)
    
    async def type_text(
        self,
        ref: str,
        text: str,
        element_description: str,
        submit: bool = False
    ) -> bool:
        """Convenience method for typing text."""
        result = await self.execute_tool(
            "browser_type",
            {
                "ref": ref,
                "text": text,
                "element": element_description,
                "submit": submit
            }
        )
        return result.get("success", False)
    
    async def wait_for(
        self,
        text: Optional[str] = None,
        timeout: int = 10
    ) -> bool:
        """Convenience method for waiting for elements."""
        params = {"time": timeout}
        if text:
            params["text"] = text
        
        result = await self.execute_tool("browser_wait_for", params)
        return result.get("success", False)
    
    async def get_snapshot(self) -> Dict[str, Any]:
        """Get page accessibility snapshot."""
        return await self.execute_tool("browser_snapshot", {})
    
    async def evaluate(
        self,
        function: str,
        element_ref: Optional[str] = None
    ) -> Any:
        """Execute JavaScript on page."""
        params = {"function": function}
        if element_ref:
            params["ref"] = element_ref
            params["element"] = "target element"
        
        result = await self.execute_tool("browser_evaluate", params)
        return result.get("result")
    
    async def take_screenshot(
        self,
        filename: Optional[str] = None,
        full_page: bool = False
    ) -> str:
        """Take screenshot of current page."""
        params = {"fullPage": full_page}
        if filename:
            params["filename"] = filename
        
        result = await self.execute_tool("browser_take_screenshot", params)
        return result.get("filename", "")
    
    async def get_console_messages(self) -> List[str]:
        """Get browser console messages."""
        result = await self.execute_tool("browser_console_messages", {})
        return result.get("messages", [])
    
    async def get_network_requests(self) -> List[Dict[str, Any]]:
        """Get network requests made by the page."""
        result = await self.execute_tool("browser_network_requests", {})
        return result.get("requests", [])