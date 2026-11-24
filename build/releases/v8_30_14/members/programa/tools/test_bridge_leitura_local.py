"""Contract between the shared local file picker, Bridge, and its 12 languages."""
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import radai_bridge
import radai_phrases
import radai_ui


class PickerMarkup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


class BridgeLocalTests(unittest.TestCase):
    def render(self):
        return radai_bridge.carga("dc", "dcCarregar", "dcProcurar", "dcLimpar", "Pasta")

    def test_local_zone_has_a_translated_accessible_name_and_a_native_folder_button(self):
        parser = PickerMarkup()
        parser.feed(self.render())
        zone = next(attrs for tag, attrs in parser.elements if attrs.get("id") == "dc_envio")
        title = zone["aria-label"]
        self.assertEqual(title, "Abrir exames nesta estação")
        self.assertFalse(any("webkitdirectory" in attrs for _, attrs in parser.elements))
        self.assertTrue(any(attrs.get("data-envio") == "pasta" for _, attrs in parser.elements))
        shared_source = Path(radai_ui.__file__).read_text(encoding="utf-8")
        states = set(re.findall(r"o\.leituraLocal \? '([^']+)'", shared_source))
        self.assertEqual(len(states), 4)
        phrases = [title, "Escolha a pasta do exame ou arraste arquivos e ZIPs.", *states, radai_bridge.AJUDA[0]]
        localized = radai_phrases.construir()
        self.assertEqual(len(localized), 11)
        for phrase in phrases:
            for language, lexicon in localized.items():
                self.assertIn(radai_phrases.normalizar(phrase), lexicon, (phrase, language))

    def test_older_suite_shell_can_render_the_same_component(self):
        original = radai_ui.area_de_envio
        def previous(ident, titulo, dica, imagens, extra):
            return original(ident, titulo=titulo, dica=dica, imagens=imagens, extra=extra)

        with patch.object(radai_ui, "area_de_envio", previous):
            self.assertIn("Abrir exames nesta estação", self.render())


if __name__ == "__main__":
    unittest.main()
