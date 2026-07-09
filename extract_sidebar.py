import re
import glob

# 1. Read utils.py and extract sidebar
with open('utils.py', 'r', encoding='utf-8') as f:
    utils_lines = f.readlines()

sidebar_start = -1
sidebar_end = -1
for i, line in enumerate(utils_lines):
    if '# SIDEBAR' in line:
        sidebar_start = i - 1
    if 'div style=\\'font-size:0.75rem;' in line:
        sidebar_end = i + 2

sidebar_code = utils_lines[sidebar_start:sidebar_end]
utils_code_new = utils_lines[:sidebar_start] + utils_lines[sidebar_end:]

with open('utils.py', 'w', encoding='utf-8') as f:
    f.writelines(utils_code_new)

# 2. Insert sidebar into app.py
with open('app.py', 'r', encoding='utf-8') as f:
    app_lines = f.readlines()

insert_idx = -1
for i, line in enumerate(app_lines):
    if 'ui_tabs = st.tabs([' in line:
        insert_idx = i
        break

app_code_new = app_lines[:insert_idx] + sidebar_code + app_lines[insert_idx:]

with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(app_code_new)
