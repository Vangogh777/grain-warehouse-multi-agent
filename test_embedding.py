# -*- coding: utf-8 -*-
"""Test embedding API"""
import os
import sys
import httpx

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Load .env
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

async def test_embedding():
    """Test embedding API directly"""
    print("=" * 50)
    print("Embedding API Test")
    print("=" * 50)

    glm5_key = os.getenv("GLM5_API_KEY", "")
    glm5_url = os.getenv("GLM5_BASE_URL", "")

    print(f"\nGLM5_API_KEY: {glm5_key[:20]}...")
    print(f"GLM5_BASE_URL: {glm5_url}")

    # Test embedding endpoint
    embedding_url = f"{glm5_url}/embeddings"
    print(f"\nTesting: POST {embedding_url}")

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(
                embedding_url,
                headers={
                    "Authorization": f"Bearer {glm5_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "embedding-3",
                    "input": "test text",
                }
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:500]}")
        except Exception as e:
            print(f"Error: {type(e).__name__}: {e}")

    # Also test with text-embedding-3-small
    print(f"\nTesting with text-embedding-3-small:")
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(
                embedding_url,
                headers={
                    "Authorization": f"Bearer {glm5_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "text-embedding-3-small",
                    "input": "test text",
                }
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:500]}")
        except Exception as e:
            print(f"Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_embedding())
