"""
Base MCP server class with common functionality
"""

from abc import ABC, abstractmethod
from mcp.server import Server
from typing import List
from mcp.types import Tool, TextContent

class BaseMCPServer(ABC):
    """Base class for all MCP servers"""
    
    def __init__(self, name: str):
        self.app = Server(name)
        self.setup_handlers()
    
    def setup_handlers(self):
        """Register MCP handlers"""
        
        @self.app.list_tools()
        async def list_tools():
            return await self.get_tools()
        
        @self.app.call_tool()
        async def call_tool(name: str, arguments: dict):
            return await self.execute_tool(name, arguments)
    
    @abstractmethod
    async def get_tools(self) -> List[Tool]:
        """Return list of available tools"""
        pass
    
    @abstractmethod
    async def execute_tool(self, name: str, arguments: dict) -> List[TextContent]:
        """Execute a tool"""
        pass
    
    async def run(self):
        """Run the MCP server"""
        import asyncio
        import mcp.server.stdio
        
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.app.run(
                read_stream,
                write_stream,
                self.app.create_initialization_options()
            )