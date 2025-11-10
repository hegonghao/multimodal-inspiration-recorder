#!/bin/bash
# Quick deployment script for Docker environment variable fix
# Run this on the server after git pull

set -e  # Exit on error

echo "============================================"
echo "Docker Environment Variable Fix Deployment"
echo "============================================"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Verify .env file
echo "Step 1: Verifying .env file..."
if [ ! -f .env ]; then
    echo -e "${RED}❌ Error: .env file not found in current directory${NC}"
    echo "Please ensure you are in the project root directory"
    exit 1
fi

echo -e "${GREEN}✅ .env file found${NC}"
echo ""

# Step 2: Verify docker-compose.yml has env_file config
echo "Step 2: Verifying docker-compose.yml configuration..."
if grep -q "env_file:" docker-compose.yml; then
    echo -e "${GREEN}✅ env_file configuration found${NC}"
else
    echo -e "${RED}❌ Error: env_file configuration missing${NC}"
    echo "Please ensure you have pulled the latest code"
    exit 1
fi
echo ""

# Step 3: Test environment variable loading
echo "Step 3: Testing environment variable loading..."
echo -e "${YELLOW}Running: docker-compose config${NC}"

# Check if key variables are loaded
CONFIG_OUTPUT=$(docker-compose config 2>&1)
if echo "$CONFIG_OUTPUT" | grep -q "OPENAI_API_KEY.*sk-"; then
    echo -e "${GREEN}✅ OPENAI_API_KEY loaded correctly${NC}"
else
    echo -e "${RED}❌ OPENAI_API_KEY not loaded or empty${NC}"
    echo "Docker Compose output:"
    echo "$CONFIG_OUTPUT" | grep "OPENAI" | head -5
    exit 1
fi

if echo "$CONFIG_OUTPUT" | grep -q "OPENAI_MODEL.*gpt"; then
    echo -e "${GREEN}✅ OPENAI_MODEL loaded correctly${NC}"
else
    echo -e "${RED}❌ OPENAI_MODEL not loaded or empty${NC}"
    exit 1
fi
echo ""

# Step 4: Stop containers
echo "Step 4: Stopping existing containers..."
docker-compose down
echo -e "${GREEN}✅ Containers stopped${NC}"
echo ""

# Step 5: Optional - rebuild if code changed
read -p "Rebuild containers? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Rebuilding backend and worker..."
    docker-compose build backend worker
    echo -e "${GREEN}✅ Containers rebuilt${NC}"
else
    echo "Skipping rebuild"
fi
echo ""

# Step 6: Start services
echo "Step 6: Starting services..."
docker-compose up -d backend worker redis
sleep 5
echo -e "${GREEN}✅ Services started${NC}"
echo ""

# Step 7: Verify environment variables in container
echo "Step 7: Verifying environment variables in container..."
OPENAI_MODEL=$(docker exec inspiration-recorder-backend env | grep "^OPENAI_MODEL=" | cut -d= -f2)

if [ -z "$OPENAI_MODEL" ]; then
    echo -e "${RED}❌ OPENAI_MODEL is empty in container${NC}"
    echo "Check docker-compose logs for errors"
    exit 1
else
    echo -e "${GREEN}✅ OPENAI_MODEL in container: $OPENAI_MODEL${NC}"
fi
echo ""

# Step 8: Check logs for initialization
echo "Step 8: Checking backend initialization logs..."
sleep 3
docker-compose logs backend | tail -30 | grep -E "AI Processor|LLM|WARN" || true
echo ""

# Step 9: Optional - clear database config
echo ""
echo -e "${YELLOW}Important: If AI processing still fails, you may need to clear database configs${NC}"
read -p "Clear database API configurations now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -f clear_db_config.py ]; then
        echo "Copying script to container..."
        docker cp clear_db_config.py inspiration-recorder-backend:/app/

        echo "Clearing database configurations..."
        docker exec inspiration-recorder-backend python /app/clear_db_config.py

        echo "Restarting services..."
        docker-compose restart backend worker

        echo -e "${GREEN}✅ Database configurations cleared${NC}"
    else
        echo -e "${RED}❌ clear_db_config.py not found${NC}"
        echo "Please run this manually later"
    fi
fi
echo ""

# Final summary
echo "============================================"
echo -e "${GREEN}Deployment Complete!${NC}"
echo "============================================"
echo ""
echo "Next steps:"
echo "1. Monitor logs: docker-compose logs -f backend"
echo "2. Test voice recording on mobile app"
echo "3. Verify AI-generated titles and categories"
echo ""
echo "Troubleshooting:"
echo "- If issues persist, check DOCKER_ENV_FIX.md"
echo "- Run: docker-compose logs backend | grep LLM"
echo "- Run: docker exec inspiration-recorder-backend env | grep OPENAI"
echo ""
