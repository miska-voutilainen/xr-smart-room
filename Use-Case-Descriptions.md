# XR-Smartroom: Use Case Descriptions

Derived from the XR-Smartroom use case diagram: 4 actors (Person in room, Camera, Person in VR, Temp. sensor), 6 use cases, and two «include» relationships from *Temperature alarm* to *Close / Open curtains* and *Sound speaker alarm*.

Details the diagram does not specify are marked *(assumed)*.

---

## UC-01: Dim lights

| Field | Description |
|---|---|
| **Actor** | Person in room |
| **Goal** | Lower the brightness of the room lighting to a comfortable level |
| **Preconditions** | The smart lighting system is powered on and reachable by the XR-Smartroom system |
| **Trigger** | The person issues a dim command *(assumed: voice, gesture, or app)* |
| **Main flow** | 1. The person issues the dim command.<br>2. The system interprets the command and the requested level.<br>3. The system sends the brightness value to the lights.<br>4. The lights dim to the requested level.<br>5. The system confirms the new state to the person. |
| **Alternative flow** | 2a. The command is unclear: the system asks the person to repeat it or select a level. |
| **Exception flow** | 3a. The lights do not respond: the system notifies the person that the lights are unavailable. |
| **Postconditions** | The lights are at the new brightness level |

---

## UC-02: Change light colors

| Field | Description |
|---|---|
| **Actor** | Person in room |
| **Goal** | Change the color of the room lighting to suit the person's mood or activity |
| **Preconditions** | The lights support color control and are reachable by the system |
| **Trigger** | The person selects or requests a color |
| **Main flow** | 1. The person requests a color or color scene.<br>2. The system validates the request.<br>3. The system sends the color value to the lights.<br>4. The lights change color.<br>5. The system confirms the change. |
| **Alternative flow** | 1a. The person picks a predefined scene (e.g. "relax", "focus") instead of a single color. |
| **Exception flow** | 3a. The lights do not support the requested color: the system keeps the current color and informs the person. |
| **Postconditions** | The lights display the new color |

---

## UC-03: Motion turns on lamp

| Field | Description |
|---|---|
| **Actor** | Camera (primary, automated) |
| **Goal** | Light the room automatically when someone is present |
| **Preconditions** | The camera is active and the lamp is reachable; automatic lighting is enabled *(assumed)* |
| **Trigger** | The camera detects motion in the room |
| **Main flow** | 1. The camera detects motion.<br>2. The camera sends a motion event to the system.<br>3. The system checks whether the lamp is already on.<br>4. The system switches the lamp on.<br>5. The system logs the event. |
| **Alternative flow** | 3a. The lamp is already on: the system takes no action. |
| **Exception flow** | 2a. The camera is offline: the system logs the error and the lamp stays off.<br>4a. The lamp does not respond: the system logs the failure and retries once *(assumed)*. |
| **Postconditions** | The lamp is on |
| **Notes** | Added use case (green in the diagram). A turn-off rule after no motion is not in the diagram and could be added. |

---

## UC-04: Close / Open curtains

| Field | Description |
|---|---|
| **Actors** | Person in VR (primary); Temperature alarm (via «include», see UC-05) |
| **Goal** | Close or open the room curtains, including while the person is inside the VR environment |
| **Preconditions** | The motorized curtains are reachable by the system; the VR session is active |
| **Trigger** | The person gives a curtain command in VR, or UC-05 invokes this use case |
| **Main flow** | 1. The person selects "close" or "open" in the VR interface.<br>2. The system sends the command to the curtain motor.<br>3. The curtains move to the requested position.<br>4. The system updates the VR interface to show the new curtain state. |
| **Alternative flow** | 1a. The curtains are already in the requested position: the system informs the person and does nothing. |
| **Exception flow** | 3a. The curtains are blocked or the motor fails: the system stops the motor and shows an error in VR. |
| **Postconditions** | The curtains are in the requested position |
| **Notes** | When included by UC-05, only the "close" action is used. |

---

## UC-05: Temperature alarm

| Field | Description |
|---|---|
| **Actor** | Temp. sensor (primary, automated) |
| **Goal** | Protect the room when the temperature goes out of the safe range, and warn people in it |
| **Preconditions** | The temperature sensor is active; a threshold is configured *(assumed)* |
| **Trigger** | The measured temperature exceeds the configured threshold |
| **Main flow** | 1. The sensor reports a temperature reading.<br>2. The system compares it with the threshold.<br>3. The threshold is exceeded, so the system raises a temperature alarm.<br>4. The system executes **UC-04: Close curtains** «include».<br>5. The system executes **UC-06: Sound speaker alarm** «include».<br>6. The system logs the alarm. |
| **Alternative flow** | 2a. The reading is within the safe range: no alarm is raised. |
| **Exception flow** | 1a. The sensor returns invalid data or goes offline: the system logs a fault and notifies the user.<br>4a. The curtains cannot close: the system continues with step 5 so the alarm still sounds. |
| **Postconditions** | The alarm is active, the curtains are closed, and the speaker alarm is sounding |
| **Includes** | UC-04 Close / Open curtains; UC-06 Sound speaker alarm |

---

## UC-06: Sound speaker alarm

| Field | Description |
|---|---|
| **Actor** | None directly (included by UC-05) |
| **Goal** | Alert people in the room audibly that the temperature alarm has been triggered |
| **Preconditions** | The speaker is powered on and reachable; UC-05 has raised an alarm |
| **Trigger** | UC-05 includes this use case |
| **Main flow** | 1. The system sends the alarm sound to the speaker.<br>2. The speaker plays the alarm at the defined volume.<br>3. The alarm repeats until the condition is resolved or someone acknowledges it *(assumed)*. |
| **Alternative flow** | 3a. The person acknowledges or silences the alarm: the speaker stops. |
| **Exception flow** | 2a. The speaker does not respond: the system logs the failure and shows a visual warning instead *(assumed)*. |
| **Postconditions** | The alarm is audible, or has been acknowledged and silenced |
| **Notes** | Added use case (green in the diagram). It cannot be started on its own, only through UC-05. |

---

## Points to check in the diagram

- *Person in VR* is linked only to curtains, and *Person in room* only to the lights. If both actors should be able to use all of these functions, add the missing associations.
- *Close / Open curtains* is used both as a manual use case (UC-04) and as an «include» target of the alarm. This is valid, but you may prefer to split it into "Close curtains" and "Open curtains".
