"""
File with script to update ui_mainwindow.py file.
"""

import re


FILE_NAME = "ui_mainwindow.py"
with open(FILE_NAME, "r", encoding="utf-8") as file:
    text = file.read()

# Add required imports
text = text.replace("#\n\nfrom", "#\n\nimport os\nfrom")
text = text.replace("PySide2", "PyQt5")
NEW_LINES = ("class Ui_MainWindow(QMainWindow):\n\n    "
             "dir_name = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n")
text = text.replace("class Ui_MainWindow(object):", NEW_LINES)

# Change paths to icons
pattern_path = re.compile(r"(?P<path>u\"\.\./media/.+\")")
pattern_file_name = re.compile(r"u\"\.\./(?P<file_name>media/.+)\"")
while True:
    result = pattern_path.search(text)
    if not result:
        break
    path = result.group("path")
    file_name = pattern_file_name.search(path)
    new_path = f"os.path.join(self.dir_name, \"{file_name.group('file_name')}\")"
    text = text[:result.start()] + new_path + text[result.end():]

# Convert unicodes
pattern_label = re.compile(r"translate\(\"MainWindow\", (?P<label>u\".+\")")
while True:
    result = pattern_label.search(text)
    if not result:
        break
    label = result.group("label")[2:-1]
    label = eval(f'u"{label}"')
    text = text[:result.start()] + f'translate("MainWindow", "{label}"' + text[result.end():]
text = text.replace('"<html>', "'<html>")
text = text.replace('</html>"', "</html>'")

# Delete comments
pattern = re.compile(r"\n\s*#.*")
while True:
    result = pattern.search(text)
    if not result:
        break
    text = text[:result.start()] + text[result.end():]

with open(FILE_NAME, "w", encoding="utf-8") as file:
    file.write(text)
