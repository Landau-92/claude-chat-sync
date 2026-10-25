# Claude Chat Sync

**Move Claude Code chats between Claude profiles on macOS.** A companion to
[claude-multiprofile](https://github.com/jmdarre-v/claude-multiprofile): once your accounts live in separate
profiles, a chat sometimes starts in the wrong one. Claude Chat Sync shows the Code chats of up to three
profiles side by side and copies or moves a chat, with all its sub-chats, from one profile to another.

> **Unofficial.** Not affiliated with Anthropic or with claude-multiprofile. It reads and writes Claude's
> internal, undocumented files. Keep backups, and expect to update it when Claude changes those files.

## What it does

- **Compares** the Code tab chats of up to three profiles in one table: where each chat exists, and whether
  the copies are identical, one is ahead (it was continued after copying), or they diverged (continued in
  both).
- **Copies** a chat to another profile, or brings an older copy up to date. A chat started from another one
  (a sub-chat) always travels with its parent, at any depth.
- **Moves** a chat: copies it, then removes it from the source the way Claude does when you delete a chat. The
  removed files go to a trash folder and can be restored.
- **Archives** the source copy instead, if you prefer to keep it.
- Never overwrites a copy that is further along, and never copies half a group: if any chat in the group
  diverged, nothing happens until you confirm, and the replaced version is kept as a backup.

Conversations stay on your Mac. Nothing is uploaded or synced to Anthropic's servers: the chat simply
appears in the other profile's Code tab and in `claude --resume` there, with its history, checkpoints and
earlier transcripts.

## Requirements

- macOS 14 or later, with Claude Desktop.
- At least two profiles, each with **both** a Desktop and a Code half, each signed in:
  your default Claude plus one or more made with
  [claude-multiprofile](https://github.com/jmdarre-v/claude-multiprofile) (`claude-multiprofile add`,
  choosing "Both"). Profiles you set up by hand also work: see [Configuration](#configuration).
- The Xcode Command Line Tools, to build the app: `xcode-select --install`.
- Optional: [Pillow](https://pypi.org/project/pillow/) for the app icon (`pip3 install --user pillow`).

## Install

```bash
git clone https://github.com/Landau-92/claude-chat-sync.git
cd claude-chat-sync
./install.sh
```

This builds the app from source and installs:

| What | Where |
|---|---|
| The app | `~/Applications/Claude Chat Sync.app` |
| The `claude-chat` command | `~/.local/bin/claude-chat` (a link into the clone) |

The app is built and signed on your Mac, so Gatekeeper does not block it. To update later: `git pull`,
then `./install.sh` again.

## Using it

Open **Claude Chat Sync** from `~/Applications` (or Spotlight).

1. **Profiles…** (bottom of the sidebar): tick up to three profiles to compare and give them names you
   recognise. Until you choose, the first three found are shown.
2. The table lists every Code tab chat, grouped by project folder. Each profile has a column:
   - **only here**: the chat exists only in that profile
   - **✓ in sync**: identical copies
   - **● latest / ○ behind**: one copy was continued after copying
   - **⚠ diverged**: continued in more than one profile
   - **—**: not in that profile
3. Filter with **Sync** (only in a profile, in sync, needs update, conflicts) and **Archive**, or search.
4. Select a chat. The panel shows, for each profile, what copying the chat and its sub-chats there would do.
   Press **Copy** or **Move**, check the per-chat list, and confirm.

Writing into a profile needs its Claude app closed (quit it with Cmd+Q). The source app can stay open: if
it is, archiving or removing the source copy is queued and done as soon as that app quits. A queued removal
is skipped if the chat was continued in the meantime.

**Trash** (bottom of the sidebar) lists moved-away chats; **Restore** puts one back (its profile's app must
be closed). The files stay in `~/.local/share/claude-chat-sync/trash` until you delete them yourself.

### Signing in a new profile

Sign each profile's Claude Desktop in with **Continue with email** and type the code, so the sign-in cannot
reach another open Claude (see claude-multiprofile's README). Then run `/login` in that profile's Claude Code
alias. The sidebar warns when a profile's Desktop and Code are signed in with different accounts: chats you
copy there would not show up where you expect.

## Command line

Everything the app does is done by `claude-chat`, which you can also use directly:

```bash
claude-chat profiles                                  # profiles, accounts, open/closed
claude-chat status                                    # how the shown profiles compare
claude-chat list --from work "invoice"               # chats of a profile, filtered
claude-chat copy "invoice" --from default --to work   # a chat and its sub-chats
claude-chat copy 1a2b3c4d --from default --to work --move
claude-chat copy 1a2b3c4d --from default --to work --dry-run
claude-chat trash list
claude-chat trash restore <entry>
claude-chat pending list
```

A chat is named by its ID (the 8 characters `list` shows, or more) or by part of its title. `--solo` leaves
the sub-chats behind, `--force` replaces diverged copies (keeping a backup), and `--json` gives
machine-readable output. Exit codes: 3 = the destination app is open, 4 = some chats diverged,
5 = the destination is further along.

## Configuration

`~/.config/claude-chat-sync/config.json`, written by the **Profiles…** sheet:

```json
{
  "show": ["default", "work"],
  "names": { "default": "Personal", "work": "Work" },
  "profiles": [
    { "key": "client", "dataDir": "~/Library/Application Support/Claude-Client", "configDir": "~/.claude-client" }
  ]
}
```

- `show`: the profiles to compare, at most three (default: the first three found).
- `names`: display names. Profile keys are `default` and the claude-multiprofile profile names.
- `profiles`: profiles made by hand, without claude-multiprofile: the Desktop data folder you start Claude
  with (`--user-data-dir`) and the `CLAUDE_CONFIG_DIR` you use for its Claude Code.

## How it works

Each profile is a Claude Desktop data folder plus a Claude Code config folder. For one chat, Claude keeps:

| Piece | Where |
|---|---|
| Its card in the Code tab | `<data>/claude-code-sessions/<account>/<org>/local_<id>.json` |
| Its conversation(s) | `<config>/projects/<folder>/<transcript id>.jsonl` and a folder beside it |
| Its checkpoints | `<config>/file-history/<transcript id>/` |
| Notes shared with sub-chats | `<data>/side-session-notes/local_<id>/` |

Copying copies all of them and points the card's paths at the new profile; references to the source account
(Remote Control, connectors, Chrome tab group) are left out. Copies are compared byte by byte: a copy whose
conversation is the start of another's is *behind*, anything else is *diverged*. Removing a chat moves these
files to the trash and leaves the `deleted_<transcript id>` marker Claude itself writes when you delete a chat.

Claude Chat Sync stores only its own settings (`~/.config/claude-chat-sync`), its trash
(`~/.local/share/claude-chat-sync`) and a comparison cache (`~/.cache/claude-chat-sync`). It never reads or
writes the Keychain, never contacts the network, and never touches a profile's sign-in.

## Development

```bash
python3 -m unittest discover tests   # end-to-end tests on fake profiles in a temporary HOME
zsh app/build.sh                     # builds build/Claude Chat Sync.app
```

The app is one SwiftUI file (`app/main.swift`); the command is one Python file (`bin/claude-chat`) using only
the standard library of macOS's `/usr/bin/python3`.

## Uninstall

```bash
rm -rf ~/Applications/"Claude Chat Sync.app" ~/.local/bin/claude-chat
rm -rf ~/.config/claude-chat-sync ~/.cache/claude-chat-sync
```

Check `~/.local/share/claude-chat-sync/trash` before deleting it: it holds the chats you moved away.

## License

MIT. See [LICENSE](LICENSE).
