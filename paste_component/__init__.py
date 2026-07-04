import os
import streamlit.components.v1 as components

_RELEASE = True

if not _RELEASE:
    _component_func = components.declare_component(
        "global_paste",
        url="http://localhost:3001",
    )
else:
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    _component_func = components.declare_component("global_paste", path=parent_dir)

def global_paste(key=None):
    return _component_func(key=key, default=None)
