import re

cfg_path = '/home/jcgar/.mednafen/mednafen.cfg'
arcade_cfg_path = '/home/jcgar/arcade/mednafen_arcade.cfg'

try:
    with open(arcade_cfg_path, 'r', encoding='utf-8') as f:
        lines = [l.strip() for l in f if l.strip() and not l.strip().startswith(';')]

    with open(cfg_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    for line in lines:
        parts = line.split(' ', 1)
        if len(parts) == 2:
            k, v = parts
            pattern = rf'^{re.escape(k)} .*$'
            if re.search(pattern, content, flags=re.MULTILINE):
                content = re.sub(pattern, f'{k} {v}', content, flags=re.MULTILINE)
            else:
                content += f'\n{k} {v}\n'

    with open(cfg_path, 'w', encoding='utf-8') as f:
        f.write(content)
except Exception:
    pass
