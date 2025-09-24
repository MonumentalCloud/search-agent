# Unified Search Agent Control Script

This document explains how to use the new unified control script for the Search Agent.

## Quick Start

### Using Python
```bash
./run.py                 # Start everything (API + WebSocket + Chat GUI)
./run.py --stop          # Stop all running services
./run.py --status        # Check status of all services
```

### Using Shell Script
```bash
./run.sh                 # Start everything (API + WebSocket + Chat GUI)
./run.sh --stop          # Stop all running services
./run.sh --status        # Check status of all services
```

## Command Line Options

### Mode Selection

Start specific components:

```bash
./run.py --api           # Start API server only
./run.py --websocket     # Start WebSocket server only
./run.py --chat          # Start Chat GUI only
./run.py --full          # Start full stack (API + WebSocket + Chat)
```

### Control Options

```bash
./run.py --stop          # Stop all running services
./run.py --status        # Show status of all services
```

### Setup Options

Skip specific setup steps:

```bash
./run.py --skip-docker   # Skip Docker/Weaviate setup
./run.py --skip-ingest   # Skip PDF ingestion
./run.py --skip-vectors  # Skip metadata vector rebuild
./run.py --skip-test     # Skip system test
```

### Configuration Options

Customize server configuration:

```bash
./run.py --api-host 127.0.0.1     # API server host
./run.py --api-port 8080          # API server port
./run.py --websocket-host 0.0.0.0 # WebSocket server host
./run.py --websocket-port 8000    # WebSocket server port
./run.py --verbose                # Verbose logging
```

## Examples

### Start Everything
```bash
./run.py
```

### Start Only WebSocket Server
```bash
./run.py --websocket --skip-docker
```

### Start API and Chat GUI
```bash
./run.py --api --chat
```

### Custom Port Configuration
```bash
./run.py --api --api-port 9000
```

## Service URLs

When services are running, they can be accessed at:

- **API Server**: http://localhost:8001
  - API Docs: http://localhost:8001/docs
  - Health Check: http://localhost:8001/health
- **WebSocket Server**: http://localhost:8000
- **Chat GUI**: http://localhost:8501
