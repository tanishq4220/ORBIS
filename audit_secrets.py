import subprocess
import re
from pathlib import Path

patterns = [
    (r"AWS Access Key", r"AKIA[0-9A-Z]{16}"),
    (r"Private Key", r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"),
    (r"Mongo URI with password", r"mongodb(?:\+srv)?:\/\/[^:]+:[^@]+@"),
    (r"Generic Secret", r"(?i)(?:api_key|client_secret|auth_token)\s*=\s*['\"][0-9a-zA-Z_\-]{16,}['\"]"),
]

print("=== 1. SCANNING TRACKED SOURCE FILES ===")
found_any = False
for name, pat in patterns:
    res = subprocess.run(["git", "grep", "-n", "-E", "-I", pat], capture_output=True, text=True)
    if res.stdout.strip():
        found_any = True
        print(f"[!] Alert ({name}):")
        for line in res.stdout.splitlines():
            print(f"    {line}")

if not found_any:
    print("[PASS] No exposed secrets, cloud credentials, or private keys in tracked source files.")

print("\n=== 2. SCANNING .env AND LOCAL CONFIG FILES ===")
env_files = list(Path(".").glob("**/.env*"))
for ef in env_files:
    if "node_modules" in ef.parts:
        continue
    print(f"Found env file: {ef}")
    text = ef.read_text(errors="ignore")
    for name, pat in patterns:
        m = re.findall(pat, text)
        if m:
            print(f"  [!] {name} match in {ef}: {m}")

print("\n=== 3. SCANNING GIT COMMIT HISTORY (Diffs across all commits) ===")
log = subprocess.run(["git", "log", "-p"], capture_output=True, text=True, errors="ignore").stdout
found_log = False
for name, pat in patterns:
    matches = re.findall(pat, log)
    if matches:
        found_log = True
        print(f"[!] Alert in git log ({name}): {len(matches)} matches found")

if not found_log:
    print("[PASS] No high-entropy secrets or private keys found in git commit history.")

print("\n=== 4. CHECKING .gitignore COVERAGE ===")
gi = Path(".gitignore").read_text()
for item in [".env", "*.env", "*.pem", "*.key", "credentials"]:
    present = item in gi
    print(f"Rule '{item}' in .gitignore: {present}")
