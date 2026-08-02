import unittest

from playerhub_etl.batch import batches


class BatchTest(unittest.TestCase):
    def test_splits_values_into_stable_batches(self) -> None:
        self.assertEqual(list(batches([1, 2, 3, 4, 5], 2)), [[1, 2], [3, 4], [5]])

    def test_rejects_invalid_batch_size(self) -> None:
        with self.assertRaises(ValueError):
            list(batches([1], 0))


if __name__ == "__main__":
    unittest.main()
