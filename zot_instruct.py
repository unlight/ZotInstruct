import json
import os
import threading
import urllib.error
import urllib.parse
import urllib.request

import sublime
import sublime_plugin

SETTINGS_FILE = "ZotInstruct.sublime-settings"
CONFIG_KEY = "zot_instruct"
DEFAULT_PORT_FILE = "~/.zot/editor-bridge.port"
FALLBACK_PORT = 47123
INPUT_CAPTION = "Zot Instruction:"
UNAVAILABLE_MESSAGE = "ZotInstruct: zot-editor-bridge unavailable (start zot)"

_HISTORY = {}


def _setting(settings, key, default):
  value = settings.get(key)
  return default if value is None else value


def _load_config(window):
  settings = sublime.load_settings(SETTINGS_FILE)
  config = {
    "url": _setting(settings, "url", ""),
    "port_file": _setting(settings, "port_file", DEFAULT_PORT_FILE),
    "fallback_port": _setting(settings, "fallback_port", FALLBACK_PORT),
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


def _resolve_target(config):
  url = str(config["url"]).strip()
  if url:
    return url, urllib.parse.urlsplit(url).port

  port_file = os.path.expanduser(str(config["port_file"]))
  paths = [port_file]
  zot_home = os.environ.get("ZOT_HOME")
  if zot_home and not os.path.exists(port_file):
    paths.append(os.path.join(zot_home, "editor-bridge.port"))

  for path in paths:
    port = _read_port(path)
    if port is not None:
      return "http://127.0.0.1:{}/send".format(port), port

  port = int(config["fallback_port"])
  return "http://127.0.0.1:{}/send".format(port), port


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


def _sent_text(port):
  if port:
    return "ZotInstruct: sent to zot (port {})".format(port)
  return "ZotInstruct: sent to zot"


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
    message = "ZotInstruct: " + _http_error_text(exc)
    print("[ZotInstruct] {}: {}".format(url, message))
    sublime.set_timeout(lambda: sublime.status_message(message), 0)
    return
  except (urllib.error.URLError, OSError) as exc:
    print("[ZotInstruct] {}: {!r}".format(url, exc))
    sublime.set_timeout(
      lambda: sublime.status_message(UNAVAILABLE_MESSAGE), 0
    )
    return

  message = _sent_text(port)
  sublime.set_timeout(lambda: sublime.status_message(message), 0)


def _submit(view, code, instruction, config):
  instruction = instruction.strip()
  if not instruction:
    return

  if view is not None and view.is_valid():
    _HISTORY[_history_key(view)] = instruction
    file_name = view.file_name() or "untitled"
    language = _language(view)
  else:
    file_name, language = "untitled", ""

  payload = {
    "code": code,
    "instruction": instruction,
    "file": file_name,
    "language": language,
    "mode": str(config["mode"]),
  }
  url, port = _resolve_target(config)
  threading.Thread(
    target=_post,
    args=(url, port, payload, int(config["request_timeout"])),
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
      sublime.status_message("ZotInstruct: select some text or code")
      return
    window = self.view.window()
    if window is not None:
      _prompt(window, self.view, code)


class ZotInstructPromptCommand(sublime_plugin.WindowCommand):
  def run(self):
    view = self.window.active_view()
    if view is None:
      sublime.status_message("ZotInstruct: no active file")
      return
    _prompt(self.window, view, "")
