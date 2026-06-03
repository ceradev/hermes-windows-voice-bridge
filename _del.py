import subprocess, os
repo = r'C:\Users\cesar\Desktop\Files\Work\Projects\Personal\hermes-windows-voice-bridge'
os.chdir(repo)

if os.path.exists('_final.py'):
    os.remove('_final.py')
    subprocess.run(['git', 'rm', '-f', '_final.py'], capture_output=True, text=True)
    r = subprocess.run(['git', 'add', '-A'], capture_output=True, text=True)
    r = subprocess.run(['git', 'commit', '-m', 'chore: remove final helper script'], capture_output=True, text=True)
    print(f"Commit: {r.returncode}")
    r = subprocess.run(['git', 'push', 'origin', 'development'], capture_output=True, text=True)
    print(f"Push: {r.returncode}")

r = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
print(f"Status: {r.stdout or 'CLEAN'}")

# Check docs/plans is empty now
docs_plans = os.path.join(repo, 'docs', 'plans')
if os.path.exists(docs_plans):
    contents = os.listdir(docs_plans)
    print(f"docs/plans contents: {contents}")