# Manual Deployment to Your Own Server

## Prerequisites

1. **Server with Docker installed**
2. **SSH access to your server**
3. **Environment variables set on server**

## Step-by-Step Deployment

### 1. Build Docker Image Locally

```bash
# Build the production image
docker build -f Dockerfile.production -t search-agent:latest .

# Save the image
docker save search-agent:latest | gzip > search-agent.tar.gz
```

### 2. Transfer to Server

```bash
# Transfer the image
scp search-agent.tar.gz user@your-server.com:~/

# Transfer your data
scp -r ./chroma_db/ user@your-server.com:~/chroma_db/
scp ./.env user@your-server.com:~/.env
```

### 3. Deploy on Server

```bash
# SSH into your server
ssh user@your-server.com

# Load the Docker image
docker load < search-agent.tar.gz

# Stop existing container (if any)
docker stop search-agent || true
docker rm search-agent || true

# Run the container
docker run -d \
    --name search-agent \
    -p 8000:8000 \
    -v $(pwd)/chroma_db:/app/chroma_db \
    -v $(pwd)/.env:/app/.env \
    -e OPENROUTER_API_KEY="$OPENROUTER_API_KEY" \
    -e BGE_API_KEY="$BGE_API_KEY" \
    search-agent:latest

# Check if it's running
docker ps | grep search-agent

# View logs
docker logs -f search-agent
```

### 4. Access Your Service

Your service will be available at: `http://your-server.com:8000`

## Useful Commands

```bash
# View logs
docker logs -f search-agent

# Stop service
docker stop search-agent

# Restart service
docker restart search-agent

# Update service (after building new image)
docker stop search-agent
docker rm search-agent
# Then run the docker run command again
```

## Environment Variables

Make sure these are set on your server:

```bash
export OPENROUTER_API_KEY="your_openrouter_api_key"
export BGE_API_KEY="your_bge_api_key"
```

Or create a `.env` file on the server with:

```
OPENROUTER_API_KEY=your_openrouter_api_key
BGE_API_KEY=your_bge_api_key
```

## Advantages of Own Server

- ✅ **Full control** over the environment
- ✅ **No platform limitations** like Render
- ✅ **Direct file access** via SSH/SCP
- ✅ **Persistent storage** without extra costs
- ✅ **Custom configuration** options
- ✅ **Better performance** (no cold starts)
