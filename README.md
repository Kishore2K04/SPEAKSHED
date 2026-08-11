# Voice Task Scheduler (Jarvis-style, Offline)

A fully offline, voice-controlled task reminder assistant. Wake word activated,
speaks back confirmations, supports recurring reminders, and stays fully local —
no internet, no API keys, no cloud services.

## Setup

1. Clone this repo.
2. Create a virtual environment and install dependencies:

pip install -r requirements.txt

3. Download a Vosk speech model (required, not bundled due to size):
   3. Download the **larger Vosk speech model** (required, not bundled due to size):
   - Get `vosk-model-en-us-0.22` (~1.8GB) from https://alphacephei.com/vosk/models
   - The smaller model (`vosk-model-small-en-us-0.15`) struggles to recognize
     uncommon words like the wake word — use the larger model for reliable results.
   - Extract it into this folder and rename it to `vosk-model/`
4. Edit `sites.json` to add your own LinkedIn/GitHub/portfolio links.
5. Run:

python main.py


## Usage

Say the wake word (default: **"hello"**), wait for "Yes sir?", then speak a command:

- "Remind me to buy milk tomorrow at 6 PM"
- "Remind me to take medicine every day at 9 AM"
- "List my tasks"
- "What's next"
- "Delete task 2"
- "Mark task 3 done"
- "Snooze this 10 minutes" (works right after a reminder fires, or with a task ID anytime)
- "Summarize my day"
- "Open GitHub" / "Open LinkedIn" / "Open portfolio"
- "Play lofi beats on YouTube"
- "Exit"

## Notes

- 100% offline: Vosk for speech-to-text, pyttsx3 for text-to-speech, SQLite for storage.
- No internet connection needed once the model is downloaded.
- Config lives in `config.json` (wake word, timezone, confirmation behavior).
- Site shortcuts live in `sites.json` — just add new entries as `"name": "url"`.
- Logs are written to `scheduler.log`.
- Minimizes to system tray if `pystray` is installed.
