# Docker Deployment Guide

Complete guide for deploying Health Bot using Docker and Docker Compose.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Building Images](#building-images)
3. [GitHub Actions CI/CD](#github-actions-cicd)
4. [Raspberry Pi Deployment](#raspberry-pi-deployment)
5. [Environment Variables](#environment-variables)
6. [Security Best Practices](#security-best-practices)
7. [Troubleshooting](#troubleshooting)

## Quick Start

### Prerequisites

- Docker Engine 20.10+ with Buildx
- Docker Compose 2.0+
- GitHub account (for GHCR access)

### 1. Create Environment File

Create a `.env` file in the project root:

```bash
# Copy and edit with your values
cat > .env << 'EOF'
REGISTRY=ghcr.io
GITHUB_REPO_OWNER=your-username
HEALTH_SVC_TAG=latest
TELEGRAM_BOT_TAG=latest
HEALTH_SVC_PORT=8000
FLOWER_PORT=5555
TELEGRAM_TOKEN=your_telegram_bot_token_here
EOF
```

### 2. Authenticate with GHCR

```bash
docker login ghcr.io -u YOUR_GITHUB_USERNAME
# Enter your GitHub Personal Access Token when prompted
```

### 3. Pull and Start Services

```bash
# Pull latest images
docker compose pull

# Start all services
docker compose up -d

# View logs
docker compose logs -f
```

## Building Images

### Local Build (Single Architecture)

```bash
# Build health_svc
docker build -t health_svc:latest -f health_svc/Dockerfile health_svc/

# Build telegram_bot
docker build -t telegram_bot:latest -f telegram_bot/Dockerfile telegram_bot/
```

### Multi-Architecture Build (for Raspberry Pi)

```bash
# Enable buildx
docker buildx create --use --name multiarch

# Build for both amd64 and arm64
docker buildx build --platform linux/amd64,linux/arm64 \
  -t ghcr.io/your-username/health_svc:latest \
  -f health_svc/Dockerfile \
  --push \
  health_svc/

docker buildx build --platform linux/amd64,linux/arm64 \
  -t ghcr.io/your-username/telegram_bot:latest \
  -f telegram_bot/Dockerfile \
  --push \
  telegram_bot/
```

## GitHub Actions CI/CD

### Automatic Builds

The project includes a GitHub Actions workflow (`.github/workflows/build.yml`) that:

- ✅ Builds multi-arch images (linux/amd64, linux/arm64)
- ✅ Pushes to GitHub Container Registry (GHCR)
- ✅ Uses layer caching for faster builds
- ✅ Triggers on push to main/master, PRs, and manual dispatch

### Workflow Triggers

1. **Push to main/master**: Automatically builds and pushes all services
2. **Pull Requests**: Builds images but doesn't push (for testing)
3. **Manual Dispatch**: Build specific services with custom tags

### Manual Workflow Trigger

1. Go to GitHub → Actions → "Build and Push Docker Images"
2. Click "Run workflow"
3. Select:
   - Service: `all`, `health_svc`, or `telegram_bot`
   - Tag: Custom tag (default: `latest`)

### Image Naming

Images are pushed as:
- `ghcr.io/<your-username>/health_svc:<tag>`
- `ghcr.io/<your-username>/telegram_bot:<tag>`

### Required GitHub Secrets

**None!** The workflow uses `GITHUB_TOKEN` automatically provided by GitHub Actions with `packages:write` permission.

## Raspberry Pi Deployment

### Step 1: Install Docker on Raspberry Pi

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group (logout/login required)
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin -y
```

### Step 2: Clone Repository

```bash
git clone https://github.com/your-username/health-bot.git
cd health-bot
```

### Step 3: Create Environment File

```bash
# Create .env file
nano .env
```

Add the following (replace with your values):

```bash
REGISTRY=ghcr.io
GITHUB_REPO_OWNER=your-username
HEALTH_SVC_TAG=latest
TELEGRAM_BOT_TAG=latest
HEALTH_SVC_PORT=8000
FLOWER_PORT=5555
TELEGRAM_TOKEN=your_telegram_bot_token_here
```

### Step 4: Authenticate with GHCR

```bash
# Create GitHub Personal Access Token with read:packages permission
# Then login:
echo YOUR_GITHUB_TOKEN | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
```

### Step 5: Deploy

```bash
# Pull latest images
docker compose pull

# Start services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

### Step 6: Verify

```bash
# Check API
curl http://localhost:8000/

# Check services
docker compose ps

# View specific service logs
docker compose logs health_svc
docker compose logs telegram_bot
```

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `TELEGRAM_TOKEN` | Telegram bot token from @BotFather | `123456789:ABC...` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `REGISTRY` | Docker registry URL | `ghcr.io` |
| `GITHUB_REPO_OWNER` | GitHub username/organization | `your-username` |
| `HEALTH_SVC_TAG` | Health service image tag | `latest` |
| `TELEGRAM_BOT_TAG` | Telegram bot image tag | `latest` |
| `HEALTH_SVC_PORT` | API port | `8000` |
| `FLOWER_PORT` | Flower dashboard port | `5555` |

### Health Service Internal Variables

These are set automatically in docker-compose.yml but can be overridden:

| Variable | Description | Default |
|----------|-------------|---------|
| `HEALTH_SVC_DB_DIR` | Database directory | `/app/data` |
| `HEALTH_SVC_DB_FILE` | Database filename | `health_bot.db` |
| `HEALTH_SVC_REDIS_URL` | Redis connection URL | `redis://redis:6379` |
| `HEALTH_SVC_UPLOAD_DIR` | Upload directory | `/app/uploads` |

## Security Best Practices

### ✅ DO

- ✅ Store `.env` file on deployment server only
- ✅ Use GitHub Personal Access Tokens with minimal required scopes
- ✅ Use Docker secrets for sensitive data in production
- ✅ Regularly update base images and dependencies
- ✅ Run containers as non-root users (already configured)
- ✅ Use `.dockerignore` to exclude sensitive files
- ✅ Review GitHub Actions logs for exposed secrets

### ❌ DON'T

- ❌ Never commit `.env` files to git
- ❌ Never hard-code secrets in Dockerfiles
- ❌ Never hard-code secrets in docker-compose.yml
- ❌ Never expose sensitive ports unnecessarily
- ❌ Never use `latest` tag in production (use specific versions)
- ❌ Never run containers as root (already prevented)

### Creating GitHub Personal Access Token

1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Select scopes:
   - `read:packages` (to pull images)
   - `write:packages` (to push images, if building manually)
4. Generate and copy token
5. Use token for `docker login ghcr.io`

## Troubleshooting

### Images Not Found

**Problem**: `Error: pull access denied` or `manifest unknown`

**Solutions**:
1. Verify GHCR authentication: `docker login ghcr.io`
2. Check image name matches your GitHub username
3. Ensure images were built and pushed successfully
4. Verify image tag exists: `docker pull ghcr.io/username/health_svc:latest`

### Services Not Starting

**Problem**: Services exit immediately or fail to start

**Solutions**:
1. Check logs: `docker compose logs <service-name>`
2. Verify `.env` file exists and contains required variables
3. Check port conflicts: `netstat -tulpn | grep <port>`
4. Verify Docker network: `docker network ls`

### Database Issues

**Problem**: Database errors or permission denied

**Solutions**:
1. Check volume permissions: `docker volume inspect health-bot_health_svc_data`
2. Verify database directory is writable
3. Check volume mount: `docker compose config`
4. Restart service: `docker compose restart health_svc`

### Network Connectivity

**Problem**: Services can't communicate

**Solutions**:
1. Verify Docker network: `docker network inspect health-bot_health-bot-network`
2. Check service names match docker-compose.yml
3. Use service names as hostnames (e.g., `http://health_svc:8000`)
4. Verify all services are on the same network

### Build Failures

**Problem**: Docker build fails

**Solutions**:
1. Check Dockerfile syntax
2. Verify all files exist in build context
3. Check `.dockerignore` isn't excluding required files
4. Review build logs for specific errors
5. Try building without cache: `docker build --no-cache ...`

### Raspberry Pi Specific Issues

**Problem**: Build fails on Raspberry Pi

**Solutions**:
1. Use pre-built images from GHCR (recommended)
2. Ensure sufficient disk space: `df -h`
3. Check memory: `free -h`
4. Use `--platform linux/arm64` explicitly
5. Consider building on more powerful machine and pushing

## Updating Services

### Update to Latest Images

```bash
# Pull latest images
docker compose pull

# Restart services
docker compose up -d

# Or force recreate
docker compose up -d --force-recreate
```

### Update Specific Service

```bash
# Pull specific service
docker compose pull health_svc

# Restart specific service
docker compose up -d --no-deps health_svc
```

### Rollback to Previous Version

```bash
# Edit .env file to use previous tag
HEALTH_SVC_TAG=v1.0.0

# Pull and restart
docker compose pull
docker compose up -d
```

## Data Backup and Restore

### Backup Volumes

```bash
# Backup database
docker run --rm -v health-bot_health_svc_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/health_svc_data_$(date +%Y%m%d).tar.gz -C /data .

# Backup uploads
docker run --rm -v health-bot_health_svc_uploads:/data -v $(pwd):/backup \
  alpine tar czf /backup/health_svc_uploads_$(date +%Y%m%d).tar.gz -C /data .
```

### Restore Volumes

```bash
# Restore database
docker run --rm -v health-bot_health_svc_data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/health_svc_data_YYYYMMDD.tar.gz -C /data

# Restore uploads
docker run --rm -v health-bot_health_svc_uploads:/data -v $(pwd):/backup \
  alpine tar xzf /backup/health_svc_uploads_YYYYMMDD.tar.gz -C /data
```

## Monitoring

### View Service Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f health_svc

# Last 100 lines
docker compose logs --tail=100 health_svc
```

### Check Service Status

```bash
# Service status
docker compose ps

# Resource usage
docker stats

# Service health
docker compose ps --format "table {{.Name}}\t{{.Status}}"
```

### Access Services

- **API**: http://localhost:8000/docs
- **Flower**: http://localhost:5555
- **Health Check**: http://localhost:8000/

## Production Considerations

1. **Use Specific Tags**: Replace `latest` with version tags
2. **Enable Logging**: Configure log rotation and aggregation
3. **Set Resource Limits**: Add CPU/memory limits in docker-compose.yml
4. **Use Secrets Management**: Consider Docker secrets or external secret managers
5. **Enable Monitoring**: Add Prometheus, Grafana, or similar
6. **Regular Backups**: Automate database backups
7. **Security Scanning**: Regularly scan images for vulnerabilities
8. **Network Security**: Use reverse proxy (nginx/traefik) with SSL/TLS





