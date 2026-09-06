"""Google Places API integration for business discovery."""

import httpx
from typing import Optional

from app.config import settings


class PlacesClient:
    BASE_URL = "https://maps.googleapis.com/maps/api/place"

    def __init__(self):
        self.api_key = settings.google_places_api_key
        self.client = httpx.AsyncClient(timeout=30.0)

    async def search_businesses(
        self,
        query: str,
        location: str,
        radius_meters: int = 25000,
        business_type: Optional[str] = None,
    ) -> list[dict]:
        """Search for businesses using Google Places Text Search."""
        params = {
            "query": f"{query} in {location}",
            "key": self.api_key,
            "radius": radius_meters,
        }
        if business_type:
            params["type"] = business_type

        all_results = []
        next_page_token = None

        while True:
            if next_page_token:
                params["pagetoken"] = next_page_token
                import asyncio
                await asyncio.sleep(2)  # Google requires delay for page tokens

            response = await self.client.get(
                f"{self.BASE_URL}/textsearch/json", params=params
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") not in ("OK", "ZERO_RESULTS"):
                raise Exception(f"Places API error: {data.get('status')}")

            all_results.extend(data.get("results", []))
            next_page_token = data.get("next_page_token")

            if not next_page_token:
                break

        return all_results

    async def get_place_details(self, place_id: str) -> dict:
        """Get detailed information about a specific place."""
        params = {
            "place_id": place_id,
            "fields": "name,formatted_address,formatted_phone_number,website,"
            "rating,user_ratings_total,opening_hours,photos,reviews,"
            "geometry/location,business_status,types",
            "key": self.api_key,
        }

        response = await self.client.get(
            f"{self.BASE_URL}/details/json", params=params
        )
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "OK":
            raise Exception(f"Place details error: {data.get('status')}")

        return data.get("result", {})

    def extract_lead_data(self, place: dict, details: Optional[dict] = None) -> dict:
        """Extract lead information from a Google Places result."""
        data = details or place

        # Determine if business has a real website
        website = data.get("website")
        has_website = bool(website)
        website_placeholder = False

        if website:
            # Check for common placeholder indicators
            placeholder_domains = [
                "yelp.com", "facebook.com", "yellowpages.com",
                "mapquest.com", "bing.com", "google.com/maps",
            ]
            if any(d in website.lower() for d in placeholder_domains):
                website_placeholder = True
                has_website = False

        # Parse address components
        address = data.get("formatted_address", "")
        address_parts = [p.strip() for p in address.split(",")]

        return {
            "google_place_id": place.get("place_id"),
            "business_name": data.get("name", ""),
            "business_type": data.get("types", [None])[0] if data.get("types") else None,
            "address": address,
            "city": address_parts[-3] if len(address_parts) >= 3 else None,
            "state": address_parts[-2].strip().split()[0] if len(address_parts) >= 2 else None,
            "zip_code": address_parts[-2].strip().split()[-1] if len(address_parts) >= 2 else None,
            "phone": data.get("formatted_phone_number"),
            "website": website,
            "has_website": has_website,
            "website_placeholder": website_placeholder,
            "rating": data.get("rating"),
            "review_count": data.get("user_ratings_total"),
            "hours": data.get("opening_hours"),
            "latitude": data.get("geometry", {}).get("location", {}).get("lat"),
            "longitude": data.get("geometry", {}).get("location", {}).get("lng"),
            "services": data.get("types", []),
        }

    async def find_businesses_without_websites(
        self,
        category: str,
        city: str,
        state: str,
        radius_meters: int = 25000,
    ) -> list[dict]:
        """Main discovery method: find businesses in a category that lack websites."""
        location_query = f"{city}, {state}"
        places = await self.search_businesses(
            query=category,
            location=location_query,
            radius_meters=radius_meters,
        )

        leads = []
        for place in places:
            place_id = place.get("place_id")
            if not place_id:
                continue

            try:
                details = await self.get_place_details(place_id)
                lead_data = self.extract_lead_data(place, details)

                # Only include businesses without real websites
                if not lead_data["has_website"] or lead_data["website_placeholder"]:
                    leads.append(lead_data)
            except Exception as e:
                print(f"Error fetching details for {place.get('name')}: {e}")
                continue

        return leads

    async def close(self):
        await self.client.aclose()


# Singleton for use across the app
places_client = PlacesClient()
