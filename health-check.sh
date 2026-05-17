#!/bin/bash

echo "🏥 NexusIQ Health Check"
echo "======================="

# Check if services are running
echo ""
echo "📦 Docker Services:"
docker-compose ps

# Test backend
echo ""
echo "🔧 Backend API:"
if curl -s http://localhost:8000/health > /dev/null; then
    echo "   ✅ Backend is healthy"
else
    echo "   ❌ Backend not responding"
fi

# Test frontend
echo ""
echo "🎨 Frontend:"
if curl -s http://localhost:3000 > /dev/null; then
    echo "   ✅ Frontend is serving"
else
    echo "   ❌ Frontend not responding"
fi

# Test database
echo ""
echo "🗄️  PostgreSQL:"
if docker-compose exec -T postgres pg_isready -U nexus > /dev/null 2>&1; then
    echo "   ✅ Database is ready"
else
    echo "   ❌ Database not ready"
fi

# Test Redis
echo ""
echo "⚡ Redis:"
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo "   ✅ Redis is responding"
else
    echo "   ❌ Redis not responding"
fi

echo ""
echo "🔍 For detailed logs: docker-compose logs -f"
echo ""
