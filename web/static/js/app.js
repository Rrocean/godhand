/**
 * GodHand Pro - Frontend Application
 * WebSocket with HTTP fallback + basic UX utilities
 */

class GodHandApp {
    constructor() {
        this.ws = null;
        this.sessionId = null;
        this.reconnectAttempts = 0;
        this.maxReconnects = 5;
        this.commandHistory = [];
        this.historyIndex = -1;
        this.chatLog = [];
        this.settings = this.loadSettings();

        this.dom = {
            chatContainer: document.getElementById('chatContainer'),
            userInput: document.getElementById('userInput'),
            sendBtn: document.getElementById('sendBtn'),
            statusDot: document.getElementById('statusDot'),
            statusText: document.getElementById('statusText'),
            sessionInfo: document.getElementById('sessionInfo'),
            clearBtn: document.getElementById('clearBtn'),
            voiceBtn: document.getElementById('voiceBtn'),
            settingsBtn: document.getElementById('settingsBtn'),
            historyBtn: document.getElementById('historyBtn'),
            exportBtn: document.getElementById('exportBtn'),
            settingsModal: document.getElementById('settingsModal'),
            closeSettings: document.getElementById('closeSettings'),
            execMode: document.getElementById('execMode'),
            confirmBeforeExec: document.getElementById('confirmBeforeExec'),
            showDetailedLog: document.getElementById('showDetailedLog'),
            quickCommands: document.getElementById('quickCommands'),
            modeToggle: document.getElementById('modeToggle')
        };

        this.init();
    }

    init() {
        this.bindEvents();
        this.connectWebSocket();
        this.applySettings();
        this.dom.userInput.focus();
    }

    bindEvents() {
        this.dom.sendBtn.addEventListener('click', () => this.sendMessage());

        this.dom.userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        this.dom.userInput.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowUp') {
                e.preventDefault();
                this.navigateHistory(-1);
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                this.navigateHistory(1);
            }
        });

        this.dom.clearBtn.addEventListener('click', () => {
            this.dom.userInput.value = '';
            this.dom.userInput.focus();
        });

        this.dom.voiceBtn.addEventListener('click', () => {
            this.showNotification('语音输入功能开发中...', 'info');
        });

        this.dom.settingsBtn.addEventListener('click', () => {
            this.dom.settingsModal.classList.add('active');
        });

        this.dom.closeSettings.addEventListener('click', () => {
            this.dom.settingsModal.classList.remove('active');
        });

        this.dom.settingsModal.addEventListener('click', (e) => {
            if (e.target === this.dom.settingsModal) {
                this.dom.settingsModal.classList.remove('active');
            }
        });

        ['execMode', 'confirmBeforeExec', 'showDetailedLog'].forEach(id => {
            this.dom[id].addEventListener('change', () => this.saveSettings());
        });

        this.dom.historyBtn.addEventListener('click', () => {
            this.showHistory();
        });

        this.dom.exportBtn.addEventListener('click', () => {
            this.exportHistory();
        });

        this.dom.quickCommands.addEventListener('click', (e) => {
            const btn = e.target.closest('.quick-btn');
            if (!btn) return;
            const cmd = btn.dataset.cmd;
            if (!cmd) return;
            this.dom.userInput.value = cmd;
            this.sendMessage();
        });

        if (this.dom.modeToggle) {
            this.dom.modeToggle.addEventListener('click', (e) => {
                const btn = e.target.closest('.mode-btn');
                if (!btn) return;
                this.setExecMode(btn.dataset.mode);
            });
        }
    }

    // ==================== WebSocket ====================

    connectWebSocket() {
        if (this.reconnectAttempts >= this.maxReconnects) {
            this.updateStatus('disconnected', '已切换到 HTTP');
            this.showNotification('WebSocket 连接失败，将使用 HTTP 模式', 'warning');
            return;
        }

        this.sessionId = this.generateSessionId();
        this.dom.sessionInfo.textContent = `Session: ${this.sessionId.substr(0, 12)}...`;

        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsHost = window.location.host || '127.0.0.1:8000';
        const wsUrl = `${wsProtocol}//${wsHost}/ws/${this.sessionId}`;

        console.log('[WebSocket] Connecting to:', wsUrl);
        this.updateStatus('connecting', '连接中...');

        try {
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log('[WebSocket] Connected');
                this.updateStatus('connected', '已连接');
                this.reconnectAttempts = 0;
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                } catch (e) {
                    console.error('[WebSocket] Parse error:', e);
                }
            };

            this.ws.onclose = () => {
                console.log('[WebSocket] Closed');
                this.updateStatus('disconnected', '已断开');
                this.reconnectAttempts++;
                setTimeout(() => this.connectWebSocket(), 3000);
            };

            this.ws.onerror = (error) => {
                console.error('[WebSocket] Error:', error);
                this.updateStatus('disconnected', '连接错误');
            };
        } catch (e) {
            console.error('[WebSocket] Connection error:', e);
            this.updateStatus('disconnected', '连接失败');
            this.reconnectAttempts++;
            setTimeout(() => this.connectWebSocket(), 3000);
        }
    }

    updateStatus(status, text) {
        this.dom.statusDot.className = `status-dot ${status}`;
        this.dom.statusText.textContent = text;
    }

    handleWebSocketMessage(data) {
        switch(data.type) {
            case 'system':
                this.addSystemMessage(data.content);
                break;
            case 'thinking':
                this.addThinkingMessage();
                break;
            case 'parsed':
                this.removeThinkingMessage();
                if (data.actions) {
                    this.showActionList(data.actions, data.content);
                }
                break;
            case 'executing':
                this.addAssistantMessage(`执行中：${data.content}`);
                break;
            case 'result': {
                const output = data.output || data.error || '完成';
                this.addResultCard(data.success, output);
                break;
            }
            case 'progress':
                this.updateProgress(data);
                break;
            case 'screenshot':
                this.showScreenshot(data.url);
                break;
            case 'done':
                this.enableSendButton();
                break;
            case 'error':
                this.removeThinkingMessage();
                this.addErrorMessage(data.content);
                this.enableSendButton();
                break;
            default:
                break;
        }
        this.scrollToBottom();
    }

    // ==================== HTTP Fallback ====================

    async sendViaHTTP(text) {
        this.updateStatus('connecting', '发送中...');

        try {
            const response = await fetch('/api/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    command: text,
                    session_id: this.sessionId,
                    mode: this.settings.execMode
                })
            });

            const data = await response.json();

            if (data.actions?.length > 0) {
                this.showActionList(data.actions, `解析出 ${data.actions.length} 个动作`);
            }

            if (data.results) {
                data.results.forEach(result => {
                    const output = result.output || result.error || '完成';
                    this.addResultCard(result.success, output);
                });
            }

            this.updateStatus('disconnected', 'HTTP 模式');
            this.enableSendButton();
        } catch (e) {
            console.error('[HTTP] Error:', e);
            this.addErrorMessage('发送失败：' + e.message);
            this.enableSendButton();
        }
    }

    // ==================== Message Handling ====================

    sendMessage() {
        const text = this.dom.userInput.value.trim();
        if (!text) return;

        this.commandHistory.push(text);
        this.historyIndex = this.commandHistory.length;

        this.addUserMessage(text);
        this.dom.userInput.value = '';
        this.disableSendButton();

        if (this.settings.confirmBeforeExec) {
            this.showConfirmation(text);
            return;
        }

        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                message: text,
                mode: this.settings.execMode
            }));
        } else {
            this.sendViaHTTP(text);
        }
    }

    showConfirmation(text) {
        this.addSystemMessage(
            `确认执行：“${text}”？ ` +
            `<button onclick="app.confirmExec(true)">确认</button> ` +
            `<button onclick="app.confirmExec(false)">取消</button>`
        );
        this.pendingCommand = text;
        this.enableSendButton();
    }

    confirmExec(confirmed) {
        if (confirmed && this.pendingCommand) {
            this.disableSendButton();
            if (this.ws?.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ message: this.pendingCommand }));
            } else {
                this.sendViaHTTP(this.pendingCommand);
            }
        }
        this.pendingCommand = null;
        const messages = this.dom.chatContainer.querySelectorAll('.message.system');
        messages[messages.length - 1]?.remove();
    }

    navigateHistory(direction) {
        if (this.commandHistory.length === 0) return;

        this.historyIndex += direction;

        if (this.historyIndex < 0) {
            this.historyIndex = 0;
        } else if (this.historyIndex > this.commandHistory.length) {
            this.historyIndex = this.commandHistory.length;
        }

        if (this.historyIndex === this.commandHistory.length) {
            this.dom.userInput.value = '';
        } else {
            this.dom.userInput.value = this.commandHistory[this.historyIndex];
        }
    }

    // ==================== UI Helpers ====================

    addMessage(role, content, isHTML = false) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${role}`;

        const avatar = role === 'user' ? '你' : (role === 'system' ? '系统' : 'GodHand');
        const name = role === 'user' ? '你' : (role === 'system' ? '系统' : 'GodHand');

        msgDiv.innerHTML = `
            <div class="message-header">
                ${role !== 'user'
                    ? `<div class="message-avatar">${avatar}</div><span>${name}</span>`
                    : `<span>${name}</span><div class="message-avatar">${avatar}</div>`}
            </div>
            <div class="message-content">${isHTML ? content : this.escapeHtml(content)}</div>
        `;

        this.dom.chatContainer.appendChild(msgDiv);
        this.chatLog.push({
            role,
            content,
            timestamp: new Date().toISOString()
        });
        this.scrollToBottom();
        return msgDiv;
    }

    addUserMessage(text) {
        return this.addMessage('user', text);
    }

    addAssistantMessage(text) {
        return this.addMessage('assistant', text);
    }

    addSystemMessage(text) {
        return this.addMessage('system', text, true);
    }

    addErrorMessage(text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message error';
        msgDiv.innerHTML = `
            <div class="message-header">
                <div class="message-avatar">错误</div>
                <span>错误</span>
            </div>
            <div class="message-content">${this.escapeHtml(text)}</div>
        `;
        this.dom.chatContainer.appendChild(msgDiv);
        this.chatLog.push({
            role: 'error',
            content: text,
            timestamp: new Date().toISOString()
        });
        this.scrollToBottom();
    }

    showActionList(actions, title) {
        let content = title;
        if (this.settings.showDetailedLog) {
            content += `\n\n`;
            actions.forEach((a, i) => {
                content += `${i + 1}. ${this.getActionEmoji(a.type)} ${a.description}\n`;
            });
        }
        this.addAssistantMessage(content);
    }

    addResultCard(success, output) {
        const card = document.createElement('div');
        card.className = `result-card ${success ? 'success' : 'error'}`;
        card.style.marginLeft = '40px';
        card.style.marginBottom = '10px';
        card.textContent = output;
        this.dom.chatContainer.appendChild(card);
        this.scrollToBottom();
    }

    addThinkingMessage() {
        this.thinkingMsg = document.createElement('div');
        this.thinkingMsg.className = 'message assistant';
        this.thinkingMsg.id = 'thinking-msg';
        this.thinkingMsg.innerHTML = `
            <div class="message-header">
                <div class="message-avatar">GodHand</div>
                <span>GodHand</span>
            </div>
            <div class="message-content">
                <div class="thinking-bubble">
                    <div class="thinking-dots">
                        <span></span><span></span><span></span>
                    </div>
                    <span>思考中...</span>
                </div>
            </div>
        `;
        this.dom.chatContainer.appendChild(this.thinkingMsg);
        this.scrollToBottom();
    }

    removeThinkingMessage() {
        if (this.thinkingMsg) {
            this.thinkingMsg.remove();
            this.thinkingMsg = null;
        }
        const existing = document.getElementById('thinking-msg');
        if (existing) existing.remove();
    }

    showScreenshot(url) {
        const img = document.createElement('img');
        img.src = url;
        img.style.maxWidth = '100%';
        img.style.borderRadius = '12px';
        img.style.marginTop = '8px';
        img.style.marginLeft = '40px';

        const container = document.createElement('div');
        container.appendChild(img);
        this.dom.chatContainer.appendChild(container);
        this.scrollToBottom();
    }

    updateProgress(data) {
        console.log('[Progress]', data);
    }

    // ==================== Settings ====================

    loadSettings() {
        const defaults = {
            execMode: 'auto',
            confirmBeforeExec: false,
            showDetailedLog: true
        };

        try {
            const saved = localStorage.getItem('godhand_settings');
            return saved ? { ...defaults, ...JSON.parse(saved) } : defaults;
        } catch {
            return defaults;
        }
    }

    saveSettings() {
        this.settings = {
            execMode: this.dom.execMode.value,
            confirmBeforeExec: this.dom.confirmBeforeExec.checked,
            showDetailedLog: this.dom.showDetailedLog.checked
        };
        localStorage.setItem('godhand_settings', JSON.stringify(this.settings));
    }

    applySettings() {
        this.dom.execMode.value = this.settings.execMode;
        this.dom.confirmBeforeExec.checked = this.settings.confirmBeforeExec;
        this.dom.showDetailedLog.checked = this.settings.showDetailedLog;
        this.syncModeButtons();
    }

    syncModeButtons() {
        if (!this.dom.modeToggle) return;
        const buttons = this.dom.modeToggle.querySelectorAll('.mode-btn');
        buttons.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.mode === this.settings.execMode);
        });
    }

    // ==================== History ====================

    showHistory() {
        if (this.commandHistory.length === 0) {
            this.showNotification('暂无历史记录', 'info');
            return;
        }

        let content = '最近指令：\n\n';
        this.commandHistory.slice(-10).forEach((cmd, i) => {
            content += `${i + 1}. ${cmd}\n`;
        });
        this.addAssistantMessage(content);
    }

    exportHistory() {
        const payload = {
            session_id: this.sessionId,
            created_at: new Date().toISOString(),
            commands: this.commandHistory,
            messages: this.chatLog
        };
        const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `godhand_history_${Date.now()}.json`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
        this.showNotification('已导出历史记录', 'info');
    }

    // ==================== Utilities ====================

    generateSessionId() {
        return 'gh_' + Date.now().toString(36) + '_' + Math.random().toString(36).substr(2, 5);
    }

    getActionEmoji(type) {
        const labels = {
            open_app: '打开',
            type_text: '输入',
            press_key: '按键',
            hotkey: '快捷键',
            click: '点击',
            wait: '等待',
            search: '搜索',
            file: '文件',
            system: '系统',
            gui: 'GUI',
            unknown: '未知'
        };
        return labels[type] || '动作';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML.replace(/\n/g, '<br>');
    }

    scrollToBottom() {
        this.dom.chatContainer.scrollTop = this.dom.chatContainer.scrollHeight;
    }

    disableSendButton() {
        this.dom.sendBtn.disabled = true;
        this.dom.sendBtn.innerHTML = `
            <div class="loading"><span></span><span></span><span></span></div>
        `;
    }

    enableSendButton() {
        this.dom.sendBtn.disabled = false;
        this.dom.sendBtn.innerHTML = `
            <span>发送</span>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9"></polygon>
            </svg>
        `;
    }

    showNotification(message, type = 'info') {
        this.addSystemMessage(`${type === 'warning' ? '提醒' : '提示'} ${message}`);
    }

    setExecMode(mode) {
        if (!mode) return;
        this.dom.execMode.value = mode;
        this.settings.execMode = mode;
        this.saveSettings();
        this.syncModeButtons();
    }
}

const app = new GodHandApp();
window.GodHandApp = GodHandApp;
