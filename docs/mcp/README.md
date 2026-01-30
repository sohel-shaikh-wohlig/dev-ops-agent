# How to Run MCP Servers - Complete Guide

## Overview

MCP servers can run in two modes:
1. **Standalone (Testing)** - Run directly from terminal for development/testing
2. **With Claude Desktop (Production)** - Automatic startup when Claude Desktop loads

---

## Method 1: Standalone Testing (Recommended for Development)

### Quick Test Run

```bash
# Navigate to your project directory
cd /path/to/your-project

# Run the MCP server directly
python mcp/servers/devops_automation.py
```

**What happens:**
- Server starts and waits for input on stdin
- You'll see: (cursor waiting, no output is normal)
- The server is now listening for MCP protocol messages
- **Press Ctrl+C to stop**

### Testing with MCP Inspector (Best for Development)

The MCP Inspector is a tool that lets you test MCP servers interactively.

**Step 1: Install MCP Inspector**

```bash
npm install -g @modelcontextprotocol/inspector
```

**Step 2: Run your server with inspector**

```bash
# Start inspector
mcp-inspector python mcp/servers/devops_automation.py
```

**Step 3: Open in browser**

The inspector will open a web interface where you can:
- See all available tools
- Test tool calls
- View responses
- Debug issues

**Example:**
```
✓ MCP Inspector running at http://localhost:5173
✓ Server connected: devops-automation

Tools Available:
  - deploy_microservice
  - check_deployment_status
  - get_deployment_plan
  - list_recent_deployments
  - rollback_deployment

Click on any tool to test it!
```

---

## Method 2: Run with Claude Desktop (Production Use)

This is the main way to use MCP servers - they run automatically when Claude Desktop starts.

### Step 1: Configure Claude Desktop

**Location of config file:**
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%/Claude/claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

**Create/edit the config:**

```json
{
  "mcpServers": {
    "devops-automation": {
      "command": "python",
      "args": ["/absolute/path/to/your-project/mcp/servers/devops_automation.py"],
      "env": {
        "MCP_FASTAPI_URL": "http://localhost:8000",
        "MCP_LOG_LEVEL": "INFO"
      }
    },
    "kubernetes": {
      "command": "python",
      "args": ["/absolute/path/to/your-project/mcp/servers/kubernetes_multi.py"]
    }
  }
}
```

**⚠️ IMPORTANT: Use absolute paths!**

```bash
# Get absolute path
cd /path/to/your-project
pwd
# Copy this path and use it in config

# Example on macOS:
# /Users/yourname/projects/devops-automation/mcp/servers/devops_automation.py
```

### Step 2: Make sure your FastAPI is running

```bash
# Your MCP server needs FastAPI to be running
cd /path/to/your-project
uvicorn api.main:app --reload

# Should see:
# INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Step 3: Restart Claude Desktop

**macOS:**
```bash
# Quit Claude Desktop (Cmd+Q)
# Then reopen from Applications

# Or via command line:
killall Claude
open -a Claude
```

**Windows:**
- Close Claude Desktop completely (check system tray)
- Reopen from Start Menu

**Linux:**
```bash
killall claude
claude &
```

### Step 4: Verify MCP servers loaded

**Check Claude Desktop logs:**

```bash
# macOS
tail -f ~/Library/Logs/Claude/mcp*.log

# You should see:
# [2024-01-30] MCP Server started: devops-automation
# [2024-01-30] Connected to FastAPI at http://localhost:8000
# [2024-01-30] Server ready
```

### Step 5: Test in Claude

Open Claude and ask:

```
"What deployment tools do you have available?"
```

Claude should respond with a list of your MCP tools!

---

## Method 3: Run with Environment Variables

### Using .env file

```bash
# Create .env file
cat > .env << 'EOF'
MCP_FASTAPI_URL=http://localhost:8000
MCP_API_TOKEN=your_token_here
MCP_LOG_LEVEL=DEBUG
EOF

# Run with dotenv
pip install python-dotenv

# Then run normally - settings will load from .env
python mcp/servers/devops_automation.py
```

### Using command line

```bash
# Set environment variables inline
MCP_FASTAPI_URL=http://localhost:8000 \
MCP_API_TOKEN=abc123 \
MCP_LOG_LEVEL=DEBUG \
python mcp/servers/devops_automation.py
```

### Using shell profile

```bash
# Add to ~/.bashrc or ~/.zshrc
export MCP_FASTAPI_URL="http://localhost:8000"
export MCP_API_TOKEN="your_token"

# Reload shell
source ~/.bashrc  # or source ~/.zshrc

# Now run normally
python mcp/servers/devops_automation.py
```

---

## Method 4: Run as a Background Service

### Using systemd (Linux)

```bash
# Create service file
sudo nano /etc/systemd/system/mcp-devops.service
```

```ini
[Unit]
Description=MCP DevOps Automation Server
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/your-project
Environment="MCP_FASTAPI_URL=http://localhost:8000"
Environment="MCP_API_TOKEN=your_token"
ExecStart=/usr/bin/python3 /path/to/your-project/mcp/servers/devops_automation.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable mcp-devops
sudo systemctl start mcp-devops

# Check status
sudo systemctl status mcp-devops

# View logs
sudo journalctl -u mcp-devops -f
```

### Using Docker (Cross-platform)

```dockerfile
# Dockerfile.mcp
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements-mcp.txt .
RUN pip install --no-cache-dir -r requirements-mcp.txt

# Copy MCP code
COPY mcp/ ./mcp/

# Set environment variables
ENV MCP_FASTAPI_URL=http://host.docker.internal:8000
ENV MCP_LOG_LEVEL=INFO

# Run server
CMD ["python", "mcp/servers/devops_automation.py"]
```

```bash
# Build
docker build -f Dockerfile.mcp -t mcp-devops .

# Run
docker run -it --name mcp-devops \
  -e MCP_FASTAPI_URL=http://host.docker.internal:8000 \
  -e MCP_API_TOKEN=your_token \
  mcp-devops
```

---

## Troubleshooting

### Problem: "Server not starting"

**Check 1: Python version**
```bash
python --version
# Should be 3.8+
```

**Check 2: Dependencies installed**
```bash
pip install -r requirements-mcp.txt
```

**Check 3: Imports working**
```bash
python -c "from mcp.server import Server; print('OK')"
```

### Problem: "Cannot connect to FastAPI"

**Check 1: FastAPI is running**
```bash
curl http://localhost:8000/docs
# Should return HTML
```

**Check 2: Check URL in config**
```bash
# In your .env or config
MCP_FASTAPI_URL=http://localhost:8000  # ✓ Correct
MCP_FASTAPI_URL=localhost:8000         # ✗ Missing http://
```

**Check 3: Check firewall**
```bash
# Test connection
nc -zv localhost 8000
```

### Problem: "Claude Desktop doesn't see MCP server"

**Check 1: Config file location**
```bash
# macOS - verify file exists
ls -la ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Check syntax
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json | jq .
# Should parse without errors
```

**Check 2: Absolute paths**
```json
{
  "mcpServers": {
    "devops-automation": {
      "command": "python",
      // ✓ Absolute path
      "args": ["/Users/you/project/mcp/servers/devops_automation.py"],
      
      // ✗ Relative path - won't work!
      // "args": ["mcp/servers/devops_automation.py"]
    }
  }
}
```

**Check 3: View Claude logs**
```bash
# macOS
tail -f ~/Library/Logs/Claude/mcp*.log

# Look for errors like:
# ERROR: Failed to start server devops-automation
# ERROR: Command not found: python
```

**Check 4: Restart Claude properly**
```bash
# Make sure to fully quit (not just close window)
# macOS: Cmd+Q
# Then reopen
```

### Problem: "MCP server crashes immediately"

**Check 1: Run manually to see error**
```bash
python mcp/servers/devops_automation.py
# You should see the actual error
```

**Check 2: Check imports**
```bash
# Test if all imports work
python -c "
from mcp.server import Server
from mcp.shared.api_client import FastAPIClient
from mcp.config.settings import settings
print('All imports OK')
"
```

**Check 3: Check permissions**
```bash
# Ensure file is executable
chmod +x mcp/servers/devops_automation.py

# Check file ownership
ls -la mcp/servers/devops_automation.py
```

### Problem: "Tools not appearing in Claude"

**Check 1: Server actually running**
```bash
# Check Claude logs
tail -f ~/Library/Logs/Claude/mcp*.log | grep devops-automation

# Should see:
# Server devops-automation: Connected
# Server devops-automation: 5 tools available
```

**Check 2: Test tools manually**
```bash
# Use MCP inspector
mcp-inspector python mcp/servers/devops_automation.py

# Verify tools are listed
```

---

## Development Workflow

### Recommended Setup for Development

**Terminal 1: Run FastAPI**
```bash
cd /path/to/your-project
uvicorn api.main:app --reload
```

**Terminal 2: Run MCP Server with Inspector**
```bash
mcp-inspector python mcp/servers/devops_automation.py
```

**Browser: Test tools**
- Open http://localhost:5173
- Test each tool
- Make changes
- Refresh inspector

**Terminal 3: Watch logs**
```bash
tail -f logs/mcp/devops_automation.log
```

### Quick Restart During Development

```bash
# Kill MCP server
pkill -f "devops_automation.py"

# Restart
python mcp/servers/devops_automation.py
```

Or use a watch script:

```bash
# watch_mcp.sh
#!/bin/bash
while true; do
    python mcp/servers/devops_automation.py
    echo "Server crashed. Restarting in 2 seconds..."
    sleep 2
done
```

---

## Production Deployment Checklist

- [ ] All dependencies installed
- [ ] Environment variables set
- [ ] FastAPI running and accessible
- [ ] MCP server tested with inspector
- [ ] Claude Desktop config updated with absolute paths
- [ ] Token refresh script running (cron/systemd)
- [ ] Logs directory exists and writable
- [ ] Server survives restart
- [ ] Monitoring/alerts configured

---

## Quick Reference Commands

```bash
# Test MCP server directly
python mcp/servers/devops_automation.py

# Test with inspector (best for dev)
mcp-inspector python mcp/servers/devops_automation.py

# Check if server is working
python -c "from mcp.servers.devops_automation import app; print('OK')"

# View Claude Desktop logs
tail -f ~/Library/Logs/Claude/mcp*.log

# Test FastAPI is running
curl http://localhost:8000/docs

# Full restart (development)
pkill -f "devops_automation.py"
uvicorn api.main:app --reload &
python mcp/servers/devops_automation.py
```

---

## Summary

**For Development:**
```bash
# 1. Start FastAPI
uvicorn api.main:app --reload

# 2. Test MCP with inspector
mcp-inspector python mcp/servers/devops_automation.py

# 3. Iterate and test
```

**For Production (Claude Desktop):**
```bash
# 1. Configure claude_desktop_config.json (absolute paths!)
# 2. Restart Claude Desktop
# 3. Test in Claude: "What tools are available?"
```

**For Server Deployment:**
```bash
# Use systemd, Docker, or process manager
# Keep FastAPI and MCP servers running
```

The key: **MCP servers read from stdin and write to stdout using the MCP protocol**. When you run them standalone, they wait for protocol messages. With Claude Desktop, it sends those messages automatically!