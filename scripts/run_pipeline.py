"""Run the full SolarPros pipeline via the API."""

import httpx


def main():
    base_url = "http://localhost:8000/api/v1"

    print("Starting SolarPros pipeline...")
    response = httpx.post(
        f"{base_url}/agents/pipeline/start",
        json={
            "counties": ["Los Angeles", "Orange", "San Diego", "Riverside", "San Bernardino"],
            "use_mock": True,
        },
    )
    response.raise_for_status()
    data = response.json()
    print(f"Pipeline started. Run ID: {data['id']}")
    print(f"Status: {data['status']}")
    print(f"\nCheck progress at: {base_url}/agents/pipeline/status")
    print(f"Flower dashboard: http://localhost:5555")


if __name__ == "__main__":
    main()
