// State variables
let isLiveConnection = false;
let currentLanguage = 'en';
let localServerUrl = 'http://localhost:8000';
let telemetryHistory = Array(30).fill(15); // History array for chart
let telemetryLabels = Array(30).fill('');
let chartCanvas, chartCtx;
let simulationIntervals = [];

// DOM Elements
const connectionBadge = document.getElementById('connection-badge');
const brainState = document.getElementById('brain-state');
const brainSubtext = document.getElementById('brain-subtext');
const coreNode = document.getElementById('core-node');
const coreIcon = document.getElementById('core-icon');
const waveform = document.getElementById('waveform');
const chatBubbles = document.getElementById('chat-bubbles');
const logStream = document.getElementById('log-stream');
const terminalInput = document.getElementById('terminal-input');
const sendBtn = document.getElementById('send-btn');
const muteCheckbox = document.getElementById('mute-voice');
const statusCard = document.getElementById('status-card');

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    chartCanvas = document.getElementById('telemetry-chart');
    chartCtx = chartCanvas.getContext('2d');
    
    // Set up terminal event listeners
    terminalInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            submitCommand();
        }
    });
    sendBtn.addEventListener('click', submitCommand);
    
    // Start canvas chart rendering loop
    drawTelemetryChart();
    
    // Start checking for local Python backend (poll every 1 second for live status sync)
    checkLocalConnection();
    setInterval(checkLocalConnection, 1000);
    
    // Start simulation loop (runs by default, overridden if connected)
    startSimulation();
    
    addLogLine('[INIT] Holographic HUD core ready.', 'cyan');
});

// Check if Python built-in server is running locally
async function checkLocalConnection() {
    try {
        const response = await fetch(`${localServerUrl}/api/status`, {
            method: 'GET',
            headers: { 'Accept': 'application/json' },
            mode: 'cors'
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.status === 'online') {
                if (!isLiveConnection) {
                    setLiveMode(true);
                }
                if (data.jarvis_state) {
                    syncVisualState(data.jarvis_state);
                }
            }
        } else {
            if (isLiveConnection) setLiveMode(false);
        }
    } catch (e) {
        if (isLiveConnection) setLiveMode(false);
    }
}

// Synchronize browser HUD state with the physical J.A.R.V.I.S. status
function syncVisualState(backendState) {
    let mappedState = 'standby';
    if (backendState === 'SPEAKING') mappedState = 'speaking';
    else if (backendState === 'LISTENING') mappedState = 'listening';
    else if (backendState === 'PROCESSING') mappedState = 'thinking';
    else if (backendState === 'STANDBY') mappedState = 'standby';
    
    const currentStateText = brainState.innerText.trim().toUpperCase();
    let currentUIState = 'standby';
    if (currentStateText === 'LISTENING...') currentUIState = 'listening';
    else if (currentStateText === 'THINKING...') currentUIState = 'thinking';
    else if (currentStateText === 'SPEAKING...') currentUIState = 'speaking';
    else if (currentStateText === 'STANDBY MODE') currentUIState = 'standby';
    
    if (mappedState !== currentUIState) {
        setVisualState(mappedState);
    }
}

function setLiveMode(connected) {
    isLiveConnection = connected;
    if (connected) {
        // Switch to Online Mode
        connectionBadge.className = 'connection-status online';
        connectionBadge.innerHTML = '<span class="status-dot"></span><span class="status-text">ONLINE (LIVE PC CONNECTION)</span>';
        addLogLine('[LINK] Local python server linked successfully.', 'green');
        
        // Stop UI metrics simulation, but keep generating background log visualizers
        clearIntervalsExceptLogs();
        startLiveTelemetryPolling();
    } else {
        // Switch to Offline Demo Mode
        connectionBadge.className = 'connection-status offline';
        connectionBadge.innerHTML = '<span class="status-dot"></span><span class="status-text">OFFLINE (DEMO MODE)</span>';
        addLogLine('[LINK] Lost server link. Defaulting to simulated demo mode.', 'red');
        
        clearIntervalsExceptLogs();
        startSimulation();
    }
}

// Clear active intervals when transitioning state
function clearIntervalsExceptLogs() {
    simulationIntervals.forEach(interval => clearInterval(interval));
    simulationIntervals = [];
}

// Start Simulated HUD loop
function startSimulation() {
    // 1. Simulate Metrics Fluctuations
    const metricInterval = setInterval(() => {
        const mockCpu = Math.floor(Math.random() * 20) + 10; // 10-30%
        const mockRam = Math.floor(Math.sin(Date.now() / 10000) * 5) + 42; // ~42% oscillates
        
        updateMetrics(mockCpu, mockRam);
        
        // Update history cache
        telemetryHistory.push(mockCpu);
        telemetryHistory.shift();
    }, 1000);
    simulationIntervals.push(metricInterval);
    
    // 2. Simulated Log Ticker
    const simulatedLogs = [
        'Diagnostics: Core temperature is stable at 46°C.',
        'Sensors: Microphones calibrated. Threshold: -42dB.',
        'Speech Engine: British Male TTS ready (pyttsx3).',
        'Language Engine: Google Speech API calibrated.',
        'Cognitive: Wake-word trigger thread running on main loop.',
        'System: psutil telemetry active.',
        'Diagnostics: Keyboard virtual mapper registered.',
        'Memory Monitor: Virtual cache cleared (0.0ms).'
    ];
    
    const logInterval = setInterval(() => {
        if (Math.random() > 0.6) {
            const randomLog = simulatedLogs[Math.floor(Math.random() * simulatedLogs.length)];
            addLogLine(`[INFO] ${randomLog}`, 'dim');
        }
    }, 4000);
    simulationIntervals.push(logInterval);
}

// Start Live PC Data Polling
function startLiveTelemetryPolling() {
    const livePolling = setInterval(async () => {
        try {
            const response = await fetch(`${localServerUrl}/api/telemetry`);
            if (response.ok) {
                const data = await response.json();
                updateMetrics(data.cpu, data.ram);
                
                telemetryHistory.push(data.cpu);
                telemetryHistory.shift();
            }
        } catch (e) {
            // Silence connection drops (handled by status check)
        }
    }, 1000);
    simulationIntervals.push(livePolling);
}

// Update DOM Metric indicators
function updateMetrics(cpu, ram) {
    document.getElementById('cpu-val').innerText = `${cpu}%`;
    document.getElementById('cpu-bar').style.width = `${cpu}%`;
    document.getElementById('cpu-status').innerText = cpu > 60 ? 'Heavy Load' : (cpu > 25 ? 'Active' : 'Idle');
    
    document.getElementById('ram-val').innerText = `${ram}%`;
    document.getElementById('ram-bar').style.width = `${ram}%`;
    document.getElementById('ram-status').innerText = ram > 80 ? 'Optimizing' : 'Optimized';
}

// Handle Command Submission
async function submitCommand() {
    const commandText = terminalInput.value.trim();
    if (!commandText) return;
    
    terminalInput.value = '';
    await processAgentRequest(commandText);
}

// Quick action buttons
async function sendQuickCmd(cmd) {
    await processAgentRequest(cmd);
}

// Main logic to route command to either simulation or real backend API
async function processAgentRequest(cmdText) {
    // Add user message to UI
    addChatBubble(cmdText, 'user', currentLanguage);
    addLogLine(`[CMD] Received command: "${cmdText}"`, 'cyan');
    
    // Check for skip command immediately to interrupt active speaking
    const lowerCmd = cmdText.toLowerCase().trim();
    if (lowerCmd === 'skip' || lowerCmd === 'skip it' || lowerCmd === 'stop' || lowerCmd === 'quiet' || lowerCmd === 'સ્કીપ') {
        addLogLine('[CMD] Skip command received. Stopping speech synthesis...', 'cyan');
        setVisualState('standby');
        
        // Stop browser speech synthesis
        if (window.speechSynthesis) {
            window.speechSynthesis.cancel();
        }
        
        // Stop local laptop speech synthesis if connected
        if (isLiveConnection) {
            try {
                await fetch(`${localServerUrl}/api/skip`, {
                    method: 'POST',
                    mode: 'cors'
                });
            } catch (e) {
                // Ignore network errors
            }
        }
        return;
    }

    // Set visual state to thinking
    setVisualState('thinking');
    
    if (isLiveConnection) {
        // Send request to real laptop Python Server
        addLogLine('[AGENT] Transmitting command to laptop core...', 'blue');
        try {
            const response = await fetch(`${localServerUrl}/api/command`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    command: cmdText,
                    lang: currentLanguage,
                    mute: muteCheckbox.checked
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                addLogLine('[AGENT] Logic execution successfully completed.', 'green');
                addChatBubble(data.response, 'jarvis', currentLanguage);
                // Visual state changes are synchronized dynamically via /api/status polling
                
            } else {
                setVisualState('standby');
                addChatBubble("Error executing command on local machine.", "system");
                addLogLine('[ERR] Local execution failed.', 'red');
            }
        } catch (e) {
            setVisualState('standby');
            addChatBubble("Failed to connect to local server endpoint.", "system");
            addLogLine(`[ERR] Fetch exception: ${e}`, 'red');
        }
    } else {
        // RUN SIMULATED RESPONSE (No server running)
        addLogLine('[SIM] Running natural language reasoning...', 'gold');
        
        setTimeout(() => {
            let responseText = '';
            
            // Basic hardcoded responses for demo mode
            const lowerCmd = cmdText.toLowerCase();
            if (lowerCmd.includes('notepad') || lowerCmd.includes('નોટપેડ')) {
                addLogLine('[EXEC] Invoked application: notepad.exe', 'green');
                responseText = currentLanguage === 'gu' 
                    ? "મેં નોટપેડ ખોલી દીધું છે, સર." 
                    : "Notepad launched successfully, sir.";
            } else if (lowerCmd.includes('chrome') || lowerCmd.includes('ક્રોમ')) {
                addLogLine('[EXEC] Invoked subprocess: chrome.exe', 'green');
                responseText = currentLanguage === 'gu' 
                    ? "મેં ગુગલ ક્રોમ ચાલુ કરી દીધું છે." 
                    : "Launching Google Chrome browser now, sir.";
            } else if (lowerCmd.includes('screenshot') || lowerCmd.includes('ફોટો') || lowerCmd.includes('સ્ક્રીનશોટ')) {
                addLogLine('[EXEC] Triggered GUI screenshot capture.', 'green');
                responseText = currentLanguage === 'gu' 
                    ? "મેં સ્ક્રીનશોટ લઈ લીધો છે, સર." 
                    : "Screenshot captured and saved to workspace.";
            } else if (lowerCmd.includes('diagnostics') || lowerCmd.includes('સીપીયુ') || lowerCmd.includes('ram')) {
                addLogLine('[EXEC] Querying system diagnostics database.', 'green');
                responseText = currentLanguage === 'gu'
                    ? "તમારા કોમ્પ્યુટરની સ્થિતિ સામાન્ય છે, સર."
                    : "All laptop telemetry points are operating within normal parameters.";
            } else {
                addLogLine('[SIM] Fallback search agent triggered.', 'blue');
                responseText = currentLanguage === 'gu'
                    ? `હું સમજી ગયો કે તમે કહ્યું: "${cmdText}". આ ડેમો મોડ છે, સર. કૃપા કરીને રીઅલ-ટાઇમ કંટ્રોલ માટે પાયથોન સર્વર ચાલુ કરો.`
                    : `I processed your request: "${cmdText}". Currently running in offline demo mode. Please launch python web_server to execute this locally on your PC.`;
            }
            
            setVisualState('speaking');
            addChatBubble(responseText, 'jarvis', currentLanguage);
            
            // Speak audio using web API
            speakAudio(responseText);
            
        }, 1200);
    }
}

// Speak response in offline browser fallback mode
function speakAudio(text) {
    if (muteCheckbox.checked || !window.speechSynthesis) {
        setTimeout(() => setVisualState('standby'), 3000);
        return;
    }
    
    // Stop any current speaking
    window.speechSynthesis.cancel();
    
    const utterance = new SpeechSynthesisUtterance(text);
    
    // Try to match appropriate language voice
    if (currentLanguage === 'gu') {
        utterance.lang = 'gu-IN';
    } else {
        utterance.lang = 'en-GB'; // British male voice preference
    }
    
    utterance.onend = () => {
        setVisualState('standby');
    };
    
    utterance.onerror = () => {
        setVisualState('standby');
    };
    
    window.speechSynthesis.speak(utterance);
}

// Update visual HUD elements depending on J.A.R.V.I.S. state
function setVisualState(state) {
    // Reset all status-related classes
    statusCard.className = 'hud-status-card';
    coreNode.className = 'core-pulse-node';
    waveform.className = 'waveform-container';
    
    switch (state) {
        case 'standby':
            brainState.innerText = 'STANDBY MODE';
            brainSubtext.innerText = 'Waiting for verbal wake-word or input command...';
            coreIcon.className = 'fa-solid fa-brain';
            break;
            
        case 'listening':
            brainState.innerText = 'LISTENING...';
            brainSubtext.innerText = 'Speak clearly into your microphone...';
            statusCard.classList.add('status-listening');
            coreNode.classList.add('node-listening');
            coreIcon.className = 'fa-solid fa-microphone';
            break;
            
        case 'thinking':
            brainState.innerText = 'THINKING...';
            brainSubtext.innerText = 'Gemini reasoning agent evaluating intent and selecting tools...';
            statusCard.classList.add('status-thinking');
            coreNode.classList.add('node-thinking');
            coreIcon.className = 'fa-solid fa-gear';
            break;
            
        case 'speaking':
            brainState.innerText = 'SPEAKING...';
            brainSubtext.innerText = 'Synthesizing voice response feedback...';
            statusCard.classList.add('status-speaking');
            coreNode.classList.add('node-speaking');
            coreIcon.className = 'fa-solid fa-volume-high';
            waveform.classList.add('active');
            break;
    }
}

// UI Utility: Add log line to terminal
function addLogLine(text, colorClass = '') {
    const timestamp = new Date().toLocaleTimeString();
    const line = document.createElement('div');
    line.className = `log-line ${colorClass ? 'text-' + colorClass : ''}`;
    line.innerText = `[${timestamp}] ${text}`;
    logStream.appendChild(line);
    logStream.scrollTop = logStream.scrollHeight;
}

// UI Utility: Add bubble to chat panel
function addChatBubble(text, sender, language) {
    const bubble = document.createElement('div');
    const senderLabel = sender === 'user' ? 'USER' : 'JARVIS';
    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    
    bubble.className = `chat-bubble ${sender}-bubble ${language === 'gu' ? 'gujarati-bubble' : ''}`;
    bubble.innerHTML = `<span class="bubble-time">${senderLabel} - ${timestamp}</span><p>${text}</p>`;
    
    chatBubbles.appendChild(bubble);
    chatBubbles.scrollTop = chatBubbles.scrollHeight;
    
    // Truncate bubble logs if too long
    while (chatBubbles.children.length > 10) {
        chatBubbles.removeChild(chatBubbles.firstChild);
    }
}

// Language Selector
function setLanguage(lang) {
    currentLanguage = lang;
    document.getElementById('lang-en').classList.toggle('active', lang === 'en');
    document.getElementById('lang-gu').classList.toggle('active', lang === 'gu');
    addLogLine(`[CONFIG] System language configured to: ${lang.toUpperCase()}`, 'cyan');
    
    // Clear terminal text placeholder
    terminalInput.placeholder = lang === 'gu' 
        ? "ગુજરાતી અથવા અંગ્રેજીમાં આદેશ ટાઇપ કરો..." 
        : "Type command in English or Gujarati...";
}

// Toggle local sound setting (also synced with backend)
function toggleMute() {
    const isMuted = muteCheckbox.checked;
    addLogLine(`[CONFIG] Audio synthesis muted locally: ${isMuted}`, 'cyan');
}

// Draw simple telemetry history graph on canvas
function drawTelemetryChart() {
    if (!chartCtx) return;
    
    const width = chartCanvas.width;
    const height = chartCanvas.height;
    
    // Draw background
    chartCtx.clearRect(0, 0, width, height);
    chartCtx.fillStyle = 'rgba(0, 0, 0, 0.1)';
    chartCtx.fillRect(0, 0, width, height);
    
    // Draw line
    chartCtx.beginPath();
    chartCtx.lineWidth = 1.5;
    chartCtx.strokeStyle = '#00e5ff';
    
    const step = width / (telemetryHistory.length - 1);
    
    for (let i = 0; i < telemetryHistory.length; i++) {
        const val = telemetryHistory[i];
        // Calculate Y coord: scale 0-100% to canvas height (leaving margins)
        const y = height - ((val / 100) * (height - 15) + 5);
        const x = i * step;
        
        if (i === 0) {
            chartCtx.moveTo(x, y);
        } else {
            chartCtx.lineTo(x, y);
        }
    }
    
    chartCtx.stroke();
    
    // Draw area gradient under line
    chartCtx.lineTo(width, height);
    chartCtx.lineTo(0, height);
    chartCtx.closePath();
    const grad = chartCtx.createLinearGradient(0, 0, 0, height);
    grad.addColorStop(0, 'rgba(0, 229, 255, 0.15)');
    grad.addColorStop(1, 'rgba(0, 229, 255, 0)');
    chartCtx.fillStyle = grad;
    chartCtx.fill();
    
    requestAnimationFrame(drawTelemetryChart);
}
