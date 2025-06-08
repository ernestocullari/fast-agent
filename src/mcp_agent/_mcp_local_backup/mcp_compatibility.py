# Quick MCP Compatibility Fix
from typing import Any, Dict, Optional

class JSONRPCMessage:
    """Compatibility class for JSONRPCMessage"""
    def __init__(self, method: str = None, params: Dict[str, Any] = None, id: Optional[str] = None, **kwargs):
        self.method = method
        self.params = params or {}
        self.id = id
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"method": self.method, "params": self.params}
        if self.id is not None:
            result["id"] = self.id
        return result

# Try multiple import paths for ServerCapabilities
try:
    from mcp.types import ServerCapabilities
except ImportError:
    try:
        from mcp.server import ServerCapabilities
    except ImportError:
        try:
            from mcp.protocol import ServerCapabilities  
        except ImportError:
            try:
                from mcp.shared import ServerCapabilities
            except ImportError:
                class ServerCapabilities:
                    def __init__(self, **kwargs):
                        for key, value in kwargs.items():
                            setattr(self, key, value)

__all__ = ['JSONRPCMessage', 'ServerCapabilities']
