#!/usr/bin/env python3
"""
Debug script to check eWork API response structure.
"""

import asyncio
import json
import httpx

async def debug_api():
    """Check the API response structure."""
    url = "https://app.verama.com/api/public/job-requests?languages=SV&languages=EN&level=SENIOR&level=EXPERT&page=1&size=5&sort=firstDayOfApplications,DESC"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
    }
    
    async with httpx.AsyncClient(headers=headers) as client:
        response = await client.get(url)
        data = response.json()
        
        print("API Response Structure:")
        print("=" * 50)
        print(f"Status: {response.status_code}")
        print(f"Response keys: {data.keys() if isinstance(data, dict) else 'Not a dict'}")
        
        if isinstance(data, dict) and 'content' in data:
            print(f"\nNumber of jobs: {len(data['content'])}")
            if data['content']:
                print("\nFirst job structure:")
                print(json.dumps(data['content'][0], indent=2, ensure_ascii=False))
        else:
            print("\nFull response (first 500 chars):")
            print(json.dumps(data, indent=2, ensure_ascii=False)[:500])

if __name__ == "__main__":
    asyncio.run(debug_api())