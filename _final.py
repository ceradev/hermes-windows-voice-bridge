import os, subprocess, shutil
repo = r'C:\Users\cesar\Desktop\Files\Work\Projects\Personal\hermes-windows-voice-bridge'
os.chdir(repo)

deleted = []

def rm(path):
    if os.path.exists(path):
        os.remove(path)
        deleted.append(path)
        print(f'DELETED: {path}')

def rmdir(path):
    if os.path.exists(path):
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        deleted.append(path)
        print(f'DELETED: {path}')

# Root level helper scripts
for f in ['_audit.py', '_del.py', '_do.py', 'fix_indent.py', 'query_schema.py']:
    rm(f)

# Docs plan old
rm('docs/plans/2026-05-24-native-refactor-plan.md')

# Empty panel-web dir
if os.path.exists('panel-web') and not os.listdir('panel-web'):
    os.rmdir('panel-web')
    deleted.append('panel-web/')
    print('DELETED: panel-web/ (empty dir)')

# HermesVoiceBridge.iss in scripts (duplicated in root as setup.iss)
rm('scripts/HermesVoiceBridge.iss')

# Check build.py - is it actually used?
print('\n--- Checking build.py ---')
with open('build.py', 'r') as f:
    content = f.read()
print(content[:300])
# This looks like a simple build script, keep it

# Remove __pycache__ in tests
for root, dirs, files in os.walk('tests'):
    for d in dirs:
        if d == '__pycache__':
            p = os.path.join(root, d)
            shutil.rmtree(p, ignore_errors=True)
            print(f'DELETED: {p}')

# Now update .gitignore
new_gitignore = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Bytecode from deleted source files (legacy cleanup orphans)
src/core/config/__pycache__/
src/core/session/__pycache__/
src/platform/windows/__pycache__/
src/platform/windows/overlay/__pycache__/
src/storage/__pycache__/
tests/__pycache__/

# Virtual environments
venv/
ENV/
env/

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# State / Secrets (NEVER commit)
state/voice.env
state/.panel_token
state/logs/
state/runtime_signal.json
state/runtime_state.json
state/runtime_state.json.lock
state/session.json
state/session.secrets
state/voice.control.json

# Build artifacts
HermesVoiceBridge.spec
setup.iss
build/
dist/
HermesVoiceBridge/
*.zip
*.tar.gz
*.exe

# Test artifacts
.pytest_cache/
tests/__pycache__/

# Legacy web panel (node_modules are huge, keep source only)
panel-web/node_modules/
panel-web/dist/

# React UI app node_modules
src/ui/app/node_modules/

# Tool / IDE metadata
.antigravitycli/
.claude/
.codegraph/
.cursor/

# Runtime tokens
state/.panel_token

# Legacy plan docs
docs/plans/2026-05-24-native-refactor-plan.md
"""

with open('.gitignore', 'w', encoding='utf-8') as f:
    f.write(new_gitignore)
print('\n.gitignore updated')

# Stage and commit
r = subprocess.run(['git', 'add', '-A'], capture_output=True, text=True)
r = subprocess.run(['git', 'commit', '-m', 'chore: clean orphaned files and update .gitignore'], capture_output=True, text=True)
print(f'\nCommit: {r.returncode}')
r = subprocess.run(['git', 'push'], capture_output=True, text=True)
print(f'Push: {r.returncode}')

# Final status
r = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
print(f'\nStatus: {r.stdout or "CLEAN"}')

print('\n=== ROOT FILES NOW ===')
for f in sorted(os.listdir('.')):
    if os.path.isfile(f):
        sz = os.path.getsize(f)
        print(f'  {f} ({sz}b)')

print('\n=== SCRIPTS NOW ===')
for f in sorted(os.listdir('scripts')):
    print(f'  {f}')

print('\n=== DOCS NOW ===')
if os.path.exists('docs'):
    for root, dirs, files in os.walk('docs'):
        for f2 in files:
            print(f'  {os.path.join(root, f2)}')