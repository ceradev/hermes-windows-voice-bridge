import sys

with open('src/platform/windows/voice_loop.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
in_loop = False
for i, line in enumerate(lines):
    if line.startswith('        try:'):
        if 'with self.audio.create_stream' in lines[i+1]:
            in_loop = True
            new_lines.append('        while self._running:\n')
            new_lines.append('    ' + line)
        else:
            new_lines.append(line)
    elif in_loop:
        if line.startswith('    def '):
            in_loop = False
            new_lines.append(line)
        else:
            if line.strip() == '':
                new_lines.append(line)
            else:
                new_lines.append('    ' + line)
                if 'print(f"Voice loop fatal error:' in line:
                    new_lines.append('                import time; time.sleep(2.0)\n')
                if 'print(f"Audio read error:' in line:
                    new_lines.append('                        break\n')
    else:
        new_lines.append(line)

with open('src/platform/windows/voice_loop.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('Done!')
