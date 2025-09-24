#!/bin/bash

# Deployment script for Search Agent
# This script helps deploy the application to various cloud platforms

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored messages
print_message() {
  echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Check if Docker is installed
if ! command_exists docker; then
  print_error "Docker is not installed. Please install Docker first."
  exit 1
fi

# Check if Docker Compose is installed
if ! command_exists docker-compose; then
  print_warning "Docker Compose is not installed. Some deployment options may not work."
fi

# Display menu
echo "==============================================="
echo "        Search Agent Deployment Tool           "
echo "==============================================="
echo "Choose a deployment option:"
echo "1. Deploy locally with Docker Compose"
echo "2. Prepare for Render.com deployment"
echo "3. Prepare for Railway.app deployment"
echo "4. Deploy frontend to Netlify"
echo "5. Exit"
echo "==============================================="

read -p "Enter your choice (1-5): " choice

case $choice in
  1)
    print_message "Deploying locally with Docker Compose..."
    docker-compose up -d
    print_message "Application deployed locally!"
    print_message "Frontend: http://localhost"
    print_message "API: http://localhost:8001"
    print_message "WebSocket: ws://localhost:8002/ws/agent"
    ;;
  2)
    print_message "Preparing for Render.com deployment..."
    
    # Create render.yaml file for Render Blueprint
    cat > render.yaml << EOL
services:
  - type: web
    name: search-agent-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python -m uvicorn apps.api.main:app --host 0.0.0.0 --port \$PORT
    envVars:
      - key: CONFIG_PATH
        value: configs/default.yaml
    disk:
      name: chroma-data
      mountPath: /app/chroma_db
      sizeGB: 1
      
  - type: web
    name: search-agent-websocket
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python -m uvicorn apps.api.websocket_server:app --host 0.0.0.0 --port \$PORT
    envVars:
      - key: CONFIG_PATH
        value: configs/default.yaml
      - key: API_HOST
        fromService:
          name: search-agent-api
          type: web
          property: host
          
  - type: static
    name: search-agent-frontend
    buildCommand: echo "Static site ready"
    staticPublishPath: ./frontend
    routes:
      - type: rewrite
        source: /ws/*
        destination: https://search-agent-websocket.onrender.com/ws/*
EOL
    
    print_message "Created render.yaml for Render Blueprint deployment"
    print_message "To deploy to Render:"
    print_message "1. Push your code to GitHub"
    print_message "2. Go to https://render.com/new/blueprint"
    print_message "3. Connect your GitHub repository"
    print_message "4. Follow the deployment instructions"
    ;;
  3)
    print_message "Preparing for Railway.app deployment..."
    print_message "To deploy to Railway:"
    print_message "1. Push your code to GitHub"
    print_message "2. Go to https://railway.app/new"
    print_message "3. Select 'Deploy from GitHub repo'"
    print_message "4. Connect your GitHub repository"
    print_message "5. Railway will detect your docker-compose.yml and deploy it"
    ;;
  4)
    print_message "Preparing for Netlify frontend deployment..."
    
    # Create netlify.toml file
    cat > frontend/netlify.toml << EOL
[build]
  publish = "/"
  command = ""

[[redirects]]
  from = "/ws/*"
  to = "https://your-backend-url.com/ws/:splat"
  status = 200
  force = true
EOL
    
    print_message "Created netlify.toml for Netlify deployment"
    print_message "To deploy to Netlify:"
    print_message "1. Push your code to GitHub"
    print_message "2. Go to https://app.netlify.com/start"
    print_message "3. Connect your GitHub repository"
    print_message "4. Set the publish directory to 'frontend'"
    print_message "5. Update the redirect URL in netlify.toml to your actual backend URL"
    ;;
  5)
    print_message "Exiting..."
    exit 0
    ;;
  *)
    print_error "Invalid choice. Exiting..."
    exit 1
    ;;
esac
