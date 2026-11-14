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
    "port_file": "~/.zot/editor-bridge.port",
    "fallback_port": 47123,
    "request_timeout": 5,
    "mode": "prompt",
    "instruction_defaults": {},
  }
  config.update(overrides)
  return config


with tempfile.TemporaryDirectory() as directory:
  port_file = os.path.join(directory, "editor-bridge.port")

  assert plugin._resolve_target(
    _config(url="http://example.test:9000/send", port_file=port_file)
  ) == ("http://example.test:9000/send", 9000)

  with open(port_file, "w", encoding="utf-8") as handle:
    handle.write("51234\n")
  assert plugin._resolve_target(
    _config(port_file=port_file)
  ) == ("http://127.0.0.1:51234/send", 51234)

  with open(port_file, "w", encoding="utf-8") as handle:
    handle.write("not-a-port")
  assert plugin._resolve_target(
    _config(port_file=port_file, fallback_port=1234)
  ) == ("http://127.0.0.1:1234/send", 1234)

  with open(os.path.join(directory, "editor-bridge.port"), "w", encoding="utf-8") as handle:
    handle.write("4321")
  os.environ["ZOT_HOME"] = directory
  assert plugin._resolve_target(
    _config(port_file=os.path.join(directory, "missing.port"), fallback_port=1)
  ) == ("http://127.0.0.1:4321/send", 4321)

  os.environ.pop("ZOT_HOME")
  assert plugin._resolve_target(
    _config(port_file=os.path.join(directory, "missing.port"), fallback_port=1)
  ) == ("http://127.0.0.1:1/send", 1)

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
