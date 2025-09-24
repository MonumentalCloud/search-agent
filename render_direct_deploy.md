# Direct Deployment to Render Without GitHub

Since you can't push your code to GitHub due to API keys, you can deploy directly to Render using their CLI tool. Here's a step-by-step guide:

## Prerequisites

1. Install the Render CLI:
```bash
npm install -g @render/cli
```

2. Create a `.env` file with your actual API keys:
```bash
cp env.sample .env
```
Then edit the `.env` file to include your actual API keys.

## Step 1: Create a ZIP Archive of Your Project

```bash
# Create a ZIP file excluding sensitive files
zip -r search_agent.zip . -x "*.git*" ".env" "chroma_db/*"
```

## Step 2: Create Services on Render Manually

1. **Log in to Render CLI**:
```bash
render login
```

2. **Create API Service**:
```bash
render create service --name search-agent-api --type web --runtime python3 --plan free --region singapore --env-file .env --build-command "pip install -r requirements.txt" --start-command "python -m uvicorn apps.api.main:app --host 0.0.0.0 --port \$PORT" search_agent.zip
```

3. **Create WebSocket Service**:
```bash
render create service --name search-agent-websocket --type web --runtime python3 --plan free --region singapore --env-file .env --build-command "pip install -r requirements.txt" --start-command "python -m uvicorn apps.api.websocket_server:app --host 0.0.0.0 --port \$PORT" search_agent.zip
```

4. **Create Frontend Static Site**:
```bash
render create service --name search-agent-frontend --type static --plan free --region singapore --publish-directory frontend search_agent.zip
```

## Step 3: Configure Environment Variables in Render Dashboard

After creating the services, log in to your Render dashboard and:

1. For each service, go to the "Environment" tab
2. Add your API keys as environment variables:
   - `OPENROUTER_API_KEY`: Your OpenRouter API key
   - `BGE_API_KEY`: Your BGE API key
   - `CONFIG_PATH`: configs/default.yaml
   - `PYTHONPATH`: .

3. For the WebSocket service, add:
   - `API_HOST`: URL of your API service (without https://)
   - `API_PORT`: 443 (HTTPS port)

4. For the Frontend service, add:
   - `WEBSOCKET_URL`: wss://search-agent-websocket.onrender.com/ws/agent

## Step 4: Create a Disk for Chroma DB

1. In the API service settings, go to "Disks"
2. Create a new disk:
   - Name: chroma-data
   - Mount path: /app/chroma_db
   - Size: 1GB

## Step 5: Deploy Updates

When you need to update your deployment:

1. Create a new ZIP archive:
```bash
zip -r search_agent.zip . -x "*.git*" ".env" "chroma_db/*"
```

2. Deploy the update:
```bash
render deploy search-agent-api search_agent.zip
render deploy search-agent-websocket search_agent.zip
render deploy search-agent-frontend search_agent.zip
```

## Accessing Your Deployed Application

Once deployed, you can access your application at:
- Frontend: https://search-agent-frontend.onrender.com
- API: https://search-agent-api.onrender.com
- WebSocket: wss://search-agent-websocket.onrender.com/ws/agent

Share the frontend URL with your boss to access the application.
