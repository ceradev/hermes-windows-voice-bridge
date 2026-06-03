import os, subprocess
repo = r'C:\Users\cesar\Desktop\Files\Work\Projects\Personal\hermes-windows-voice-bridge'
os.chdir(repo)

deleted = []

def rm(path):
    if os.path.exists(path):
        os.remove(path)
        subprocess.run(['git', 'rm', '-f', path], capture_output=True, text=True)
        deleted.append(path)
        print(f'DELETED: {path}')

# Entry point files (old/duplicate systems)
for f in [
    'src/windows_hermes_voice.py',
    'src/windows_hermes_voice_tray.py',
    'src/windows_hermes_voice_control.py',
    'src/windows_hermes_voice_panel_api.py',
]:
    rm(f)

# Deprecated scripts
for f in [
    'scripts/run_voice.ps1',
    'scripts/run_voice_desktop.ps1',
    'scripts/run_voice_panel_web.ps1',
    'scripts/run_voice_watchdog.ps1',
]:
    rm(f)

# hermes_voice_bridge namespace (stubs, no function)
import shutil
for root, dirs, files in os.walk('src/hermes_voice_bridge'):
    for f in files:
        p = os.path.join(root, f)
        os.remove(p)
        subprocess.run(['git', 'rm', '-f', p], capture_output=True, text=True)
        print(f'DELETED: {p}')
    for d in dirs:
        # remove __pycache__
        pd = os.path.join(root, d, '__pycache__')
        if os.path.exists(pd):
            shutil.rmtree(pd, ignore_errors=True)

# Remove the whole directory
if os.path.exists('src/hermes_voice_bridge'):
    subprocess.run(['git', 'rm', '-r', '-f', 'src/hermes_voice_bridge'], capture_output=True, text=True)
    print('DELETED: src/hermes_voice_bridge/ (namespace)')

# Commit and push
r = subprocess.run(['git', 'add', '-A'], capture_output=True, text=True)
r = subprocess.run(['git', 'commit', '-m', 'chore: remove deprecated entry points and unused hermes_voice_bridge namespace'], capture_output=True, text=True)
print(f'\nCommit: {r.returncode} - {r.stdout[:200]}')
r = subprocess.run(['git', 'push'], capture_output=True, text=True)
print(f'Push: {r.returncode}')

print(f'\nTotal deleted: {len([x for x in deleted if os.path.exists(x.replace(repo, repo))])} items')
r = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
print(f'Status: {r.stdout or "CLEAN"}')