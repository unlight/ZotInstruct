import importlib.util
import json
import os
import sys
import tempfile
import threading
import types
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS = {}


def _load_settings(name):
  return SETTINGS


sublime = types.ModuleType("sublime")
sublime.load_settings = _load_settings
sublime.set_timeout = lambda callback, delay: callback()
sublime.status_message = lambda text: None
sys.modules["sublime"] = sublime

sublime_plugin = types.ModuleType("sublime_plugin")
sublime_plugin.TextCommand = object
sublime_plugin.WindowCommand = object
sys.modules["sublime_plugin"] = sublime_plugin

spec = importlib.util.spec_from_file_location(
  "zot_instruct", os.path.join(ROOT, "zot_instruct.py")
)
plugin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plugin)


def _config(**overrides):
  config = {
    "request_timeout": 5,
    "instruction_defaults": {},
  }
  config.update(overrides)
  return config


def _write_port(path, port):
  os.makedirs(os.path.dirname(path), exist_ok=True)
  with open(path, "w", encoding="utf-8") as handle:
    handle.write("{}\n".format(port))


def _clear_env():
  for name in ("ZOT_HOME", "XDG_STATE_HOME", "LOCALAPPDATA"):
    os.environ.pop(name, None)


class _View:
  def __init__(self, file_name, folders):
    self._file_name = file_name
    self._window = types.SimpleNamespace(folders=lambda: folders)

  def file_name(self):
    return self._file_name

  def window(self):
    return self._window


class _BridgeHandler(BaseHTTPRequestHandler):
  cwd = "/"
  sent = []

  def do_GET(self):
    self._reply({"ok": True, "cwd": self.cwd})

  def do_POST(self):
    length = int(self.headers.get("Content-Length", 0))
    body = self.rfile.read(length).decode("utf-8")
    _BridgeHandler.sent.append(json.loads(body))
    self._reply({"ok": True})

  def _reply(self, payload):
    body = json.dumps(payload).encode("utf-8")
    self.send_response(200)
    self.send_header("Content-Type", "application/json")
    self.send_header("Content-Length", str(len(body)))
    self.end_headers()
    self.wfile.write(body)

  def log_message(self, *args):
    pass


assert plugin._clean_path("/tmp//./a/../project/") == "/tmp/project"
assert plugin._clean_path("///tmp//project") == "/tmp/project"
assert plugin._port_file_name("/home/roman/Dev/zot-editor-bridge") == (
  "editor-bridge-7db538f0.port"
)
assert "mode" not in plugin._load_config(None)

assert plugin._project_root(
  _View("/work/api/src/app.py", ["/work/web", "/work/api"])
) == "/work/api"
assert plugin._project_root(
  _View("/work/api/src/app.py", ["/work", "/work/api"])
) == "/work/api"
assert plugin._project_root(_View(None, ["/work/api"])) == "/work/api"
assert plugin._project_root(_View("/work/single.py", [])) == "/work"

with tempfile.TemporaryDirectory() as directory:
  home = os.path.join(directory, "home")
  os.makedirs(home)
  saved_home = os.environ.get("HOME")
  os.environ["HOME"] = home
  _clear_env()

  name = plugin._port_file_name("/work/app")
  paths = plugin._port_file_paths("/work/app")
  assert os.path.join(home, ".zot", name) in paths
  assert any(path.endswith(os.path.join("zot", name)) for path in paths)

  zot_home = os.path.join(directory, "zot_home")
  os.environ["ZOT_HOME"] = zot_home
  assert plugin._port_file_paths("/work/app") == [
    os.path.join(zot_home, name)
  ]

  root = "/work/app"
  port_path = os.path.join(zot_home, name)
  server = HTTPServer(("127.0.0.1", 0), _BridgeHandler)
  thread = threading.Thread(target=server.serve_forever, daemon=True)
  thread.start()
  try:
    _write_port(port_path, server.server_port)
    _BridgeHandler.cwd = root + "/"
    assert plugin._discover_port(root) == server.server_port

    _BridgeHandler.cwd = "/work/other"
    assert plugin._discover_port(root) is None
    assert not os.path.exists(port_path)

    _BridgeHandler.cwd = root
    _write_port(port_path, server.server_port)
    payload = {
      "code": "print(1)",
      "instruction": "review",
      "file": "/work/app/app.py",
      "language": "py",
    }
    plugin._deliver(_config(), root, payload)
    assert _BridgeHandler.sent == [payload]
  finally:
    server.shutdown()
    server.server_close()

  if saved_home is None:
    os.environ.pop("HOME", None)
  else:
    os.environ["HOME"] = saved_home
  _clear_env()

defaults = {
  "py": "python",
  "ts,tsx,mts": "typescript",
  "js,jsx,mjs": "javascript",
  "go": "go",
  "default": "generic",
}
assert plugin._default_instruction(defaults, "py") == "python"
assert plugin._default_instruction(defaults, "tsx") == "typescript"
assert plugin._default_instruction(defaults, "mts") == "typescript"
assert plugin._default_instruction(defaults, "jsx") == "javascript"
assert plugin._default_instruction(defaults, "mjs") == "javascript"
assert plugin._default_instruction(defaults, "rs") == "generic"
assert plugin._default_instruction(defaults, "") == "generic"
assert plugin._default_instruction("broken", "py") == ""

print("zot_instruct selfcheck: ok")
