#!/usr/bin/env python3
import time
import json
import os
import subprocess
import urllib.request

TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO = "samake-2T2/keyboardio-preonic-zmk-config"

# Get current git commit SHA
head_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
print(f"Waiting for GitHub Actions run triggered by commit {head_sha[:7]}...")

run_id = None
for _ in range(30):
    url = f"https://api.github.com/repos/{REPO}/actions/runs?per_page=5"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"token {TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "antigravity-monitor"
        }
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for r in data.get("workflow_runs", []):
                if r.get("head_sha") == head_sha:
                    run_id = r["id"]
                    print(f"Found workflow run ID: {run_id}")
                    break
    except Exception as e:
        print(f"Error finding run: {e}")
    if run_id:
        break
    time.sleep(3)

if not run_id:
    print(f"Failed to find run for {head_sha}")
    exit(1)

print(f"Monitoring GitHub Actions Run {run_id}...")
while True:
    url = f"https://api.github.com/repos/{REPO}/actions/runs/{run_id}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"token {TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "antigravity-monitor"
        }
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            status = data.get("status")
            conclusion = data.get("conclusion")
            print(f"[{time.strftime('%H:%M:%S')}] Status: {status}, Conclusion: {conclusion}")
            if status == "completed":
                if conclusion != "success":
                    print(f"Build failed with conclusion: {conclusion}")
                    exit(1)
                break
    except Exception as e:
        print(f"Error checking run: {e}")

    time.sleep(15)

print("Build completed successfully! Fetching artifacts...")
art_url = f"https://api.github.com/repos/{REPO}/actions/runs/{run_id}/artifacts"
art_req = urllib.request.Request(
    art_url,
    headers={
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "antigravity-monitor"
    }
)
with urllib.request.urlopen(art_req) as resp:
    art_data = json.loads(resp.read().decode("utf-8"))

artifacts = art_data.get("artifacts", [])
print(f"Found {len(artifacts)} artifacts.")

firmware_art = None
for art in artifacts:
    if art["name"] == "firmware":
        firmware_art = art
        break

if not firmware_art:
    print("No artifact named 'firmware' found!")
    exit(1)

download_url = firmware_art["archive_download_url"]
print(f"Downloading artifact from {download_url}...")

os.makedirs("/tmp/firmware_v180", exist_ok=True)
zip_path = "/tmp/firmware_v180/firmware.zip"

cmd = [
    "curl", "-L",
    "-H", f"Authorization: token {TOKEN}",
    "-H", "Accept: application/vnd.github.v3+json",
    "-o", zip_path,
    download_url
]
subprocess.run(cmd, check=True)
print(f"Downloaded firmware.zip ({os.path.getsize(zip_path)} bytes)")

subprocess.run(["unzip", "-o", zip_path, "-d", "/tmp/firmware_v180/"], check=True)

os.makedirs("/root/latest_firmware", exist_ok=True)
subprocess.run("cp /tmp/firmware_v180/*.uf2 /root/latest_firmware/", shell=True, check=True)

print("Extracted UF2 files:")
for f in os.listdir("/tmp/firmware_v180"):
    if f.endswith(".uf2"):
        p = os.path.join("/tmp/firmware_v180", f)
        print(f" - {f}: {os.path.getsize(p):,} bytes")

print("All done!")
