# J.A.R.V.I.S. — Agentic Laptop Control System

This project transitions your laptop automation from static if-else scripts to an **Agentic Workflow** powered by the Gemini API. Using voice activation (or console fallback), JARVIS reasons about your spoken commands, selects the correct Python-based tool, runs it, and feeds the execution output back into its cognitive layer to formulate a spoken confirmation.

---

## ⚙️ Technology Stack

1. **Cognitive Brain (LLM)**: `google-generativeai` (Gemini API) for agentic reasoning, intent classification, and tool selection.
2. **Audio Pipeline**:
   - **Speech-to-Text (STT)**: `SpeechRecognition` (using Google Web Speech API) for voice capture.
   - **Text-to-Speech (TTS)**: `pyttsx3` for local offline voice synthesis (tuned for a British Male voice).
3. **Laptop Controls**:
   - **Diagnostics**: `psutil` to fetch live CPU, RAM, and Disk metrics.
   - **Automation**: `PyAutoGUI` to capture screenshots, simulate keyboard presses, and perform mouse operations.
   - **App Launcher**: `subprocess` & `os` for launching system applications.

---

## 📂 Project Structure

- **`main.py`**: The central command run loop. Controls the transition between **Passive Standby** (listening for the wake word "Jarvis" or "J") and **Active Execution** (processing command context).
- **`agent.py`**: Configures the Gemini model, registers python tools, and feeds natural language speech through the agent's function-calling loop.
- **`tools.py`**: Defines the physical tools JARVIS can execute:
  - `get_system_diagnostics()` (SystemInfo)
  - `open_application()` (SystemControl)
  - `take_screenshot()` (SystemControl)
  - `simulate_keystroke()` (SystemControl)
  - `move_mouse_and_click()` (SystemControl)
  - `search_internet()` (WebSearch)
- **`voice.py`**: Wraps the speech recognition and speech synthesis engines. Handles ambient noise calibration and fallback to terminal text input if microphone access is unavailable.
- **`config.py`**: Reads variables from the `.env` file and defines the system instructions.
- **`.env`**: Holds local environment variables (e.g., your `GEMINI_API_KEY`).

---

## 🚀 Setup & Installation

### 1. Clone/Setup Workspace
Ensure all project files are in your desired workspace directory (e.g., `d:\JARVIS`).

### 2. Install Python Dependencies
Open PowerShell/CMD in the project folder and run:
```bash
pip install -r requirements.txt
```
> **Note for Windows Users**: PyAudio is required by the `SpeechRecognition` library to access your physical microphone. If `pip install pyaudio` fails, you can install the precompiled wheel using:
> `pip install pipwin` followed by `pipwin install pyaudio`, or download the wheel directly for your Python version from [Unofficial Windows Binaries](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio).

### 3. Add API Keys
Create or open the `.env` file in the root folder and add your Gemini API Key:
```env
GEMINI_API_KEY=AIzaSy...
```
You can generate a free Gemini API Key in seconds from [Google AI Studio](https://aistudio.google.com/).

---

## 🎙️ Operating Modes

### 💤 Passive (Standby) Mode
In passive mode, JARVIS listens in the background for the wake word **"Jarvis"** or **"J"**.
- **Standby Sleep**: Ignored audio will display in the terminal as `[Standby] Ignored audio: '...'`.
- **Inline Commands**: You can speak a direct action in one breath:  
  *🗣️ "Jarvis, open Google Chrome"*  
  JARVIS will wake up, run the command, speak the completion confirmation, and immediately go back to standby.
- **Direct Wake**: Speak just the wake word:  
  *🗣️ "Jarvis"*  
  The system will play a chime, speak *"At your service, sir"* or *"Awaiting your instructions"*, and enter **Active Mode** to listen for your next input.

### 🔥 Active Mode
In active mode, the terminal displays `[Listening...]` and JARVIS accepts any instruction directly without requiring the wake word.
- If no speech is heard for **12 seconds**, JARVIS will automatically say *"Going standby, sir"* and revert to Passive mode to save resource load.
- You can manually return to standby by saying:  
  *🗣️ "Go to sleep"*, *"Standby"*, or *"Sleep"*.
- You can terminate the entire script by saying:  
  *🗣️ "Shutdown Jarvis"* or *"Exit"*.

---

## 🛠️ Example Commands

Here are some real instructions you can give JARVIS once online:

- **System Diagnostics**:
  - *"How is my laptop doing?"*
  - *"Show me system diagnostics."*
  - *"What is my RAM usage?"*
- **App Launching**:
  - *"Open Chrome."*
  - *"Jarvis, launch VS Code."*
  - *"Open Notepad."*
- **Automation / Gui Control**:
  - *"Take a screenshot."*
  - *"Show desktop."* (Triggers simulating hotkey `win+d`)
  - *"Press enter."*
- **Web Search**:
  - *"Search the web for Python type annotations."*
  - *"Who won the last football world cup?"*
  - *"Find documentation on PyAutoGUI mouse functions."*
- **Technical/Creative Questions** (Reasoned inside Gemini's brain):
  - *"Explain the difference between a list and a tuple in Python."*
  - *"Write a quick shell script to clean up temporary files."*
