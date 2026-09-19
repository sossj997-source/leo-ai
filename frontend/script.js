/* ================================================================
   J.A.R.V.I.S — FRONTEND CONTROLLER
   ================================================================ */

   const API = 'https://localhost:8000';

   let sessionId = null;
   let currentMode = 'general';
   
   let isStreaming = false;
   let isListening = false;
   
   let orb = null;
   let recognition = null;
   let ttsPlayer = null;
   
   
   /* ================================================================
      DOM
      ================================================================ */
   
   const $ = id => document.getElementById(id);
   
   const chatMessages = $('chat-messages');
   const messageInput = $('message-input');
   const sendBtn = $('send-btn');
   const micBtn = $('mic-btn');
   const ttsBtn = $('tts-btn');
   const newChatBtn = $('new-chat-btn');
   
   const modeLabel = $('mode-label');
   const charCount = $('char-count');
   const welcomeTitle = $('welcome-title');
   
   const modeSlider = $('mode-slider');
   const btnGeneral = $('btn-general');
   const btnRealtime = $('btn-realtime');
   const btnAgent = $('btn-agent');
   
   const statusDot = document.querySelector('.status-dot');
   const statusText = document.querySelector('.status-text');
   
   const orbContainer = $('orb-container');
   
   const searchResultsToggle = $('search-results-toggle');
   const searchResultsWidget = $('search-results-widget');
   const searchResultsClose = $('search-results-close');
   const searchResultsQuery = $('search-results-query');
   const searchResultsAnswer = $('search-results-answer');
   const searchResultsList = $('search-results-list');
   
   
   /* ================================================================
      HELPERS
      ================================================================ */
   
   /**
    * Clean any text response: remove [object Object] artifacts.
    */
   function cleanText(text) {
       if (text === null || text === undefined) {
           return '';
       }
   
       if (typeof text !== 'string') {
           try {
               text = JSON.stringify(text);
           } catch (_) {
               text = String(text);
           }
       }
   
       return text
           .replace(/\[object Object\]/g, '')
           .replace(/\uFFFD/g, '')
           .replace(/\s+/g, ' ')
           .trim();
   }
   
   
   /* ================================================================
      TTS PLAYER
      ================================================================ */
   
   class TTSPlayer {
   
       constructor() {
   
           this.queue = [];
           this.playing = false;
           this.enabled = true;
           this.stopped = false;
   
           this.audio = document.createElement('audio');
   
           this.audio.preload = 'auto';
           this.audio.setAttribute('playsinline', '');
       }
   
   
       unlock() {
   
           try {
   
               const silentWav =
                   'data:audio/wav;base64,' +
                   'UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA';
   
               this.audio.src = silentWav;
   
               const promise = this.audio.play();
   
               if (promise) {
                   promise.catch(() => {});
               }
   
           } catch (_) {}
       }
   
   
       reset() {
   
           this.stop();
   
           this.stopped = false;
       }
   
   
       enqueue(base64Audio) {
   
           if (!this.enabled) {
               return;
           }
   
           if (this.stopped) {
               return;
           }
   
           if (!base64Audio) {
               return;
           }
   
           this.queue.push(base64Audio);
   
           if (!this.playing) {
               this._playLoop();
           }
       }
   
   
       async _playLoop() {
   
           if (this.playing) {
               return;
           }
   
           this.playing = true;
   
           try {
   
               while (
                   this.queue.length > 0 &&
                   this.enabled &&
                   !this.stopped
               ) {
   
                   const b64 = this.queue.shift();
   
                   await this._playB64(b64);
               }
   
           } finally {
   
               this.playing = false;
   
               this._setSpeaking(false);
           }
       }
   
   
       _playB64(b64) {
   
           return new Promise(resolve => {
   
               if (!b64) {
                   resolve();
                   return;
               }
   
               let finished = false;
   
               const done = () => {
   
                   if (finished) {
                       return;
                   }
   
                   finished = true;
   
                   this.audio.onended = null;
                   this.audio.onerror = null;
   
                   resolve();
               };
   
   
               /*
                * Edge TTS returns MP3 audio.
                */
               this.audio.src =
                   'data:audio/mpeg;base64,' + b64;
   
   
               this.audio.onended = done;
   
               this.audio.onerror = () => {
   
                   console.warn(
                       'TTS audio playback error'
                   );
   
                   done();
               };
   
   
               this._setSpeaking(true);
   
   
               const promise = this.audio.play();
   
               if (promise) {
   
                   promise.catch(error => {
   
                       console.warn(
                           'TTS play blocked:',
                           error
                       );
   
                       done();
                   });
               }
           });
       }
   
   
       stop() {
   
           this.stopped = true;
   
           this.queue.length = 0;
   
           try {
               this.audio.pause();
               this.audio.currentTime = 0;
           } catch (_) {}
   
           this.playing = false;
   
           this._setSpeaking(false);
       }
   
   
       _setSpeaking(active) {
   
           if (ttsBtn) {
               ttsBtn.classList.toggle(
                   'tts-speaking',
                   active
               );
           }
   
           if (orb) {
   
               try {
                   orb.setActive(active);
               } catch (_) {}
           }
       }
   }
   
   
   /* ================================================================
      INITIALIZATION
      ================================================================ */
   
   function init() {
   
       ttsPlayer = new TTSPlayer();
   
       if (ttsBtn) {
           ttsBtn.classList.add('tts-active');
       }
   
       setGreeting();
   
       initOrb();
   
       initSpeech();
   
       checkHealth();
   
       bindEvents();
   
       autoResizeInput();
   }
   
   
   /* ================================================================
      GREETING
      ================================================================ */
   
   function setGreeting() {
   
       if (!welcomeTitle) {
           return;
       }
   
       const hour = new Date().getHours();
   
       let greeting = 'Good evening.';
   
       if (hour < 12) {
   
           greeting = 'Good morning.';
   
       } else if (hour < 17) {
   
           greeting = 'Good afternoon.';
   
       } else if (hour >= 22) {
   
           greeting = 'Burning the midnight oil?';
       }
   
       welcomeTitle.textContent = greeting;
   }
   
   
   /* ================================================================
      ORB
      ================================================================ */
   
   function initOrb() {
   
       if (
           typeof OrbRenderer === 'undefined' ||
           !orbContainer
       ) {
           return;
       }
   
       try {
   
           orb = new OrbRenderer(
               orbContainer,
               {
                   hue: 0,
                   hoverIntensity: 0.3,
                   backgroundColor: [
                       0.02,
                       0.02,
                       0.06
                   ]
               }
           );
   
       } catch (error) {
   
           console.warn(
               'Orb initialization failed:',
               error
           );
       }
   }
   
   
   /* ================================================================
      SPEECH RECOGNITION
      ================================================================ */
   
   function initSpeech() {
   
       const SpeechRecognition =
           window.SpeechRecognition ||
           window.webkitSpeechRecognition;
   
       if (!SpeechRecognition) {
   
           console.warn(
               'Speech Recognition is not supported.'
           );
   
           if (micBtn) {
               micBtn.disabled = true;
           }
   
           return;
       }
   
   
       recognition = new SpeechRecognition();
   
       recognition.continuous = false;
       recognition.interimResults = true;
       recognition.lang = 'en-US';
   
   
       recognition.onstart = () => {
   
           isListening = true;
   
           if (micBtn) {
               micBtn.classList.add(
                   'listening'
               );
           }
       };
   
   
       recognition.onresult = event => {
   
           let finalText = '';
           let interimText = '';
   
           for (
               let i = event.resultIndex;
               i < event.results.length;
               i++
           ) {
   
               const result = event.results[i];
   
               const transcript =
                   result[0].transcript;
   
               if (result.isFinal) {
   
                   finalText += transcript;
   
               } else {
   
                   interimText += transcript;
               }
           }
   
   
           const displayText =
               finalText || interimText;
   
           if (messageInput) {
   
               messageInput.value =
                   displayText;
   
               autoResizeInput();
           }
   
   
           if (finalText.trim()) {
   
               const text =
                   finalText.trim();
   
               stopListening();
   
               sendMessage(text);
           }
       };
   
   
       recognition.onerror = event => {
   
           console.warn(
               'Speech recognition error:',
               event.error
           );
   
           isListening = false;
   
           if (micBtn) {
               micBtn.classList.remove(
                   'listening'
               );
           }
       };
   
   
       recognition.onend = () => {
   
           isListening = false;
   
           if (micBtn) {
               micBtn.classList.remove(
                   'listening'
               );
           }
       };
   }
   
   
   function startListening() {
   
       if (!recognition) {
           return;
       }
   
       if (isListening) {
           return;
       }
   
       try {
   
           recognition.start();
   
       } catch (error) {
   
           console.warn(
               'Could not start microphone:',
               error
           );
       }
   }
   
   
   function stopListening() {
   
       if (!recognition) {
           return;
       }
   
       try {
   
           recognition.stop();
   
       } catch (_) {}
   
       isListening = false;
   
       if (micBtn) {
           micBtn.classList.remove(
               'listening'
           );
       }
   }
   
   
   /* ================================================================
      MESSAGE RENDERING
      ================================================================ */
   
   function addMessage(role, text) {
   
       const wrapper =
           document.createElement('div');
   
       wrapper.className =
           `message ${role}`;
   
       const avatar =
           document.createElement('div');
   
       avatar.className =
           'message-avatar';
   
       avatar.textContent =
           role === 'user' ? 'U' : 'J';
   
   
       const body =
           document.createElement('div');
   
       body.className =
           'message-body';
   
   
       const label =
           document.createElement('div');
   
       label.className =
           'message-label';
   
       if (role === 'user') {
   
           label.textContent = 'You';
   
       } else {
   
           if (currentMode === 'realtime') {
               label.textContent = 'Jarvis (Realtime)';
           } else if (currentMode === 'agent') {
               label.textContent = 'Jarvis (Agent)';
           } else {
               label.textContent = 'Jarvis (General)';
           }
       }
   
   
       const content =
           document.createElement('div');
   
       content.className =
           'message-content';
   
       content.textContent =
           cleanText(text) || '';
   
   
       body.appendChild(label);
       body.appendChild(content);
   
       wrapper.appendChild(avatar);
       wrapper.appendChild(body);
   
       chatMessages.appendChild(wrapper);
   
       scrollToBottom();
   
       return content;
   }
   
   
   function addTypingIndicator() {
   
       removeTypingIndicator();
   
       const wrapper =
           document.createElement('div');
   
       wrapper.id =
           'typing-indicator';
   
       wrapper.className =
           'message assistant';
   
   
       wrapper.innerHTML = `
           <div class="message-avatar">J</div>
           <div class="message-body">
               <div class="message-label">
                   Jarvis
               </div>
               <div class="message-content">
                   <span class="typing-dots">•••</span>
               </div>
           </div>
       `;
   
   
       chatMessages.appendChild(wrapper);
   
       scrollToBottom();
   }
   
   
   function removeTypingIndicator() {
   
       const indicator =
           document.getElementById(
               'typing-indicator'
           );
   
       if (indicator) {
           indicator.remove();
       }
   }
   
   
   function scrollToBottom() {
   
       if (!chatMessages) {
           return;
       }
   
       chatMessages.scrollTop =
           chatMessages.scrollHeight;
   }
   
   
   /* ================================================================
      SEARCH RESULTS
      ================================================================ */
   
   function renderSearchResults(data) {
   
       if (!data) {
           return;
       }
   
   
       if (searchResultsQuery) {
   
           searchResultsQuery.textContent =
               data.query || '';
       }
   
   
       if (searchResultsAnswer) {
   
           searchResultsAnswer.textContent =
               data.answer || '';
       }
   
   
       if (searchResultsList) {
   
           searchResultsList.innerHTML = '';
   
           const results =
               Array.isArray(data.results)
                   ? data.results
                   : [];
   
   
           results.forEach(result => {
   
               const card =
                   document.createElement('div');
   
               card.className =
                   'search-result-card';
   
   
               const title =
                   document.createElement('div');
   
               title.className =
                   'search-result-title';
   
               title.textContent =
                   result.title || 'Untitled';
   
   
               const content =
                   document.createElement('div');
   
               content.className =
                   'search-result-content';
   
               content.textContent =
                   result.content || '';
   
   
               card.appendChild(title);
               card.appendChild(content);
   
   
               if (result.url) {
   
                   const link =
                       document.createElement('a');
   
                   link.href =
                       result.url;
   
                   link.target = '_blank';
   
                   link.rel =
                       'noopener noreferrer';
   
                   link.textContent =
                       result.url;
   
                   card.appendChild(link);
               }
   
   
               searchResultsList.appendChild(
                   card
               );
           });
       }
   }
   
   
   /* ================================================================
      SEND MESSAGE
      ================================================================ */
   
   async function sendMessage(textOverride) {
   
       const text =
           (
               textOverride ||
               messageInput.value
           ).trim();
   
   
       if (!text || isStreaming) {
           return;
       }
   
   
       messageInput.value = '';
   
       autoResizeInput();
   
       if (charCount) {
           charCount.textContent = '';
       }
   
   
       addMessage(
           'user',
           text
       );
   
       addTypingIndicator();
   
   
       isStreaming = true;
   
       if (sendBtn) {
           sendBtn.disabled = true;
       }
   
   
       /*
        * Reset previous TTS.
        * Audio is unlocked during the user click.
        */
       if (ttsPlayer) {
   
           ttsPlayer.reset();
   
           ttsPlayer.unlock();
       }
   
   
       const endpoint =
           currentMode === 'agent'
               ? '/agent'
               : currentMode === 'realtime'
                   ? '/chat/realtime/stream'
                   : '/chat/stream';
   
   
       try {
   
           const response =
               await fetch(
                   `${API}${endpoint}`,
                   {
                       method: 'POST',
   
                       headers: {
                           'Content-Type':
                               'application/json'
                       },
   
                       body: JSON.stringify({
                           message: text,
                           session_id: sessionId,
   
                           /*
                            * Backend can use this later
                            * to decide whether to generate
                            * TTS audio.
                            */
                           tts:
                               !!(
                                   ttsPlayer &&
                                   ttsPlayer.enabled
                               )
                       })
                   }
               );
   
   
           /* ============================================================
              AGENT RESPONSE
              Agent endpoint returns normal JSON, not SSE.
              ============================================================ */
   
           if (currentMode === 'agent') {
   
               if (!response.ok) {
   
                   const errorData =
                       await response
                           .json()
                           .catch(() => null);
   
                   throw new Error(
                       errorData?.detail ||
                       `HTTP ${response.status}`
                   );
               }
   
   
               const data =
                   await response.json();
   
   
               removeTypingIndicator();
   
   
               let agentMessage =
                   data.message ||
                   'Agent completed the request.';
   
   
               // Safety: if object, stringify
               if (typeof agentMessage !== 'string') {
                   try {
                       agentMessage = JSON.stringify(agentMessage);
                   } catch (_) {
                       agentMessage = 'Agent completed the request.';
                   }
               }
   
   
               // Clean [object Object] artifacts
               agentMessage = cleanText(agentMessage);
   
   
               addMessage(
                   'assistant',
                   agentMessage
               );
   
   
               return;
           }
   
   
           /* ============================================================
              STREAMING (General + Realtime)
              ============================================================ */
   
           if (!response.ok) {
   
               const errorData =
                   await response
                       .json()
                       .catch(() => null);
   
               throw new Error(
                   errorData?.detail ||
                   `HTTP ${response.status}`
               );
           }
   
   
           removeTypingIndicator();
   
   
           const contentEl =
               addMessage(
                   'assistant',
                   ''
               );
   
   
           const placeholder =
               currentMode === 'realtime'
                   ? 'Searching...'
                   : 'Thinking...';
   
   
           contentEl.innerHTML =
               `<span class="msg-stream-text">${placeholder}</span>`;
   
   
           scrollToBottom();
   
   
           if (!response.body) {
   
               throw new Error(
                   'Streaming response body is unavailable.'
               );
           }
   
   
           const reader =
               response.body.getReader();
   
           const decoder =
               new TextDecoder();
   
   
           let sseBuffer = '';
           let fullResponse = '';
   
           let cursorEl = null;
   
           let streamFinished = false;
   
   
           while (!streamFinished) {
   
               const {
                   done,
                   value
               } = await reader.read();
   
   
               if (done) {
                   break;
               }
   
   
               sseBuffer +=
                   decoder.decode(
                       value,
                       {
                           stream: true
                       }
                   );
   
   
               const lines =
                   sseBuffer.split('\n');
   
   
               sseBuffer =
                   lines.pop() || '';
   
   
               for (const rawLine of lines) {
   
                   const line =
                       rawLine.trim();
   
   
                   if (!line.startsWith('data:')) {
                       continue;
                   }
   
   
                   const rawData =
                       line.slice(5).trim();
   
   
                   if (!rawData) {
                       continue;
                   }
   
   
                   let data;
   
   
                   try {
   
                       data =
                           JSON.parse(rawData);
   
                   } catch (error) {
   
                       console.warn(
                           'Invalid SSE JSON:',
                           rawData
                       );
   
                       continue;
                   }
   
   
                   /* ----------------------------------------
                      SESSION
                      ---------------------------------------- */
   
                   if (data.session_id) {
   
                       sessionId =
                           data.session_id;
                   }
   
   
                   /* ----------------------------------------
                      SEARCH RESULTS
                      ---------------------------------------- */
   
                   if (data.search_results) {
   
                       renderSearchResults(
                           data.search_results
                       );
   
   
                       if (
                           searchResultsToggle
                       ) {
   
                           searchResultsToggle.style.display =
                               '';
                       }
   
   
                       if (
                           searchResultsWidget
                       ) {
   
                           searchResultsWidget.classList.add(
                               'open'
                           );
                       }
                   }
   
   
                   /* ----------------------------------------
                      TEXT
                      ---------------------------------------- */
   
                   if (data.chunk) {
   
                       // Handle both string and object chunks
                       let chunkText = '';
   
                       if (typeof data.chunk === 'string') {
                           chunkText = data.chunk;
                       } else if (
                           data.chunk &&
                           typeof data.chunk === 'object'
                       ) {
                           chunkText =
                               data.chunk.content ||
                               data.chunk.text ||
                               data.chunk.value ||
                               '';
                       }
   
                       // Safety: if still not string, skip
                       if (typeof chunkText !== 'string') {
                           chunkText = '';
                       }
   
   
                       fullResponse +=
                           chunkText;
   
   
                       const textSpan =
                           contentEl.querySelector(
                               '.msg-stream-text'
                           );
   
   
                       if (textSpan) {
   
                           // Clean while streaming
                           const displayText =
                               fullResponse
                                   .replace(
                                       /\[object Object\]/g,
                                       ''
                                   );
   
   
                           textSpan.textContent =
                               displayText;
                       }
   
   
                       if (!cursorEl) {
   
                           cursorEl =
                               document.createElement(
                                   'span'
                               );
   
                           cursorEl.className =
                               'stream-cursor';
   
                           cursorEl.textContent =
                               '|';
   
                           contentEl.appendChild(
                               cursorEl
                           );
                       }
   
   
                       scrollToBottom();
                   }
   
   
                   /* ----------------------------------------
                      TTS AUDIO
                      ---------------------------------------- */
   
                   if (
                       data.audio &&
                       ttsPlayer
                   ) {
   
                       ttsPlayer.enqueue(
                           data.audio
                       );
                   }
   
   
                   /* ----------------------------------------
                      ERROR
                      ---------------------------------------- */
   
                   if (data.error) {
   
                       throw new Error(
                           data.error
                       );
                   }
   
   
                   /* ----------------------------------------
                      DONE
                      ---------------------------------------- */
   
                   if (data.done === true) {
   
                       streamFinished = true;
   
                       break;
                   }
               }
           }
   
   
           if (cursorEl) {
               cursorEl.remove();
           }
   
   
           // Final cleanup: remove [object Object] artifacts
           const textSpan =
               contentEl.querySelector(
                   '.msg-stream-text'
               );
   
   
           let cleanFinal =
               fullResponse
                   .replace(
                       /\[object Object\]/g,
                       ''
                   )
                   .replace(
                       /[ \t]+/g,
                       ' '
                   )
                   .trim();
   
   
           if (
               textSpan &&
               !cleanFinal
           ) {
   
               textSpan.textContent =
                   '(No response)';
   
           } else if (textSpan) {
   
               textSpan.textContent =
                   cleanFinal;
           }
   
   
       } catch (error) {
   
           removeTypingIndicator();
   
           console.error(
               'Chat error:',
               error
           );
   
   
           addMessage(
               'assistant',
               `Something went wrong: ${error.message}`
           );
   
       } finally {
   
           isStreaming = false;
   
           if (sendBtn) {
               sendBtn.disabled = false;
           }
       }
   }
   
   
   /* ================================================================
      NEW CHAT
      ================================================================ */
   
   function newChat() {
   
       if (ttsPlayer) {
           ttsPlayer.stop();
       }
   
   
       sessionId = null;
   
   
       if (chatMessages) {
   
           chatMessages.innerHTML = '';
   
           chatMessages.appendChild(
               createWelcome()
           );
       }
   
   
       if (messageInput) {
   
           messageInput.value = '';
   
           autoResizeInput();
       }
   
   
       setGreeting();
   
   
       if (searchResultsWidget) {
   
           searchResultsWidget.classList.remove(
               'open'
           );
       }
   
   
       if (searchResultsToggle) {
   
           searchResultsToggle.style.display =
               'none';
       }
   }
   
   
   function createWelcome() {
   
       const hour =
           new Date().getHours();
   
   
       let greeting =
           'Good evening.';
   
   
       if (hour < 12) {
   
           greeting =
               'Good morning.';
   
       } else if (hour < 17) {
   
           greeting =
               'Good afternoon.';
   
       } else if (hour >= 22) {
   
           greeting =
               'Burning the midnight oil?';
       }
   
   
       const div =
           document.createElement('div');
   
   
       div.className =
           'welcome-screen';
   
       div.id =
           'welcome-screen';
   
   
       div.innerHTML = `
           <div class="welcome-icon">
               <svg
                   width="48"
                   height="48"
                   viewBox="0 0 24 24"
                   fill="none"
                   stroke="currentColor"
                   stroke-width="1.5">
                   <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                   <path d="M2 17l10 5 10-5"/>
                   <path d="M2 12l10 5 10-5"/>
               </svg>
           </div>
   
           <h2 class="welcome-title">
               ${greeting}
           </h2>
   
           <p class="welcome-sub">
               How may I assist you today?
           </p>
   
           <div class="welcome-chips">
   
               <button
                   class="chip"
                   data-msg="What can you do?">
                   What can you do?
               </button>
   
               <button
                   class="chip"
                   data-msg="Open YouTube for me">
                   Open YouTube
               </button>
   
               <button
                   class="chip"
                   data-msg="Tell me a fun fact">
                   Fun fact
               </button>
   
               <button
                   class="chip"
                   data-msg="Play some music">
                   Play music
               </button>
   
           </div>
       `;
   
   
       div.querySelectorAll(
           '.chip'
       ).forEach(chip => {
   
           chip.addEventListener(
               'click',
               () => {
   
                   if (!isStreaming) {
   
                       sendMessage(
                           chip.dataset.msg
                       );
                   }
               }
           );
       });
   
   
       return div;
   }
   
   
   /* ================================================================
      MODE
      ================================================================ */
   
   function setMode(mode) {
   
       if (
           mode !== 'general' &&
           mode !== 'realtime' &&
           mode !== 'agent'
       ) {
           return;
       }
   
       currentMode = mode;
   
   
       if (btnGeneral) {
   
           btnGeneral.classList.toggle(
               'active',
               mode === 'general'
           );
       }
   
   
       if (btnRealtime) {
   
           btnRealtime.classList.toggle(
               'active',
               mode === 'realtime'
           );
       }
   
   
       if (btnAgent) {
   
           btnAgent.classList.toggle(
               'active',
               mode === 'agent'
           );
       }
   
   
       if (modeSlider) {
   
           modeSlider.classList.toggle(
               'right',
               mode === 'realtime'
           );
   
           modeSlider.classList.toggle(
               'agent',
               mode === 'agent'
           );
       }
   
   
       if (modeLabel) {
   
           if (mode === 'general') {
   
               modeLabel.textContent =
                   'General Mode';
   
           } else if (mode === 'realtime') {
   
               modeLabel.textContent =
                   'Realtime Mode';
   
           } else {
   
               modeLabel.textContent =
                   'Agent Mode';
           }
       }
   }
   
   
   /* ================================================================
      INPUT
      ================================================================ */
   
   function autoResizeInput() {
   
       if (!messageInput) {
           return;
       }
   
       messageInput.style.height =
           'auto';
   
   
       messageInput.style.height =
           Math.min(
               messageInput.scrollHeight,
               120
           ) + 'px';
   }
   
   
   /* ================================================================
      HEALTH
      ================================================================ */
   
   async function checkHealth() {
   
       try {
   
           const response =
               await fetch(
                   `${API}/health`
               );
   
   
           const data =
               await response.json();
   
   
           const online =
               data.status === 'healthy';
   
   
           if (statusDot) {
   
               statusDot.classList.toggle(
                   'offline',
                   !online
               );
           }
   
   
           if (statusText) {
   
               statusText.textContent =
                   online
                       ? 'Online'
                       : 'Offline';
           }
   
       } catch (_) {
   
           if (statusDot) {
   
               statusDot.classList.add(
                   'offline'
               );
           }
   
   
           if (statusText) {
   
               statusText.textContent =
                   'Offline';
           }
       }
   }
   
   
   /* ================================================================
      EVENTS
      ================================================================ */
   
   function bindEvents() {
   
       if (sendBtn) {
   
           sendBtn.addEventListener(
               'click',
               () => {
   
                   if (!isStreaming) {
                       sendMessage();
                   }
               }
           );
       }
   
   
       if (messageInput) {
   
           messageInput.addEventListener(
               'keydown',
               event => {
   
                   if (
                       event.key === 'Enter' &&
                       !event.shiftKey
                   ) {
   
                       event.preventDefault();
   
                       if (!isStreaming) {
                           sendMessage();
                       }
                   }
               }
           );
   
   
           messageInput.addEventListener(
               'input',
               () => {
   
                   autoResizeInput();
   
                   if (charCount) {
   
                       const length =
                           messageInput.value.length;
   
                       charCount.textContent =
                           length > 100
                               ? `${length.toLocaleString()} / 32,000`
                               : '';
                   }
               }
           );
       }
   
   
       if (micBtn) {
   
           micBtn.addEventListener(
               'click',
               () => {
   
                   if (isListening) {
   
                       stopListening();
   
                   } else {
   
                       startListening();
                   }
               }
           );
       }
   
   
       if (ttsBtn) {
   
           ttsBtn.addEventListener(
               'click',
               () => {
   
                   if (!ttsPlayer) {
                       return;
                   }
   
   
                   ttsPlayer.enabled =
                       !ttsPlayer.enabled;
   
   
                   ttsBtn.classList.toggle(
                       'tts-active',
                       ttsPlayer.enabled
                   );
   
   
                   if (!ttsPlayer.enabled) {
   
                       ttsPlayer.stop();
                   }
               }
           );
       }
   
   
       if (newChatBtn) {
   
           newChatBtn.addEventListener(
               'click',
               newChat
           );
       }
   
   
       if (btnGeneral) {
   
           btnGeneral.addEventListener(
               'click',
               () => setMode('general')
           );
       }
   
   
       if (btnRealtime) {
   
           btnRealtime.addEventListener(
               'click',
               () => setMode('realtime')
           );
       }
   
   
       if (btnAgent) {
   
           btnAgent.addEventListener(
               'click',
               () => setMode('agent')
           );
       }
   
   
       document
           .querySelectorAll('.chip')
           .forEach(chip => {
   
               chip.addEventListener(
                   'click',
                   () => {
   
                       if (!isStreaming) {
   
                           sendMessage(
                               chip.dataset.msg
                           );
                       }
                   }
               );
           });
   
   
       if (searchResultsToggle) {
   
           searchResultsToggle.addEventListener(
               'click',
               () => {
   
                   if (searchResultsWidget) {
   
                       searchResultsWidget.classList.add(
                           'open'
                       );
                   }
               }
           );
       }
   
   
       if (
           searchResultsClose &&
           searchResultsWidget
       ) {
   
           searchResultsClose.addEventListener(
               'click',
               () => {
   
                   searchResultsWidget.classList.remove(
                       'open'
                   );
               }
           );
       }
   }
   
   
   /* ================================================================
      START
      ================================================================ */
   
   document.addEventListener(
       'DOMContentLoaded',
       init
   );