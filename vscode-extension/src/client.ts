import axios from 'axios';
import WebSocket from 'ws';
import { EventEmitter } from 'events';

export interface ExecutionResult {
    success: boolean;
    command: string;
    result: any;
    timestamp: string;
}

export class GodHandClient extends EventEmitter {
    private baseUrl: string;
    private ws: WebSocket | null = null;
    private sessionId: string;

    constructor(baseUrl: string) {
        super();
        this.baseUrl = baseUrl;
        this.sessionId = `vscode_${Date.now()}`;
    }

    async connect(): Promise<void> {
        // Check HTTP connection
        const response = await axios.get(`${this.baseUrl}/api/health`);
        if (response.data.status !== 'ok') {
            throw new Error('GodHand server not ready');
        }

        // Connect WebSocket
        const wsUrl = this.baseUrl.replace('http', 'ws') + `/ws/${this.sessionId}`;
        this.ws = new WebSocket(wsUrl);

        return new Promise((resolve, reject) => {
            this.ws!.on('open', () => {
                console.log('GodHand WebSocket connected');
                this.emit('connected');
                resolve();
            });

            this.ws!.on('error', (error) => {
                console.error('WebSocket error:', error);
                this.emit('error', error);
                reject(error);
            });

            this.ws!.on('message', (data) => {
                const message = JSON.parse(data.toString());
                this.emit('message', message);
            });

            this.ws!.on('close', () => {
                console.log('WebSocket closed');
                this.emit('disconnected');
            });
        });
    }

    disconnect(): void {
        this.ws?.close();
        this.ws = null;
    }

    async execute(command: string, mode: string = 'auto'): Promise<ExecutionResult> {
        const response = await axios.post(`${this.baseUrl}/api/execute`, {
            command,
            mode,
            session_id: this.sessionId
        });
        return response.data;
    }

    async plan(instruction: string): Promise<any> {
        const response = await axios.post(`${this.baseUrl}/api/plan`, {
            instruction
        });
        return response.data;
    }

    async detectElements(): Promise<any> {
        const response = await axios.post(`${this.baseUrl}/api/detect`, {});
        return response.data;
    }

    async takeScreenshot(): Promise<string | null> {
        try {
            const response = await axios.get(`${this.baseUrl}/api/screenshot`, {
                responseType: 'arraybuffer'
            });
            const base64 = Buffer.from(response.data, 'binary').toString('base64');
            return `data:image/png;base64,${base64}`;
        } catch (error) {
            console.error('Screenshot failed:', error);
            return null;
        }
    }

    async startRecording(name: string): Promise<void> {
        // Implementation depends on GodHand API
        console.log(`Starting recording: ${name}`);
    }

    async stopRecording(): Promise<void> {
        console.log('Stopping recording');
    }

    isConnected(): boolean {
        return this.ws?.readyState === WebSocket.OPEN;
    }
}
