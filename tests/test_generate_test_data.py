import unittest
from unittest.mock import patch
import pandas as pd

from generate_test_data import generate_random_operations, ALL_OPERATION_COLUMNS

class TestGenerateTestData(unittest.TestCase):

    @patch('generate_test_data.os.makedirs')
    @patch('pandas.DataFrame.to_csv')
    def test_generate_random_operations_logic(self, mock_to_csv, mock_makedirs):
        # Call the function to generate data and get the returned DataFrame
        df = generate_random_operations(num_records=50)

        # Check that our mocks were called
        mock_makedirs.assert_called_once()
        mock_to_csv.assert_called_once()

        # --- Assertions ---
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(df.shape[0], 50)
        self.assertEqual(df.shape[1], len(ALL_OPERATION_COLUMNS))
        self.assertListEqual(list(df.columns), ALL_OPERATION_COLUMNS)
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(df['timestamp_open']))
        self.assertTrue(pd.api.types.is_numeric_dtype(df['entry_price']))

        # Logic for closed positions
        closed_ops = df[df['exit_price'].notna()]
        for _, row in closed_ops.iterrows():
            self.assertIsNotNone(row['pnl_percent'])
            self.assertNotEqual(row['reason_close'], "N/A")
            expected_pnl = round(row['size_usdt'] * (row['pnl_percent'] / 100), 2)
            self.assertAlmostEqual(row['pnl_usdt'], expected_pnl, places=2)

        # Logic for open positions
        open_ops = df[df['exit_price'].isna()]
        for _, row in open_ops.iterrows():
            self.assertTrue(pd.isna(row['pnl_percent']))
            self.assertEqual(row['reason_close'], "N/A")
            self.assertTrue(pd.isna(row['pnl_usdt']))
