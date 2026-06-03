import subprocess, os
repo = r'C:\Users\cesar\Desktop\Files\Work\Projects\Personal\hermes-windows-voice-bridge'
os.chdir(repo)

os.remove('_final.py')
subprocess.run(['git', 'rm', '-f', '_final.py'], capture_output=True, text=True)
r = subprocess.run(['git', 'add', '-A'], capture_output=True, text=True)
r = subprocess.run(['git', 'commit', '-m', 'chore: remove final helper script'], capture_output=True, text=True)
print(f'Commit: {r.returncode}')
r = subprocess.run(['git', 'push'], capture_output=True, text=True)
print(f'Push: {r.returncode}')

r = subprocess.run(['git', 'log', '--oneline', '-5'], capture_output=True, text=True)
print(f'\nLog:\n{r.stdout}')
r = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
print(f'Status: {r.stdout or "CLEAN"}')

print('\n=== FINAL ROOT FILES ===')
for f in sorted(os.listdir('.')):
    if os.path.isfile(f):
        print(f'  {f} ({os.path.getsize(f)}b)')

print('\n=== FINAL SCRIPTS ===')
for f in sorted(os.listdir('scripts')):
    print(f'  scripts/{f}')

print('\n=== FINAL DOCS ===')
if os.path.exists('docs') and os.listdir('docs'):
    for root, dirs, files in os.walk('docs'):
        for f2 in files:
            print(f'  {os.path.join(root, f2)}')
else:
    print('  (empty)')

print('\n=== STATE ===')
if os.path.exists('state'):
    for f in sorted(os.listdir('state')):
        print(f'  state/{f}')