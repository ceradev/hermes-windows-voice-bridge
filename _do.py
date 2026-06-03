import subprocess, os, shutil
repo = r'C:\Users\cesar\Desktop\Files\Work\Projects\Personal\hermes-windows-voice-bridge'
os.chdir(repo)

# Remove empty overlay/ directory if nothing inside
overlay = 'src/platform/windows/overlay'
if os.path.exists(overlay):
    remaining = os.listdir(overlay)
    if not remaining:
        os.rmdir(overlay)
        print(f'Removed empty: {overlay}')
    else:
        print(f'overlay/ still has: {remaining}')

# Remove _fix_cleanup.py
if os.path.exists('_fix_cleanup.py'):
    os.remove('_fix_cleanup.py')
    subprocess.run(['git', 'rm', '-f', '_fix_cleanup.py'], capture_output=True, text=True)
    print('Removed _fix_cleanup.py')

r = subprocess.run(['git', 'add', '-A'], capture_output=True, text=True)
r = subprocess.run(['git', 'commit', '-m', 'chore: remove empty overlay dir and cleanup scripts'], capture_output=True, text=True)
print(f'Commit: {r.returncode}')
r = subprocess.run(['git', 'push'], capture_output=True, text=True)
print(f'Push: {r.returncode}')

r = subprocess.run(['git', 'log', '--oneline', '-5'], capture_output=True, text=True)
print(f'\nLog:\n{r.stdout}')
r = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
print(f'Status: {r.stdout or "CLEAN"}')