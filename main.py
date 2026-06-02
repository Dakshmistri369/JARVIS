import os
import sys
import time
import random
import argparse
import config
from voice import VoicePipeline
from agent import JarvisAgent

# Ensure UTF-8 output encoding on Windows terminals to prevent UnicodeEncodeError
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def print_banner():
    banner = """
    ===============================================================
       J.A.R.V.I.S. SYSTEM AUTOMATION CONTROLLER
       Agentic System Automation Workflow V1.0 (Bilingual)
       English & Gujarati Voice Command Integration
       Integrated on Daksh Mistri's Laptop
    ===============================================================
    """
    print(banner)

def run_cli_mode():
    print_banner()
    
    # Initialize components
    print("[*] Initializing voice synthesizer (with English & Gujarati support)...")
    voice = VoicePipeline()
    
    print("[*] Initializing Gemini reasoning core...")
    agent = JarvisAgent()
    
    # Prompt user if API key is missing
    if not config.GEMINI_API_KEY:
        voice.speak(
            "Warning, sir: The Gemini API Key is missing. I will start in offline fallback mode."
        )
    
    # Calibrate microphone for ambient noise
    mic_available = voice.mic is not None
    pref_lang = "en"  # Default fallback
    
    if mic_available:
        voice.calibrate_microphone()
        # Welcoming sequence and language preference check
        voice.speak(
            "Please say English or Gujarati to select your language."
        )
        
        for attempt in range(3):
            result = voice.listen_speech(timeout=5)
            if result:
                phrase, lang = result
                phrase_clean = phrase.lower().strip()
                if "english" in phrase_clean or "અંગ્રેજી" in phrase_clean:
                    pref_lang = "en"
                    voice.speak("English language selected. At your service, sir.")
                    break
                elif "gujarati" in phrase_clean or "ગુજરાતી" in phrase_clean or "ગુજરાત" in phrase_clean:
                    pref_lang = "gu"
                    voice.speak("ગુજરાતી ભાષા પસંદ કરવામાં આવી છે. આદેશ આપો, સર.")
                    break
            print(f"[*] Attempt {attempt+1}/3 failed. Speak clearly...")
        else:
            voice.speak("Defaulting to English, sir. Starting main interface.")
            
    else:
        # No microphone available: text input mode selection
        print("\nWelcome sir. Please choose your language:")
        print("1. English (default)")
        print("2. Gujarati (ગુજરાતી)")
        choice = input("Enter choice (1 or 2): ").strip()
        pref_lang = "gu" if choice == "2" else "en"
        if pref_lang == "gu":
            voice.speak("ગુજરાતી ભાષા સેટ કરવામાં આવી છે. આદેશ આપો, સર.")
        else:
            voice.speak("English language selected. At your service, sir.")

    # State variables
    mode = config.INITIAL_MODE  # 'passive' (wake word standby) or 'active'
    active_timeout = 15.0  # Seconds to wait for command in active mode before going standby
    last_active_time = 0
    
    COMMAND_TRIGGER_WORDS = [
        # English triggers
        "open", "launch", "run", "start", "search", "find", "google",
        "take", "capture", "screenshot", "diagnostics", "system",
        "cpu", "ram", "disk", "health", "status", "who", "what",
        "how", "tell", "explain", "write", "create", "simulate", "press",
        "speak", "say", "talk", "hello", "hi", "hey", "help",
        # Gujarati triggers
        "ખોલો", "ચાલુ", "બંધ", "શોધો", "લખો", "ફોટો", "સ્ક્રીનશોટ",
        "કેમ", "કેવી", "શું", "કોણ", "બોલો", "કહો", "નમસ્તે", "હેલો",
        "મદદ", "સીપીયુ", "રેમ", "સ્થિતિ", "તબિયત"
    ]

    print(f"\n[!] System running in CLI mode. Selected language: {pref_lang.upper()}. Current mode: {mode.upper()}")
    if mic_available:
        print("[!] Say 'Jarvis' or 'J' (જાર્વિસ) to activate.")
        print("[!] Or speak directly (e.g. 'open notepad', 'નમસ્તે જાર્વિસ', 'કેમ છો').")
    else:
        print("[!] Type commands directly into the terminal.")
        
    try:
        while True:
            # 1. Handle Active Mode Timeout (return to passive mode if inactive)
            if mode == 'active' and mic_available:
                if time.time() - last_active_time > active_timeout:
                    mode = 'passive'
                    print("\n[!] Timeout: Reverting to PASSIVE mode.")
                    voice.speak("Going standby, sir. હું સ્લીપ મોડમાં જાઉં છું.")
                    continue

            # 2. Listen for speech or text input
            result = voice.listen_speech(timeout=4 if mode == 'active' else None)
            if not result or not isinstance(result, tuple):
                continue
                
            phrase, lang = result
            if not phrase:
                continue
                
            clean_phrase = phrase.strip().lower()
            
            # 3. Mode State Machine Logic
            if mode == 'passive' and mic_available:
                # Check for English/Gujarati wake words
                words = clean_phrase.split()
                has_wake_word = words and (
                    words[0] in ["jarvis", "j"] or 
                    "jarvis" in clean_phrase or 
                    "જાર્વિસ" in clean_phrase or 
                    "જા રવિશ" in clean_phrase
                )
                has_command_trigger = any(w in clean_phrase for w in COMMAND_TRIGGER_WORDS)
                
                if has_wake_word or has_command_trigger:
                    print(f"\n[+] Activation triggered! (Wake word: {has_wake_word}, Command pattern: {has_command_trigger})")
                    
                    # Extract inline command if wake word is present
                    cmd_to_process = clean_phrase
                    if has_wake_word:
                        if words[0] in ["jarvis", "j"]:
                            cmd_to_process = " ".join(words[1:])
                        else:
                            for wake in ["jarvis", "જાર્વિસ", "જા રવિશ"]:
                                if wake in cmd_to_process:
                                    cmd_to_process = cmd_to_process.replace(wake, "").strip()
                            
                    if cmd_to_process:
                        mode = 'active'
                        last_active_time = time.time()
                        
                        is_automation = any(w in cmd_to_process for w in [
                            "open", "launch", "run", "start", "screenshot", "press", "simulate", "click", 
                            "diagnostics", "system", "health", "ખોલો", "ચાલુ", "બંધ", "સ્ક્રીનશોટ"
                        ])
                        if is_automation:
                            if lang == "gu":
                                voice.speak("ચાલુ કરું છું, સર.")
                            else:
                                voice.speak("Executing, sir.")
                            
                        print(f"[*] Processing Command: '{cmd_to_process}' ({lang.upper()})")
                        response = agent.process_command(cmd_to_process, lang)
                        voice.speak(response)
                        
                        mode = 'passive'
                        print("\n[!] Command completed. Returning to PASSIVE standby.")
                    else:
                        # Wake word only: activate and greet
                        mode = 'active'
                        last_active_time = time.time()
                        greetings_en = ["Yes, sir?", "At your service, sir.", "Online and ready, sir.", "Awaiting your instructions."]
                        greetings_gu = ["હા સર, કહો?", "હું સાંભળું છું, સર.", "આદેશ આપો, સર.", "હું તમારી સેવામાં હાજર છું, સર."]
                        voice.speak(random.choice(greetings_gu if lang == "gu" else greetings_en))
                else:
                    print(f"\r[Standby] Ignored audio: '{phrase}'", end="", flush=True)
                    
            elif mode == 'active' or not mic_available:
                last_active_time = time.time()
                
                # Check for exit commands
                is_exit = any(w in clean_phrase for w in ["standby", "go to sleep", "sleep", "shutdown jarvis", "exit", "બંધ", "બંધ કર", "શાંત"])
                if is_exit:
                    if any(w in clean_phrase for w in ["shutdown jarvis", "exit", "બંધ કર", "બંધ"]):
                        if lang == "gu":
                            voice.speak("સેશન સમાપ્ત કરી રહ્યો છું, સર. આવજો!")
                        else:
                            voice.speak("Terminating system session. Goodbye, sir.")
                        print("[*] Exiting program...")
                        break
                    else:
                        mode = 'passive'
                        if lang == "gu":
                            voice.speak("બરાબર સર, હું ઊંઘી જાઉં છું.")
                        else:
                            voice.speak("Understood, entering standby mode.")
                        print("\n[!] Reverted to PASSIVE mode.")
                        continue
                
                print(f"[*] Sending to Brain: '{phrase}' ({lang.upper()})")
                response = agent.process_command(phrase, lang)
                voice.speak(response)
                
                if mic_available:
                    mode = 'passive'
                    print("\n[!] Command completed. Returning to PASSIVE standby.")
            
    except KeyboardInterrupt:
        print("\n[*] KeyboardInterrupt detected. Shutdown sequence initiated.")
        if voice:
            voice.speak("Shutting down core processors. Goodbye, sir. આવજો સર.")
        sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description="J.A.R.V.I.S. Command & Automation Agent")
    parser.add_argument("--cli", action="store_true", help="Launch in raw Command Line Interface mode instead of GUI.")
    args = parser.parse_args()
    
    if args.cli:
        run_cli_mode()
    else:
        # Launch GUI Mode
        print("[*] Launching J.A.R.V.I.S. Desktop HUD GUI...")
        try:
            from gui import JarvisGUI
            app = JarvisGUI()
            app.mainloop()
        except Exception as e:
            print(f"[!] Error starting Desktop GUI: {e}")
            print("[*] Falling back to CLI mode...")
            run_cli_mode()

if __name__ == "__main__":
    main()
