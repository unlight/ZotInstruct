# ZotInstruct

A Sublime Text 4 plugin that sends the selected code together with an instruction
to the active [zot](https://github.com/) session through the local HTTP server of
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
   line.
2. Press `Ctrl+Enter` (`Super+Enter` on macOS) or run
   `ZotInstruct: Send Selection with Instruction` from the Command Palette
   (`Ctrl+Shift+P`).
3. Type the instruction in the input panel and press `Enter`. The panel is
   prefilled with the last instruction used for this file in the current Sublime
   Text session, or with the template for the file extension from the settings.
   The prefilled text is selected, so it can be replaced immediately.

Additional command:

- `ZotInstruct: Send Prompt Only` (`zot_instruct_prompt`) sends the instruction
  without code.

With an empty selection the plugin does not intercept `Ctrl+Enter`, so the
default behavior is preserved.

## Settings

`Preferences > Package Settings > ZotInstruct > Settings` (the file
`Packages/User/ZotInstruct.sublime-settings` overrides the defaults).

| Setting | Default | Meaning |
| --- | --- | --- |
| `url` | `""` | Full `/send` URL. A non-empty value disables port file discovery. |
| `port_file` | `"~/.zot/editor-bridge.port"` | File with the port number; `~` is expanded. |
| `fallback_port` | `47123` | Port used when the port file is missing or empty. |
| `request_timeout` | `5` | HTTP request timeout in seconds. |
| `mode` | `"prompt"` | `prompt` submits the request to the agent, `notify` only reports status. |
| `instruction_defaults` | see the settings file | Instruction templates per extension; the `default` key covers the rest. |

Keys in `instruction_defaults` may list several extensions separated by commas:
`"ts,tsx,js,jsx"`.

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

The `zot-editor-bridge` extension starts an HTTP server on `127.0.0.1` and
publishes its port in a file:

1. `$ZOT_HOME/editor-bridge.port` when `ZOT_HOME` is set;
2. otherwise in the zot state directory, plus `~/.zot/editor-bridge.port` on
   Linux.

The plugin reads `~/.zot/editor-bridge.port`; if the file is missing and
`ZOT_HOME` is set, it falls back to `$ZOT_HOME/editor-bridge.port`.

Install the extension:

```bash
cd zot-editor-bridge
zot ext install .
```

Start zot: the extension reports the port on startup, and the `/editor-bridge`
command shows the current `/send` and `/health` URLs.

Manual check:

```bash
cat ~/.zot/editor-bridge.port
curl http://127.0.0.1:$(cat ~/.zot/editor-bridge.port)/health
```

## Troubleshooting

Errors appear in the status bar; details are printed to the Sublime Text console
(``Ctrl+` ``) with the `[ZotInstruct]` prefix.

- `zot-editor-bridge unavailable (start zot)` means the port does not answer:
  make sure zot is running with the extension and the port file exists.
- `HTTP 4xx/5xx` means the server returned an error; the response text is shown
  in the status bar and the console.
