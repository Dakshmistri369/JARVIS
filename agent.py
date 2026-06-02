import google.generativeai as genai
import config
from tools import (
    get_system_diagnostics,
    open_application,
    take_screenshot,
    simulate_keystroke,
    move_mouse_and_click,
    search_internet
)

# Configure the Google Generative AI SDK
if config.GEMINI_API_KEY:
    genai.configure(api_key=config.GEMINI_API_KEY)
else:
    # Handle missing API key gracefully
    pass

class JarvisAgent:
    def __init__(self):
        # Expose functions to the Gemini model as tools
        self.tools = [
            get_system_diagnostics,
            open_application,
            take_screenshot,
            simulate_keystroke,
            move_mouse_and_click,
            search_internet
        ]
        
        # Configure model parameters
        self.generation_config = {
            "temperature": 0.3,  # Lower temperature for precise decision making
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 1024,
        }

        self.model = None
        self.chat = None
        self.initialize_model()

    def initialize_model(self):
        """Initializes the Gemini model with tools and system instruction."""
        if not config.GEMINI_API_KEY:
            return
            
        try:
            # We use gemini-3.5-flash as it is the model configured for your API environment.
            self.model = genai.GenerativeModel(
                model_name="gemini-3.5-flash",
                tools=self.tools,
                system_instruction=config.SYSTEM_PROMPT,
                generation_config=self.generation_config
            )
            
            # Start chat session with automatic function calling enabled.
            # This allows the SDK to automatically execute functions and send the results back to the LLM.
            self.chat = self.model.start_chat(enable_automatic_function_calling=True)
            print("[+] JARVIS brain initialized successfully using Gemini.")
        except Exception as e:
            print(f"[!] Error initializing Gemini API: {e}")
            self.model = None
            self.chat = None

    def process_command(self, prompt: str, language: str = "en") -> str:
        """Sends a user command to the Gemini reasoning loop.
        
        It detects tool usage, executes matching functions, and returns JARVIS's final response.
        """
        # If Gujarati, append instructions to respond in Gujarati matching the persona
        if language == "gu":
            full_prompt = f"{prompt}\n\n(IMPORTANT: Please reply to me in Gujarati language only. Maintain the polite, witty JARVIS persona. Do not translate tool names but describe their outcome in Gujarati.)"
        else:
            full_prompt = prompt

        # If API key is missing, fall back to simple local keyword recognition or request key
        if not config.GEMINI_API_KEY or not self.chat:
            return self._fallback_local_rules(prompt, language)

        try:
            # Send message. The SDK automatically resolves tool calls and returns final LLM response
            response = self.chat.send_message(full_prompt)
            return response.text
        except Exception as e:
            print(f"[!] Gemini API request failed (e.g. quota limit, offline): {e}")
            print("[*] Falling back to local offline rules...")
            return self._fallback_local_rules(prompt, language)

    def _fallback_local_rules(self, prompt: str, language: str = "en") -> str:
        """Fallback rule-based execution if Gemini API is offline or not configured."""
        cmd = prompt.lower().strip()
        
        print("[!] Running in offline fallback mode (No API Key).")
        
        if language == "gu":
            if any(w in cmd for w in ["સિસ્ટમ", "તબિયત", "સીપીયુ", "રેમ", "સ્થિતિ", "diagnostics", "cpu", "ram"]):
                print("[*] Calling Tool [SystemInfo: get_system_diagnostics]...")
                res = get_system_diagnostics()
                return f"સિસ્ટમ ટેલિમેટ્રી પરિણામો:\n{res}\nબધું બરાબર ચાલી રહ્યું છે."
                
            # Map Gujarati phonetic app names to English command keys
            app_map_gu = {
                "નોટપેડ": "notepad",
                "ક્રોમ": "chrome",
                "કેલ્ક્યુલેટર": "calculator",
                "પેઇન્ટ": "paint",
                "વીએસ કોડ": "vscode",
                "વીએસકોડ": "vscode",
                "કમાન્ડ": "cmd",
                "પાવરશેલ": "powershell"
            }
            
            target_app = None
            for gu_name, eng_id in app_map_gu.items():
                if gu_name in cmd or eng_id in cmd:
                    target_app = eng_id
                    break
                    
            if target_app:
                print(f"[*] Calling Tool [SystemControl: open_application] for {target_app}...")
                open_application(target_app)
                return f"મેં {target_app} ખોલી દીધું છે, સર."
                    
            if any(w in cmd for w in ["ફોટો", "સ્ક્રીનશોટ", "screenshot"]):
                print("[*] Calling Tool [SystemControl: take_screenshot]...")
                take_screenshot()
                return "મેં પિક્ચર્સ ફોલ્ડરમાં સ્ક્રીનશોટ લઈ લીધો છે, સર."
                
            return "દિલગીર છું સર, પરંતુ ક્વોટા અથવા ઇન્ટરનેટ કનેક્શન મર્યાદિત છે. તમે ક્રોમ/નોટપેડ ખોલવા, સ્ક્રીનશોટ લેવા અથવા સિસ્ટમની તબિયત જાણવા માટે સ્થાનિક આદેશો આપી શકો છો."
        else:
            if any(w in cmd for w in ["system", "diagnostics", "health", "cpu", "ram", "disk"]):
                print("[*] Calling Tool [SystemInfo: get_system_diagnostics]...")
                return get_system_diagnostics()
                
            # If application name is mentioned
            for app in ["chrome", "notepad", "calculator", "paint", "vscode", "vs code", "cmd", "powershell"]:
                if app in cmd:
                    print(f"[*] Calling Tool [SystemControl: open_application] for {app}...")
                    return open_application(app)
                    
            if "screenshot" in cmd or "capture" in cmd:
                print("[*] Calling Tool [SystemControl: take_screenshot]...")
                return take_screenshot()
                
            return (
                "I am currently operating with limited cognitive capacity as the GEMINI_API_KEY is not configured.\n"
                "Please paste your API key in the .env file to enable my agentic workflow capabilities."
            )
