import unittest

from data_kondo import clean, infer_type, profile, readiness, snake

MESSY = """Cust. Name,E-mail ,Signup Date,Phone,Active?,Notes (old)
 Alice  Smith,ALICE@X.COM,2026-01-05,(555) 123-4567,yes,
Bob,bob@y.com,01/07/2026,555.987.6543,no,N/A
Bob,bob@y.com,01/07/2026,555.987.6543,no,null
Carol,N/A,Mar 03 2026,-,true,
"""


class Tests(unittest.TestCase):
    def test_infer(self):
        self.assertEqual(infer_type("a@b.co"), "email")
        self.assertEqual(infer_type("2026-01-01"), "date")
        self.assertEqual(infer_type("42"), "int")
        self.assertEqual(infer_type("yes"), "bool")
        self.assertEqual(snake("Cust. Name"), "cust_name")

    def test_profile_and_score(self):
        p = profile(MESSY)
        self.assertEqual(p["rows"], 4)
        self.assertEqual(p["duplicate_rows"], 0)  # differing null spellings hide the dupe
        cols = {c["name"]: c for c in p["columns"]}
        self.assertEqual(cols["Signup Date"]["type"], "date")
        self.assertGreater(cols["Signup Date"]["date_formats"], 1)
        score, issues = readiness(p)
        self.assertLess(score, 90)
        self.assertTrue(issues)

    def test_clean(self):
        out, log = clean(MESSY)
        lines = out.strip().splitlines()
        self.assertEqual(lines[0], "cust_name,e_mail,signup_date,phone,active")
        self.assertIn("Alice Smith,alice@x.com,2026-01-05,5551234567,true", lines[1])
        self.assertEqual(len(lines), 4)  # Bob dedupe after null normalisation, notes column dropped
        self.assertIn("2026-03-03", lines[3])
        self.assertGreater(readiness(profile(out))[0], readiness(profile(MESSY))[0])

    def test_clean_by_key(self):
        out, _ = clean("email,name\na@b.co,A\nA@B.CO,Alpha\n", key="email")
        self.assertEqual(len(out.strip().splitlines()), 2)


if __name__ == "__main__":
    unittest.main()
