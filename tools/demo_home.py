"""Builds a fake HOME with three Claude profiles and made-up chats, for the README screenshot.

    python3 tools/demo_home.py /tmp/demo-home
    HOME=/tmp/demo-home CLAUDE_CHAT_PS_OUTPUT="" "build/Claude Chat Sync.app/Contents/MacOS/ClaudeChatSync"

Nothing here is real: the accounts are @example.com and the chats are invented.
"""
import json
import os
import sys
import time

root = os.path.abspath(sys.argv[1])
support = os.path.join(root, "Library/Application Support")
now = int(time.time() * 1000)
H = 3600 * 1000

PROFILES = {
    "default": ("Personal", os.path.join(support, "Claude"), os.path.join(root, ".claude"), os.path.join(root, ".claude.json")),
    "work": ("Work", os.path.join(support, "Claude-Work"), os.path.join(root, ".claude-work"), None),
    "client": ("Client", os.path.join(support, "Claude-Client"), os.path.join(root, ".claude-client"), None),
}


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(data if isinstance(data, str) else json.dumps(data))


reg = []
for key, (name, data, cfg, account_json) in PROFILES.items():
    acct = f"00000000-0000-4000-8000-00000000000{len(reg) + 1}"
    write(os.path.join(data, "config.json"), {"lastKnownAccountUuid": acct})
    write(os.path.join(data, "claude-code-sessions", acct, "org", "archived-sessions.idx"), {"v": 1, "archived": []})
    write(account_json or os.path.join(cfg, ".claude.json"),
          {"oauthAccount": {"accountUuid": acct, "emailAddress": f"{key if key != 'default' else 'me'}@example.com"}})
    if key != "default":
        reg.append({"name": key, "desktop": {"dataDir": data, "color": "pink" if key == "work" else "teal"},
                    "code": {"configDir": cfg}})
    else:
        reg.append(None)
write(os.path.join(root, ".config/claude-multiprofile/profiles.json"), {"profiles": [p for p in reg if p]})
write(os.path.join(root, ".config/claude-chat-sync/config.json"),
      {"names": {k: v[0] for k, v in PROFILES.items()}, "show": list(PROFILES)})

n = 0


def chat(title, project, where, hours_ago, parent=None, archived=False):
    """where: {profile: transcript text}; equal texts = in sync, a prefix = behind."""
    global n
    n += 1
    sid = f"local_{n:08d}-0000-4000-8000-000000000000"
    cli = f"{n:08d}-1111-4000-8000-000000000000"
    cwd = os.path.join("/Users/demo/Projects", project) if project else "/Users/demo/scratch-workspaces/x"
    for key, text in where.items():
        _, data, cfg, _ = PROFILES[key]
        acct = json.load(open(os.path.join(data, "config.json")))["lastKnownAccountUuid"]
        rec = {"sessionId": sid, "cliSessionId": cli, "cwd": cwd, "title": title,
               "lastActivityAt": now - hours_ago * H, "isArchived": archived}
        if parent:
            rec["spawnedFrom"] = {"sessionId": parent}
        write(os.path.join(data, "claude-code-sessions", acct, "org", sid + ".json"), rec)
        enc = "".join(c if c.isalnum() else "-" for c in cwd)
        write(os.path.join(cfg, "projects", enc, cli + ".jsonl"), text)
    return sid


a = "line\n" * 40
chat("Checkout redesign", "acme-web", {"default": a + "more\n", "work": a}, 2)
lead = chat("Release 2.4: plan and split the work", "acme-web", {"work": a}, 3)
chat("Fix flaky payment tests", "acme-web", {"work": a}, 4, parent=lead)
chat("Migrate images to the new CDN", "acme-web", {"work": a}, 5, parent=lead)
chat("Changelog and release notes", "acme-web", {"work": a, "client": a}, 6, parent=lead)
chat("Invoice PDF export", "billing-api", {"client": a, "work": a}, 20)
chat("Webhook retries", "billing-api", {"client": a + "x\n", "work": a + "y\n"}, 26)
chat("Rate limiter spike", "billing-api", {"client": a}, 30)
chat("Holiday photo renamer", "home-scripts", {"default": a}, 50)
chat("Garden watering schedule", "home-scripts", {"default": a}, 80, archived=True)
chat("Explain this regex", "", {"default": a, "work": a}, 8)
print(root)
