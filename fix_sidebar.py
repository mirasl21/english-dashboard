import os
import glob
import re

# We will wrap the sidebar code in utils.py in a function
with open('utils.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Make the widgets use keys and we don't need to assign them to local variables if they are in session_state, but we will keep them for simplicity.
# Find where the sidebar starts
start_idx = content.find('with st.sidebar:')
end_idx = content.find('# -----------------------------------------------------------------------------', start_idx)

sidebar_code = content[start_idx:end_idx]

# Wrap in def
new_sidebar = 'def render_sidebar():\n'
for line in sidebar_code.split('\n'):
    new_sidebar += '    ' + line + '\n'

new_content = content[:start_idx] + new_sidebar + content[end_idx:]

with open('utils.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

# Now modify app.py to call render_sidebar()
with open('app.py', 'r', encoding='utf-8') as f:
    app_content = f.read()

app_content = app_content.replace('ui_tabs = st.tabs([', 'render_sidebar()\n\nui_tabs = st.tabs([')
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_content)

