#!/bin/bash
# Deploy to your own server via SSH and Docker

# Configuration
SERVER_HOST="your-server.com"  # Replace with your server
SERVER_USER="your-username"    # Replace with your username
SERVICE_NAME="search-agent"
PORT="8000"

echo "🚀 Deploying Search Agent to your server..."
echo "Server: ${SERVER_USER}@${SERVER_HOST}"
echo ""

# Check if we can connect to the server
echo "Testing SSH connection..."
if ! ssh -o ConnectTimeout=10 ${SERVER_USER}@${SERVER_HOST} "echo 'SSH connection successful'"; then
    echo "❌ Cannot connect to server. Please check:"
    echo "   - Server hostname/IP: ${SERVER_HOST}"
    echo "   - Username: ${SERVER_USER}"
    echo "   - SSH key is set up"
    exit 1
fi

echo "✅ SSH connection successful"
echo ""

# Build the Docker image locally
echo "Building Docker image..."
docker build -f Dockerfile.production -t ${SERVICE_NAME}:latest .

if [ $? -ne 0 ]; then
    echo "❌ Docker build failed"
    exit 1
fi

echo "✅ Docker image built successfully"
echo ""

# Save the Docker image to a tar file
echo "Saving Docker image..."
docker save ${SERVICE_NAME}:latest | gzip > ${SERVICE_NAME}.tar.gz

if [ $? -ne 0 ]; then
    echo "❌ Failed to save Docker image"
    exit 1
fi

echo "✅ Docker image saved to ${SERVICE_NAME}.tar.gz"
echo ""

# Transfer the image to the server
echo "Transferring Docker image to server..."
scp ${SERVICE_NAME}.tar.gz ${SERVER_USER}@${SERVER_HOST}:~/

if [ $? -ne 0 ]; then
    echo "❌ Failed to transfer Docker image"
    exit 1
fi

echo "✅ Docker image transferred to server"
echo ""

# Deploy on the server
echo "Deploying on server..."
ssh ${SERVER_USER}@${SERVER_HOST} << EOF
    echo "Loading Docker image..."
    docker load < ${SERVICE_NAME}.tar.gz
    
    echo "Stopping existing container (if any)..."
    docker stop ${SERVICE_NAME} || true
    docker rm ${SERVICE_NAME} || true
    
    echo "Starting new container..."
    docker run -d \
        --name ${SERVICE_NAME} \
        -p ${PORT}:8000 \
        -v \$(pwd)/chroma_db:/app/chroma_db \
        -v \$(pwd)/.env:/app/.env \
        -e OPENROUTER_API_KEY="\${OPENROUTER_API_KEY}" \
        -e BGE_API_KEY="\${BGE_API_KEY}" \
        ${SERVICE_NAME}:latest
    
    echo "Cleaning up..."
    rm ${SERVICE_NAME}.tar.gz
    
    echo "Checking container status..."
    docker ps | grep ${SERVICE_NAME}
    
    echo "Container logs (last 20 lines):"
    docker logs --tail 20 ${SERVICE_NAME}
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Deployment successful!"
    echo "Your service should be available at: http://${SERVER_HOST}:${PORT}"
    echo ""
    echo "Useful commands:"
    echo "  View logs: ssh ${SERVER_USER}@${SERVER_HOST} 'docker logs -f ${SERVICE_NAME}'"
    echo "  Stop service: ssh ${SERVER_USER}@${SERVER_HOST} 'docker stop ${SERVICE_NAME}'"
    echo "  Restart service: ssh ${SERVER_USER}@${SERVER_HOST} 'docker restart ${SERVICE_NAME}'"
else
    echo "❌ Deployment failed"
    exit 1
fi

# Clean up local files
echo "Cleaning up local files..."
rm ${SERVICE_NAME}.tar.gz

echo "✅ Deployment complete!"
