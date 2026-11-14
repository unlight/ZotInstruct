import importlib.util
import os
import sys
import tempfile
import types

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
    "url": "",
    "port_file": "",
    "fallback_port": 47123,
    "request_timeout": 5,
    "mode": "prompt",
    "instruction_defaults": {},
  }
  config.update(overrides)
  return config


def _write_port(path, port):
  os.makedirs(os.path.dirname(path), exist_ok=True)
  with open(path, "w", encoding="utf-8") as handle:
    handle.write(str(port))


def _clear_env():
  for name in ("ZOT_HOME", "XDG_STATE_HOME", "LOCALAPPDATA"):
    os.environ.pop(name, None)


def _port(config):
  return plugin._resolve_target(_config(**config))[1]


assert plugin._resolve_target(
  _config(url="http://example.test:9000/send")
) == ("http://example.test:9000/send", 9000)

with tempfile.TemporaryDirectory() as directory:
  home = os.path.join(directory, "home")
  os.makedirs(home)
  saved_home = os.environ.get("HOME")
  os.environ["HOME"] = home
  _clear_env()

  explicit = os.path.join(directory, "custom.port")
  _write_port(explicit, 5000)
  assert plugin._resolve_target(
    _config(port_file=explicit, fallback_port=1)
  ) == ("http://127.0.0.1:5000/send", 5000)

  _write_port(explicit, 0)
  assert _port({"port_file": explicit, "fallback_port": 1}) == 1
  assert _port({
    "port_file": os.path.join(directory, "missing.port"), "fallback_port": 1,
  }) == 1

  _write_port(os.path.join(home, ".zot", "editor-bridge.port"), 1111)
  assert _port({"fallback_port": 1}) == 1111

  _write_port(
    os.path.join(home, ".local", "state", "zot", "editor-bridge.port"), 2222
  )
  assert _port({"fallback_port": 1}) == 2222

  xdg = os.path.join(directory, "xdg")
  os.environ["XDG_STATE_HOME"] = xdg
  _write_port(os.path.join(xdg, "zot", "editor-bridge.port"), 3333)
  assert _port({"fallback_port": 1}) == 3333

  zot_home = os.path.join(directory, "zot_home")
  os.environ["ZOT_HOME"] = zot_home
  _write_port(os.path.join(zot_home, "editor-bridge.port"), 4444)
  assert _port({"fallback_port": 1}) == 4444

  if saved_home is None:
    os.environ.pop("HOME", None)
  else:
    os.environ["HOME"] = saved_home
  _clear_env()

defaults = {
  "py": "python",
  "ts,tsx,js,jsx": "javascript",
  "go": "go",
  "default": "generic",
}
assert plugin._default_instruction(defaults, "py") == "python"
assert plugin._default_instruction(defaults, "tsx") == "javascript"
assert plugin._default_instruction(defaults, "rs") == "generic"
assert plugin._default_instruction(defaults, "") == "generic"
assert plugin._default_instruction("broken", "py") == ""

print("zot_instruct selfcheck: ok")
