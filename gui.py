import os
import sys
import queue
import threading
import time
import random
import psutil
import customtkinter as ctk
from voice import VoicePipeline
from agent import JarvisAgent

# Ensure UTF-8 output encoding on Windows terminals to prevent UnicodeEncodeError
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

class JarvisWorker(threading.Thread):
    def __init__(self, voice, agent, gui, gui_queue):
        super().__init__()
        self.voice = voice
        self.agent = agent
        self.gui = gui
        self.gui_queue = gui_queue
        self.daemon = True
        self.running = True
        self.mode = "passive"
        
    def run(self):
        active_timeout = 15.0
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
        
        # 1. Calibrate microphone
        self.gui_queue.put(("log", "[*] Calibrating microphone for ambient noise..."))
        self.voice.calibrate_microphone()
        self.gui_queue.put(("log", "[+] Calibration complete."))
        
        # 2. Vocal and Log Announcement for Language Selection
        self.gui_queue.put(("status", "SPEAKING"))
        self.gui_queue.put(("log", "[*] Awaiting language selection (English or Gujarati)..."))
        
        # Prompt for language selection
        self.voice.speak(
            "Please select your preferred language."
        )
        self.gui_queue.put(("status", "LISTENING"))
        
        # Listen for verbal preference while overlay is open
        while not self.gui.lang_selected_event.is_set():
            result = self.voice.listen_speech(timeout=2, phrase_time_limit=3)
            if result:
                phrase, lang = result
                phrase_clean = phrase.lower().strip()
                if "english" in phrase_clean or "અંગ્રેજી" in phrase_clean:
                    self.gui.select_language("en")
                    break
                elif "gujarati" in phrase_clean or "ગુજરાતી" in phrase_clean or "ગુજરાત" in phrase_clean:
                    self.gui.select_language("gu")
                    break
            time.sleep(0.1)
            
        # Post selection initialization
        pref_lang = self.gui.selected_lang
        self.gui_queue.put(("log", f"[+] Preferred language initialized: {pref_lang.upper()}"))
        self.gui_queue.put(("status", "STANDBY"))
        
        while self.running:
            try:
                # 1. Handle Active Mode Timeout
                if self.mode == 'active' and self.voice.mic is not None:
                    if time.time() - last_active_time > active_timeout:
                        self.mode = 'passive'
                        self.gui_queue.put(("mode", "PASSIVE"))
                        self.gui_queue.put(("log", "[!] Timeout: Reverting to passive standby mode."))
                        if pref_lang == "gu":
                            self.voice.speak("Going standby, sir. હું સ્લીપ મોડમાં જાઉં છું.")
                        else:
                            self.voice.speak("Going standby, sir. Entering sleep mode.")
                        continue

                # 2. Listen for speech or manual typed inputs
                result = self.voice.listen_speech(timeout=4 if self.mode == 'active' else None)
                if not result:
                    continue
                phrase, lang = result
                if not phrase:
                    continue
                
                # If command is typed, it might not contain lang detail; we fallback to user's preferred lang
                if lang == "en" and pref_lang == "gu":
                    # Check if user spoke/typed in Gujarati characters
                    is_guj = any('\u0a80' <= char <= '\u0aff' for char in phrase)
                    if is_guj:
                        lang = "gu"
                
                clean_phrase = phrase.strip().lower()
                self.gui_queue.put(("log", f"Transcribed: '{phrase}' ({lang.upper()})"))
                
                # 3. State machine logic
                if self.mode == 'passive' and self.voice.mic is not None:
                    words = clean_phrase.split()
                    has_wake_word = words and (
                        words[0] in ["jarvis", "j"] or 
                        "jarvis" in clean_phrase or 
                        "જાર્વિસ" in clean_phrase or 
                        "જા રવિશ" in clean_phrase
                    )
                    has_command_trigger = any(w in clean_phrase for w in COMMAND_TRIGGER_WORDS)
                    
                    if has_wake_word or has_command_trigger:
                        self.gui_queue.put(("log", f"[+] Activation triggered (Wake: {has_wake_word}, Command: {has_command_trigger})"))
                        
                        cmd_to_process = clean_phrase
                        if has_wake_word:
                            if words[0] in ["jarvis", "j"]:
                                cmd_to_process = " ".join(words[1:])
                            else:
                                for wake in ["jarvis", "જાર્વિસ", "જા રવિશ"]:
                                    if wake in cmd_to_process:
                                        cmd_to_process = cmd_to_process.replace(wake, "").strip()
                                        
                        if cmd_to_process:
                            self.mode = 'active'
                            self.gui_queue.put(("mode", "ACTIVE"))
                            last_active_time = time.time()
                            
                            is_automation = any(w in cmd_to_process for w in [
                                "open", "launch", "run", "start", "screenshot", "press", "simulate", "click", 
                                "diagnostics", "system", "health", "ખોલો", "ચાલુ", "બંધ", "સ્ક્રીનશોટ"
                            ])
                            if is_automation:
                                if lang == "gu":
                                    self.voice.speak("ચાલુ કરું છું, સર.")
                                else:
                                    self.voice.speak("Executing, sir.")
                                    
                            self.gui_queue.put(("log", f"[*] Processing command: '{cmd_to_process}'"))
                            response = self.agent.process_command(cmd_to_process, lang)
                            self.voice.speak(response)
                            
                            # Revert to passive
                            self.mode = 'passive'
                            self.gui_queue.put(("mode", "PASSIVE"))
                        else:
                            # Wake word only, request command
                            self.mode = 'active'
                            self.gui_queue.put(("mode", "ACTIVE"))
                            last_active_time = time.time()
                            greetings_en = ["Yes, sir?", "At your service, sir.", "Online and ready, sir.", "Awaiting your instructions."]
                            greetings_gu = ["હા સર, કહો?", "હું સાંભળું છું, સર.", "આદેશ આપો, સર.", "હું તમારી સેવામાં હાજર છું, સર."]
                            self.voice.speak(random.choice(greetings_gu if lang == "gu" else greetings_en))
                    else:
                        # Ignore
                        pass
                else:
                    # Active mode or text-only fallback
                    last_active_time = time.time()
                    
                    is_exit = any(w in clean_phrase for w in ["standby", "go to sleep", "sleep", "shutdown jarvis", "exit", "બંધ", "બંધ કર", "શાંત"])
                    if is_exit:
                        if any(w in clean_phrase for w in ["shutdown jarvis", "exit", "બંધ કર", "બંધ"]):
                            if lang == "gu":
                                self.voice.speak("સેશન સમાપ્ત કરી રહ્યો છું, સર. આવજો!")
                            else:
                                self.voice.speak("Terminating system session. Goodbye, sir.")
                            self.gui_queue.put(("log", "[*] Shutting down UI..."))
                            time.sleep(2)
                            os._exit(0)
                        else:
                            self.mode = 'passive'
                            self.gui_queue.put(("mode", "PASSIVE"))
                            if lang == "gu":
                                self.voice.speak("બરાબર સર, હું ઊંઘી જાઉં છું.")
                            else:
                                self.voice.speak("Understood, entering standby mode.")
                            continue
                            
                    self.gui_queue.put(("log", f"[*] Sending active command: '{phrase}'"))
                    response = self.agent.process_command(phrase, lang)
                    self.voice.speak(response)
                    
                    if self.voice.mic is not None:
                        self.mode = 'passive'
                        self.gui_queue.put(("mode", "PASSIVE"))
            except Exception as e:
                self.gui_queue.put(("log", f"[!] Runner loop exception: {e}"))
                time.sleep(1)

class JarvisGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("J.A.R.V.I.S. System Controller HUD")
        self.geometry("1100x680")
        self.resizable(True, True)
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color="#07090e")
        
        # Communications and Events
        self.gui_queue = queue.Queue()
        self.lang_selected_event = threading.Event()
        self.selected_lang = "en"  # Default fallback
        
        # Initialize Backend Components
        self.voice = VoicePipeline(self.gui_queue)
        self.agent = JarvisAgent()
        
        # GUI Layout Construction (Grid Layout)
        self.grid_columnconfigure(0, weight=1) # Sidebar controls
        self.grid_columnconfigure(1, weight=3) # Center Console HUD
        self.grid_columnconfigure(2, weight=2) # Scrolling Diagnostic logs
        self.grid_rowconfigure(0, weight=1)
        
        self.create_sidebar()
        self.create_console()
        self.create_logs_panel()
        self.create_language_overlay()
        
        # Start Worker Thread
        self.worker = JarvisWorker(self.voice, self.agent, self, self.gui_queue)
        self.worker.start()
        
        # Start GUI polling queue
        self.after(100, self.process_queue)
        
        # Start Telemetry update
        self.update_telemetry()
        
    def create_sidebar(self):
        # Sidebar Frame - Dark Obsidian
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#0c0e12")
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.sidebar.grid_rowconfigure(11, weight=1)
        
        # Title/Logo - Cyber Cyan
        self.logo_label = ctk.CTkLabel(self.sidebar, text="J.A.R.V.I.S.", font=ctk.CTkFont(size=24, weight="bold", family="Consolas"), text_color="#00e5ff")
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        self.subtitle_label = ctk.CTkLabel(self.sidebar, text="AGENTIC SYSTEM AUTOMATION", font=ctk.CTkFont(size=10, family="Arial"), text_color="#7e8a9f")
        self.subtitle_label.grid(row=1, column=0, padx=20, pady=(0, 20))
        
        # Mode indicator - Polished Panel
        self.mode_frame = ctk.CTkFrame(self.sidebar, fg_color="#10141d", border_color="#1e293b", border_width=1, corner_radius=6)
        self.mode_frame.grid(row=2, column=0, padx=15, pady=10, sticky="ew")
        
        self.mode_title = ctk.CTkLabel(self.mode_frame, text="SYSTEM STATUS MODE:", font=ctk.CTkFont(size=10, weight="bold"), text_color="#7e8a9f")
        self.mode_title.pack(padx=10, pady=(8, 2), anchor="w")
        
        self.mode_val = ctk.CTkLabel(self.mode_frame, text="SELECTING LANGUAGE", font=ctk.CTkFont(size=14, weight="bold", family="Consolas"), text_color="#00e5ff")
        self.mode_val.pack(padx=10, pady=(0, 8), anchor="w")
        
        # Telemetry Labels
        self.telemetry_title = ctk.CTkLabel(self.sidebar, text="SYSTEM TELEMETRY", font=ctk.CTkFont(size=11, weight="bold"), text_color="#00e5ff")
        self.telemetry_title.grid(row=3, column=0, padx=20, pady=(20, 5), sticky="w")
        
        # CPU Usage Meter
        self.cpu_label = ctk.CTkLabel(self.sidebar, text="CPU Usage: 0%", font=ctk.CTkFont(size=11, weight="bold"), text_color="#f1f5f9")
        self.cpu_label.grid(row=4, column=0, padx=20, pady=(10, 2), sticky="w")
        
        self.cpu_bar = ctk.CTkProgressBar(self.sidebar, height=8, progress_color="#00d2ff", fg_color="#151c27")
        self.cpu_bar.grid(row=5, column=0, padx=20, pady=(2, 10), sticky="ew")
        self.cpu_bar.set(0.0)
        
        # RAM Usage Meter
        self.ram_label = ctk.CTkLabel(self.sidebar, text="RAM Usage: 0%", font=ctk.CTkFont(size=11, weight="bold"), text_color="#f1f5f9")
        self.ram_label.grid(row=6, column=0, padx=20, pady=(10, 2), sticky="w")
        
        self.ram_bar = ctk.CTkProgressBar(self.sidebar, height=8, progress_color="#00e676", fg_color="#151c27")
        self.ram_bar.grid(row=7, column=0, padx=20, pady=(2, 10), sticky="ew")
        self.ram_bar.set(0.0)
        
        # Controls Title
        self.controls_title = ctk.CTkLabel(self.sidebar, text="QUICK ACTIONS", font=ctk.CTkFont(size=11, weight="bold"), text_color="#00e5ff")
        self.controls_title.grid(row=8, column=0, padx=20, pady=(20, 5), sticky="w")
        
        # Wake Up Manual Button - Royal Blue Accent
        self.btn_wakeup = ctk.CTkButton(self.sidebar, text="Force Wake Up", command=self.action_wakeup, height=32, font=ctk.CTkFont(size=12, weight="bold"), fg_color="#1d4ed8", hover_color="#1e40af", text_color="#ffffff")
        self.btn_wakeup.grid(row=9, column=0, padx=15, pady=6, sticky="ew")
        
        # Toggle Sound Checkbox
        self.mute_var = ctk.BooleanVar(value=False)
        self.chk_mute = ctk.CTkCheckBox(self.sidebar, text="Mute Voice Synthesis", variable=self.mute_var, onvalue=True, offvalue=False, command=self.toggle_mute, font=ctk.CTkFont(size=11, weight="bold"), text_color="#f1f5f9", checkbox_width=18, checkbox_height=18)
        self.chk_mute.grid(row=10, column=0, padx=20, pady=20, sticky="s")
        
    def create_console(self):
        # Center Console Frame - Deep Space Background
        self.console = ctk.CTkFrame(self, corner_radius=0, fg_color="#07090e")
        self.console.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.console.grid_rowconfigure(3, weight=1)
        self.console.grid_columnconfigure(0, weight=1)
        
        # Cyber HUD Status Core - Sleek Dark Border Panel
        self.status_core = ctk.CTkFrame(self.console, fg_color="#10141d", border_color="#1e293b", border_width=1, height=100, corner_radius=12)
        self.status_core.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        self.status_core.pack_propagate(False)
        
        self.status_icon = ctk.CTkLabel(self.status_core, text="●", font=ctk.CTkFont(size=28), text_color="#00e5ff")
        self.status_icon.pack(side="left", padx=(30, 10))
        
        self.status_title = ctk.CTkLabel(self.status_core, text="SELECT LANGUAGE", font=ctk.CTkFont(size=22, weight="bold", family="Consolas"), text_color="#00e5ff")
        self.status_title.pack(side="left", pady=10)
        
        self.status_sub = ctk.CTkLabel(self.status_core, text=" - Choose English or Gujarati via screen or mic", font=ctk.CTkFont(size=12), text_color="#7e8a9f")
        self.status_sub.pack(side="left", pady=10)
        
        # User Speech Box
        self.lbl_transcript = ctk.CTkLabel(self.console, text="USER SPEECH TRANSCRIPT (BILINGUAL):", font=ctk.CTkFont(size=11, weight="bold"), text_color="#7e8a9f")
        self.lbl_transcript.grid(row=1, column=0, padx=20, pady=(5, 0), sticky="w")
        
        self.txt_transcript = ctk.CTkTextbox(self.console, height=100, font=ctk.CTkFont(size=14, family="Segoe UI"), fg_color="#10141d", border_color="#1e293b", border_width=1, corner_radius=6, text_color="#f1f5f9")
        self.txt_transcript.grid(row=1, column=0, padx=20, pady=(20, 10), sticky="ew")
        self.txt_transcript.insert("1.0", "Awaiting language selection...")
        self.txt_transcript.configure(state="disabled")
        
        # Jarvis Response Box
        self.lbl_response = ctk.CTkLabel(self.console, text="JARVIS RESPONSE:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#7e8a9f")
        self.lbl_response.grid(row=2, column=0, padx=20, pady=(5, 0), sticky="w")
        
        self.txt_response = ctk.CTkTextbox(self.console, font=ctk.CTkFont(size=15, family="Segoe UI"), fg_color="#10141d", border_color="#1e293b", border_width=1, corner_radius=6, text_color="#f1f5f9")
        self.txt_response.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")
        self.txt_response.insert("1.0", "Awaiting preferred language settings...")
        self.txt_response.configure(state="disabled")
        
        # Manual Entry Command Bar
        self.entry_frame = ctk.CTkFrame(self.console, fg_color="transparent")
        self.entry_frame.grid(row=4, column=0, padx=20, pady=20, sticky="ew")
        self.entry_frame.grid_columnconfigure(0, weight=1)
        
        self.cmd_entry = ctk.CTkEntry(self.entry_frame, placeholder_text="Type English/Gujarati command here (e.g. 'open calculator', 'તમે કેમ છો?')...", height=40, font=ctk.CTkFont(size=13), fg_color="#10141d", border_color="#1e293b", border_width=1, text_color="#f1f5f9")
        self.cmd_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.cmd_entry.bind("<Return>", self.send_manual_command)
        
        # Neon Green accent button for action
        self.btn_send = ctk.CTkButton(self.entry_frame, text="Submit Command", command=self.send_manual_command, width=130, height=40, font=ctk.CTkFont(size=12, weight="bold"), fg_color="#06b6d4", text_color="#07090e", hover_color="#0891b2")
        self.btn_send.grid(row=0, column=1, sticky="e")
        
    def create_logs_panel(self):
        # Right Logs Frame - Slate Obsidian
        self.logs_panel = ctk.CTkFrame(self, width=280, corner_radius=0, fg_color="#0c0e12")
        self.logs_panel.grid(row=0, column=2, sticky="nsew", padx=0, pady=0)
        self.logs_panel.grid_rowconfigure(1, weight=1)
        
        self.logs_title = ctk.CTkLabel(self.logs_panel, text="DIAGNOSTIC WORKFLOW LOGS", font=ctk.CTkFont(size=11, weight="bold"), text_color="#7e8a9f")
        self.logs_title.grid(row=0, column=0, padx=15, pady=(20, 10), sticky="w")
        
        self.txt_logs = ctk.CTkTextbox(self.logs_panel, font=ctk.CTkFont(size=11, family="Consolas"), fg_color="#07090e", border_color="#1e293b", border_width=1, text_color="#e2e8f0")
        self.txt_logs.grid(row=1, column=0, padx=15, pady=(0, 20), sticky="nsew")
        self.txt_logs.insert("1.0", "[*] JARVIS logging pipeline initialized.\n")
        self.txt_logs.configure(state="disabled")

    def create_language_overlay(self):
        # Create Language Selection Frame Overlay (covering everything)
        self.lang_overlay = ctk.CTkFrame(self, fg_color="#07090e")
        self.lang_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # Add labels and buttons in the overlay
        self.lang_title = ctk.CTkLabel(
            self.lang_overlay, 
            text="WELCOME TO J.A.R.V.I.S.", 
            font=ctk.CTkFont(size=26, weight="bold", family="Consolas"), 
            text_color="#00e5ff"
        )
        self.lang_title.pack(pady=(120, 10))
        
        self.lang_subtitle = ctk.CTkLabel(
            self.lang_overlay, 
            text="Please select or say your preferred language:\nમહેરબાની કરીને ભાષા પસંદ કરો અથવા માઇક પર બોલો:", 
            font=ctk.CTkFont(size=14, family="Segoe UI"), 
            text_color="#94a3b8"
        )
        self.lang_subtitle.pack(pady=20)
        
        # Buttons Container
        self.btn_frame = ctk.CTkFrame(self.lang_overlay, fg_color="transparent")
        self.btn_frame.pack(pady=20)
        
        self.btn_en = ctk.CTkButton(
            self.btn_frame, 
            text="ENGLISH\n(અંગ્રેજી)", 
            command=lambda: self.select_language("en"), 
            width=200, 
            height=80, 
            font=ctk.CTkFont(size=15, weight="bold"), 
            fg_color="#1d4ed8", 
            hover_color="#1e40af",
            text_color="#ffffff"
        )
        self.btn_en.grid(row=0, column=0, padx=20)
        
        self.btn_gu = ctk.CTkButton(
            self.btn_frame, 
            text="GUJARATI\n(ગુજરાતી)", 
            command=lambda: self.select_language("gu"), 
            width=200, 
            height=80, 
            font=ctk.CTkFont(size=15, weight="bold"), 
            fg_color="#10b981", 
            hover_color="#047857",
            text_color="#07090e"
        )
        self.btn_gu.grid(row=0, column=1, padx=20)
        
        self.lang_status = ctk.CTkLabel(
            self.lang_overlay, 
            text="[ Listening for voice choice: 'English' or 'Gujarati' / 'અંગ્રેજી' અથવા 'ગુજરાતી' ]", 
            font=ctk.CTkFont(size=11, slant="italic"), 
            text_color="#5a687c"
        )
        self.lang_status.pack(pady=40)
        
    def select_language(self, lang):
        if self.lang_selected_event.is_set():
            return
            
        self.selected_lang = lang
        self.voice.pref_lang = lang  # Set preferred language inside voice pipeline
        self.lang_selected_event.set()
        
        # Hide overlay
        self.lang_overlay.place_forget()
        
        # Update mode status and logs
        self.update_mode("PASSIVE")
        self.gui_queue.put(("log", f"[+] Preferred language initialized: {lang.upper()}"))
        
        # Speak confirmation asynchronously to prevent GUI thread freezing
        confirm_text = "ગુજરાતી ભાષા પસંદ કરવામાં આવી છે. કહો સર, હું શું મદદ કરું?" if lang == "gu" else "English language selected. How can I assist you, sir?"
        threading.Thread(target=self.voice.speak, args=(confirm_text,), daemon=True).start()
        
    def process_queue(self):
        """Poll the queue for background worker events."""
        while not self.gui_queue.empty():
            msg_type, content = self.gui_queue.get()
            if msg_type == "status":
                self.update_status(content)
            elif msg_type == "transcript":
                phrase, lang = content
                self.update_transcript(phrase, lang)
            elif msg_type == "response":
                self.update_response(content)
            elif msg_type == "log":
                self.update_log(content)
            elif msg_type == "mode":
                self.update_mode(content)
                
        self.after(100, self.process_queue)
        
    def update_status(self, status):
        status = status.upper()
        if status == "STANDBY":
            self.status_icon.configure(text_color="#00e5ff")
            self.status_title.configure(text="STANDBY MODE", text_color="#00e5ff")
            self.status_core.configure(border_color="#00e5ff")
            self.status_sub.configure(text=" - Say 'Jarvis' (જાર્વિસ) or trigger commands below")
        elif status == "LISTENING":
            self.status_icon.configure(text_color="#2979ff")
            self.status_title.configure(text="LISTENING...", text_color="#2979ff")
            self.status_core.configure(border_color="#2979ff")
            self.status_sub.configure(text=" - Speak your command into the microphone")
        elif status == "PROCESSING":
            self.status_icon.configure(text_color="#ffc400")
            self.status_title.configure(text="THINKING...", text_color="#ffc400")
            self.status_core.configure(border_color="#ffc400")
            self.status_sub.configure(text=" - Reasoning agent workflow and evaluating tools")
        elif status == "SPEAKING":
            self.status_icon.configure(text_color="#00e676")
            self.status_title.configure(text="SPEAKING...", text_color="#00e676")
            self.status_core.configure(border_color="#00e676")
            self.status_sub.configure(text=" - Synthesizing natural vocal feedback response")
            
    def update_mode(self, mode):
        mode = mode.upper()
        self.mode_val.configure(text=mode)
        if mode == "ACTIVE":
            self.mode_val.configure(text_color="#00e676")
        else:
            self.mode_val.configure(text_color="#00d2ff")
            
    def update_transcript(self, phrase, lang):
        self.txt_transcript.configure(state="normal")
        self.txt_transcript.delete("1.0", "end")
        self.txt_transcript.insert("1.0", f"[{lang.upper()}] {phrase}")
        self.txt_transcript.configure(state="disabled")
        
    def update_response(self, text):
        self.txt_response.configure(state="normal")
        self.txt_response.delete("1.0", "end")
        self.txt_response.insert("1.0", text)
        self.txt_response.configure(state="disabled")
        
    def update_log(self, text):
        self.txt_logs.configure(state="normal")
        self.txt_logs.insert("end", f"{text}\n")
        self.txt_logs.see("end")
        self.txt_logs.configure(state="disabled")
        
    def update_telemetry(self):
        """Update system metrics once per second."""
        try:
            cpu_val = psutil.cpu_percent()
            ram_val = psutil.virtual_memory().percent
            
            self.cpu_label.configure(text=f"CPU Usage: {cpu_val}%")
            self.cpu_bar.set(cpu_val / 100.0)
            
            self.ram_label.configure(text=f"RAM Usage: {ram_val}%")
            self.ram_bar.set(ram_val / 100.0)
        except Exception:
            pass
        self.after(1000, self.update_telemetry)
        
    def action_wakeup(self):
        """Forces the worker thread to go active immediately."""
        self.worker.mode = "active"
        self.update_mode("ACTIVE")
        self.gui_queue.put(("log", "[*] Manual Active Wake-up triggered."))
        self.gui_queue.put(("status", "LISTENING"))
        
    def toggle_mute(self):
        is_muted = self.mute_var.get()
        self.voice.voice_muted = is_muted
        self.gui_queue.put(("log", f"[*] Voice synthesis muted: {is_muted}"))
        
    def send_manual_command(self, event=None):
        cmd = self.cmd_entry.get().strip()
        if not cmd:
            return
            
        self.cmd_entry.delete(0, "end")
        self.gui_queue.put(("log", f"[*] GUI Command Sent: '{cmd}'"))
        
        # Intercept skip and stop commands to immediately interrupt voice synthesis
        cmd_lower = cmd.lower().strip()
        if cmd_lower in ["skip", "skip it", "stop", "quiet", "shutup", "સ્કીપ", "શાંત"]:
            self.gui_queue.put(("log", "[*] GUI: Skip command received. Stopping speech..."))
            self.voice.stop_speaking()
            return
            
        # Put in command queue for background loop to capture immediately
        self.voice.cmd_queue.put(cmd)

if __name__ == "__main__":
    app = JarvisGUI()
    app.mainloop()
