"""Billing shape tests: monthly checkout carries the 14-day trial; /pricing notes it."""

import pathlib
import tempfile
import unittest

from data_kondo import web


def _billing():
    tmp = tempfile.TemporaryDirectory()
    data_dir = pathlib.Path(tmp.name) / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    gate = web.Gate(data_dir)
    env = {
        "STRIPE_SECRET_KEY": "sk_test_x",
        "STRIPE_WEBHOOK_SECRET": "whsec_test",
        "STRIPE_PRICES": "starter=price_123,pro=price_456",
        "PUBLIC_URL": "https://data-kondo.example.com",
    }
    billing = web.Billing(data_dir, gate, env)
    return tmp, billing


class BillingTests(unittest.TestCase):
    def test_monthly_checkout_carries_trial(self):
        tmp, billing = _billing()
        captured = {}

        def fake_stripe(path, form):
            captured["path"] = path
            captured["form"] = form
            return {"url": "https://checkout.stripe.test/session"}

        billing._stripe = fake_stripe
        url = billing.checkout("starter")
        self.assertEqual(url, "https://checkout.stripe.test/session")
        form = captured["form"]
        self.assertEqual(form["mode"], "subscription")
        self.assertEqual(form["line_items[0][price]"], "price_123")
        self.assertEqual(form["subscription_data[trial_period_days]"], "14")
        tmp.cleanup()

    def test_pricing_page_notes_trial(self):
        tmp, billing = _billing()
        self.assertTrue(billing.enabled)
        page = web.pricing_page(billing)
        self.assertIn("14-day free trial", page)
        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
