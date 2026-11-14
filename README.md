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
| `url` | `""` | Full `/send` URL. A non-empty value disables port file discovery. |
| `port_file` | `""` | Explicit port file path; `~` is expanded. Empty enables state directory discovery. |
| `fallback_port` | `47123` | Port used when the port file is missing or empty. |
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

The `zot-editor-bridge` extension starts an HTTP server on `127.0.0.1` and writes
its port to `editor-bridge.port` in zot's state directory:

1. `$ZOT_HOME` when set;
2. `$XDG_STATE_HOME/zot` when `XDG_STATE_HOME` is set;
3. otherwise `~/.local/state/zot` on Linux, `~/Library/Application Support/zot`
   on macOS, or `%LOCALAPPDATA%\zot` on Windows.

When `ZOT_HOME` is unset, the bridge also writes a compatible copy to
`~/.zot/editor-bridge.port`.

Unless `port_file` is set, the plugin checks the same locations in this order,
with the legacy `~/.zot` copy last.

Install the extension:

```bash
cd zot-editor-bridge
zot ext install .
```

Start zot: the extension reports the port on startup, and the `/editor-bridge`
command shows the current `/send` and `/health` URLs.

Manual check:

```bash
# Linux default; adjust for ZOT_HOME or XDG_STATE_HOME
PORT=$(cat ~/.local/state/zot/editor-bridge.port)
curl "http://127.0.0.1:$PORT/health"
```

## Troubleshooting

Errors appear in the status bar; details are printed to the Sublime Text console
(``Ctrl+` ``) with the `[ZotInstruct]` prefix.

- `zot-editor-bridge unavailable (start zot)` means the port does not answer:
  make sure zot is running with the extension and the port file exists.
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
