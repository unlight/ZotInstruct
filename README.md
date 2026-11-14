# ZotInstruct

A Sublime Text 4 plugin that sends the selected code together with an instruction
to the active [zot](https://www.zot.sh/) session through the local HTTP server of
the `zot-editor-bridge` extension.

## Install

Clone the repository into the Sublime Text `Packages` directory:

```bash
git clone <repo-url> \
  "$HOME/.config/sublime-text/Packages/ZotInstruct"
```

Default locations:

- Linux: `~/.config/sublime-text/Packages/ZotInstruct`
- macOS: `~/Library/Application Support/Sublime Text/Packages/ZotInstruct`
- Windows: `%APPDATA%\Sublime Text\Packages\ZotInstruct`

Restart Sublime Text or run `sublime_plugin.reload_plugin` from the console
(``Ctrl+` ``).

No third-party dependencies: the plugin uses the bundled Python 3.8 only.

## Usage

1. Select code or text. Multiple selections are supported and joined with a blank
   line. With an empty selection the plugin sends only the instruction.
2. Press `Alt+Enter` (`Option+Enter` on macOS) or run
   `ZotInstruct: Send Selection with Instruction` from the Command Palette
   (`Ctrl+Shift+P`).
3. Type the instruction in the input panel and press `Enter`. The panel is
   prefilled with the last instruction used for this file in the current Sublime
   Text session, or with the template for the file extension from the settings.
   The prefilled text is selected, so it can be replaced immediately.

Additional command:

- `ZotInstruct: Send Prompt Only` (`zot_instruct_prompt`) sends the instruction
  without code. This is what `Alt+Enter` runs when the selection is empty.

## Settings

`Preferences > Package Settings > ZotInstruct > Settings` opens the settings;
`Key Bindings` opens the keymap. Files in `Packages/User/` override the
defaults.

| Setting | Default | Meaning |
| --- | --- | --- |
| `url` | `""` | Full `/send` URL. A non-empty value skips port discovery and the health check. |
| `request_timeout` | `5` | HTTP request timeout in seconds. |
| `mode` | `"prompt"` | `prompt` submits the request to the agent, `notify` only reports status. |
| `instruction_defaults` | see the settings file | Instruction templates per extension; the `default` key covers the rest. |

Keys in `instruction_defaults` may list several extensions separated by commas:
`"ts,tsx,mts"`.

### Per-project overrides

Add a `zot_instruct` object to the `settings` section of a `.sublime-project`
file:

```json
{
  "folders": [{ "path": "." }],
  "settings": {
    "zot_instruct": {
      "url": "http://127.0.0.1:47831/send",
      "request_timeout": 10
    }
  }
}
```

These keys override `ZotInstruct.sublime-settings` for that project only.

## zot-editor-bridge integration

The `zot-editor-bridge` extension runs an HTTP server inside each zot process and
publishes its port in a file named after the session working directory:

```text
editor-bridge-<sha256(cwd)[:8]>.port
```

The plugin hashes the project root open in Sublime Text (the window folder
containing the active file), normalizes it like Go `filepath.Clean`, and looks
for the file:

1. `$ZOT_HOME/editor-bridge-<hash>.port` when `ZOT_HOME` is set;
2. otherwise in the zot state directory (`$XDG_STATE_HOME/zot` or
   `~/.local/state/zot` on Linux, `~/Library/Application Support/zot` on macOS,
   `%LOCALAPPDATA%\zot` on Windows);
3. when `ZOT_HOME` is unset, the compatible `~/.zot` copy.

Before sending, the plugin calls `GET /health` with a one second timeout and
requires the reported `cwd` to match the project root. A stale file is removed
only if it still contains the same port. Discovery runs on every send, never in
the background.

Each zot window in a different project gets its own file, so requests reach the
session started in that project. Two zot windows in the same project share one
file: the last started window wins.

Install the extension:

```bash
cd zot-editor-bridge
zot ext install .
```

Start zot: the extension reports the port on startup. Run `/editor-bridge` in
zot to print its `/send` and `/health` URLs and the port file path.

## Troubleshooting

Errors appear in the status bar; details are printed to the Sublime Text console
(``Ctrl+` ``) with the `[ZotInstruct]` prefix.

- `zot is not running for this project` means no live port file matched the
  project root: start zot in the project directory.
- `HTTP 4xx/5xx` means the server returned an error; the response text is shown
  in the status bar and the console.

## Development

```bash
python3 tests/selfcheck.py
```

The plugin targets the Python 3.8 runtime bundled with Sublime Text 4; CI also
runs the self-check on Python 3.12.

## Release

Releases are automated by semantic-release on pushes to `master`
(`.github/workflows/ci.yml`). Commit messages must follow Conventional Commits:

- `fix` creates a patch release;
- `feat` creates a minor release;
- `feat!` or a `BREAKING CHANGE` footer creates a major release;
- `docs`, `chore`, `refactor`, `test`, `build`, and `ci` create no release.

A release creates the tag and the GitHub release and commits `CHANGELOG.md`.
