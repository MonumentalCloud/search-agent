#!/bin/bash
# Build and push Docker image to Docker Hub

set -e

# Configuration
IMAGE_NAME="cloudsx3/search-agent"  # Replace with your Docker Hub username
TAG="latest"

echo "Building Docker image locally for linux/amd64 platform..."
docker build --platform linux/amd64 -f Dockerfile.fast -t $IMAGE_NAME:$TAG .

echo "Tagging image..."
docker tag $IMAGE_NAME:$TAG $IMAGE_NAME:latest

echo "Pushing to Docker Hub..."
docker push $IMAGE_NAME:$TAG
docker push $IMAGE_NAME:latest

echo "✅ Image pushed successfully!"
echo "Image URL: docker.io/$IMAGE_NAME:$TAG"
echo ""
echo "Now update your Render service to use this image:"
echo "1. Go to Render dashboard"
echo "2. Change deployment method to 'Deploy from Docker Repository'"
echo "3. Use image URL: docker.io/$IMAGE_NAME:$TAG"
