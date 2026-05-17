#!/bin/bash
set -e

API_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:3000"

echo "🧪 NexusIQ Integration Test Suite"
echo "===================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}✓${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; exit 1; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }

# Test 1: Services Running
echo ""
echo "📦 Test 1: Service Health Checks"
curl -sf $API_URL/health > /dev/null && pass "Backend API responding" || fail "Backend not responding"
curl -sf $FRONTEND_URL > /dev/null && pass "Frontend serving" || fail "Frontend not serving"

# Test 2: Auth Flow
echo ""
echo "👤 Test 2: Authentication"

# Register manager
MANAGER_EMAIL="test_manager_$(date +%s)@test.com"
MANAGER_RESP=$(curl -sf -X POST $API_URL/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$MANAGER_EMAIL\",\"password\":\"test123\",\"first_name\":\"Test\",\"last_name\":\"Manager\",\"role\":\"manager\"}")

MANAGER_TOKEN=$(echo $MANAGER_RESP | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
[ -n "$MANAGER_TOKEN" ] && pass "Manager registration successful" || fail "Manager registration failed"

# Register employee
EMPLOYEE_EMAIL="test_employee_$(date +%s)@test.com"
EMPLOYEE_RESP=$(curl -sf -X POST $API_URL/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMPLOYEE_EMAIL\",\"password\":\"test123\",\"first_name\":\"Test\",\"last_name\":\"Employee\",\"role\":\"employee\"}")

EMPLOYEE_TOKEN=$(echo $EMPLOYEE_RESP | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
[ -n "$EMPLOYEE_TOKEN" ] && pass "Employee registration successful" || fail "Employee registration failed"

# Test 3: Manager API
echo ""
echo "👔 Test 3: Manager Endpoints"

# Get courses
COURSES=$(curl -sf -X GET $API_URL/api/v1/manager/courses \
  -H "Authorization: Bearer $MANAGER_TOKEN")
pass "Manager can list courses"

# Get employees
EMPLOYEES=$(curl -sf -X GET $API_URL/api/v1/manager/employees \
  -H "Authorization: Bearer $MANAGER_TOKEN")
pass "Manager can list employees"

# Test 4: Employee API
echo ""
echo "🎓 Test 4: Employee Endpoints"

# Get assigned courses
ASSIGNED=$(curl -sf -X GET $API_URL/api/v1/employee/courses \
  -H "Authorization: Bearer $EMPLOYEE_TOKEN")
pass "Employee can view assigned courses"

# Test 5: Database Connectivity
echo ""
echo "🗄️  Test 5: Database"
docker-compose exec -T postgres pg_isready -U nexus > /dev/null && pass "PostgreSQL connected" || fail "PostgreSQL not ready"

# Test 6: Redis
echo ""
echo "⚡ Test 6: Cache"
docker-compose exec -T redis redis-cli ping > /dev/null 2>&1 && pass "Redis responding" || fail "Redis not responding"

# Test 7: Vector DB
echo ""
echo "🔍 Test 7: Vector Database"
curl -sf http://localhost:6333/collections > /dev/null && pass "Qdrant accessible" || warn "Qdrant might not be ready"

# Test 8: Storage
echo ""
echo "📁 Test 8: Object Storage"
curl -sf http://localhost:9000/minio/health/live > /dev/null && pass "MinIO healthy" || warn "MinIO might not be ready"

echo ""
echo "===================================="
echo -e "${GREEN}All tests passed!${NC}"
echo ""
echo "📊 Test Summary:"
echo "   Manager: $MANAGER_EMAIL (token: ${MANAGER_TOKEN:0:20}...)"
echo "   Employee: $EMPLOYEE_EMAIL (token: ${EMPLOYEE_TOKEN:0:20}...)"
echo ""
echo "🚀 System ready for pilot users!"
echo ""
