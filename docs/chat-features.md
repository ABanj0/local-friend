# Chat management and attachments

Restart Studio with ` .\desktop-dev.ps1` after this update so Python loads the new routes
and SQLite schema. Existing conversations are migrated without deleting their content.

## Manage conversations

- Use the pencil beside a chat to rename it. **Search chats** filters conversation titles.
- Use the trash icon to open a deletion confirmation. It removes the conversation's
  messages, attachments and task history. Finish or cancel its active task first.
- **Export** downloads the displayed conversation as Markdown, with attachment filenames.
  Image bytes and attachment contents are not embedded in that export.

Deletion removes database records; it does not undo agent edits, remove project files or
erase the separate content-free tool audit log. It is not a secure disk-wipe operation.

## Attach images and files

Use the paperclip to choose files, drop files onto the composer, or paste an image.
For a selected screenshot region, press **Win + Shift + S**, select the region, then
press **Ctrl + V** in the message box. Click an attachment chip to preview it and its
**X** to remove a pending attachment. Add a message describing what you want, then send.

The camera button asks permission to capture the main screen and opens a preview. It
may include other windows, including Studio itself. Close the preview, add an instruction,
and send when ready. Capturing/attaching alone does not send a model request.

Supported inputs:

- PNG, JPEG and WebP: up to 5 MiB uploaded, 20 megapixels. Images are resized to fit
  1600 × 1600, re-encoded as JPEG without metadata, and stored at <=2 MiB.
- UTF-8 text/code: up to 64 KiB, including TXT, Markdown, Python, JS/TS, JSON, CSV,
  logs, YAML, TOML, HTML/CSS, Rust, SQL, PowerShell, shell, XML/INI/CFG and C/C++.
- Up to four attachments per message. At most eight images can remain in the model's
  conversation context. Text still needs to fit the selected context window.

PDF, Office documents, archives and arbitrary binaries are not parsed. Credential-file
names such as `.env`, private keys and `.pem` are rejected. Text redaction is best-effort;
image previews can still contain sensitive information.

Images require an Ollama model reporting vision support. Attachments are available to
Chat and Agent workspaces and retained with history, including regenerated responses.
Attachment contents are untrusted data and never authorize new tools, commands or paths.
Selecting a file uploads its bytes only; it does not grant access to its original folder.
Attachments are stored locally in the Studio database until their chat is deleted.

## Validation

Backend regressions:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_studio_features -v
```

Live image/text model acceptance:

```powershell
$env:LIVE_STUDIO_FEATURES = '1'
.\.venv\Scripts\python.exe -m unittest tests.test_studio_features.AttachmentLiveTests -v
Remove-Item Env:LIVE_STUDIO_FEATURES
```

Browser acceptance (requires built frontend, installed Edge/Playwright, and running Ollama):

```powershell
$env:LIVE_STUDIO_UI = '1'
.\.venv\Scripts\python.exe -m unittest tests.test_studio_ui -v
Remove-Item Env:LIVE_STUDIO_UI
```

The browser test uses real services and an isolated temporary database. Only native IPC
is bridged for the browser harness. It reuses an existing Studio frontend on port 1420
without stopping it, or serves the built assets there. A UI screenshot is saved under
`workspace/studio-attachments-acceptance.png`. Native Windows dialog, capture and clipboard
behavior should also be checked after restarting the desktop app.
