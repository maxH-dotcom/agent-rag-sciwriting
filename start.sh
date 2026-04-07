#!/bin/bash
cd "$(dirname "$0")"

echo "启动后端..."
source "scw agent mvp/venv/bin/activate"
uvicorn backend.main:app --reload --port 8000 &
BACKEND_PID=$!

echo "启动前端..."
cd frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "======================================"
echo "后端: http://127.0.0.1:8000"
echo "前端: http://localhost:3000"
echo "API文档: http://127.0.0.1:8000/docs"
echo "======================================"
echo ""
echo "按 Ctrl+C 停止所有服务"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
