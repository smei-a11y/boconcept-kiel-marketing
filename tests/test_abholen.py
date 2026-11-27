"""Prüft die Auswertung mit Antworten in der Form, die Google und Meta dokumentieren."""

import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import abholen  # noqa: E402


class Monate(unittest.TestCase):
    def test_monatsliste_ueber_jahreswechsel(self):
        liste = abholen.monatsliste(dt.date(2026, 2, 10))
        self.assertEqual(len(liste), abholen.MONATE_ZURUECK)
        self.assertEqual(liste[-1], "2026-01")
        self.assertEqual(liste[-2], "2025-12")

    def test_fenster_hoechstens_30_tage(self):
        stuecke = list(abholen.fenster(dt.date(2026, 1, 1), dt.date(2026, 1, 31)))
        self.assertEqual(stuecke, [(dt.date(2026, 1, 1), dt.date(2026, 1, 30)), (dt.date(2026, 1, 31), dt.date(2026, 1, 31))])


class Google(unittest.TestCase):
    def test_summen_je_monat(self):
        antwort = {"multiDailyMetricTimeSeries": [{"dailyMetricTimeSeries": [
            {"dailyMetric": "BUSINESS_IMPRESSIONS_MOBILE_MAPS", "timeSeries": {"datedValues": [
                {"date": {"year": 2026, "month": 10, "day": 1}, "value": "40"},
                {"date": {"year": 2026, "month": 10, "day": 2}},
                {"date": {"year": 2026, "month": 11, "day": 1}, "value": "5"}]}},
            {"dailyMetric": "BUSINESS_IMPRESSIONS_DESKTOP_MAPS", "timeSeries": {"datedValues": [
                {"date": {"year": 2026, "month": 10, "day": 1}, "value": "2"}]}},
            {"dailyMetric": "CALL_CLICKS", "timeSeries": {"datedValues": [
                {"date": {"year": 2026, "month": 10, "day": 3}, "value": "3"}]}},
        ]}]}
        s = abholen.google_summen(antwort)
        self.assertEqual(s[("2026-10", "gbp_maps")], 42)
        self.assertEqual(s[("2026-11", "gbp_maps")], 5)
        self.assertEqual(s[("2026-10", "gbp_anrufe")], 3)

    def test_bewertungen_bis_monatsende(self):
        bewertungen = [
            {"starRating": "FIVE", "createTime": "2026-09-03T10:00:00Z"},
            {"starRating": "THREE", "createTime": "2026-10-20T10:00:00Z", "reviewReply": {"comment": "Danke"}},
            {"starRating": "FOUR", "createTime": "2026-11-02T10:00:00Z", "comment": "Schöner Laden"},
        ]
        m = abholen.bewertungen_je_monat(bewertungen, ["2026-09", "2026-10", "2026-11"])
        self.assertEqual(m["2026-09"], {"gbp_bewertungen": 1, "gbp_sterne": 5.0})
        self.assertEqual(m["2026-10"], {"gbp_bewertungen": 2, "gbp_sterne": 4.0})
        self.assertEqual(m["2026-11"]["gbp_bewertungen"], 3)
        offen = abholen.offene_bewertungen(bewertungen)
        self.assertEqual([o["datum"] for o in offen], ["2026-11-02", "2026-09-03"])
        self.assertNotIn("reviewer", offen[0])


class Meta(unittest.TestCase):
    def test_tageswerte_und_gesamtwert(self):
        self.assertEqual(abholen.tageswerte_summe({"data": [{"values": [{"value": 10}, {"value": 5}]}]}), 15)
        self.assertEqual(abholen.gesamtwert({"data": [{"total_value": {"value": 7}}]}), 7)

    def test_beitraege_je_monat(self):
        zaehler = abholen.zaehle_je_monat([{"timestamp": "2026-10-01T09:00:00+0000"},
                                           {"timestamp": "2026-10-30T09:00:00+0000"},
                                           {"timestamp": "2026-11-01T09:00:00+0000"}], "timestamp")
        self.assertEqual(zaehler, {"2026-10": 2, "2026-11": 1})


if __name__ == "__main__":
    unittest.main()
