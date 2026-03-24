import sys
import os

# 将插件根目录加入 path，让 utils 作为独立模块可 import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 防止 pytest 遍历父目录的 __init__.py（需要 substance_painter）
collect_ignore_glob = ["../__init__.py", "../sp_sync*.py"]
