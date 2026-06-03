import subprocess, os, shutil
repo = r'C:\Users\cesar\Desktop\Files\Work\Projects\Personal\hermes-windows-voice-bridge'
os.chdir(repo)

# Remove hermes_voice_bridge namespace (now empty directories)
hermes_bridge = 'src/hermes_voice_bridge'
if os.path.exists(hermes_bridge):
    # Remove all __pycache__ inside it
    for root, dirs, files in os.walk(hermes_bridge):
        for d in dirs:
            if d == '__pycache__':
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
    # Remove remaining empty dirs
    for root, dirs, files in os.walk(hermes_bridge, topdown=False):
        for d in dirs:
            p = os.path.join(root, d)
            if os.path.exists(p) and not os.listdir(p):
                os.rmdir(p)
    # Remove the root if empty
    if os.path.exists(hermes_bridge) and not os.listdir(hermes_bridge):
        os.rmdir(hermes_bridge)
        print(f'Removed empty dir: {hermes_bridge}')
    elif os.path.exists(hermes_bridge):
        remaining = os.listdir(hermes_bridge)
        print(f'Non-empty, remaining: {remaining}')
        # Force remove whatever's left
        shutil.rmtree(hermes_bridge, ignore_errors=True)
        print(f'Force removed: {hermes_bridge}')

# Also remove any orphaned __pycache__ directories in src/
for root, dirs, files in os.walk('src'):
    for d in dirs:
        if d == '__pycache__':
            p = os.path.join(root, d)
            shutil.rmtree(p, ignore_errors=True)
            print(f'Removed: {p}')

# Remove _final_cleanup.py
if os.path.exists('_final_cleanup.py'):
    os.remove('_final_cleanup.py')
    subprocess.run(['git', 'rm', '-f', '_final_cleanup.py'], capture_output=True, text=True)
    print('Removed _final_cleanup.py')

# Commit
r = subprocess.run(['git', 'add', '-A'], capture_output=True, text=True)
r = subprocess.run(['git', 'commit', '-m', 'chore: remove empty hermes_voice_bridge namespace dir and clean pycache'], capture_output=True, text=True)
print(f'Commit: {r.returncode}')
r = subprocess.run(['git', 'push'], capture_output=True, text=True)
print(f'Push: {r.returncode}')

# Final check
print('\n=== Remaining src/ structure ===')
for root, dirs, files in os.walk('src'):
    # Skip __pycache__
    if '__pycache__' in root:
        continue
    level = root.replace('src', '').count(os.sep)
    indent = '  ' * level
    print(f'{indent}{os.path.basename(root)}/')
    subindent = '  ' * (level + 1)
    for f in sorted(files):
        if f.endswith('.py'):
            print(f'{subindent}{f}')