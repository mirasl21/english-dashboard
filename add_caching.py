import re

with open("data_manager.py", "r", encoding="utf-8") as f:
    content = f.read()

if "import streamlit as st" not in content:
    content = "import streamlit as st\n" + content

# Functions to cache
get_funcs = re.findall(r"^def (get_[a-zA-Z0-9_]+)\(", content, flags=re.MULTILINE)

# Replace 'def get_...' with '@st.cache_data(ttl=60)\ndef get_...'
for func in set(get_funcs):
    if func == "get_file": continue
    # Only replace if not already decorated
    idx = content.find(f"def {func}(")
    if idx != -1:
        prefix = content[:idx]
        if not prefix.endswith("@st.cache_data(ttl=60)\n"):
            content = re.sub(rf"^(def {func}\()", rf"@st.cache_data(ttl=60)\n\1", content, count=1, flags=re.MULTILINE)

# Functions to clear cache
write_funcs = re.findall(r"^def (add_[a-zA-Z0-9_]+|delete_[a-zA-Z0-9_]+|update_[a-zA-Z0-9_]+|mark_[a-zA-Z0-9_]+|link_[a-zA-Z0-9_]+|upload_[a-zA-Z0-9_]+|reschedule_[a-zA-Z0-9_]+|save_[a-zA-Z0-9_]+)\(", content, flags=re.MULTILINE)

for func in set(write_funcs):
    # Safe injection right after def line
    pattern = rf"^(def {func}\(.*?\)\s*(?:->.*?)?:\n)"
    replacement = rf"\1    st.cache_data.clear()\n"
    content = re.sub(pattern, replacement, content, count=1, flags=re.MULTILINE)

with open("data_manager.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Injected caching into data_manager.py")
