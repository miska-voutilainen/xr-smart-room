# Agent prompt: get OrangeRoom onto a Meta Quest (store ALPHA channel)

Paste everything below the line into your coding agent (Claude Code, Codex, Cursor...) from the root of a clone of this
repo. It tells the agent what the release flow is, what it must never do, and the traps we already hit.

---

You are helping a member of the OrangeTeam (XR Smart-Room Twin) get the OrangeRoom VR app onto a Meta Quest 3/3S,
either by installing it as a tester or by building and uploading a new version to the Meta Horizon Store **ALPHA**
release channel. The repo is **public**: nothing secret may ever be written into it.

## Facts

- App: Meta Horizon app id `1346868381845594`, package `com.orangeteam.orangeroom`, channel `ALPHA` (invite only, not
  searchable in the store).
- Unity project: `unity/`, editor **2022.3.62f3** with Android Build Support (OpenJDK + SDK/NDK). Other versions will
  re-import and change files; do not upgrade.
- Headless build entry: `unity/Assets/Editor/OrangeRoomQuest.cs`, method `OrangeRoomQuest.Apk`. Output
  `unity/Build/OrangeRoom-Quest3S.apk`.
- Release script: `tools/quest_release.sh` (build, verify, upload). Docs: `docs/store-release.md`.
- Store requirements the APK must meet: arm64 only, targetSdk 34, `installLocation=auto`, not debuggable, v2 signature
  from the **release** key (not the Android debug key), `versionCode` higher than every previous upload, APK under 1 GB,
  no prohibited permissions (location, camera, phone, SMS, contacts, calendar, overlay). `INTERNET` must stay (the
  RoomBridge WebSocket needs it).

Read `docs/store-release.md`, `tools/quest_release.sh` and `OrangeRoomQuest.Apk` before doing anything else.

## First, ask the human which job this is

**A. "I just want the app on my headset."** No build needed. Go to section A.
**B. "I need to ship a new version."** Needs the release keystore and store access. Go to section B.

Do not guess. Ask.

## A. Install as a tester

1. The human sends the email address of the **Meta account that is logged in on their headset** to whoever manages the
   app (Developer Dashboard > the app > Distribution > Release Channels > ALPHA > add users / invite link).
2. They accept the invite email (or open the invite link) while logged into that same Meta account.
3. On the headset: Library > filter **My Preview Apps** (or search the store page from the invite link) > install.
   It will not show up in normal store search. That is expected for ALPHA.
4. Updates to ALPHA arrive like normal store updates.
5. For the live IoT link: run `python3 bridge/server.py` (or `--simulate` without real devices) on a laptop on the
   **same Wi-Fi** as the headset, then set that laptop's IP in the in-VR panel if it differs from the default.

If the app does not appear: wrong Meta account on the headset (most common), invite not accepted yet, or the headset
has not synced. Restarting the headset forces a sync.

## B. Build and upload a new version

### Prerequisites (check each, report what is missing, stop if any is missing)

1. A Meta account **verified with SMS phone number or credit/debit card** (authenticator app and PayPal do not count),
   added to the team's organization in the Meta Horizon Developer Dashboard with a role that can upload builds.
2. The release keystore `orangeroom-release.keystore` plus its store password and key alias, received **privately**
   from the keystore owner (never via the repo, issues or a public chat). Every build must be signed with this exact
   key; a different key means Meta treats it as a different app and refuses the update.
3. The app secret: Developer Dashboard > the app > Development > API. Same rules as the keystore.
4. Unity 2022.3.62f3 + Android module, and Meta's `ovr-platform-util` for the human's OS (Linux build is labeled
   experimental but works).

Keys live **outside the repo**, by default in `~/.config/orangeteam-keys/`:

- `keystore.env` with `ORANGE_KEYSTORE=/abs/path/orangeroom-release.keystore`, `ORANGE_KEYSTORE_PASS=...`,
  `ORANGE_KEY_ALIAS=...`
- `store.env` with `OCULUS_APP_SECRET=...` (or export it in the shell)

### Steps

1. **Find the next versionCode.** Look at the highest versionCode already on the dashboard (the app > Distribution >
   Release Channels / builds list) and add 1. The store rejects any code it has seen before. Do not trust the default
   in the script blindly; someone else may have uploaded since.
2. **Adapt paths if not on the original Linux laptop.** `tools/quest_release.sh` hardcodes the Unity Hub path
   (`$HOME/Unity/Hub/Editor/2022.3.62f3/...`), the `unity` CLI, and `~/.local/opt/ovr-platform-util`. On another
   machine or OS, point those at the local install. On Windows, run it in Git Bash/WSL or run the same three steps by
   hand: Unity batchmode `-buildTarget Android -executeMethod OrangeRoomQuest.Apk`, then `aapt dump badging` +
   `apksigner verify --print-certs`, then the upload command. Do not commit machine-specific paths.
3. **Build and verify without uploading:**
   `ORANGE_VERSION_CODE=<n> tools/quest_release.sh`
   It must end with `OK: com.orangeteam.orangeroom versionCode <n>, targetSdk 34, v2-signed (CN=OrangeTeam ...), not debuggable`.
   If it says "signed with the debug key", the keystore env was not picked up. Fix that; never upload a debug build.
4. **Show the human the result and get an explicit yes**, then upload:
   `ORANGE_VERSION_CODE=<n> tools/quest_release.sh --no-build --upload --notes "what changed"`
5. **Confirm** the new build shows on the dashboard under the ALPHA channel. Testers get it as an update.
6. **Before any commit**, run `git status` and `git diff` and make sure there is no keystore, `.env`, password, app
   secret, or `keystoreName` path in `unity/ProjectSettings/ProjectSettings.asset` (the build script clears it, check
   anyway). Then bump the default `ORANGE_VERSION_CODE` in `tools/quest_release.sh` and the "last upload" note in
   `docs/store-release.md` to `<n>`.

## Hard rules

- Never commit, print, paste or log the keystore, its passwords or `OCULUS_APP_SECRET`. The repo is public and search
  engines index it.
- Never generate a new keystore, change the package name or change the app id. That breaks updates for everyone.
- Only the `ALPHA` channel. Never upload to `PRODUCTION`/store review unless the whole team agreed.
- Never upload without the human's explicit confirmation in this session.
- Do not "fix" store requirements by editing Unity Player Settings in the GUI; change `OrangeRoomQuest.Apk` so the
  headless build stays reproducible.

## Traps we already hit

- **Dashboard confusion:** the build lives under Developer Dashboard > *your organization* > the app > Distribution.
  If the app is not listed, the account is not in the organization yet. The app will never appear in public store
  search; testers find it under Library > My Preview Apps.
- **Wrong account on the headset:** invites, developer mode and preview apps are all tied to the Meta account the
  headset is logged into, which is often not the one used on the laptop. Check the email on the headset first.
- **Developer mode / USB sideload (debug only):** enabling it needs the account to be in a developer organization and
  verified, then a headset restart. If `adb devices` shows nothing at all (not even `unauthorized`), developer mode is
  not active yet: re-toggle it in the Meta Horizon phone app for the right headset, reboot the headset, replug USB,
  accept the "Allow USB debugging" prompt inside the headset. Sideloading is for quick tests only; the store path does
  not need developer mode.
- **targetSdk:** Unity defaulted to 36; Meta wants 34. The build script pins 34. Leave it.
- **Debug signature:** if the keystore env vars are missing, Unity silently signs with the debug key. The verify step
  catches this.
- **"User access token is expired"** on Unity package resolve: open Unity Hub once to refresh the login, then retry.
- **Lightmaps:** the baked lighting is committed. Do not re-bake as part of a release; it takes 15 to 30 minutes on CPU
  and changes large binary files.

## Done means

- A: the app runs on the human's headset from My Preview Apps.
- B: the dashboard shows the new versionCode on ALPHA, at least one tester received the update, and the repo diff
  contains only the version bump (no secrets, no local paths).
