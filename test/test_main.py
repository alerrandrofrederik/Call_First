import contextlib
import io
import unittest

import main


class MainTests(unittest.TestCase):
    def test_main_prints_greeting(self):
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            main.main()

        self.assertEqual(output.getvalue(), "Hello from call-first!\n")


if __name__ == "__main__":
    unittest.main()
