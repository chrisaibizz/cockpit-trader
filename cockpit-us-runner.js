// cockpit-us-runner.js
// Liest Prompt-Datei und uebergibt sie korrekt an claude CLI via Node.js spawn().
// Hintergrund: PowerShell 5.1 hat einen bekannten Bug beim Uebergeben von mehrzeiligen
// Strings an native Commands (word-splitting bei Strings mit "..." oder Zeilenumbruechen).
// Node.js spawn() umgeht Windows CreateProcess cmdline-Parsing komplett.

const { spawn } = require('child_process');
const fs = require('fs');

const promptFile = process.argv[2] || 'C:/Users/chris/TradingFloor/cockpit-us-prompt.txt';
const allowedTools = process.argv[3] || 'mcp__tradingview__*,Bash,Read,Write';

let prompt;
try {
  prompt = fs.readFileSync(promptFile, 'utf8').trim();
} catch (e) {
  console.error('Fehler beim Lesen der Prompt-Datei:', e.message);
  process.exit(1);
}

const child = spawn('claude', [
  '-p', prompt,
  '--allowedTools', allowedTools,
  '--dangerously-skip-permissions'
], { stdio: 'inherit', windowsHide: false });

child.on('error', (err) => {
  console.error('Fehler beim Starten von claude:', err.message);
  process.exit(1);
});

child.on('exit', (code) => process.exit(code || 0));
