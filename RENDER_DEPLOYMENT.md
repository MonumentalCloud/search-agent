# Deploy Search Agent to Render.com (Without Docker & GitHub)

This guide shows you how to deploy your search agent to Render.com without using Docker or GitHub integration.

## Prerequisites

1. **Render.com Account**: Sign up at [render.com](https://render.com)
2. **API Keys**: You'll need:
   - OpenRouter API key (for LLM)
   - BGE API key (for embeddings)
3. **Project Files**: Your search agent project files

## Method 1: Manual Deployment (Recommended)

### Step 1: Prepare Your Project

1. **Create a deployment package** by zipping your project:
   ```bash
   # In your project directory
   zip -r search-agent-deploy.zip . -x "*.git*" "*.pyc" "__pycache__/*" "*.log" "chroma_db/*"
   ```

2. **Or use the provided files**:
   - `render_start.py` - Main startup script
   - `render_build.sh` - Build script
   - `render.yaml` - Render configuration
   - `env.production` - Environment template

### Step 2: Create Render Service

1. **Go to Render Dashboard**: https://dashboard.render.com
2. **Click "New +"** → **"Web Service"**
3. **Choose "Build and deploy from a Git repository"** → **"Skip"** (we'll upload manually)
4. **Fill in the form**:
   - **Name**: `search-agent`
   - **Environment**: `Python 3`
   - **Build Command**: `chmod +x render_build.sh && ./render_build.sh`
   - **Start Command**: `python render_start.py`
   - **Instance Type**: `Free` (or upgrade as needed)

### Step 3: Configure Environment Variables

In the Render dashboard, go to **Environment** tab and add:

```
CONFIG_PATH=configs/default.yaml
PYTHONPATH=.
OPENROUTER_API_KEY=your_actual_openrouter_key
BGE_API_KEY=your_actual_bge_key
```

### Step 4: Add Persistent Disk

1. **Go to "Disks" tab**
2. **Click "Connect New Disk"**
3. **Configure**:
   - **Name**: `chroma-data`
   - **Mount Path**: `/opt/render/project/src/chroma_db`
   - **Size**: `1 GB`

### Step 5: Upload Your Code

1. **Go to "Manual Deploy" tab**
2. **Upload your zip file** or drag and drop your project files
3. **Click "Deploy"**

## Method 2: Using Render Blueprint

### Step 1: Prepare Blueprint

1. **Ensure `render.yaml` exists** in your project root
2. **Update environment variables** in the blueprint:
   ```yaml
   envVars:
     - key: OPENROUTER_API_KEY
       sync: false  # You'll set this manually
     - key: BGE_API_KEY
       sync: false  # You'll set this manually
   ```

### Step 2: Deploy via Blueprint

1. **Go to**: https://render.com/new/blueprint
2. **Upload your project** (zip file or drag files)
3. **Render will automatically**:
   - Create the web service
   - Set up the disk
   - Configure the build and start commands

### Step 3: Set Environment Variables

After deployment, go to your service dashboard and add:
- `OPENROUTER_API_KEY`
- `BGE_API_KEY`

## Method 3: Direct File Upload

### Step 1: Create Web Service

1. **Create new Web Service** in Render dashboard
2. **Skip Git connection**
3. **Set basic configuration**:
   - **Name**: `search-agent`
   - **Environment**: `Python 3`
   - **Build Command**: `chmod +x render_build.sh && ./render_build.sh`
   - **Start Command**: `python render_start.py`

### Step 2: Upload Files

1. **Go to "Manual Deploy"**
2. **Upload your project files** (you can drag and drop the entire folder)
3. **Deploy**

## Post-Deployment Configuration

### 1. Set Environment Variables

In your Render service dashboard:

```
CONFIG_PATH=configs/default.yaml
PYTHONPATH=.
OPENROUTER_API_KEY=your_openrouter_api_key
BGE_API_KEY=your_bge_api_key
```

### 2. Add Persistent Disk

- **Name**: `chroma-data`
- **Mount Path**: `/opt/render/project/src/chroma_db`
- **Size**: `1 GB` (minimum)

### 3. Configure Health Check

- **Health Check Path**: `/health`
- **Health Check Timeout**: `30 seconds`

## Testing Your Deployment

### 1. Check Service Status

- Go to your service dashboard
- Check the **"Logs"** tab for startup messages
- Verify the service shows as **"Live"**

### 2. Test Endpoints

Your service will be available at: `https://your-service-name.onrender.com`

Test endpoints:
- **Health**: `GET /health`
- **Query**: `POST /api/query` with JSON body:
  ```json
  {
    "query": "test query",
    "query_id": "test-123"
  }
  ```
- **SSE**: `GET /sse/agent?query_id=test-123`

### 3. Test Frontend

The frontend is served from the same service at the root path `/`.

## Troubleshooting

### Common Issues

1. **Build Failures**:
   - Check the build logs in Render dashboard
   - Ensure all dependencies are in `requirements.txt`
   - Verify build script permissions

2. **Startup Failures**:
   - Check environment variables are set correctly
   - Verify API keys are valid
   - Check startup logs for errors

3. **Database Issues**:
   - Ensure disk is mounted correctly
   - Check disk has enough space
   - Verify ChromaDB can write to the mounted path

4. **Memory Issues**:
   - Free tier has 512MB RAM limit
   - Consider upgrading to paid plan for production
   - Optimize model loading if needed

### Logs and Debugging

- **View logs**: Render dashboard → Your service → "Logs" tab
- **Debug locally**: Use `python render_start.py` to test startup
- **Check health**: Visit `/health` endpoint

## Free Tier Limitations

- **512MB RAM**: May be limiting for large models
- **750 hours/month**: Service spins down after 15 minutes of inactivity
- **1GB disk**: Sufficient for small to medium datasets
- **Cold starts**: First request after inactivity may be slow

## Upgrading for Production

For production use, consider:

1. **Upgrade to Starter Plan** ($7/month):
   - 512MB RAM → 1GB RAM
   - Always-on service
   - Custom domains

2. **Add more disk space** if needed
3. **Set up monitoring** and alerts
4. **Configure custom domain**

## Security Considerations

1. **API Keys**: Never commit API keys to version control
2. **Environment Variables**: Use Render's secure environment variable system
3. **CORS**: Configure CORS properly for production domains
4. **Rate Limiting**: Consider adding rate limiting for production use

## Next Steps

After successful deployment:

1. **Test all functionality** thoroughly
2. **Set up monitoring** and alerts
3. **Configure custom domain** (if needed)
4. **Set up CI/CD** for future updates
5. **Backup your data** regularly

## Support

- **Render Documentation**: https://render.com/docs
- **Render Community**: https://community.render.com
- **Project Issues**: Check your project's issue tracker
