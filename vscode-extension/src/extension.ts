import * as vscode from 'vscode';
import { GodHandClient } from './client';
import { GodHandPanel } from './panel';
import { GodHandTreeDataProvider } from './treeProvider';

let client: GodHandClient | undefined;
let panel: GodHandPanel | undefined;
let treeDataProvider: GodHandTreeDataProvider | undefined;

export function activate(context: vscode.ExtensionContext) {
    console.log('GodHand extension is now active!');

    const config = vscode.workspace.getConfiguration('godhand');

    // Initialize client
    client = new GodHandClient(config.get('serverHost') || 'http://127.0.0.1:8000');

    // Initialize tree data provider
    treeDataProvider = new GodHandTreeDataProvider();
    vscode.window.registerTreeDataProvider('godhandPanel', treeDataProvider);

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('godhand.start', async () => {
            try {
                await client?.connect();
                vscode.window.showInformationMessage('GodHand connected successfully!');
                vscode.commands.executeCommand('setContext', 'godhand.running', true);
                treeDataProvider?.refresh();
            } catch (error) {
                vscode.window.showErrorMessage(`Failed to connect to GodHand: ${error}`);
            }
        }),

        vscode.commands.registerCommand('godhand.stop', async () => {
            client?.disconnect();
            vscode.window.showInformationMessage('GodHand disconnected');
            vscode.commands.executeCommand('setContext', 'godhand.running', false);
            treeDataProvider?.refresh();
        }),

        vscode.commands.registerCommand('godhand.execute', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showWarningMessage('No active editor');
                return;
            }

            const selection = editor.selection;
            const command = editor.document.getText(selection.isEmpty ?
                editor.document.lineAt(selection.active.line).range : selection);

            if (!command.trim()) {
                vscode.window.showWarningMessage('No command to execute');
                return;
            }

            try {
                const result = await client?.execute(command);
                if (config.get('showNotifications')) {
                    vscode.window.showInformationMessage(`Executed: ${command}`);
                }
                treeDataProvider?.addToHistory(command, result);
            } catch (error) {
                vscode.window.showErrorMessage(`Execution failed: ${error}`);
            }
        }),

        vscode.commands.registerCommand('godhand.record', async () => {
            const name = await vscode.window.showInputBox({
                prompt: 'Enter a name for this recording',
                placeHolder: 'My Automation'
            });

            if (name) {
                try {
                    await client?.startRecording(name);
                    vscode.window.showInformationMessage(`Started recording: ${name}`);
                    vscode.commands.executeCommand('setContext', 'godhand.recording', true);
                } catch (error) {
                    vscode.window.showErrorMessage(`Failed to start recording: ${error}`);
                }
            }
        }),

        vscode.commands.registerCommand('godhand.stopRecording', async () => {
            try {
                await client?.stopRecording();
                vscode.window.showInformationMessage('Recording saved');
                vscode.commands.executeCommand('setContext', 'godhand.recording', false);
            } catch (error) {
                vscode.window.showErrorMessage(`Failed to stop recording: ${error}`);
            }
        }),

        vscode.commands.registerCommand('godhand.screenshot', async () => {
            try {
                const screenshot = await client?.takeScreenshot();
                if (screenshot) {
                    const panel = vscode.window.createWebviewPanel(
                        'godhandScreenshot',
                        'GodHand Screenshot',
                        vscode.ViewColumn.One,
                        {}
                    );
                    panel.webview.html = `<img src="${screenshot}" style="max-width:100%">`;
                }
            } catch (error) {
                vscode.window.showErrorMessage(`Screenshot failed: ${error}`);
            }
        }),

        vscode.commands.registerCommand('godhand.openPanel', () => {
            if (!panel) {
                panel = new GodHandPanel(context.extensionUri, client!);
            }
            panel.reveal();
        }),

        vscode.commands.registerCommand('godhand.quickCommand', async () => {
            const quickPick = vscode.window.createQuickPick();
            quickPick.items = [
                { label: '$(play) 打开计算器', description: 'open calculator' },
                { label: '$(file-text) 打开记事本', description: 'open notepad' },
                { label: '$(device-camera) 截图', description: 'screenshot' },
                { label: '$(search) 搜索...', description: 'search' },
            ];
            quickPick.placeholder = 'Select a quick command';

            quickPick.onDidAccept(async () => {
                const selected = quickPick.selectedItems[0];
                if (selected) {
                    try {
                        await client?.execute(selected.description!);
                        vscode.window.showInformationMessage(`Executed: ${selected.label}`);
                    } catch (error) {
                        vscode.window.showErrorMessage(`Failed: ${error}`);
                    }
                }
                quickPick.hide();
            });

            quickPick.show();
        })
    );

    // Auto start if configured
    if (config.get('autoStart')) {
        vscode.commands.executeCommand('godhand.start');
    }

    // Set initial context
    vscode.commands.executeCommand('setContext', 'godhand.enabled', true);
}

export function deactivate() {
    client?.disconnect();
}
