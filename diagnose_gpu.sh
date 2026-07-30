#!/bin/bash

# GPU Diagnostic Script for Scoratis Application
# Checks all components and provides actionable recommendations

set -e

echo "========================================="
echo "  SCORATIS GPU DIAGNOSTIC REPORT"
echo "========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 1. Check GPU Hardware
echo -e "${YELLOW}[1/6] GPU Hardware${NC}"
if command -v nvidia-smi &> /dev/null; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader)
    VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader)
    echo -e "${GREEN}✓ GPU Detected: $GPU_NAME${NC}"
    echo "  VRAM: $VRAM"
else
    echo -e "${RED}✗ nvidia-smi not found${NC}"
fi
echo ""

# 2. Check PyTorch CUDA
echo -e "${YELLOW}[2/6] PyTorch CUDA Support${NC}"
BACKEND_VENV="/home/lenin/Apps Developed/Socratic-ai/backend/.venv/bin/python"

if [ -f "$BACKEND_VENV" ]; then
    TORCH_VERSION=$($BACKEND_VENV -c "import torch; print(torch.__version__)" 2>&1)
    CUDA_AVAILABLE=$($BACKEND_VENV -c "import torch; print(torch.cuda.is_available())" 2>&1)
    CUDA_VERSION=$($BACKEND_VENV -c "import torch; print(torch.version.cuda)" 2>&1)
    DEVICE_NAME=$($BACKEND_VENV -c "import torch; print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')" 2>&1)
    
    if [ "$CUDA_AVAILABLE" = "True" ]; then
        echo -e "${GREEN}✓ PyTorch: $TORCH_VERSION${NC}"
        echo -e "${GREEN}✓ CUDA Available: $CUDA_AVAILABLE (Version: $CUDA_VERSION)${NC}"
        echo "  Device: $DEVICE_NAME"
    else
        echo -e "${RED}✗ CUDA NOT available in backend venv${NC}"
    fi
else
    echo -e "${RED}✗ Backend venv not found at: $BACKEND_VENV${NC}"
fi
echo ""

# 3. Check Ollama Service
echo -e "${YELLOW}[3/6] Ollama Service${NC}"
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Ollama is running${NC}"
    
    # Check loaded models
    echo "  Loaded models:"
    ollama ps 2>/dev/null | while read line; do
        echo "    $line"
    done
    
    # Check GPU offloading
    GPU_LAYERS=$(journalctl -u ollama --no-pager -n 200 2>/dev/null | grep "offloaded.*GPU" | tail -1)
    if echo "$GPU_LAYERS" | grep -q "0/.*GPU"; then
        echo -e "${RED}✗ GPU OFFLOADING DISABLED: Models running on CPU only${NC}"
        echo "  Last log: $GPU_LAYERS"
    elif [ -z "$GPU_LAYERS" ]; then
        echo -e "${YELLOW}? GPU offloading status unclear${NC}"
    else
        echo -e "${GREEN}✓ GPU offloading detected: $GPU_LAYERS${NC}"
    fi
else
    echo -e "${RED}✗ Ollama is NOT running${NC}"
fi
echo ""

# 4. Check Ollama Environment Variables
echo -e "${YELLOW}[4/6] Ollama GPU Configuration${NC}"
if [ -f "/etc/systemd/system/ollama.service.d/override.conf" ]; then
    echo "  Systemd override.conf exists"
    grep -E "CUDA|GPU|NVIDIA" /etc/systemd/system/ollama.service.d/override.conf | while read line; do
        echo "    $line"
    done
    
    # Check if OLLAMA_NUM_GPU is set
    if grep -q "OLLAMA_NUM_GPU" /etc/systemd/system/ollama.service.d/override.conf; then
        echo -e "${GREEN}✓ OLLAMA_NUM_GPU is configured${NC}"
    else
        echo -e "${RED}✗ OLLAMA_NUM_GPU NOT set (needed to force GPU layers)${NC}"
    fi
else
    echo -e "${RED}✗ No systemd override.conf found${NC}"
fi
echo ""

# 5. Check Backend Process
echo -e "${YELLOW}[5/6] Backend Process${NC}"
BACKEND_PID=$(pgrep -f "uvicorn main:app" | head -1)
if [ -n "$BACKEND_PID" ]; then
    BACKEND_PYTHON=$(ps -p $BACKEND_PID -o cmd= | awk '{print $1}')
    echo -e "${GREEN}✓ Backend running (PID: $BACKEND_PID)${NC}"
    echo "  Python: $BACKEND_PYTHON"
    
    # Check if using correct venv
    if echo "$BACKEND_PYTHON" | grep -q "backend/.venv"; then
        echo -e "${GREEN}✓ Using backend venv${NC}"
    else
        echo -e "${RED}✗ NOT using backend venv${NC}"
    fi
else
    echo -e "${RED}✗ Backend is NOT running${NC}"
fi
echo ""

# 6. Check Cross-Encoder Reranker
echo -e "${YELLOW}[6/6] Cross-Encoder Reranker${NC}"
RERANKER_FILE="/home/lenin/Apps Developed/Socratic-ai/backend/services/reranker_service.py"
if [ -f "$RERANKER_FILE" ]; then
    if grep -q "_cross_encoder_failed = True" "$RERANKER_FILE"; then
        echo -e "${RED}✗ Cross-encoder is DISABLED${NC}"
    else
        echo -e "${GREEN}✓ Cross-encoder is enabled${NC}"
    fi
    
    if grep -q "ENABLE_CROSS_ENCODER" "$RERANKER_FILE"; then
        echo "  Can be enabled with: ENABLE_CROSS_ENCODER=true"
    fi
else
    echo -e "${RED}✗ Reranker service file not found${NC}"
fi
echo ""

# Summary and Recommendations
echo "========================================="
echo "  RECOMMENDATIONS"
echo "========================================="
echo ""
echo "To enable GPU for Ollama, run:"
echo ""
echo "  1. sudo bash -c 'cat >> /etc/systemd/system/ollama.service.d/override.conf << EOF"
echo "Environment=\"OLLAMA_NUM_GPU=99\""
echo "EOF"
echo ""
echo "  2. sudo systemctl daemon-reload"
echo "  3. sudo systemctl restart ollama"
echo ""
echo "  4. ollama pull llama3.2  # Reload model"
echo "  5. Test with a query and check: nvidia-smi"
echo ""
echo "To enable Cross-Encoder Reranker:"
echo "  export ENABLE_CROSS_ENCODER=true"
echo "  # Then restart backend"
echo ""
echo "========================================="
