import subprocess, os
repo = r'C:\Users\cesar\Desktop\Files\Work\Projects\Personal\hermes-windows-voice-bridge'
os.chdir(repo)

os.remove('_cleanup_deprecated.py')
subprocess.run(['git', 'rm', '-f', '_cleanup_deprecated.py'], capture_output=True, text=True)
r = subprocess.run(['git', 'add', '-A'], capture_output=True, text=True)
r = subprocess.run(['git', 'commit', '-m', 'chore: remove cleanup helper script'], capture_output=True, text=True)
print(f'Commit: {r.returncode}')
r = subprocess.run(['git', 'push'], capture_output=True, text=True)
print(f'Push: {r.returncode}')

# Final verification
r = subprocess.run(['git', 'log', '--oneline', '-5'], capture_output=True, text=True)
print(f'\nFinal log:\n{r.stdout}')

r = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
print(f'Status: {r.stdout or "CLEAN"}')

# List what remains in src/
print('\n=== src/ structure ===')
for root, dirs, files in os.walk('src'):
    level = root.replace('src', '').count(os.sep)
    indent = '  ' * level
    print(f'{indent}{os.path.basename(root)}/')
    subindent = '  ' * (level + 1)
    for f in sorted(files):
        if f.endswith('.py') and '__pycache__' not in root:
            print(f'{subindent}{f}')