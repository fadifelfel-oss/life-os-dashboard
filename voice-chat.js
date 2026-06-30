// voice-chat.js — Voice Chat module for Life OS
// Provides: voice recording, Whisper transcription, TTS playback, voice memo management

let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let audioContext = null;

// Load voice memos list
function loadVoiceMemos() {
  const container = document.getElementById('voice-memo-list');
  container.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-muted);">Loading voice memos...</div>';
  
  // Request file list from server
  fetch('/api/voice-memos')
    .then(r => r.json())
    .then(data => {
      if (!data.files || data.files.length === 0) {
        container.innerHTML = `
          <div class="mcp-empty-state">
            <div class="icon">🎙️</div>
            <div>No voice memos yet</div>
            <div style="font-size:11px;margin-top:4px;">Record one using the button above</div>
          </div>`;
        return;
      }
      container.innerHTML = '';
      data.files.forEach(f => {
        const div = document.createElement('div');
        div.className = 'voice-memo-item';
        div.innerHTML = `
          <div class="voice-memo-info">
            <div class="voice-memo-name">${f.name}</div>
            <div class="voice-memo-meta">${f.size} • ${f.date} • ${f.duration || '?'}</div>
          </div>
          <div class="voice-memo-actions">
            <button class="mcp-btn sm" onclick="playVoiceMemo('${f.path}')" style="border-color:var(--green);color:var(--green);">▶ Play</button>
            <button class="mcp-btn sm transcribe-btn" data-path="${f.path}" onclick="transcribeVoiceMemo('${f.path}', this)">📝 Transcribe</button>
            <button class="mcp-btn sm danger" onclick="deleteVoiceMemo('${f.path}')">🗑️</button>
          </div>
          <div class="voice-memo-transcript" id="transcript-${f.name.replace(/[^a-z0-9]/gi,'')}" style="display:none;"></div>
        `;
        container.appendChild(div);
      });
    })
    .catch(() => {
      container.innerHTML = `<div class="mcp-empty-state"><div class="icon">⚠️</div><div>Could not load voice memos<br><span style="font-size:10px;">API endpoint not available in static mode</span></div></div>`;
    });
}

// Start recording
function startRecording() {
  navigator.mediaDevices.getUserMedia({ audio: true })
    .then(stream => {
      mediaRecorder = new MediaRecorder(stream);
      audioChunks = [];
      mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
      mediaRecorder.onstop = () => {
        const blob = new Blob(audioChunks, { type: 'audio/webm' });
        saveRecording(blob);
        stream.getTracks().forEach(t => t.stop());
      };
      mediaRecorder.start();
      isRecording = true;
      updateRecordUI();
    })
    .catch(err => {
      alert('Microphone access denied: ' + err.message);
    });
}

function stopRecording() {
  if (mediaRecorder && isRecording) {
    mediaRecorder.stop();
    isRecording = false;
    updateRecordUI();
  }
}

function toggleRecording() {
  if (isRecording) stopRecording();
  else startRecording();
}

function updateRecordUI() {
  const btn = document.getElementById('voice-record-btn');
  const status = document.getElementById('voice-recording-status');
  if (isRecording) {
    btn.innerHTML = '⏹ Stop Recording';
    btn.style.borderColor = 'var(--red)';
    btn.style.color = 'var(--red)';
    status.innerHTML = '<span style="color:var(--red);">● Recording...</span>';
  } else {
    btn.innerHTML = '🎙️ Start Recording';
    btn.style.borderColor = 'var(--green)';
    btn.style.color = 'var(--green)';
    status.innerHTML = '';
  }
}

function saveRecording(blob) {
  // Convert to base64 and send to server for saving + transcription
  const reader = new FileReader();
  reader.onloadend = () => {
    const base64 = reader.result.split(',')[1];
    
    // Show processing status
    const container = document.getElementById('voice-memo-list');
    const processingDiv = document.createElement('div');
    processingDiv.id = 'voice-processing';
    processingDiv.style.cssText = 'padding:16px;text-align:center;color:var(--accent);';
    processingDiv.innerHTML = '<span>⏳ Processing voice memo...</span>';
    container.prepend(processingDiv);
    
    fetch('/api/voice-memo', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ audio: base64, format: 'webm' })
    })
    .then(r => r.json())
    .then(data => {
      document.getElementById('voice-processing')?.remove();
      if (data.success) {
        // Auto-transcribe
        const transcriptDiv = document.createElement('div');
        transcriptDiv.style.cssText = 'padding:12px;background:rgba(63,185,80,0.08);border-radius:8px;margin-top:8px;font-size:12px;';
        transcriptDiv.innerHTML = `<b style="color:var(--green);">📝 Transcript:</b><br>${data.transcript || 'Transcription pending...'}`;
        container.prepend(transcriptDiv);
        
        // Refresh after delay
        setTimeout(loadVoiceMemos, 2000);
      } else {
        alert('Error saving: ' + (data.error || 'Unknown error'));
      }
    })
    .catch(err => {
      document.getElementById('voice-processing')?.remove();
      // Fallback: save locally as blob URL
      const url = URL.createObjectURL(blob);
      const div = document.createElement('div');
      div.className = 'voice-memo-item';
      div.innerHTML = `
        <div class="voice-memo-info">
          <div class="voice-memo-name">Recording ${new Date().toLocaleTimeString()}</div>
          <div class="voice-memo-meta">Saved locally • ${(blob.size/1024).toFixed(0)} KB</div>
        </div>
        <div class="voice-memo-actions">
          <audio controls src="${url}" style="height:32px;width:200px;"></audio>
        </div>`;
      container.prepend(div);
    });
  };
  reader.readAsDataURL(blob);
}

function playVoiceMemo(path) {
  const audio = new Audio(path);
  audio.play();
}

function transcribeVoiceMemo(path, btn) {
  const name = path.split('/').pop().replace(/\.[^.]+$/, '').replace(/[^a-z0-9]/gi, '');
  const div = document.getElementById('transcript-' + name);
  if (!div) return;
  
  div.style.display = 'block';
  div.innerHTML = '<span style="color:var(--accent);">⏳ Transcribing with Whisper...</span>';
  btn.disabled = true;
  btn.textContent = '⏳ Working...';
  
  fetch('/api/transcribe', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path })
  })
  .then(r => r.json())
  .then(data => {
    btn.disabled = false;
    btn.textContent = '📝 Transcribe';
    if (data.transcript) {
      div.innerHTML = `<b style="color:var(--green);">📝 Transcript:</b><br>${data.transcript}`;
    } else {
      div.innerHTML = `<span style="color:var(--red);">Error: ${data.error || 'Transcription failed'}</span>`;
    }
  })
  .catch(err => {
    btn.disabled = false;
    btn.textContent = '📝 Transcribe';
    div.innerHTML = `<span style="color:var(--red);">Error: ${err.message}</span>`;
  });
}

function deleteVoiceMemo(path) {
  if (!confirm('Delete this voice memo?')) return;
  fetch('/api/voice-memo', {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path })
  })
  .then(() => loadVoiceMemos())
  .catch(() => alert('Could not delete via API'));
}

function cleanupVoiceMemos() {
  // Delete all voice memos older than 7 days or all if confirmed
  if (!confirm('Clean up old voice memos? This will delete audio files older than 7 days.')) return;
  fetch('/api/voice-memos/cleanup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ days: 7 })
  })
  .then(r => r.json())
  .then(data => {
    alert(`Cleaned up ${data.deleted || 0} voice memos`);
    loadVoiceMemos();
  })
  .catch(() => alert('Cleanup API not available'));
}

// Text-to-Speech: speak a response
function speakText(text) {
  if (!text) return;
  
  // Use browser's built-in TTS as fallback
  if ('speechSynthesis' in window) {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;
    // Try to use a natural voice
    const voices = speechSynthesis.getVoices();
    const preferred = voices.find(v => v.name.includes('Google') || v.name.includes('Natural') || v.name.includes('Enhanced'));
    if (preferred) utterance.voice = preferred;
    speechSynthesis.speak(utterance);
  } else {
    alert('Text-to-speech not supported in this browser');
  }
}

function stopSpeaking() {
  if ('speechSynthesis' in window) speechSynthesis.cancel();
}

function toggleVoicePanel() {
  const panel = document.getElementById('voice-chat-panel');
  panel.classList.toggle('open');
  if (panel.classList.contains('open')) {
    loadVoiceMemos();
    // Load voices for TTS
    if ('speechSynthesis' in window) speechSynthesis.getVoices();
  }
}

// Voice-to-text for message input (dictation)
let isDictating = false;
let recognition = null;

function startDictation() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    alert('Speech recognition not supported. Use Chrome or Edge.');
    return;
  }
  recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.lang = 'en-US';
  
  const input = document.getElementById('voice-message-input');
  const btn = document.getElementById('voice-dictate-btn');
  
  recognition.onresult = (e) => {
    let transcript = '';
    for (let i = e.resultIndex; i < e.results.length; i++) {
      transcript += e.results[i][0].transcript;
    }
    input.value = transcript;
    if (e.results[e.results.length - 1].isFinal) {
      isDictating = false;
      btn.textContent = '🎤 Dictate';
      btn.style.color = 'var(--text)';
    }
  };
  
  recognition.onend = () => {
    isDictating = false;
    btn.textContent = '🎤 Dictate';
    btn.style.color = 'var(--text)';
  };
  
  recognition.onerror = (e) => {
    isDictating = false;
    btn.textContent = '🎤 Dictate';
    btn.style.color = 'var(--text)';
    console.error('Speech recognition error:', e.error);
  };
  
  recognition.start();
  isDictating = true;
  btn.textContent = '⏹ Stop';
  btn.style.color = 'var(--red)';
}

function toggleDictation() {
  if (isDictating) {
    recognition?.stop();
    isDictating = false;
  } else {
    startDictation();
  }
}

// Listen for messages from parent (Life OS)
window.addEventListener('message', (e) => {
  if (e.data.type === 'speak') {
    speakText(e.data.text);
  }
  if (e.data.type === 'load-memos') {
    loadVoiceMemos();
  }
});
