# Deployment Guide for Search Agent

This guide explains how to deploy the Search Agent application (Chroma DB, FastAPI backend, and frontend) to various cloud platforms, including free options.

## Quick Start

The easiest way to deploy is using our deployment script:

```bash
./deploy.sh
```

This interactive script will guide you through deployment options for different platforms.

## Option 1: Render.com (Free Tier)

Render offers a free tier that works well for this project:

### Manual Deployment

1. **Create a Render account** at [render.com](https://render.com)

2. **Deploy the API Server**:
   - Create a new Web Service
   - Connect your GitHub repository
   - Set build command: `pip install -r requirements.txt`
   - Set start command: `python -m uvicorn apps.api.main:app --host 0.0.0.0 --port $PORT`
   - Add environment variable: `CONFIG_PATH=configs/default.yaml`
   - Create a disk: 1GB mounted at `/app/chroma_db`

3. **Deploy the WebSocket Server**:
   - Create another Web Service
   - Connect the same GitHub repository
   - Set build command: `pip install -r requirements.txt`
   - Set start command: `python -m uvicorn apps.api.websocket_server:app --host 0.0.0.0 --port $PORT`
   - Add environment variables:
     - `CONFIG_PATH=configs/default.yaml`
     - `API_HOST=your-api-service-url.onrender.com` (without https://)

4. **Deploy the Frontend**:
   - Create a Static Site
   - Connect the same GitHub repository
   - Set publish directory: `frontend`
   - Add environment variable: `WEBSOCKET_URL=wss://your-websocket-service-url.onrender.com/ws/agent`

### Blueprint Deployment (Easier)

Alternatively, use the Render Blueprint in `render.yaml`:

1. Push your code to GitHub
2. Go to https://render.com/new/blueprint
3. Connect your GitHub repository
4. Render will automatically set up all services

### Limitations

- Free tier instances spin down after 15 minutes of inactivity
- Limited to 512MB RAM
- 750 hours of free usage per month

## Option 2: Railway.app (Free Credit)

Railway offers a starter plan with $5 of free credit monthly:

1. **Create a Railway account** at [railway.app](https://railway.app)
2. Go to https://railway.app/new
3. Select "Deploy from GitHub repo"
4. Connect your GitHub repository
5. Railway will detect your `docker-compose.yml` and deploy it
6. Configure environment variables in the Railway dashboard if needed

### Advantages

- Better performance than Render's free tier
- Supports Docker Compose directly
- Persistent storage for Chroma DB

### Limitations

- $5 credit runs out based on usage
- Requires credit card for verification

## Option 3: Netlify (Frontend) + Render (Backend)

Split your deployment for better performance:

### Frontend on Netlify (Free)

1. **Create a Netlify account** at [netlify.com](https://netlify.com)
2. Go to https://app.netlify.com/start
3. Connect your GitHub repository
4. Set the publish directory to `frontend`
5. Configure environment variables:
   - `WEBSOCKET_URL=wss://your-websocket-service-url.onrender.com/ws/agent`
6. Deploy

### Backend on Render (Free)

Follow the Render.com instructions above, but only deploy the API and WebSocket services.

## Local Deployment

To deploy locally with Docker Compose:

```bash
docker-compose up -d
```

This will start all services:
- Frontend: http://localhost
- API: http://localhost:8001
- WebSocket: ws://localhost:8002/ws/agent

## Troubleshooting

### Connection Issues

- Ensure CORS is properly configured in the backend
- Check that WebSocket URLs use `wss://` (secure) for HTTPS sites
- Verify environment variables are correctly set

### Database Persistence

- On Render, make sure to create a disk for Chroma DB
- On Railway, the Docker volume should handle persistence

### Memory Limitations

- Consider reducing model sizes or batch processing for free tiers
- Monitor memory usage and optimize as needed
