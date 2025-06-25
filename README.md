# Meshcapade Avatar Upload Tool

A Python tool for uploading avatar images to Meshcapade API and downloading body measurements.

## Prerequisites

- Python 3.13 or higher
- [uv](https://docs.astral.sh/uv/) package manager (recommended) or pip
- Meshcapade account with API credentials
- Optional: Local segmentation API for background removal (see Background Removal section)

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd meshcapade
```

### 2. Install Dependencies

Using uv (recommended):

```bash
uv sync
```

Using pip:

```bash
pip install -e .
```

### 3. Configure Environment

Create a `.env` file in the project root:

```bash
cp .env.example .env  # if example exists, or create manually
```

Add your Meshcapade credentials to `.env`:

```
USERNAME=your_meshcapade_username
PASSWORD=your_meshcapade_password
API_URL=https://api.meshcapade.com/api/v1
```

### 4. Prepare Subject Data

Create subject directories in the `data/` folder:

```
data/
├── subject_name/
│   ├── avatar.json          # Required metadata
│   ├── image1.jpg           # 4 images max
│   ├── image2.jpg
│   ├── image3.jpg
│   └── image4.jpg
```

**Required `avatar.json` format:**

```json
{
  "gender": "female",
  "height": 170.5
}
```

- `gender`: "male", "female", or "neutral"
- `height`: height in centimeters (required)
- `weight`: weight in kilograms (optional)

### 5. Run the Tool

```bash
uv run main.py
```

The tool will:

1. Show available subjects
2. Let you select a subject
3. Choose to upload new avatar or download measurements
4. Handle authentication and API calls automatically

## Features

### Avatar Upload

- Creates avatar from 4 images maximum
- Supports JPG, JPEG, PNG formats
- Automatically handles authentication
- Stores avatar ID for future reference

### Measurements Download

- Downloads body measurements when avatar processing is complete
- Converts measurements to both metric and imperial units
- Saves measurements as JSON files

## API Endpoints Used

- Authentication: `https://auth.meshcapade.com/realms/meshcapade-me/protocol/openid-connect/token`
- Avatar creation: `{API_URL}/avatars/create/from-images`
- Image upload: `{API_URL}/avatars/{id}/images`
- Start fitting: `{API_URL}/avatars/{id}/fit-to-images`
- Get avatar status: `{API_URL}/avatars/{id}`

## Troubleshooting

### Common Issues

**"USERNAME and PASSWORD must be set"**

- Ensure `.env` file exists with correct credentials
- Check that `.env` is in the project root directory

**"No test subjects found"**

- Verify `data/` directory exists with subject folders
- Each subject folder must contain `avatar.json`
- Check `avatar.json` format matches requirements

**"Avatar not ready yet"**

- Avatar processing takes time on Meshcapade servers
- Re-run the tool and select "Download measurements" to check status
- Processing state will show current status

**Image upload fails**

- Ensure images are in supported formats (JPG, JPEG, PNG)
- Check image file sizes aren't too large
- Verify internet connection
