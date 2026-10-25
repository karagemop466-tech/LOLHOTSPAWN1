"""New low-tier esportsbook candidates (session 3d124b45): unique, HTTPS, officially verified pages."""
import importlib.util, unittest
spec = importlib.util.spec_from_file_location("probe", "tools/probe_esportsbook_feeds.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

NEW = {"cloudbet_esports": "cloudbet.com", "stake_lol": "stake.com", "rainbet_lol": "rainbet.com",
       "duelbits_esports": "duelbits.com", "roobet_sports": "roobet.com",
       "egamersworld_lol_bets": "egamersworld.com"}

class TestCandidates(unittest.TestCase):
    def test_unique_slugs_and_https(self):
        slugs = [c["slug"] for c in m.CANDIDATES]
        self.assertEqual(len(slugs), len(set(slugs)))
        for c in m.CANDIDATES:
            self.assertTrue(c["url"].startswith("https://"), c["slug"])

    def test_new_candidates_present_on_official_domains(self):
        by = {c["slug"]: c for c in m.CANDIDATES}
        for slug, host in NEW.items():
            self.assertIn(slug, by)
            self.assertIn(host, by[slug]["url"])
            self.assertTrue(by[slug]["expect"])

if __name__ == "__main__":
    unittest.main()
