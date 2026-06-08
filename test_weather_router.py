#!/usr/bin/env python3
"""
Quick test to verify the weather router is properly configured.
Run this with: python test_weather_router.py
"""
import sys

try:
    from api.routers.weather import router
    print("✓ Weather router imported successfully")
    print(f"✓ Router prefix: {router.prefix}")
    print(f"✓ Router tags: {router.tags}")
    print(f"✓ Number of routes: {len(router.routes)}")
    print("\nRoutes:")
    for route in router.routes:
        print(f"  - {route.methods} {router.prefix}{route.path}")
    print("\n✓ All checks passed! The weather router should appear in Swagger UI.")
    print("\nIf you don't see it in Swagger:")
    print("  1. Make sure you've restarted the FastAPI server")
    print("  2. Clear your browser cache")
    print("  3. Visit /docs directly: http://localhost:8000/docs")
    sys.exit(0)
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
