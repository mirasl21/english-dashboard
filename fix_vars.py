# -*- coding: utf-8 -*-
import glob
for filepath in glob.glob('tabs/*.py'):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace(', provider)', ', st.session_state.get("provider", "OpenAI (GPT-4o)"))')
    content = content.replace('{level_code}', '{st.session_state.get("level_code", "B2")}')
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

with open('utils.py', 'r', encoding='utf-8') as f:
    u_content = f.read()
u_content = u_content.replace('if provider ==', 'if st.session_state.get("provider", "OpenAI (GPT-4o)") ==')
with open('utils.py', 'w', encoding='utf-8') as f:
    f.write(u_content)
