
import torch
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

def test_gpu():
    print(f"CUDA Available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU Device: {torch.cuda.get_device_name(0)}")
        print(f"Current Device Index: {torch.cuda.current_device()}")
    else:
        print("CUDA NOT AVAILABLE")
        return

    print("\n--- Testing Reranker Service (Direct) ---")
    try:
        from sentence_transformers import CrossEncoder
        model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        print(f"Attempting to load {model_name} on CUDA...")
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        encoder = CrossEncoder(model_name, max_length=512, device=device)
        print(f"Reranker Model Device: {encoder.model.device}")
        
        # Test with a dummy query
        print("Testing reranking...")
        scores = encoder.predict([("What is AI?", "AI is artificial intelligence.")])
        print(f"Rerank Score: {scores}")
    except Exception as e:
        print(f"Reranker Direct Error: {e}")

    print("\n--- Testing Coqui TTS Service ---")
    try:
        from coqui_tts_service import coqui_tts_service
        # Force initialization using the correct method
        initialized = coqui_tts_service._ensure_initialized()
        print(f"Coqui TTS Initialized: {initialized}")
        if initialized and hasattr(coqui_tts_service, 'tts') and coqui_tts_service.tts:
            # Check for device attribute or similar
            device = getattr(coqui_tts_service.tts, 'device', 'unknown')
            print(f"Coqui TTS Device: {device}")
    except Exception as e:
        print(f"Coqui TTS Error: {e}")

if __name__ == "__main__":
    test_gpu()
