import os
import sys
import subprocess
import psutil
import pyautogui
import urllib.request
import urllib.parse
import datetime
from bs4 import BeautifulSoup

# --- SystemInfo Tools ---

def get_system_diagnostics() -> str:
    """
    Fetches real-time system metrics including CPU load, RAM utilization, 
    disk space, and active processes.
    
    Returns:
        str: A formatted summary of the laptop's physical resources and health.
    """
    try:
        # CPU Info
        cpu_pct = psutil.cpu_percent(interval=0.5)
        cpu_cores = psutil.cpu_percent(interval=0.1, percpu=True)
        cpu_freq = psutil.cpu_freq()
        cpu_freq_str = f"{cpu_freq.current:.1f}MHz" if cpu_freq else "Unknown"

        # RAM Info
        ram = psutil.virtual_memory()
        ram_total = ram.total / (1024 ** 3)
        ram_used = ram.used / (1024 ** 3)
        ram_pct = ram.percent

        # Disk Info (C: drive)
        disk_c = psutil.disk_usage('C:\\')
        c_total = disk_c.total / (1024 ** 3)
        c_used = disk_c.used / (1024 ** 3)
        c_pct = disk_c.percent

        # Disk Info (D: drive if exists)
        d_str = ""
        if os.path.exists('D:\\'):
            try:
                disk_d = psutil.disk_usage('D:\\')
                d_total = disk_d.total / (1024 ** 3)
                d_used = disk_d.used / (1024 ** 3)
                d_pct = disk_d.percent
                d_str = f"Disk D: {d_used:.1f}GB / {d_total:.1f}GB ({d_pct}%)\n"
            except Exception:
                pass

        # Top Processes by CPU usage
        processes = []
        for proc in psutil.process_iter(['name', 'cpu_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        processes = sorted(processes, key=lambda x: x.get('cpu_percent', 0) or 0, reverse=True)[:3]
        proc_str = "\n".join([f"  - {p['name']}: {p['cpu_percent']}%" for p in processes if p['name']])

        diagnostics = (
            f"=== SYSTEM TELEMETRY ===\n"
            f"CPU Utilization: {cpu_pct}% ({len(cpu_cores)} Cores)\n"
            f"CPU Frequency: {cpu_freq_str}\n"
            f"RAM Utilization: {ram_used:.1f}GB / {ram_total:.1f}GB ({ram_pct}%)\n"
            f"Disk C: {c_used:.1f}GB / {c_total:.1f}GB ({c_pct}%)\n"
            f"{d_str}"
            f"Top Processes:\n{proc_str}"
        )
        return diagnostics
    except Exception as e:
        return f"Error gathering diagnostics: {str(e)}"


# --- SystemControl Tools ---

def open_application(app_name: str) -> str:
    """
    Launches a specified application on the local computer.
    
    Args:
        app_name (str): The common name of the application (e.g., 'chrome', 'notepad', 'calculator', 'vs code', 'paint').
        
    Returns:
        str: A confirmation message indicating success or failure.
    """
    app_map = {
        "chrome": "chrome",
        "google chrome": "chrome",
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "paint": "mspaint.exe",
        "mspaint": "mspaint.exe",
        "explorer": "explorer.exe",
        "cmd": "cmd.exe",
        "powershell": "powershell.exe",
        "vs code": "code",
        "vscode": "code"
    }

    app_name_lower = app_name.lower().strip()
    command = app_map.get(app_name_lower, app_name_lower)

    try:
        # Run in background without blocking
        if sys.platform == "win32":
            # For Windows, use start command via shell or launch directly
            subprocess.Popen(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(command, shell=True)
        return f"Successfully initialized {app_name}."
    except Exception as e:
        # Try a fallback of search paths or os.startfile if it's a full path
        try:
            if os.path.exists(command):
                os.startfile(command)
                return f"Successfully opened {app_name} via startfile."
        except Exception:
            pass
        return f"Failed to open {app_name}. Error: {str(e)}. (Hint: Check if the application name is spelled correctly or in PATH)"


def take_screenshot(filename: str = None) -> str:
    """
    Captures a screenshot of the primary screen and saves it as an image.
    
    Args:
        filename (str, optional): The name of the file to save (e.g., 'screenshot.png'). If None, a timestamped name is generated.
        
    Returns:
        str: A message with the path of the saved screenshot.
    """
    try:
        # Ensure we have a directory for screenshots
        save_dir = os.path.join(os.path.expanduser('~'), 'Pictures', 'JARVIS_Screenshots')
        os.makedirs(save_dir, exist_ok=True)
        
        if not filename:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"jarvis_screen_{timestamp}.png"
        
        # Ensure correct extension
        if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            filename += '.png'
            
        filepath = os.path.join(save_dir, filename)
        
        # Take the screenshot
        screenshot = pyautogui.screenshot()
        screenshot.save(filepath)
        return f"Screenshot successfully saved to: {filepath}"
    except Exception as e:
        return f"Failed to capture screenshot: {str(e)}"


def simulate_keystroke(keys: str) -> str:
    """
    Simulates keyboard key presses or hotkey combinations.
    
    Args:
        keys (str): Key name or shortcut combination (e.g., 'ctrl+c', 'win+d', 'enter', 'space').
        
    Returns:
        str: Confirmation of simulated keystrokes.
    """
    try:
        pyautogui.PAUSE = 0.5
        if '+' in keys:
            hotkeys = [k.strip().lower() for k in keys.split('+')]
            pyautogui.hotkey(*hotkeys)
            return f"Simulated hotkey shortcut: {', '.join(hotkeys)}"
        else:
            pyautogui.press(keys.lower().strip())
            return f"Simulated keypress: {keys}"
    except Exception as e:
        return f"Failed to simulate keystroke: {str(e)}"


def move_mouse_and_click(x: int, y: int) -> str:
    """
    Moves the mouse pointer to screen coordinates (x, y) and performs a click.
    
    Args:
        x (int): Horizontal pixel coordinate from left of screen.
        y (int): Vertical pixel coordinate from top of screen.
        
    Returns:
        str: Confirmation of mouse action.
    """
    try:
        screen_w, screen_h = pyautogui.size()
        if not (0 <= x <= screen_w) or not (0 <= y <= screen_h):
            return f"Error: Coordinates ({x}, {y}) out of screen boundaries ({screen_w}x{screen_h})."
            
        pyautogui.moveTo(x, y, duration=1.0)
        pyautogui.click()
        return f"Successfully moved mouse to ({x}, {y}) and clicked."
    except Exception as e:
        return f"Failed to execute mouse click: {str(e)}"


# --- WebSearch Tools ---

def search_internet(query: str) -> str:
    """
    Queries the internet for information, documentations, or answers using DuckDuckGo.
    
    Args:
        query (str): The search term or question.
        
    Returns:
        str: A summary of web search results.
    """
    try:
        # Use DuckDuckGo HTML search page
        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote_plus(query)
        req = urllib.request.Request(
            url, 
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read()
            
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Scrape result snippets
        snippets = soup.find_all('a', class_='result__snippet')
        titles = soup.find_all('a', class_='result__url')
        
        for i, snippet in enumerate(snippets[:4]):
            title = titles[i].get_text().strip() if i < len(titles) else "Result"
            results.append(f"[{i+1}] {title}\n    {snippet.get_text().strip()}")
            
        # Fallback query if beautifulsoup layout changes
        if not results:
            td_snippets = soup.find_all('td', class_='result-snippet')
            for i, snippet in enumerate(td_snippets[:4]):
                results.append(f"[{i+1}] Web result:\n    {snippet.get_text().strip()}")
                
        if results:
            return f"Web search results for: '{query}':\n\n" + "\n\n".join(results)
        else:
            return f"Search returned no snippets. Visit search page: {url}"
            
    except Exception as e:
        return f"Failed to complete internet search: {str(e)}"
