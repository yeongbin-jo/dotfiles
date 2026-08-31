# Isolated logged-in browser fallback (macOS)

Use this only when no supported browser control can reach an already authenticated Claude session
and the user has explicitly approved copying authentication state into an ephemeral profile. This
copy contains sensitive session material. Never place it in a workspace, logs, prompts, or chezmoi.
On non-macOS machines, stop at the authentication gate rather than adapting this procedure by guess.

## Launch

1. Confirm `agent-browser`, Google Chrome, `curl`, `nc`, and an existing Chrome `Default` profile.
2. Create a restrictive temporary profile and copy only the state needed by claude.ai. Do not copy
   history, saved passwords, extensions, downloads, or the whole profile.

```bash
set -euo pipefail
umask 077
chrome_source="${HOME}/Library/Application Support/Google/Chrome"
profile_dir=$(mktemp -d "${TMPDIR%/}/claude-artifact-profile.XXXXXX")
mkdir -p "$profile_dir/Default/IndexedDB"
cp "$chrome_source/Local State" "$profile_dir/Local State"
for file in Preferences 'Secure Preferences' Cookies Cookies-journal 'Web Data' 'Web Data-journal'; do
  [ ! -f "$chrome_source/Default/$file" ] || cp "$chrome_source/Default/$file" "$profile_dir/Default/$file"
done
for directory in 'Local Storage' 'Session Storage' Network; do
  [ ! -d "$chrome_source/Default/$directory" ] || cp -R "$chrome_source/Default/$directory" "$profile_dir/Default/$directory"
done
claude_indexed_db="$chrome_source/Default/IndexedDB/https_claude.ai_0.indexeddb.leveldb"
[ ! -d "$claude_indexed_db" ] || cp -R "$claude_indexed_db" "$profile_dir/Default/IndexedDB/"
chmod -R go-rwx "$profile_dir"
```

3. Choose a localhost port from a narrow private range and refuse a port that is already listening.
   Record both `profile_dir` and `cdp_port`; cleanup authority is limited to those exact values.
4. Launch a separate Chrome instance. Never close, relaunch, or add flags to the normal Chrome.

```bash
cdp_port=9223
while nc -z 127.0.0.1 "$cdp_port" 2>/dev/null; do cdp_port=$((cdp_port + 1)); done
[ "$cdp_port" -le 9299 ] || { echo "no free approved CDP port" >&2; exit 1; }
open -na 'Google Chrome' --args \
  --user-data-dir="$profile_dir" \
  --profile-directory=Default \
  --remote-debugging-address=127.0.0.1 \
  --remote-debugging-port="$cdp_port" \
  --no-first-run --no-default-browser-check --disable-sync \
  https://claude.ai/new
for attempt in $(seq 1 40); do
  nc -z 127.0.0.1 "$cdp_port" 2>/dev/null && break
  sleep 1
done
curl -fsS "http://127.0.0.1:$cdp_port/json/version" >/dev/null
agent-browser --session claude-artifact connect "$cdp_port"
```

5. Confirm authenticated Claude UI before uploading public material. If the page shows login,
   challenge, or an unexpected account, stop and clean up.

## Reliable UI sequence

- Start from the original authoring chat in update mode; use `https://claude.ai/new` only for create.
- Confirm a named HTML Artifact with Preview/Code controls after generation.
- Use the Artifact pane's `More options`, not conversation Share.
- Select `Publish artifact`, `Publish to web`, then `Publish & copy link`.
- Extract the URL from the DOM if the field truncates it. Match only
  `https://claude.ai/public/artifacts/[A-Za-z0-9_-]+`.
- A clean browser may meet an anti-bot interstitial. That is not proof of privacy; use the main
  workflow's alternate clean interactive verification.

## Cleanup

Stop duplicate Claude runs first. Close the automation session, then terminate only processes whose
command line contains the exact temporary `--user-data-dir` value. Before removing the profile,
require every condition below:

- `profile_dir` is non-empty and begins with `${TMPDIR%/}/claude-artifact-profile.`;
- it is not `/`, `${HOME}`, the Chrome source profile, or any workspace/chezmoi root;
- no process still uses it;
- the target resolves to the exact directory created in this invocation.

Remove only that directory and report that the ephemeral authentication copy was destroyed. Never
delete or alter the source Chrome profile.
