import json
from pathlib import Path
import tempfile
import unittest

from control_panel import render_page
from project_profile import DEFAULTS, load_profile


class ProjectProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, values):
        (self.root / 'project.json').write_text(json.dumps(values), encoding='utf-8')

    def test_missing_profile_has_safe_defaults(self):
        self.assertEqual(load_profile(self.root), DEFAULTS)

    def test_company_operator_and_brand_are_editable(self):
        self.write({'company_name':'Example Transport', 'default_operator':'Example operator', 'accent_color':'#123abc'})
        profile = load_profile(self.root)
        page = render_page('token','nonce',profile)
        self.assertIn('value="Example Transport"', page)
        self.assertIn('value="Example operator"', page)
        self.assertIn('#123abc', page)

    def test_profile_text_is_escaped_in_interface(self):
        self.write({'project_name':'<img src=x onerror=alert(1)>', 'author':'A & B'})
        page = render_page('token','nonce',load_profile(self.root))
        self.assertNotIn('<img src=x onerror=alert(1)>', page)
        self.assertIn('A &amp; B', page)

    def test_invalid_json_or_object_is_actionable(self):
        (self.root / 'project.json').write_text('{broken', encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'valid JSON'):
            load_profile(self.root)
        self.write(['invalid'])
        with self.assertRaisesRegex(ValueError,'JSON object'):
            load_profile(self.root)

    def test_unknown_fields_and_css_injection_are_rejected(self):
        for values in ({'commission':999}, {'accent_color':'red;}body{display:none'}, {'company_name':None}):
            self.write(values)
            with self.assertRaises(ValueError):
                load_profile(self.root)

    def test_repository_identity_must_be_names_not_paths(self):
        for values in ({'github_username':'../owner'}, {'repository_name':'https://github.com/project'}):
            self.write(values)
            with self.assertRaises(ValueError):
                load_profile(self.root)


if __name__ == '__main__':
    unittest.main()
