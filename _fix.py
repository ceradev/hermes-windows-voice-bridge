import subprocess, os
repo = r'C:/Users/cesar/Desktop/Files/Work/Projects/Personal/hermes-windows-voice-bridge'
os.chdir(repo)

# Delete helper files
for f in ['_x.py', '_s.py']:
    if os.path.exists(f):
        os.remove(f)
        subprocess.run(['git', 'rm', '-f', f], capture_output=True, text=True)
        print(f'Deleted: {f}')

# Stage all and commit
r = subprocess.run(['git', 'add', '-A'], capture_output=True, text=True)
r = subprocess.run(['git', 'commit', '-m', 'chore: remove stale helper scripts'], capture_output=True, text=True)
print(f'Commit: {r.returncode}')
r = subprocess.run(['git', 'push'], capture_output=True, text=True)
print(f'Push: {r.returncode}')

r = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
print(f'Status: {r.stdout or "CLEAN"}')