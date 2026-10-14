#!/usr/bin/env bash
# Meta Horizon Store release: build the release-signed APK, check it, print (or run) the ALPHA upload.
#   tools/quest_release.sh [--no-build] [--upload] [--notes "text"]
#   ORANGE_VERSION_CODE=4 tools/quest_release.sh    # versionCode must go up on every upload (last uploaded: 2)
# Keystore env: ~/.config/orangeteam-keys/keystore.env. App secret: $OCULUS_APP_SECRET or ~/.config/orangeteam-keys/store.env.
# See docs/store-release.md.
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
KEYS=$HOME/.config/orangeteam-keys
ANDROID=$HOME/Unity/Hub/Editor/2022.3.62f3/Editor/Data/PlaybackEngines/AndroidPlayer
TOOLS=$ANDROID/SDK/build-tools/34.0.0
OVR=$HOME/.local/opt/ovr-platform-util/ovr-platform-util
APP_ID=1346868381845594
APK=$ROOT/unity/Build/OrangeRoom-Quest3S.apk
export ORANGE_VERSION_CODE=${ORANGE_VERSION_CODE:-3}
export PATH=$ANDROID/OpenJDK/bin:$PATH   # apksigner needs java

build=1 upload=0 notes="OrangeRoom build $ORANGE_VERSION_CODE"
while [ $# -gt 0 ]; do
  case $1 in
    --no-build) build=0 ;;
    --upload) upload=1 ;;
    --notes) notes=$2; shift ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

fail() { echo "FAIL: $*" >&2; exit 1; }

# (a) build
if [ $build = 1 ]; then
  [ -f "$KEYS/keystore.env" ] || fail "missing $KEYS/keystore.env (ORANGE_KEYSTORE, ORANGE_KEYSTORE_PASS, ORANGE_KEY_ALIAS)"
  set -a; . "$KEYS/keystore.env"; set +a
  [ -n "${ORANGE_KEYSTORE:-}" ] && [ -n "${ORANGE_KEYSTORE_PASS:-}" ] && [ -n "${ORANGE_KEY_ALIAS:-}" ] \
    || fail "keystore.env must set ORANGE_KEYSTORE, ORANGE_KEYSTORE_PASS, ORANGE_KEY_ALIAS"
  echo "== building versionCode $ORANGE_VERSION_CODE (log: unity/Logs/Apk.log)"
  (cd "$ROOT/unity" && unity run . --editor-version 2022.3.62f3 --log-file Logs/Apk.log -- \
    -buildTarget Android -executeMethod OrangeRoomQuest.Apk)
fi

# (b) verify
[ -f "$APK" ] || fail "no APK at $APK"
echo "== verifying $APK"
badging=$("$TOOLS/aapt" dump badging "$APK")
sig=$("$TOOLS/apksigner" verify -v --print-certs "$APK" 2>/dev/null) || fail "apksigner verify failed"
grep -q "^package: name='com.orangeteam.orangeroom' " <<<"$badging" || fail "package is not com.orangeteam.orangeroom"
grep -q " versionCode='$ORANGE_VERSION_CODE' " <<<"$badging" || fail "versionCode is not $ORANGE_VERSION_CODE"
grep -q "^targetSdkVersion:'34'" <<<"$badging" || fail "targetSdkVersion is not 34"
if grep -q "^application-debuggable" <<<"$badging"; then fail "APK is debuggable"; fi
grep -q "^uses-permission: name='android.permission.INTERNET'" <<<"$badging" || fail "INTERNET permission missing (RoomBridge)"
# ponytail: Meta's prohibited list as of 2026 (location, camera, phone, SMS, contacts, calendar, overlay); the upload check is authoritative
bad=$(grep -oE "uses-permission: name='android\.permission\.(ACCESS_(COARSE|FINE|MOCK|BACKGROUND)_LOCATION|CAMERA|READ_PHONE_STATE|READ_PHONE_NUMBERS|CALL_PHONE|PROCESS_OUTGOING_CALLS|(READ|WRITE)_CALL_LOG|(READ|SEND|RECEIVE)_SMS|RECEIVE_(MMS|WAP_PUSH)|(READ|WRITE)_CONTACTS|(READ|WRITE)_CALENDAR|SYSTEM_ALERT_WINDOW)'" <<<"$badging" || true)
[ -z "$bad" ] || fail "prohibited permissions: $bad"
grep -q "Verified using v2 scheme (APK Signature Scheme v2): true" <<<"$sig" || fail "no v2 signature"
if grep -q "certificate DN: CN=Android Debug" <<<"$sig"; then fail "signed with the debug key (keystore env not picked up?)"; fi
echo "OK: com.orangeteam.orangeroom versionCode $ORANGE_VERSION_CODE, targetSdk 34, v2-signed ($(grep -m1 'certificate DN' <<<"$sig" | cut -d: -f2-)), not debuggable"

# (c) upload
cmd=("$OVR" upload-quest-build --app-id "$APP_ID" --app-secret '$OCULUS_APP_SECRET' --apk "$APK" \
  --channel ALPHA --age-group TEENS_AND_ADULTS --notes "$notes")
echo "== upload command:"; printf '%q ' "${cmd[@]:0:5}"; printf '"$OCULUS_APP_SECRET" '; printf '%q ' "${cmd[@]:6}"; echo
[ $upload = 1 ] || { echo "(not uploading; re-run with --upload)"; exit 0; }
if [ -z "${OCULUS_APP_SECRET:-}" ] && [ -f "$KEYS/store.env" ]; then set -a; . "$KEYS/store.env"; set +a; fi
[ -n "${OCULUS_APP_SECRET:-}" ] || fail "OCULUS_APP_SECRET not set: export it or put OCULUS_APP_SECRET=... in $KEYS/store.env (Developer Dashboard > your app > Development > API)"
cmd[5]=$OCULUS_APP_SECRET   # ponytail: secret is visible in ps while uploading; use the uploader's --config file if that matters
"${cmd[@]}"
