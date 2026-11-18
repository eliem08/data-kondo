import contextlib
import io
import json
import os
import pathlib
import tempfile
import unittest

from data_kondo.__main__ import main
from data_kondo.formats import load_table, write_table

EX = pathlib.Path(__file__).resolve().parent.parent / "examples"


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = main(list(argv))
    return code, out.getvalue()


class FormatTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, name, text):
        p = self.dir / name
        p.write_text(text, encoding="utf-8")
        return str(p)

    def test_excel_written_by_a_real_spreadsheet_library(self):
        # examples/customers.xlsx was saved by openpyxl: shared strings, a date format, booleans, two sheets
        text = load_table(str(EX / "customers.xlsx"))
        lines = text.splitlines()
        self.assertEqual(lines[0].split(",")[-3:], ["Signed up", "Active", "Spend"])
        self.assertTrue(lines[1].endswith("2026-01-05,true,1200.5"))
        self.assertTrue(lines[2].endswith("2026-01-06,false,10"))
        self.assertEqual(load_table(str(EX / "customers.xlsx"), "Notes"), "note\nsecond sheet\n")
        with self.assertRaises(ValueError):
            load_table(str(EX / "customers.xlsx"), "Missing")

    def test_json_jsonl_and_delimiters(self):
        recs = [{"id": 1, "name": "Ann", "tags": ["a"]}, {"id": 2, "name": "Bo", "extra": None}]
        expected = 'id,name,tags,extra\n1,Ann,"[""a""]",\n2,Bo,,\n'
        self.assertEqual(load_table(self.put("a.json", json.dumps(recs))), expected)
        self.assertEqual(load_table(self.put("w.json", json.dumps({"data": recs}))), expected)
        self.assertEqual(load_table(self.put("a.jsonl", "\n".join(json.dumps(r) for r in recs))), expected)
        self.assertEqual(load_table(self.put("a.tsv", "x\ty\n1\t2\n")), "x,y\n1,2\n")
        self.assertEqual(load_table(self.put("semi.csv", "x;y\n1;2\n3;4\n")), "x,y\n1,2\n3,4\n")
        with self.assertRaises(ValueError):
            load_table(self.put("bad.json", "[1, 2]"))
        with self.assertRaises(ValueError):
            load_table(self.put("bad.xlsx", "not a zip"))

    def test_output_format_follows_the_file_name(self):
        out = self.dir / "o.json"
        write_table(str(out), "a,b\n1,x\n")
        self.assertEqual(json.loads(out.read_text(encoding="utf-8")), [{"a": "1", "b": "x"}])
        write_table(str(self.dir / "o.jsonl"), "a\n1\n2\n")
        self.assertEqual((self.dir / "o.jsonl").read_text(encoding="utf-8"), '{"a": "1"}\n{"a": "2"}\n')

    def test_cli_cleans_excel_into_json(self):
        out = str(self.dir / "clean.json")
        code, text = run("clean", str(EX / "customers.xlsx"), out, "--key", "e_mail")
        self.assertEqual(code, 0, text)
        rows = json.loads(pathlib.Path(out).read_text(encoding="utf-8"))
        self.assertIn("signed_up", rows[0])
        self.assertEqual(len(rows), 4)  # the duplicate Bob is gone
        self.assertEqual(run("clean", str(EX / "customers.xlsx"), out, "--key", "email")[0], 2)  # no such column
        code, text = run("profile", str(EX / "customers.xlsx"), "--sheet", "Notes")
        self.assertEqual((code, "1 rows" in text), (0, True))
        self.assertEqual(run("profile", os.path.join(self.tmp.name, "nope.xls"))[0], 2)


if __name__ == "__main__":
    unittest.main()
