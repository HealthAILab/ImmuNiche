"""Check startup when the server still holds the pre-upgrade API module."""
from pathlib import Path
import sys
import types
import unittest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'code/webapp'))
import component_api


class StartupTests(unittest.TestCase):
    def test_stale_api_module_is_refreshed(self):
        original = sys.modules['component_api']
        previous_entry = sys.modules.pop('streamlit_local', None)
        stale = types.ModuleType('component_api')
        stale.__file__ = original.__file__
        stale.bootstrap = original.bootstrap
        stale.route_request = original.route_request
        sys.modules['component_api'] = stale
        try:
            app = AppTest.from_file(str(ROOT / 'streamlit_app.py')).run(timeout=30)
            self.assertEqual(len(app.exception), 0)
            self.assertTrue(hasattr(sys.modules['component_api'], 'RequestError'))
            self.assertEqual(app.get('component_instance')[0].proto.component_name, 'streamlit_local.immuniche_local_ui')
            app.run(timeout=30)
            self.assertEqual(len(app.exception), 0)
        finally:
            sys.modules['component_api'] = original
            sys.modules.pop('streamlit_local', None)
            if previous_entry is not None:
                sys.modules['streamlit_local'] = previous_entry


if __name__ == '__main__':
    unittest.main()
