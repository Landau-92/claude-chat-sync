"""End-to-end tests for bin/claude-chat on fake profiles in a temporary HOME.

Run: python3 -m unittest discover tests
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

TOOL = os.path.join(os.path.dirname(__file__), "..", "bin", "claude-chat")
APP = "/Applications/Claude.app/Contents/MacOS/Claude"


class Home:
    """A fake HOME with Claude profiles: the default one plus claude-multiprofile ones."""

    def __init__(self, extra=("work", "client")):
        self.root = tempfile.mkdtemp(prefix="claude-chat-test-")
        self.support = os.path.join(self.root, "Library/Application Support")
        self.profiles = {"default": (os.path.join(self.support, "Claude"), os.path.join(self.root, ".claude"))}
        reg = []
        for name in extra:
            data, cfg = os.path.join(self.support, f"Claude-{name}"), os.path.join(self.root, f".claude-{name}")
            self.profiles[name] = (data, cfg)
            reg.append({"name": name, "desktop": {"dataDir": data}, "code": {"configDir": cfg}})
        self.write(".config/claude-multiprofile/profiles.json", {"profiles": reg})
        for i, (name, (data, cfg)) in enumerate(self.profiles.items()):
            acct = f"acct-{name}"
            self.write_abs(os.path.join(data, "config.json"), {"lastKnownAccountUuid": acct})
            self.write_abs(os.path.join(data, "claude-code-sessions", acct, "org", "archived-sessions.idx"),
                           {"v": 1, "archived": []})
            account_json = os.path.join(self.root, ".claude.json") if name == "default" else os.path.join(cfg, ".claude.json")
            self.write_abs(account_json, {"oauthAccount": {"accountUuid": acct, "emailAddress": f"{name}@example.com"}})
        self.open_apps = set()

    def write(self, rel, data):
        self.write_abs(os.path.join(self.root, rel), data)

    def write_abs(self, path, data):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(data if isinstance(data, str) else json.dumps(data))

    def sessions(self, name):
        return os.path.join(self.profiles[name][0], "claude-code-sessions", f"acct-{name}", "org")

    def transcript(self, name, cwd, cli):
        enc = "".join(c if c.isalnum() else "-" for c in cwd)
        return os.path.join(self.profiles[name][1], "projects", enc, cli + ".jsonl")

    def chat(self, name, sid, cli, title, text, cwd="/tmp/proj", parent=None, **extra):
        rec = {"sessionId": sid, "cliSessionId": cli, "cwd": cwd, "title": title, "lastActivityAt": 1, **extra}
        if parent:
            rec["spawnedFrom"] = {"sessionId": parent}
        self.write_abs(os.path.join(self.sessions(name), sid + ".json"), rec)
        self.write_abs(self.transcript(name, cwd, cli), text)

    def run(self, *args, ok=True):
        ps = "\n".join(APP if n == "default" else f"{APP} --user-data-dir={self.profiles[n][0]}"
                       for n in self.open_apps)
        env = dict(os.environ, HOME=self.root, CLAUDE_CHAT_PS_OUTPUT=ps)
        r = subprocess.run(["/usr/bin/python3", "-I", TOOL, *args], capture_output=True, text=True, env=env)
        if ok and r.returncode != 0:
            raise AssertionError(f"{args} failed ({r.returncode}): {r.stderr}")
        return r

    def json(self, *args):
        return json.loads(self.run(*args, "--json").stdout)

    def read(self, name, cli):
        with open(self.transcript(name, "/tmp/proj", cli)) as f:
            return f.read()

    def cleanup(self):
        shutil.rmtree(self.root)


class ClaudeChatTest(unittest.TestCase):
    def setUp(self):
        self.h = Home()

    def tearDown(self):
        self.h.cleanup()

    def family(self, name="default"):
        h = self.h
        h.chat(name, "local_P", "cP", "Parent", "a\n", priorCliSessionIds=["cOld"])
        h.write_abs(h.transcript(name, "/tmp/proj", "cOld"), "old\n")
        h.chat(name, "local_C", "cC", "Child", "c\n", parent="local_P")
        h.chat(name, "local_G", "cG", "Grandchild", "g\n", parent="local_C")
        h.chat(name, "local_X", "cX", "Detached", "x\n", parent="local_P", lineageDetached=True)

    def test_profiles_from_multiprofile_and_names(self):
        self.h.write(".config/claude-chat-sync/config.json", {"names": {"default": "Personal"}})
        ps = {p["key"]: p for p in self.h.json("profiles")}
        self.assertEqual(list(ps), ["default", "work", "client"])
        self.assertEqual(ps["default"]["name"], "Personal")
        self.assertEqual(ps["work"]["email"], "work@example.com")
        self.assertFalse(ps["work"]["accountMismatch"])

    def test_copy_family_with_sub_chats(self):
        self.family()
        r = self.h.json("copy", "Parent", "--from", "default", "--to", "work")
        self.assertEqual([c["title"] for c in r["chats"]], ["Parent", "Child", "Grandchild"])
        self.assertTrue(all(c["state"] == "new" for c in r["chats"]))
        for sid in ("local_P", "local_C", "local_G"):
            self.assertTrue(os.path.exists(os.path.join(self.h.sessions("work"), sid + ".json")))
        self.assertFalse(os.path.exists(os.path.join(self.h.sessions("work"), "local_X.json")))
        self.assertTrue(os.path.exists(self.h.transcript("work", "/tmp/proj", "cOld")))

    def test_destination_app_open_is_refused(self):
        self.family()
        self.h.open_apps = {"work"}
        r = self.h.run("copy", "Parent", "--from", "default", "--to", "work", ok=False)
        self.assertEqual(r.returncode, 3)

    def test_move_trashes_source_and_restore_brings_it_back(self):
        self.family()
        r = self.h.json("copy", "Parent", "--from", "default", "--to", "work", "--move")
        self.assertTrue(all(c["after"] == "removed" for c in r["chats"]))
        sess = self.h.sessions("default")
        self.assertFalse(os.path.exists(os.path.join(sess, "local_P.json")))
        self.assertTrue(os.path.exists(os.path.join(sess, "deleted_cP")))
        self.assertFalse(os.path.exists(self.h.transcript("default", "/tmp/proj", "cP")))
        entries = self.h.json("trash", "list")
        self.assertEqual(len(entries), 3)
        for e in entries:
            self.h.run("trash", "restore", e["id"])
        self.assertTrue(os.path.exists(os.path.join(sess, "local_P.json")))
        self.assertFalse(os.path.exists(os.path.join(sess, "deleted_cP")))
        self.assertEqual(self.h.read("default", "cP"), "a\n")
        self.assertEqual(self.h.json("trash", "list"), [])

    def test_move_with_source_open_waits_for_quit(self):
        self.family()
        self.h.open_apps = {"default"}
        r = self.h.json("copy", "Parent", "--from", "default", "--to", "work", "--move")
        self.assertTrue(all(c["after"] == "remove-pending" for c in r["chats"]))
        self.assertTrue(os.path.exists(os.path.join(self.h.sessions("default"), "local_P.json")))
        # The child is continued in the source before the app quits: it must stay
        with open(self.h.transcript("default", "/tmp/proj", "cC"), "a") as f:
            f.write("more\n")
        self.h.open_apps = set()
        self.h.run("profiles")
        sess = self.h.sessions("default")
        self.assertFalse(os.path.exists(os.path.join(sess, "local_P.json")))
        self.assertTrue(os.path.exists(os.path.join(sess, "local_C.json")))
        self.assertEqual(self.h.json("pending", "list"), [])

    def test_archive_source(self):
        self.family()
        self.h.run("copy", "Parent", "--from", "default", "--to", "work", "--archive-source")
        with open(os.path.join(self.h.sessions("default"), "archived-sessions.idx")) as f:
            idx = json.load(f)
        self.assertIn("local_P", idx["archived"])

    def test_diverged_group_is_left_untouched_unless_forced(self):
        self.family()
        self.h.run("copy", "Parent", "--from", "default", "--to", "work")
        for name, extra in (("default", "D\n"), ("work", "W\n")):
            with open(self.h.transcript(name, "/tmp/proj", "cC"), "a") as f:
                f.write(extra)
        with open(self.h.transcript("default", "/tmp/proj", "cP"), "a") as f:
            f.write("newer\n")
        before = self.h.read("work", "cP")
        r = self.h.run("copy", "Parent", "--from", "default", "--to", "work", ok=False)
        self.assertEqual(r.returncode, 4)
        self.assertEqual(self.h.read("work", "cP"), before)
        self.h.run("copy", "Parent", "--from", "default", "--to", "work", "--force")
        self.assertEqual(self.h.read("work", "cC"), "c\nD\n")
        backups = [f for f in os.listdir(os.path.dirname(self.h.transcript("work", "/tmp/proj", "cC"))) if ".bak-" in f]
        self.assertEqual(len(backups), 1)

    def test_status_across_three_profiles(self):
        h = self.h
        h.chat("default", "local_A", "cA", "Same", "1\n")
        h.chat("work", "local_A", "cA", "Same", "1\n")
        h.chat("default", "local_B", "cB", "Ahead", "1\n2\n")
        h.chat("work", "local_B", "cB", "Ahead", "1\n")
        h.chat("client", "local_B", "cB", "Ahead", "1\n2\n")
        h.chat("default", "local_C", "cC", "Conflict", "1\nx\n")
        h.chat("client", "local_C", "cC", "Conflict", "1\ny\n")
        h.chat("work", "local_D", "cD", "Only", "1\n")
        st = h.json("status")
        self.assertEqual([p["key"] for p in st["profiles"]], ["default", "work", "client"])
        sides = {c["title"]: {k: s["state"] for k, s in c["sides"].items()} for c in st["chats"]}
        self.assertEqual(sides["Same"], {"default": "same", "work": "same"})
        self.assertEqual(sides["Ahead"], {"default": "latest", "work": "behind", "client": "latest"})
        self.assertEqual(sides["Conflict"], {"default": "diverged", "client": "diverged"})
        self.assertEqual(sides["Only"], {"work": "only"})

    def test_show_limits_profiles(self):
        self.h.write(".config/claude-chat-sync/config.json", {"show": ["client", "default"]})
        st = self.h.json("status")
        self.assertEqual([p["key"] for p in st["profiles"]], ["client", "default"])


if __name__ == "__main__":
    unittest.main()
