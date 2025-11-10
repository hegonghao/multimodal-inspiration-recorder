#!/usr/bin/env python3
"""Test API response format"""
import asyncio
import httpx

async def test_api():
    async with httpx.AsyncClient() as client:
        # Test list endpoint
        response = await client.get('http://localhost:8000/api/v1/records?page=1&page_size=5')
        data = response.json()

        print(f"Total records: {data['pagination']['total_count']}")
        print(f"\nFirst 3 records:")
        print("=" * 80)

        for r in data['data'][:3]:
            print(f"\nID: {r['id']}")
            print(f"Title: {r['title'][:50]}")
            print(f"Category Tags: {r['category_tags']}")
            print(f"Summary: {r['summary'][:50] if r['summary'] else None}...")
            print(f"AI Status: {r['ai_processing_status']}")

if __name__ == "__main__":
    asyncio.run(test_api())
