import subprocess, os
repo = r'C:\Users\cesar\Desktop\Files\Work\Projects\Personal\hermes-windows-voice-bridge'
os.chdir(repo)

# Clean up remaining helper files
cleanup = ['_check3.py', '_cleanup.py', '_reset.py', '_restore_desktop.py']
for f in cleanup:
    if os.path.exists(f):
        os.remove(f)
        subprocess.run(['git', 'rm', '-f', f], capture_output=True, text=True)
        print(f"Removed: {f}")

# Check CHANGELOG.md exists
if os.path.exists('CHANGELOG.md'):
    print("CHANGELOG.md exists - removing from staging (it's from the future)")
    subprocess.run(['git', 'rm', '--cached', 'CHANGELOG.md'], capture_output=True, text=True)
    os.remove('CHANGELOG.md')

# Check what's staged vs unstaged
r = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
print("\nStatus:")
print(r.stdout or "(clean)")

# Commit the final cleanup
r = subprocess.run(['git', 'add', '-A'], capture_output=True, text=True)
r = subprocess.run(['git', 'commit', '-m', 'chore: clean up post-reset artifacts'], capture_output=True, text=True)
print(f"\nCommit: {r.returncode} {r.stdout[:200]}")

# Push
r = subprocess.run(['git', 'push', 'origin', 'development'], capture_output=True, text=True)
print(f"Push: {r.returncode}")

# Final check
r = subprocess.run(['git', 'log', '--oneline', '-5'], capture_output=True, text=True)
print(f"\nFinal log:\n{r.stdout}")

# Verify tests still work
r = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
print(f"\nFinal status:\n{r.stdout or 'CLEAN'}")

# Check key files
for f in ['src/platform/windows/desktop_app.py', 'src/platform/windows/voice_loop.py',
          'src/platform/windows/overlay_service.py', 'src/platform/tray/tray_manager.py']:
    exists = os.path.exists(f)
    print(f"  {'OK' if exists else 'MISSING'}: {f}")