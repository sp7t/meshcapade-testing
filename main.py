import json
import mimetypes
import os
from pathlib import Path
from typing import Dict, List

import requests
from dotenv import load_dotenv

load_dotenv()

# Global configuration
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
API_URL = os.getenv("API_URL", "https://api.meshcapade.com/api/v1")

if not USERNAME or not PASSWORD:
    raise ValueError("USERNAME and PASSWORD must be set in .env file")


def authenticate() -> str:
    """Authenticate with Meshcapade and return access token."""
    url = (
        "https://auth.meshcapade.com/realms/meshcapade-me/protocol/openid-connect/token"
    )

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "password",
        "client_id": "meshcapade-me",
        "username": USERNAME,
        "password": PASSWORD,
    }

    response = requests.post(url, headers=headers, data=data)
    response.raise_for_status()
    return response.json()["access_token"]


def get_auth_headers(access_token: str) -> Dict[str, str]:
    """Get standard authorization headers."""
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }


def get_available_subjects() -> List[str]:
    """Get list of available test subjects."""
    data_dir = Path("data")
    subjects = []

    for item in data_dir.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            avatar_json = item / "avatar.json"
            if avatar_json.exists():
                subjects.append(item.name)

    return sorted(subjects)


def load_subject_data(subject_name: str) -> tuple:
    """Load subject's avatar data and image files."""
    subject_dir = Path("data") / subject_name

    # Load avatar metadata
    with open(subject_dir / "avatar.json") as f:
        avatar_data = json.load(f)

    # Validate and normalize gender
    valid_genders = ["female", "male", "neutral"]
    gender = avatar_data.get("gender", "neutral").lower()
    if gender not in valid_genders:
        print(
            f"Warning: Invalid gender '{avatar_data.get('gender')}' for {subject_name}, defaulting to 'neutral'"
        )
        gender = "neutral"
    avatar_data["gender"] = gender

    # Find image files
    image_files = []
    for ext in ["*.jpg", "*.jpeg", "*.png"]:
        image_files.extend(subject_dir.glob(ext))

    # Limit to 4 images
    image_files = image_files[:4]

    return avatar_data, image_files


def create_avatar(access_token: str) -> str:
    """Create empty avatar and return avatar ID."""
    url = f"{API_URL}/avatars/create/from-images"
    headers = get_auth_headers(access_token)

    response = requests.post(url, headers=headers)
    response.raise_for_status()

    return response.json()["data"]["id"]


def upload_images(access_token: str, avatar_id: str, image_files: List[Path]):
    """Upload all images for the avatar."""
    headers = get_auth_headers(access_token)

    for image_file in image_files:
        print(f"  Uploading {image_file.name}...")

        # Generate presigned URL
        url = f"{API_URL}/avatars/{avatar_id}/images"
        response = requests.post(url, headers=headers)
        response.raise_for_status()

        presigned_url = response.json()["data"]["links"]["upload"]

        # Upload image with correct content type
        with open(image_file, "rb") as f:
            image_content = f.read()

        # Get content type using mimetypes module
        content_type = mimetypes.guess_type(image_file)[0] or "image/jpeg"

        upload_headers = {"Content-Type": content_type}
        response = requests.put(
            presigned_url, data=image_content, headers=upload_headers
        )
        response.raise_for_status()


def start_fitting(
    access_token: str, avatar_id: str, subject_name: str, avatar_data: Dict
) -> Dict:
    """Start the fitting process and return the response."""
    url = f"{API_URL}/avatars/{avatar_id}/fit-to-images"
    headers = get_auth_headers(access_token)

    payload = {
        "avatarname": subject_name,
        "gender": avatar_data["gender"],
        "imageMode": "AFI",
    }

    # Add optional fields
    if "height" in avatar_data:
        payload["height"] = avatar_data["height"]
    if "weight" in avatar_data:
        payload["weight"] = avatar_data["weight"]

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()


def download_measurements(access_token: str, avatar_id: str, subject_name: str) -> bool:
    """Download measurements if avatar is ready."""
    url = f"{API_URL}/avatars/{avatar_id}"
    headers = get_auth_headers(access_token)

    print("Checking avatar status...")
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    avatar_data = response.json()

    # Check if avatar is ready
    if avatar_data.get("data", {}).get("attributes", {}).get("state") == "READY":
        print("✓ Avatar is ready! Downloading measurements...")

        # Extract measurements
        raw_measurements = (
            avatar_data.get("data", {})
            .get("attributes", {})
            .get("metadata", {})
            .get("bodyShape", {})
            .get("mesh_measurements", {})
        )

        if raw_measurements:
            # Convert measurements to include both units
            processed_measurements = {}
            for measurement_name, value in raw_measurements.items():
                if isinstance(value, (int, float)):
                    if measurement_name.lower() == "weight":
                        # Weight: kg to lbs conversion
                        kg_rounded = round(value, 2)
                        lbs_rounded = round(value * 2.20462, 2)
                        processed_measurements[measurement_name] = {
                            "kg": kg_rounded,
                            "lbs": lbs_rounded,
                        }
                    else:
                        # Length measurements: cm to inches conversion
                        cm_rounded = round(value, 2)
                        inches_rounded = round(value / 2.54, 2)
                        processed_measurements[measurement_name] = {
                            "cm": cm_rounded,
                            "in": inches_rounded,
                        }
                else:
                    # Keep non-numeric values as-is
                    processed_measurements[measurement_name] = value

            # Save measurements to file
            subject_dir = Path("data") / subject_name
            measurements_file = subject_dir / "measurements.json"
            with open(measurements_file, "w") as f:
                json.dump(processed_measurements, f, indent=2)
            print(f"✓ Measurements saved to {measurements_file}")
            return True
        else:
            print("❌ No measurements found in response")
            return False
    else:
        current_state = (
            avatar_data.get("data", {}).get("attributes", {}).get("state", "UNKNOWN")
        )
        print(f"❌ Avatar not ready yet. Current state: {current_state}")
        return False


def upload_avatar(
    access_token: str, selected_subject: str, avatar_data: dict, image_files: list
):
    """Upload avatar workflow."""
    # Create avatar
    print("Creating avatar...")
    avatar_id = create_avatar(access_token)
    print(f"✓ Avatar created with ID: {avatar_id}")

    # Save avatar ID to avatar.json
    subject_dir = Path("data") / selected_subject
    avatar_file = subject_dir / "avatar.json"
    avatar_data["avatar_id"] = avatar_id
    with open(avatar_file, "w") as f:
        json.dump(avatar_data, f, indent=2)
    print(f"✓ Avatar ID saved to {avatar_file}")

    # Upload images
    print("Uploading images...")
    upload_images(access_token, avatar_id, image_files)
    print(f"✓ Uploaded {len(image_files)} images")

    # Start fitting
    print("Starting fitting process...")
    start_fitting(access_token, avatar_id, selected_subject, avatar_data)
    print("✓ Fitting process started successfully")


def main():
    """Main script execution."""
    try:
        # Get available subjects
        subjects = get_available_subjects()
        if not subjects:
            print("No test subjects found in data folder!")
            return

        # Prompt user to select subject
        print("Available test subjects:")
        for i, subject in enumerate(subjects, 1):
            print(f"  {i}. {subject}")

        while True:
            try:
                choice = int(input(f"\nSelect subject (1-{len(subjects)}): ")) - 1
                if 0 <= choice < len(subjects):
                    selected_subject = subjects[choice]
                    break
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a valid number.")

        print(f"\nSelected subject: {selected_subject}")

        # Load subject data
        avatar_data, image_files = load_subject_data(selected_subject)
        print(f"Found {len(image_files)} images")
        print(f"Avatar data: {avatar_data}")

        # Check if avatar_id exists
        has_avatar_id = "avatar_id" in avatar_data

        # Present options
        print("\nWhat would you like to do?")
        if has_avatar_id:
            print("  1. Download measurements")
            print("  2. Re-upload avatar")
            valid_choices = [1, 2]
        else:
            print("  1. Upload avatar (no existing avatar found)")
            valid_choices = [1]

        while True:
            try:
                action = int(
                    input(f"\nSelect action ({'/'.join(map(str, valid_choices))}): ")
                )
                if action in valid_choices:
                    break
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a valid number.")

        # Authenticate
        print("\nAuthenticating...")
        access_token = authenticate()
        print("✓ Authenticated successfully")

        # Execute chosen action
        if has_avatar_id and action == 1:
            # Download measurements
            avatar_id = avatar_data["avatar_id"]
            success = download_measurements(access_token, avatar_id, selected_subject)
            if success:
                print(f"\n🎉 Measurements downloaded for '{selected_subject}'!")
            else:
                print(f"\n❌ Could not download measurements for '{selected_subject}'")
        else:
            # Upload avatar (either new upload or re-upload)
            upload_avatar(access_token, selected_subject, avatar_data, image_files)
            print(f"\n🎉 Avatar '{selected_subject}' uploaded and processing started!")

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    main()
