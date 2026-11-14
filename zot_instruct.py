import hashlib
import http.client
import json
import os
import threading
import urllib.error
import urllib.request

import sublime
import sublime_plugin

SETTINGS_FILE = "ZotInstruct.sublime-settings"
CONFIG_KEY = "zot_instruct"
SEND_URL_TEMPLATE = "http://127.0.0.1:{}/send"
HEALTH_TIMEOUT = 1
INPUT_CAPTION = "Instruction"
UNAVAILABLE_MESSAGE = "Zot Instruct: zot is not running for this project"

_HISTORY = {}


def _setting(settings, key, default):
  value = settings.get(key)
  return default if value is None else value


def _load_config(window):
  settings = sublime.load_settings(SETTINGS_FILE)
  config = {
    "request_timeout": _setting(settings, "request_timeout", 5),
    "mode": _setting(settings, "mode", "prompt"),
    "instruction_defaults": _setting(settings, "instruction_defaults", {}),
  }

  project_data = window.project_data() if window is not None else None
  project_settings = (project_data or {}).get("settings") or {}
  overrides = project_settings.get(CONFIG_KEY)
  if isinstance(overrides, dict):
    config.update(overrides)
  return config


def _read_port(path):
  try:
    with open(path, "r", encoding="utf-8") as handle:
      port = int(handle.read().strip())
  except (OSError, ValueError):
    return None
  return port if 0 < port < 65536 else None


def _env(name):
  return (os.environ.get(name) or "").strip()


def _clean_path(path):
  path = os.path.normpath(path)
  if os.name != "nt" and path.startswith("//"):
    path = "/" + path.lstrip("/")
  return path


def _port_file_name(root):
  digest = hashlib.sha256(root.encode("utf-8")).hexdigest()
  return "editor-bridge-{}.port".format(digest[:8])


def _port_file_paths(root):
  name = _port_file_name(root)
  zot_home = _env("ZOT_HOME")
  if zot_home:
    return [os.path.join(zot_home, name)]

  home = os.path.expanduser("~")
  xdg_state = _env("XDG_STATE_HOME")
  dirs = [
    os.path.join(xdg_state, "zot") if xdg_state else "",
    _env("LOCALAPPDATA"),
    os.path.join(home, ".local", "state", "zot"),
    os.path.join(home, "Library", "Application Support", "zot"),
    os.path.join(home, ".zot"),
  ]
  paths = []
  for directory in dirs:
    path = os.path.join(directory, name) if directory else ""
    if path and path not in paths:
      paths.append(path)
  return paths


def _health_check(port, root):
  request = urllib.request.Request("http://127.0.0.1:{}/health".format(port))
  try:
    with urllib.request.urlopen(request, timeout=HEALTH_TIMEOUT) as response:
      payload = json.loads(response.read().decode("utf-8"))
  except (OSError, ValueError, http.client.HTTPException):
    return False
  if not isinstance(payload, dict) or payload.get("ok") is not True:
    return False
  cwd = payload.get("cwd")
  return isinstance(cwd, str) and _clean_path(cwd) == root


def _remove_stale(path, port):
  # Keep the file if another session has already replaced it.
  if _read_port(path) != port:
    return
  try:
    os.remove(path)
  except OSError:
    pass


def _discover_port(root):
  for path in _port_file_paths(root):
    port = _read_port(path)
    if port is None:
      continue
    if _health_check(port, root):
      return port
    _remove_stale(path, port)
  return None


def _is_within(path, directory):
  try:
    return os.path.commonpath([path, directory]) == directory
  except ValueError:
    return False


def _project_root(view):
  window = view.window()
  folders = window.folders() if window is not None else []
  folders = [_clean_path(folder) for folder in folders]
  file_name = view.file_name()
  if file_name:
    file_name = _clean_path(file_name)
    for folder in sorted(folders, key=len, reverse=True):
      if _is_within(file_name, folder):
        return folder
  if folders:
    return folders[0]
  return _clean_path(os.path.dirname(file_name)) if file_name else None


def _language(view):
  file_name = view.file_name()
  return os.path.splitext(file_name)[1].lstrip(".").lower() if file_name else ""


def _history_key(view):
  file_name = view.file_name()
  return os.path.normcase(os.path.normpath(file_name)) if file_name else None


def _selection_text(view):
  return "\n\n".join(
    view.substr(region) for region in view.sel() if not region.empty()
  )


def _default_instruction(defaults, language):
  if not isinstance(defaults, dict):
    return ""
  fallback = ""
  for key, instruction in defaults.items():
    for extension in str(key).split(","):
      extension = extension.strip().lower()
      if extension and extension == language:
        return instruction
      if extension == "default":
        fallback = instruction
  return fallback


def _initial_instruction(view, config):
  saved = _HISTORY.get(_history_key(view))
  if saved:
    return saved
  return _default_instruction(config["instruction_defaults"], _language(view))


def _http_error_text(exc):
  try:
    detail = exc.read().decode("utf-8", "replace").strip()
  except OSError:
    detail = ""
  text = "HTTP {} {}".format(exc.code, exc.reason)
  return text + (": " + detail[:300] if detail else "")


def _post(url, port, payload, timeout):
  request = urllib.request.Request(
    url,
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json; charset=utf-8"},
    method="POST",
  )
  try:
    with urllib.request.urlopen(request, timeout=timeout) as response:
      response.read()
  except urllib.error.HTTPError as exc:
    message = "Zot Instruct: " + _http_error_text(exc)
    print("[ZotInstruct] {}: {}".format(url, message))
    sublime.set_timeout(lambda: sublime.status_message(message), 0)
    return
  except (urllib.error.URLError, OSError, http.client.HTTPException) as exc:
    print("[ZotInstruct] {}: {!r}".format(url, exc))
    sublime.set_timeout(
      lambda: sublime.status_message(UNAVAILABLE_MESSAGE), 0
    )
    return

  message = "Zot Instruct: sent to zot (port {})".format(port)
  sublime.set_timeout(lambda: sublime.status_message(message), 0)


def _deliver(config, root, payload):
  port = _discover_port(root) if root else None
  if port is None:
    print("[ZotInstruct] no live zot session for {}".format(root))
    sublime.set_timeout(
      lambda: sublime.status_message(UNAVAILABLE_MESSAGE), 0
    )
    return
  _post(
    SEND_URL_TEMPLATE.format(port),
    port,
    payload,
    int(config["request_timeout"]),
  )


def _submit(view, code, instruction, config):
  instruction = instruction.strip()
  if not instruction:
    return

  if view is not None and view.is_valid():
    _HISTORY[_history_key(view)] = instruction
    file_name = view.file_name() or "untitled"
    language = _language(view)
    root = _project_root(view)
  else:
    file_name, language, root = "untitled", "", None

  payload = {
    "code": code,
    "instruction": instruction,
    "file": file_name,
    "language": language,
    "mode": str(config["mode"]),
  }
  threading.Thread(
    target=_deliver,
    args=(config, root, payload),
    daemon=True,
  ).start()


def _prompt(window, view, code):
  config = _load_config(window)
  window.show_input_panel(
    INPUT_CAPTION,
    _initial_instruction(view, config),
    lambda instruction: _submit(view, code, instruction, config),
    None,
    None,
  )

  # show_input_panel focuses the panel view synchronously.
  input_view = window.active_view()
  if input_view is not None and input_view != view:
    selection = input_view.sel()
    selection.clear()
    selection.add(sublime.Region(0, input_view.size()))


class ZotInstructCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    code = _selection_text(self.view)
    if not code:
      sublime.status_message("Zot Instruct: select some text or code")
      return
    window = self.view.window()
    if window is not None:
      _prompt(window, self.view, code)


class ZotInstructPromptCommand(sublime_plugin.WindowCommand):
  def run(self):
    view = self.window.active_view()
    if view is None:
      sublime.status_message("Zot Instruct: no active file")
      return
    _prompt(self.window, view, "")
