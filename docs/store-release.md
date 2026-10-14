# Meta Horizon Store release (ALPHA channel)

App id `1346868381845594`, package `com.orangeteam.orangeroom`. One command builds, checks and (optionally) uploads:

```bash
tools/quest_release.sh                          # build versionCode 3, verify, print the upload command
ORANGE_VERSION_CODE=4 tools/quest_release.sh --upload --notes "UC2 curtain fix"
tools/quest_release.sh --no-build               # only re-check unity/Build/OrangeRoom-Quest3S.apk
```

## Keys (never in the repo)

`~/.config/orangeteam-keys/` on the build laptop:

- `orangeroom-release.keystore`: the upload key. Every build of the app must be signed with it; lose it and the store
  app cannot be updated. Keep a backup off this machine.
- `keystore.env`: `ORANGE_KEYSTORE`, `ORANGE_KEYSTORE_PASS`, `ORANGE_KEY_ALIAS`. `OrangeRoomQuest.Apk` reads them and clears
  the keystore path from ProjectSettings after the build, so nothing ends up in the public repo. Without `ORANGE_KEYSTORE`
  the Apk step signs with the debug key (sideload only); the script refuses to build without `keystore.env`.
- `store.env` (optional): `OCULUS_APP_SECRET=...` from Developer Dashboard > the app > Development > API.
  An exported `OCULUS_APP_SECRET` wins over the file.

## Versioning

`versionCode` must go up on every upload; the store rejects a code it has seen. The last upload was **2**, so the script
defaults to 3. Pass `ORANGE_VERSION_CODE=<n>` for the next ones and bump the default in `tools/quest_release.sh` after
each upload. `versionName` stays `1.0` (only shown to people).

## What the script checks

Through the Unity Android SDK (`aapt`, `apksigner` from build-tools 34.0.0): package name, versionCode, targetSdk 34,
v2 signature from the release key (not `CN=Android Debug`), not debuggable, `INTERNET` present (RoomBridge WebSocket),
no prohibited permissions (location, camera, phone, SMS, contacts, calendar, overlay). The uploader does its own check
on top.

## Upload

Only with `--upload`. It runs
`~/.local/opt/ovr-platform-util/ovr-platform-util upload-quest-build --app-id 1346868381845594 --app-secret "$OCULUS_APP_SECRET" --apk unity/Build/OrangeRoom-Quest3S.apk --channel ALPHA --age-group TEENS_AND_ADULTS --notes "..."`.

## Testers

1. Developer Dashboard > the app > Distribution > Release Channels > ALPHA: add testers by the email of their Meta account
   (or share the channel's invite link). They accept the email invite.
2. On the headset (same Meta account): Library > filter **My Preview Apps**,
   install. Updates to the ALPHA channel arrive like normal store updates.
3. Bridge: on the same Wi-Fi start `python3 bridge/server.py` (or `--simulate`) on the laptop. DHCP changes its address,
   so check it with `ip -4 addr`, set it on the VR test panel (-/+ per octet), press **Apply & reconnect** and look for
   `online`. If it stays on `connecting`, suspect Wi-Fi client isolation and use a phone hotspot.
