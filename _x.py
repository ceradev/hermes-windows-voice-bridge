import subprocess, os
repo = r'C:\Users\cesar\Desktop\Files\Work\Projects\Personal\hermes-windows-voice-bridge'
os.chdir(repo)

os.remove('_cleanup.py')
subprocess.run(['git', 'rm', '-f', '_cleanup.py'], capture_output=True, text=True)
r = subprocess.run(['git', 'add', '-A'], capture_output=True, text=True)
r = subprocess.run(['git', 'commit', '-m', 'chore: remove cleanup script'], capture_output=True, text=True)
print(f'Commit: {r.returncode}')
r = subprocess.run(['git', 'push'], capture_output=True, text=True)
print(f'Push: {r.returncode}')
r = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
print(f'Status: {r.stdout or "CLEAN"}')