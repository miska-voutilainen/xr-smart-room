# Speaker - Sonos Roam and Google Nest

The lab has several Sonos and Google Nest speakers, all visible in [Home Assistant](home-assistant.md). The bridge uses the Sonos Roam "Office" by default, because Home Assistant can save and restore what a Sonos was playing.

| | |
|---|---|
| Default speaker | Sonos Roam "Office", 192.168.15.183 |
| Entity | `media_player.roam_2_2` |
| Path | Bridge -> Home Assistant -> speaker. Songs are streamed from the bridge PC over HTTP on port 8000 |
| Bridge name | `speaker1` |

## Speakers in the Lab

| Entity | Name | Type | Notes |
|---|---|---|---|
| `media_player.roam_2_2` | Office | Sonos Roam | Default. Often plays someone's phone over Bluetooth |
| `media_player.kitchen` | Kitchen | Sonos | |
| `media_player.googlehome6580` | Dali stand WhiteNest | Google Nest | On the DALI stand. Candidate for the UC3 alarm sound |
| `media_player.famnest2` | Sonos Stand DarkNest | Google Nest | A Nest placed at the Sonos stand |
| `media_player.home_group` | Home group | Google speaker group | |
| `media_player.nesthub371f*`, `media_player.office_display` | Nest Hub displays | Google | Unavailable when tested |

## Testing

```
python bridge/lab.py speaker status
python bridge/lab.py speaker play song.mp3 --volume 15    # local file or http(s) URL
python bridge/lab.py speaker pause                         # also: resume, stop
python bridge/lab.py speaker volume up                     # also: down, or 0-100
python bridge/lab.py speaker restore                       # Sonos: back to what played before
python bridge/lab.py speaker status --entity media_player.googlehome6580
```

Playing a song works like this:
1. **Serve the file.** `lab.py` serves the file (from the current folder or `bridge/`) over HTTP on port 8000, and the speaker downloads it from the PC. Windows Firewall must allow Python on private networks.
2. **Save the state.** On a Sonos, it saves the speaker's state (source, volume, queue) with `sonos.snapshot`.
3. **Play.** It sets the volume if `--volume` is given, then starts the song.
4. **Restore.** When the song ends, or on Ctrl+C, it puts the previous state back with `sonos.restore`. If the script is killed, run `speaker restore`.

Audio files are git-ignored.

## Bridge Server

| Sends to XR | Accepts from XR |
|---|---|
| `state` (playing, paused, idle), `volume` (0-100), `title` (song name or "Bluetooth"), `status` | `play` (file name in `bridge/`), `pause`, `resume`, `stop`, `volume_up`, `volume_down`, `set_volume` (0-100), `restore` |

The server saves the Sonos state before the first song and restores it when the song ends. `play` only accepts audio files placed directly in `bridge/`.

## Test Results

| Test | Result |
|---|---|
| Read state and volume | Works |
| Play a local mp3 at 15% on the Sonos | Works, the whole song (2:31) played |
| Restore afterwards | Works, back to the Bluetooth phone at 48% |
| Pause, resume, volume buttons | Not tested on the real speaker yet |
| Playback on a Google Nest | Not tested |

## Notes

- **Bluetooth takeover.** Playing a song switches the Sonos away from whoever is playing over Bluetooth. Use a low volume and let it restore.
- **Pausing Bluetooth.** Pausing a Bluetooth source on a Sonos may not work. Pausing our own song does.
- **Google Nest.** A Nest can't save and restore its state, so what played before is lost. Bluetooth playback on a Nest is invisible to Home Assistant; it shows "off" while playing.
- **Several connections.** While buffering, the Sonos opens several HTTP connections and drops the extras. This is normal.
- **SoundCloud.** We looked into it and didn't build it. API access is hard to get, and the streams are often in a format the speakers don't play reliably.

## In XR

- **Controls:** a virtual speaker with a play/pause button and a volume knob. Send `set_volume` at most a few times per second.
- **UC3:** sounds an alert on a temperature alarm. Not yet wired to a real speaker. Agree with the lab staff which speaker to use, for example the Nest on the DALI stand.
