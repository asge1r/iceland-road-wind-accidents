import unittest

import pandas as pd

from src.weather.download_weather import (
    parse_index,
    select_files,
)


class WeatherDownloadTests(unittest.TestCase):
    def test_index_preserves_complementary_f_and_fj_files(self) -> None:
        html = """
<a href="f_1475.txt">f_1475.txt</a> 09-Sep-2026 11:50 42M
<a href="fj_1475.txt">fj_1475.txt</a> 09-Sep-2026 14:13 12M
<a href="fv_31380.txt">fv_31380.txt</a> 09-Sep-2026 15:03 30M
"""
        index = parse_index(html)
        selected = select_files(index, {1475})
        self.assertEqual(selected["source_file"].tolist(), ["f_1475.txt", "fj_1475.txt"])
        self.assertEqual(selected["listed_bytes"].sum(), 54 * 1024**2)

    def test_missing_official_file_is_an_error(self) -> None:
        index = pd.DataFrame(
            {"source_file": ["fv_1.txt"], "station": [1], "listed_bytes": [1]}
        )
        with self.assertRaisesRegex(ValueError, "2"):
            select_files(index, {1, 2})

if __name__ == "__main__":
    unittest.main()
