#!/usr/bin/env node
/**
 * Cyber Turtle Studio — Unified CLI & Desktop Workstation Launcher
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const rootDir = path.resolve(__dirname, '..');
const srcDir = path.join(rootDir, 'src');
const args = process.argv.slice(2);
const defaultPort = String(process.env.PORT || '8129');

const isWeb = args[0] === 'web' || args.includes('--web');
const isAppRequest =
  !isWeb &&
  (args.includes('--gui') ||
    args.includes('--app') ||
    args.includes('--desktop') ||
    args[0] === 'app' ||
    args[0] === 'desktop' ||
    args[0] === 'gui');

if (isWeb) {
  console.log(`Launching Cyber Turtle Studio Web UI on http://127.0.0.1:${defaultPort} ...`);
  const pyChild = spawn('python3', ['-m', 'cyber_turtle_studio.cli', 'serve', '--port', defaultPort], {
    cwd: rootDir,
    stdio: 'inherit',
    env: {
      ...process.env,
      PYTHONPATH: process.env.PYTHONPATH ? `${srcDir}:${process.env.PYTHONPATH}` : srcDir,
      ZOTH_ZERO_EGRESS: 'true',
    },
  });
  pyChild.on('error', (pyErr) => {
    console.error('[CyberTurtle] Failed to start web server:', pyErr);
  });
} else if (isAppRequest) {
  console.log('Launching Cyber Turtle Studio Desktop Workstation...');
  const localElectron = path.join(rootDir, 'node_modules', '.bin', 'electron');
  const electronCmd = fs.existsSync(localElectron) ? localElectron : 'electron';

  const child = spawn(electronCmd, ['.'], {
    cwd: rootDir,
    stdio: 'inherit',
    env: {
      ...process.env,
      PYTHONPATH: process.env.PYTHONPATH ? `${srcDir}:${process.env.PYTHONPATH}` : srcDir,
      ELECTRON_ENABLE_LOGGING: '1',
      ZOTH_ZERO_EGRESS: 'true',
    },
  });

  child.on('error', (err) => {
    console.warn(`[CyberTurtle] Electron notice: ${err.message}. Starting web UI on port ${defaultPort}...`);
    const pyChild = spawn('python3', ['-m', 'cyber_turtle_studio.cli', 'serve', '--port', defaultPort], {
      cwd: rootDir,
      stdio: 'inherit',
      env: {
        ...process.env,
        PYTHONPATH: process.env.PYTHONPATH ? `${srcDir}:${process.env.PYTHONPATH}` : srcDir,
      },
    });
    pyChild.on('error', (pyErr) => {
      console.error('[CyberTurtle] Failed to start backend:', pyErr);
    });
  });
} else {
  const child = spawn('python3', ['-m', 'cyber_turtle_studio.cli', ...args], {
    cwd: rootDir,
    stdio: 'inherit',
    env: {
      ...process.env,
      PYTHONPATH: process.env.PYTHONPATH ? `${srcDir}:${process.env.PYTHONPATH}` : srcDir,
    },
  });

  child.on('exit', (code) => {
    process.exit(code || 0);
  });
}
