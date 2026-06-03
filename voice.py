import os
import sys
import queue
import time
import speech_recognition as sr
import config

class VoicePipeline:
    def __init__(self, gui_queue=None):
        self.gui_queue = gui_queue
        self.cmd_queue = queue.Queue()
        self.voice_muted = False
        self.pref_lang = "en"  # Default preferred language
        
        import threading
        self.stop_speech_event = threading.Event()
        self.current_alias = None
        
        self.mic_ready = False
        self.is_calibrating = False
        
        self.tts_engine = None
        self.use_sapi = False

        # Initialize local offline TTS fallback
        if sys.platform == "win32":
            try:
                import win32com.client
                self.tts_engine = win32com.client.Dispatch("SAPI.SpVoice")
                self.use_sapi = True
                self._configure_sapi()
                print("[+] Native Windows TTS (SAPI5) offline fallback active.")
            except Exception as e:
                print(f"[!] Warning: Native Windows SAPI5 initialization failed: {e}")
                self.use_sapi = False

        if not self.use_sapi:
            try:
                import pyttsx3
                self.tts_engine = pyttsx3.init()
                self._configure_pyttsx3()
                print("[+] Cross-platform TTS (pyttsx3) offline fallback active.")
            except Exception as e:
                print(f"[!] Warning: Failed to initialize offline TTS fallback: {e}")
                self.tts_engine = None

        # Initialize Speech-to-Text
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.energy_threshold = 300  # Voice sensitivity
        
        self.mic = None
        try:
            self.mic = sr.Microphone()
            print("[+] Microphone initialized successfully.")
        except Exception as e:
            print(f"[!] Warning: Microphone not detected or unavailable: {e}")
            if self.gui_queue:
                self.gui_queue.put(("log", "[!] Warning: Microphone not detected or unavailable. Keyboard mode active."))

    def _configure_sapi(self):
        """Configure SAPI5 settings for offline fallback."""
        if not self.tts_engine:
            return
        self.tts_engine.Volume = int(config.VOICE_VOLUME * 100)
        sapi_rate = (config.VOICE_RATE - 150) // 10
        self.tts_engine.Rate = max(-10, min(10, sapi_rate))
        
        voices = self.tts_engine.GetVoices()
        selected_index = 0
        for i in range(voices.Count):
            desc = voices.Item(i).GetDescription().lower()
            if config.VOICE_GENDER == "male" and "david" in desc:
                selected_index = i
                break
            elif config.VOICE_GENDER == "female" and "zira" in desc:
                selected_index = i
                break
        if voices.Count > 0:
            self.tts_engine.Voice = voices.Item(selected_index)

    def _configure_pyttsx3(self):
        """Configure pyttsx3 settings."""
        if not self.tts_engine:
            return
        self.tts_engine.setProperty('rate', config.VOICE_RATE)
        self.tts_engine.setProperty('volume', config.VOICE_VOLUME)

    def stop_speaking(self):
        """Immediately interrupt and stop any active speech synthesis."""
        self.stop_speech_event.set()
        if self.current_alias:
            try:
                import ctypes
                ctypes.windll.winmm.mciSendStringW(f"stop {self.current_alias}", None, 0, 0)
                ctypes.windll.winmm.mciSendStringW(f"close {self.current_alias}", None, 0, 0)
            except Exception:
                pass
            self.current_alias = None
        if self.tts_engine:
            try:
                if self.use_sapi:
                    self.tts_engine.Speak("", 2)  # SVSFPurgeBeforeSpeak
                else:
                    self.tts_engine.stop()
            except Exception:
                pass
        if self.gui_queue:
            self.gui_queue.put(("status", "STANDBY"))

    def _start_interrupt_listener(self):
        """Start a background listener to detect interrupt voice commands while speaking."""
        if not self.mic or not getattr(self, "mic_ready", False) or getattr(self, "is_calibrating", False):
            return None

        def callback(recognizer, audio):
            try:
                # Recognize English using Google API
                phrase = recognizer.recognize_google(audio, language="en-IN").strip().lower()
                if any(w in phrase for w in ["skip it", "skip", "stop speaking", "stop", "shutup", "quiet"]):
                    print(f"\n[!] Voice Interrupt Detected: '{phrase}'. Halting speech.")
                    self.stop_speaking()
                    return
            except Exception:
                pass

            try:
                # Recognize Gujarati using Google API
                phrase_gu = recognizer.recognize_google(audio, language="gu-IN").strip().lower()
                if any(w in phrase_gu for w in ["સ્કીપ", "શાંત થાઓ", "બંધ કર"]):
                    print(f"\n[!] Voice Interrupt Detected (Gujarati): '{phrase_gu}'. Halting speech.")
                    self.stop_speaking()
                    return
            except Exception:
                pass

        try:
            # Start background thread (limit phrase time to 2 seconds for quick response)
            stop_listening = self.recognizer.listen_in_background(self.mic, callback, phrase_time_limit=2)
            return stop_listening
        except Exception as e:
            print(f"[!] Warning: Failed to start background voice interrupt listener: {e}")
            return None

    def speak(self, text: str):
        """Output text to console and synthesize speech in English or Gujarati."""
        print(f"\nJARVIS: {text}")
        if not text.strip():
            return

        self.stop_speech_event.clear()

        if self.gui_queue:
            self.gui_queue.put(("status", "SPEAKING"))
            self.gui_queue.put(("response", text))

        if self.voice_muted:
            if self.gui_queue:
                self.gui_queue.put(("status", "STANDBY"))
            return

        # Check if text contains Gujarati unicode characters (\u0a80 to \u0aff)
        is_gujarati = any('\u0a80' <= char <= '\u0aff' for char in text)
        lang_code = 'gu' if is_gujarati else 'en'

        if self.stop_speech_event.is_set():
            if self.gui_queue:
                self.gui_queue.put(("status", "STANDBY"))
            return

        # Start voice interrupt listener in background
        stop_listening = self._start_interrupt_listener()

        try:
            # Try Google TTS for premium natural bilingual speech
            try:
                from gtts import gTTS
                import ctypes
                
                # Generate unique path and alias based on timestamp to avoid WinError 32 resource locks
                timestamp = int(time.time() * 1000)
                temp_filename = f"temp_speech_{timestamp}.mp3"
                temp_path = os.path.abspath(temp_filename)
                alias = f"speech_alias_{timestamp}"
                
                # Generate the TTS file
                tts = gTTS(text=text, lang=lang_code, slow=False)
                tts.save(temp_path)
                
                if self.stop_speech_event.is_set():
                    if os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except Exception:
                            pass
                    if self.gui_queue:
                        self.gui_queue.put(("status", "STANDBY"))
                    return

                # Play using native Windows MCI command string (non-blocking, we poll it)
                self.current_alias = alias
                ctypes.windll.winmm.mciSendStringW(f"open \"{temp_path}\" type mpegvideo alias {alias}", None, 0, 0)
                ctypes.windll.winmm.mciSendStringW(f"play {alias}", None, 0, 0)
                
                # Poll status of the alias in 0.1s increments until it stops or we are interrupted
                while not self.stop_speech_event.is_set():
                    buffer = ctypes.create_unicode_buffer(64)
                    ctypes.windll.winmm.mciSendStringW(f"status {alias} mode", buffer, 64, 0)
                    status = buffer.value.strip().lower()
                    if status != "playing":
                        break
                    time.sleep(0.1)

                # Cleanup MCI alias
                ctypes.windll.winmm.mciSendStringW(f"stop {alias}", None, 0, 0)
                ctypes.windll.winmm.mciSendStringW(f"close {alias}", None, 0, 0)
                self.current_alias = None
                
                # Delete temporary file safely
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
                    
                if self.gui_queue:
                    self.gui_queue.put(("status", "STANDBY"))
                return
            except Exception as e:
                # Fallback to local offline TTS if there's no internet connection
                print(f"[!] Online TTS error (falling back to offline system): {e}")
                if self.gui_queue:
                    self.gui_queue.put(("log", f"[!] TTS Online error: {e}"))

            # Local fallback execution
            if not self.tts_engine:
                if self.gui_queue:
                    self.gui_queue.put(("status", "STANDBY"))
                return
            try:
                if self.use_sapi:
                    if not is_gujarati:
                        if self.stop_speech_event.is_set():
                            return
                        # Speak asynchronously (flag 1 = SVSFlagsAsync)
                        self.tts_engine.Speak(text, 1)
                        # Poll SAPI status
                        while not self.stop_speech_event.is_set():
                            # RunningState = 2 is SRSEIsSpeaking
                            if self.tts_engine.Status.RunningState != 2:
                                break
                            time.sleep(0.1)
                        if self.stop_speech_event.is_set():
                            self.tts_engine.Speak("", 2) # Purge
                    else:
                        print("[!] Offline Fallback Error: Native SAPI5 cannot speak Gujarati.")
                        if self.gui_queue:
                            self.gui_queue.put(("log", "[!] SAPI5 cannot speak Gujarati offline."))
                else:
                    if not self.stop_speech_event.is_set():
                        self.tts_engine.say(text)
                        self.tts_engine.runAndWait()
            except Exception as e:
                print(f"[!] Offline TTS speech synthesis failed: {e}")
                
            if self.gui_queue:
                self.gui_queue.put(("status", "STANDBY"))
        finally:
            # Always clean up background listener thread when exiting speak
            if stop_listening:
                try:
                    stop_listening(wait_for_stop=False)
                except Exception:
                    pass

    def calibrate_microphone(self):
        """Calibrate microphone for ambient noise adjustment."""
        if not self.mic:
            return False
            
        self.is_calibrating = True
        print("[*] Calibrating microphone for ambient noise... Please stay quiet for a moment.")
        if self.gui_queue:
            self.gui_queue.put(("log", "[*] Calibrating microphone for ambient noise..."))
            
        try:
            # Wait for microphone stream to be released if busy
            import time
            start_wait = time.time()
            while getattr(self.mic, "stream", None) is not None and (time.time() - start_wait) < 2.0:
                time.sleep(0.05)
                
            with self.mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
            print("[+] Calibrated. Optimal noise threshold set.")
            if self.gui_queue:
                self.gui_queue.put(("log", "[+] Calibrated. Optimal noise threshold set."))
            self.mic_ready = True
            return True
        finally:
            self.is_calibrating = False

    def listen_speech(self, timeout=None, phrase_time_limit=8) -> tuple[str, str]:
        """Listen to the microphone and return (transcribed_text, lang_code)."""
        # 1. Check command queue first (typed inputs from GUI)
        if not self.cmd_queue.empty():
            cmd = self.cmd_queue.get()
            is_guj = any('\u0a80' <= char <= '\u0aff' for char in cmd)
            if self.gui_queue:
                self.gui_queue.put(("transcript", (cmd, "gu" if is_guj else "en")))
                self.gui_queue.put(("status", "PROCESSING"))
            return cmd, "gu" if is_guj else "en"

        # 2. If mic is unavailable, loop checking command queue
        if not self.mic:
            if self.gui_queue:
                self.gui_queue.put(("status", "STANDBY"))
            while self.cmd_queue.empty():
                time.sleep(0.1)
            cmd = self.cmd_queue.get()
            is_guj = any('\u0a80' <= char <= '\u0aff' for char in cmd)
            if self.gui_queue:
                self.gui_queue.put(("transcript", (cmd, "gu" if is_guj else "en")))
                self.gui_queue.put(("status", "PROCESSING"))
            return cmd, "gu" if is_guj else "en"

        if self.gui_queue:
            self.gui_queue.put(("status", "LISTENING"))

        # Wait for microphone stream to be released if busy
        import time
        start_wait = time.time()
        while getattr(self.mic, "stream", None) is not None and (time.time() - start_wait) < 2.0:
            time.sleep(0.05)

        with self.mic as source:
            try:
                print("\n[ Listening... ]", end="", flush=True)
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                
                # Check command queue immediately after listening (gives priority if user typed during listen)
                if not self.cmd_queue.empty():
                    cmd = self.cmd_queue.get()
                    is_guj = any('\u0a80' <= char <= '\u0aff' for char in cmd)
                    if self.gui_queue:
                        self.gui_queue.put(("transcript", (cmd, "gu" if is_guj else "en")))
                        self.gui_queue.put(("status", "PROCESSING"))
                    return cmd, "gu" if is_guj else "en"

                print("\r[ Processing... ]", end="", flush=True)
                if self.gui_queue:
                    self.gui_queue.put(("status", "PROCESSING"))
                
                # Fetch transcripts in both languages, prioritizing the preferred language
                gujarati_query = ""
                english_query = ""
                
                # Check preferred language first for efficiency and to respect selection
                if getattr(self, "pref_lang", "en") == "gu":
                    # Try Gujarati first
                    try:
                        gujarati_query = self.recognizer.recognize_google(audio, language="gu-IN").strip()
                    except Exception:
                        pass
                    
                    has_guj_chars = any('\u0a80' <= char <= '\u0aff' for char in gujarati_query)
                    if gujarati_query and has_guj_chars:
                        print(f"User (Gujarati): {gujarati_query}")
                        if self.gui_queue:
                            self.gui_queue.put(("transcript", (gujarati_query, "gu")))
                        return gujarati_query, "gu"
                        
                    # Fallback to English
                    try:
                        english_query = self.recognizer.recognize_google(audio, language="en-IN").strip()
                    except Exception:
                        pass
                        
                    if english_query:
                        print(f"User (English): {english_query}")
                        if self.gui_queue:
                            self.gui_queue.put(("transcript", (english_query, "en")))
                        return english_query, "en"
                else:
                    # Try English first
                    try:
                        english_query = self.recognizer.recognize_google(audio, language="en-IN").strip()
                    except Exception:
                        pass
                        
                    if english_query:
                        print(f"User (English): {english_query}")
                        if self.gui_queue:
                            self.gui_queue.put(("transcript", (english_query, "en")))
                        return english_query, "en"
                        
                    # Fallback to Gujarati
                    try:
                        gujarati_query = self.recognizer.recognize_google(audio, language="gu-IN").strip()
                    except Exception:
                        pass
                        
                    has_guj_chars = any('\u0a80' <= char <= '\u0aff' for char in gujarati_query)
                    if gujarati_query and has_guj_chars:
                        print(f"User (Gujarati): {gujarati_query}")
                        if self.gui_queue:
                            self.gui_queue.put(("transcript", (gujarati_query, "gu")))
                        return gujarati_query, "gu"
                
                # Clean up console line
                print("\r" + " " * 40 + "\r", end="", flush=True)
                
                if self.gui_queue:
                    self.gui_queue.put(("status", "STANDBY"))
                return "", "en"
                
            except sr.WaitTimeoutError:
                print("\r" + " " * 20 + "\r", end="", flush=True)
                if self.gui_queue:
                    self.gui_queue.put(("status", "STANDBY"))
                return "", "en"
            except sr.UnknownValueError:
                print("\r" + " " * 20 + "\r", end="", flush=True)
                if self.gui_queue:
                    self.gui_queue.put(("status", "STANDBY"))
                return "", "en"
            except sr.RequestError as e:
                print(f"\r[!] Speech recognition service error: {e}")
                if self.gui_queue:
                    self.gui_queue.put(("log", f"[!] STT service error: {e}"))
                    self.gui_queue.put(("status", "STANDBY"))
                # If in GUI mode, wait for keyboard inputs instead of input()
                while self.cmd_queue.empty():
                    time.sleep(0.1)
                cmd = self.cmd_queue.get()
                is_guj = any('\u0a80' <= char <= '\u0aff' for char in cmd)
                if self.gui_queue:
                    self.gui_queue.put(("transcript", (cmd, "gu" if is_guj else "en")))
                    self.gui_queue.put(("status", "PROCESSING"))
                return cmd, "gu" if is_guj else "en"
            except Exception as e:
                print(f"\r[!] Microphone exception: {e}")
                if self.gui_queue:
                    self.gui_queue.put(("log", f"[!] Mic error: {e}"))
                    self.gui_queue.put(("status", "STANDBY"))
                return "", "en"
