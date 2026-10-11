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

// Check if user requested web mode, desktop app, or CLI
const isWeb = args[0] === 'web' || args.includes('--web');
const isAppRequest = !isWeb && (args.length === 0 || args.includes('--gui') || args.includes('--app') || args.includes('--desktop') || args[0] === 'app' || args[0] === 'desktop' || args[0] === 'gui');

if (isWeb) {
  console.log('⚡ Launching Cyber Turtle Studio Web UI on http://127.0.0.1:8085 ...');
  const pyChild = spawn('python3', ['-m', 'cyber_turtle_studio.cli', 'serve', '--port', '8085'], {
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
  console.log('⚡ Launching Cyber Turtle Studio Desktop Workstation...');
  
  // Find Electron in local node_modules, sibling micro-repos, or system PATH
  const candidateElectronPaths = [
    path.join(rootDir, 'node_modules', '.bin', 'electron'),
    '/media/neo/f2fdda77-178b-4603-ae80-c7aa4cd97908/zoth-micro-repos/NullAI-HexStrike-AI-Terminal/node_modules/.bin/electron',
    '/media/neo/f2fdda77-178b-4603-ae80-c7aa4cd97908/zoth-micro-repos/promptmaster-studio/node_modules/.bin/electron',
    '/media/neo/f2fdda77-178b-4603-ae80-c7aa4cd97908/zoth-micro-repos/jwt-inspector-guard/node_modules/.bin/electron',
    '/media/neo/f2fdda77-178b-4603-ae80-c7aa4cd97908/zoth-micro-repos/envguard-secrets-vault/node_modules/.bin/electron',
    '/media/neo/f2fdda77-178b-4603-ae80-c7aa4cd97908/zoth-micro-repos/cron-rhythm-studio/node_modules/.bin/electron',
    '/media/neo/f2fdda77-178b-4603-ae80-c7aa4cd97908/regex-droid-builder/node_modules/.bin/electron',
    '/media/neo/f2fdda77-178b-4603-ae80-c7aa4cd97908/schema-illustrator-studio/node_modules/.bin/electron',
    '/media/neo/f2fdda77-178b-4603-ae80-c7aa4cd97908/zoth-micro-repos/payload-entropy-studio/node_modules/.bin/electron',
    '/media/neo/f2fdda77-178b-4603-ae80-c7aa4cd97908/zoth-micro-repos/audiocipher-stego-engine/node_modules/.bin/electron',
    '/media/neo/f2fdda77-178b-4603-ae80-c7aa4cd97908/pwa-manifest-builder/node_modules/.bin/electron',
    '/media/neo/f2fdda77-178b-4603-ae80-c7aa4cd97908/certpath-roadmap-studio/node_modules/.bin/electron',
    '/media/neo/f2fdda77-178b-4603-ae80-c7aa4cd97908/subsweep-lead-scanner/node_modules/.bin/electron',
    '/media/neo/f2fdda77-178b-4603-ae80-c7aa4cd97908/web-security-guard/node_modules/.bin/electron',
    '/media/neo/f2fdda77-178b-4603-ae80-c7aa4cd97908/cwv-speed-engine/node_modules/.bin/electron',
    '/media/neo/f2fdda77-178b-4603-ae80-c7aa4cd97908/vector-search-engine/node_modules/.bin/electron',
    '/media/neo/f2fdda77-178b-4603-ae80-c7aa4cd97908/neuro-memory-daemon/node_modules/.bin/electron',
    '/media/neo/f2fdda77-178b-4603-ae80-c7aa4cd97908/aeo-graph-engine/node_modules/.bin/electron',
    '/media/neo/f2fdda77-178b-4603-ae80-c7aa4cd97908/polyglot-framework-exporter/node_modules/.bin/electron',
    '/media/neo/f2fdda77-178b-4603-ae80-c7aa4cd97908/zoth-webgen/node_modules/.bin/electron',
    '/media/neo/f2fdda77-178b-4603-ae80-c7aa4cd97908/deepsearch-research-agent/node_modules/.bin/electron',
    '/media/neo/f2fdda77-178b-4603-ae80-c7aa4cd97908/omnipost-social-engine/node_modules/.bin/electron',
    '/media/neo/f2fdda77-178b-4603-ae80-c7aa4cd97908/nexus-3d-scene-studio/node_modules/.bin/electron',
    '/media/neo/f2fdda77-178b-4603-ae80-c7aa4cd97908/datamosh-glitch-studio/node_modules/.bin/electron',
  ];

  let electronCmd = 'electron';
  for (const p of candidateElectronPaths) {
    if (fs.existsSync(p)) {
      electronCmd = p;
      break;
    }
  }

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
    console.warn(`[CyberTurtle] Electron notice: ${err.message}. Starting web UI on port 8085...`);
    const pyChild = spawn('python3', ['-m', 'cyber_turtle_studio.cli', 'serve', '--port', '8085'], {
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
  // Delegate to Python CLI / MCP engine
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
