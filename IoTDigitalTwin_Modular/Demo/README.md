# Interactive demonstration

Import Shared, all nine device folders and Demo. Choose Tools > IoT Digital Twin > Generate Prefabs and Demo. The Editor generator creates the real scene at Scenes/IoT_Interactive_Demo.unity, configures the nine instances, camera, input, lights, panel and smoke-test references. Scenes/ initially contains setup documentation; no fabricated .unity file is supplied.

Press Play. Select devices 1–9 in the left panel. Gallery shows the full layout; zoom adjusts framing; hold right mouse to orbit. Automatic readings update LCD temperature/humidity, thermostat measured temperature and BACnet number once per second. Disable that toggle to inspect manually set readings. Aqara links to the blind by default; disable Connect to demo blind to exercise standalone movement.

## Manual acceptance checklist

| Device | Actions | Verify |
|---|---|---|
| Dimmer | Drag knob, scroll, short click, panel brightness/power | Shaft stays fixed except temporary inward press; angle and lamp brightness agree; off is dark |
| LCD | Plus/Minus, Mode, humidity edits, Pair | Numbers update without duplicate samples; buttons depress/recover; PAIR clears after five seconds |
| Thermostat | All five touch keys | Schedule label, three modes, setpoint ±0.5, power display ON/OFF |
| Camera | Drag head, click head, click flood, panel sliders | Head hinge stays fixed, mount stays still, tilt/yaw limits work, flood and status reflect power |
| Aqara | Hold/release Raise and Lower; cover; panel Raise/Lower/Stop; toggle link | Buttons recover; beads circulate smoothly in one mesh; cover slides; Stop holds; optional blind follows |
| Blind | Open, Close, Stop, panel 0/25/50/75/100%, rail drag | Cloth bottom stays at rail; full endpoints; roller/clutch/chain move together; Stop freezes target |
| BACnet | Face click/scroll, status click, values 0/11/42/99 | Digit patterns change, leading zero, indicator on/off; old static digits remain hidden |
| Speaker | Mute click, face drag/scroll, face click | Slider moves, red muted LEDs, active colours and volume feedback; active off dark |
| DALI | On/Off, both vertical sliders, field click/drag, three scene targets | Output lamp, numeric values, markers and presets update; all eight controls respond |

Test on Built-in and/or the pipeline used by your room. Inspect camera/chain/blind from side views and several positions. Check Console for missing references, shader errors and import warnings. Test a standalone prefab outside this scene with a camera and IoTMouseInput. Input uses trigger raycasts; unrelated room colliders can obstruct them.

## Automated Play Mode test

Choose Run API / animation self-test. It temporarily suspends automatic readings and pointer interactions, exercises controller APIs and motion, and restores saved state. Aqara is detached during its standalone check. The report is written to Application.persistentDataPath/IoT_PlayMode_Verification.json and its full path is logged in Console. Expect all checks to pass; failed checks include details. Run it once after generation and again if importer settings change. It does not test mouse gestures, shader visuals, all supported Unity versions or performance.

Unity Editor was not available when this package was created; neither scene generation nor this test has been executed here. The delivered Verification~/Offline sources/logs are separate offline checks and contain no real Unity Play Mode result.
