#!/usr/bin/env python3
"""
Script para corregir MCPResponse en PaperTradingMCP
"""

import re

def fix_mcp_responses():
    file_path = "mcps/paper_trading_mcp.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Patrón para encontrar MCPResponse con id= y result=
    pattern1 = r'MCPResponse\(\s*id=message\.id,\s*result='
    replacement1 = 'MCPResponse(\n                request_id=message.id,\n                success=True,\n                data='
    
    # Patrón para encontrar MCPResponse con id= y error=
    pattern2 = r'MCPResponse\(\s*id=message\.id,\s*error='
    replacement2 = 'MCPResponse(\n                request_id=message.id,\n                success=False,\n                data=None,\n                error='
    
    # Aplicar reemplazos
    content = re.sub(pattern1, replacement1, content)
    content = re.sub(pattern2, replacement2, content)
    
    # Escribir archivo corregido
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ MCPResponse corregidos en paper_trading_mcp.py")

if __name__ == "__main__":
    fix_mcp_responses()