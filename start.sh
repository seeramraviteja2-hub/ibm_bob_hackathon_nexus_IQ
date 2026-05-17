#!/bin/bash
set -e

echo "🚀 NexusIQ Production Setup"
echo "=============================="

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found. Install: https://docs.docker.com/compose/install/"
    exit 1
fi

# Check .env
if [ ! -f .env ]; then
    echo "📝 Creating .env from template..."
    cp .env.example .env
    echo "⚠️  IMPORTANT: Edit .env and add your ANTHROPIC_API_KEY before continuing!"
    echo "   Get one here: https://console.anthropic.com"
    read -p "Press Enter after you've added your API key..."
fi

# Validate API key
if grep -q "your-anthropic-api-key-here" .env; then
    echo "❌ Please set your real ANTHROPIC_API_KEY in .env"
    exit 1
fi

echo "🐳 Starting Docker services..."
docker-compose up -d

echo "⏳ Waiting for services to be healthy..."
sleep 10

echo "🗄️  Initializing database..."
docker-compose exec -T backend python -c "from db.session import init_db; init_db()" || true

echo ""
echo "✅ NexusIQ is running!"
echo ""
echo "📍 URLs:"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "👤 Create your first accounts at:"
echo "   http://localhost:3000/auth/register"
echo ""
echo "📊 View logs: docker-compose logs -f"
echo "🛑 Stop:      docker-compose down"
echo ""
