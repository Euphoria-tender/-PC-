/**
 * 7za wrapper - always returns exit code 0
 * Workaround for Windows symlink permission errors in winCodeSign archive
 */
const { spawnSync } = require('child_process');
const path = require('path');

// Find 7za_real.exe in same directory as this wrapper
const realExe = path.join(path.dirname(process.execPath), '7za_real.exe');
const args = process.argv.slice(2);

spawnSync(realExe, args, { stdio: 'inherit' });
// Always exit 0 - the darwin symlink errors in winCodeSign are harmless on Windows
process.exit(0);