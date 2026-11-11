"""NetraRakshak capture agent — fundus camera → screening session bridge (reference implementation).

Runs on the PC attached to the fundus camera. Most fundus cameras (and their vendor software) can export each
capture to a folder as JPEG/TIFF; vendor SDKs and DICOM (Ophthalmic Photography IOD, modality "OP") are
integrated behind the same `CaptureSource` interface (see docs/architecture.md §Camera integration).

Folder-watch mode: the technician opens a screening in NetraRakshak, copies its Screening ID into the agent
(or passes --screening), captures right eye then left eye; the agent uploads each new file to the session
with source=camera_agent. The eye is taken from the filename when it contains OD/R/RIGHT or OS/L/LEFT,
otherwise the first capture is treated as right and the second as left.

    python tools/capture_agent.py --api http://localhost:8000 --email tech@aarogya.example ^
        --watch "C:\\FundusExports" --screening <screening-uuid>

The agent never alters pixels and never decides quality; the server performs quality assessment.
Only standard library + `requests`-free urllib is used so it runs on locked-down clinic PCs.
"""
import argparse
import getpass
import json
import mimetypes
import re
import time
import urllib.request
import uuid
from pathlib import Path

EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}


class CaptureSource:
    """Interface for camera integrations. Implementations yield (path, eye_hint) for each new capture."""

    def poll(self):  # pragma: no cover - interface
        raise NotImplementedError


class FolderWatchSource(CaptureSource):
    def __init__(self, folder: Path):
        self.folder = folder
        self.seen = {p for p in folder.iterdir() if p.is_file()}

    def poll(self):
        for p in sorted(self.folder.iterdir(), key=lambda x: x.stat().st_mtime):
            if p.is_file() and p not in self.seen and p.suffix.lower() in EXTS:
                size = p.stat().st_size
                time.sleep(1.0)  # wait until the camera software finishes writing
                if p.stat().st_size != size:
                    continue
                self.seen.add(p)
                yield p, eye_from_name(p.name)


def eye_from_name(name: str):
    n = name.upper()
    if re.search(r"(^|[^A-Z])(OD|RIGHT|R)([^A-Z]|$)", n):
        return "right"
    if re.search(r"(^|[^A-Z])(OS|LEFT|L)([^A-Z]|$)", n):
        return "left"
    return None


def _req(url, data=None, headers=None, method=None):
    r = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(r, timeout=120) as resp:
        return json.loads(resp.read())


def login(api, email, password):
    return _req(f"{api}/api/auth/login", json.dumps({"email": email, "password": password}).encode(),
                {"Content-Type": "application/json"})["access_token"]


def upload(api, token, screening, eye, path: Path):
    boundary = uuid.uuid4().hex
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"source\"\r\n\r\ncamera_agent\r\n"
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{path.name}\"\r\n"
            f"Content-Type: {ctype}\r\n\r\n").encode() + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    return _req(f"{api}/api/screenings/{screening}/images/{eye}", body,
                {"Authorization": f"Bearer {token}", "Content-Type": f"multipart/form-data; boundary={boundary}"})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--email", required=True)
    ap.add_argument("--watch", required=True)
    ap.add_argument("--screening", required=True)
    a = ap.parse_args()
    token = login(a.api, a.email, getpass.getpass("NetraRakshak password: "))
    src = FolderWatchSource(Path(a.watch))
    order = ["right", "left"]
    print(f"Watching {a.watch}. Capture the RIGHT eye first, then the LEFT eye. Ctrl+C to stop.")
    while True:
        for path, hint in src.poll():
            eye = hint or (order.pop(0) if order else None)
            if not eye:
                print(f"Skipping {path.name}: both eyes already captured (name the file with OD/OS to replace)")
                continue
            res = upload(a.api, token, a.screening, eye, path)
            print(f"{eye:>5} eye ← {path.name}: quality {res['quality_verdict']} — {res['quality']['summary']}")
        time.sleep(2)


if __name__ == "__main__":
    main()
