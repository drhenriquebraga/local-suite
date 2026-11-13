"""All shared-editor strings and public API errors are explicit in 12 languages."""
import ast
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
from radai_contour_edit_i18n import TEXT, ERRORS, LANGUAGES, error_message


class ContourEditorLanguages(unittest.TestCase):
    def test_all_twelve_catalogs_have_identical_complete_key_sets(self):
        expected = {'pt-BR','en','es','de','fr','it','pl','ja','zh-CN','ar','ko','bn'}
        self.assertEqual(set(LANGUAGES), expected)
        self.assertEqual(set(TEXT), expected)
        self.assertGreaterEqual(len(TEXT['en']), 47)
        for language in expected:
            self.assertEqual(set(TEXT[language]), set(TEXT['en']), language)
            self.assertTrue(all(isinstance(v, str) and v.strip() for v in TEXT[language].values()), language)
            if language != 'pt-BR':
                for key in ('saved','select','loading','failed','saveFirst','local','interpolationHelp',
                            'measureHint','needSeries','sourceChanged','fallbackSaved','longStroke','unsupportedROI'):
                    self.assertNotEqual(TEXT[language][key], TEXT['pt-BR'][key], (language,key))

    def test_current_ui_literal_lookups_exist_in_every_language(self):
        source = (ROOT / 'app/radai_contour_editor_ui.py').read_text(encoding='utf8')
        keys = set(re.findall(r"\bt\(['\"]([^'\"]+)['\"]\)", source))
        for language, entries in TEXT.items():
            self.assertFalse(keys - set(entries), (language, keys - set(entries)))

    def test_current_public_backend_codes_have_twelve_translations(self):
        codes = {'EDIT_FAILED'}
        for path in ('app/radai_contour_edit.py','app/radai_contour_edit_api.py'):
            tree = ast.parse((ROOT / path).read_text(encoding='utf8'))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not node.args or not isinstance(node.args[0], ast.Constant):
                    continue
                name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ''
                if name == 'fail':
                    codes.add(node.args[0].value)
        self.assertFalse(codes - set(ERRORS), codes - set(ERRORS))
        for code in codes:
            self.assertEqual(set(ERRORS[code]), set(LANGUAGES), code)
            for language in LANGUAGES:
                self.assertTrue(ERRORS[code][language].strip(), (code,language))
                if language != 'pt-BR':
                    self.assertNotEqual(ERRORS[code][language], ERRORS[code]['pt-BR'], (code,language))

    def test_unknown_code_uses_localized_general_error_without_portuguese_fallback(self):
        for language in LANGUAGES:
            self.assertEqual(error_message('UNKNOWN', language), ERRORS['EDIT_FAILED'][language])
        self.assertEqual(error_message('INVALID_TICKET', 'unknown'), ERRORS['INVALID_TICKET']['en'])


if __name__ == '__main__':
    unittest.main()
