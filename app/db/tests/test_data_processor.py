import unittest
import pandas as pd
import tempfile
import os
from data_processor import DataProcessor, DataValidator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging

class TestDataProcessor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test database and test files."""
        # Use SQLite for testing
        cls.db_url = "sqlite:///:memory:"
        cls.processor = DataProcessor(cls.db_url)
        
        # Create temporary directory for test files
        cls.temp_dir = tempfile.mkdtemp()
        
        # Create test data
        cls.create_test_files()

    @classmethod
    def tearDownClass(cls):
        """Clean up temporary files."""
        for file in os.listdir(cls.temp_dir):
            os.remove(os.path.join(cls.temp_dir, file))
        os.rmdir(cls.temp_dir)

    @classmethod
    def create_test_files(cls):
        """Create test CSV files with valid and invalid data."""
        # Valid variants data
        valid_variants = pd.DataFrame({
            'id': [1, 2],
            'chr': [1, 2],
            'pos': [1000, 2000],
            'a1': ['A', 'C'],
            'a2': ['T', 'G'],
            'causal': [True, False],
            'sas_freq': [0.1, 0.2],
            'eas_freq': [0.2, 0.3],
            'eur_freq': [0.3, 0.4],
            'afr_freq': [0.4, 0.5],
            'his_freq': [0.5, 0.6],
            'sas_ldscore': [1.1, 1.2],
            'eas_ldscore': [1.2, 1.3],
            'eur_ldscore': [1.3, 1.4],
            'afr_ldscore': [1.4, 1.5],
            'his_ldscore': [1.5, 1.6]
        })
        
        # Invalid variants data (missing columns)
        invalid_variants = pd.DataFrame({
            'id': [1, 2],
            'chr': [1, 2],
            'pos': [1000, 2000]
        })
        
        # Valid traits data
        valid_traits = pd.DataFrame({
            'trait_name': ['trait1', 'trait2'],
            'study': [1, 2],
            'ontology': ['onto1', 'onto2'],
            'sample_size': [1000, 2000],
            'ncase': [500, 1000],
            'ncontrol': [500, 1000],
            'units': ['unit1', 'unit2'],
            'ancestry': [1, 2],
            'type': ['type1', 'type2'],
            'id': [1, 2]
        })
        
        # Invalid traits data (wrong data types)
        invalid_traits = pd.DataFrame({
            'trait_name': ['trait1', 'trait2'],
            'study': ['invalid', 'not_number'],  # Should be integers
            'ontology': ['onto1', 'onto2'],
            'sample_size': [1000, 2000],
            'ncase': [500, 1000],
            'ncontrol': [500, 1000],
            'units': ['unit1', 'unit2'],
            'ancestry': [1, 2],
            'type': ['type1', 'type2'],
            'id': [1, 2]
        })
        
        # Save test files
        cls.valid_variants_file = os.path.join(cls.temp_dir, 'valid_variants.csv')
        cls.invalid_variants_file = os.path.join(cls.temp_dir, 'invalid_variants.csv')
        cls.valid_traits_file = os.path.join(cls.temp_dir, 'valid_traits.csv')
        cls.invalid_traits_file = os.path.join(cls.temp_dir, 'invalid_traits.csv')
        
        valid_variants.to_csv(cls.valid_variants_file, index=False)
        invalid_variants.to_csv(cls.invalid_variants_file, index=False)
        valid_traits.to_csv(cls.valid_traits_file, index=False)
        invalid_traits.to_csv(cls.invalid_traits_file, index=False)

    def test_valid_variants_processing(self):
        """Test processing of valid variants data."""
        result = self.processor.process_file(self.valid_variants_file, 'variants')
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        self.assertTrue(all(col in result.columns for col in [
            'id', 'chr', 'pos', 'a1', 'a2', 'causal',
            'sas_freq', 'eas_freq', 'eur_freq', 'afr_freq', 'his_freq',
            'sas_ldscore', 'eas_ldscore', 'eur_ldscore', 'afr_ldscore', 'his_ldscore'
        ]))

    def test_invalid_variants_processing(self):
        """Test processing of invalid variants data."""
        result = self.processor.process_file(self.invalid_variants_file, 'variants')
        self.assertIsNone(result)

    def test_valid_traits_processing(self):
        """Test processing of valid traits data."""
        result = self.processor.process_file(self.valid_traits_file, 'traits')
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        self.assertTrue(all(col in result.columns for col in [
            'trait_name', 'study', 'ontology', 'sample_size',
            'ncase', 'ncontrol', 'units', 'ancestry', 'type', 'id'
        ]))

    def test_invalid_traits_processing(self):
        """Test processing of invalid traits data."""
        result = self.processor.process_file(self.invalid_traits_file, 'traits')
        self.assertIsNone(result)

    def test_database_loading(self):
        """Test loading data to database."""
        # Process valid variants
        df = self.processor.process_file(self.valid_variants_file, 'variants')
        self.assertTrue(self.processor.load_to_database(df, 'variants'))
        
        # Verify data in database
        with self.processor.engine.connect() as conn:
            result = pd.read_sql_table('variants', conn)
            self.assertEqual(len(result), 2)

    def test_complete_pipeline(self):
        """Test the complete process_and_load pipeline."""
        # Test with valid data
        self.assertTrue(
            self.processor.process_and_load(self.valid_variants_file, 'variants')
        )
        
        # Test with invalid data
        self.assertFalse(
            self.processor.process_and_load(self.invalid_variants_file, 'variants')
        )

    def test_file_type_handling(self):
        """Test handling of different file types."""
        # Create a TSV version of valid variants
        tsv_file = os.path.join(self.temp_dir, 'valid_variants.tsv')
        pd.read_csv(self.valid_variants_file).to_csv(tsv_file, sep='\t', index=False)
        
        # Test TSV processing
        result = self.processor.process_file(tsv_file, 'variants')
        self.assertIsNotNone(result)
        
        # Test unsupported file type
        invalid_file = os.path.join(self.temp_dir, 'invalid.txt')
        with open(invalid_file, 'w') as f:
            f.write('invalid data')
        result = self.processor.process_file(invalid_file, 'variants')
        self.assertIsNone(result)

if __name__ == '__main__':
    # Disable logging for tests
    logging.getLogger('data_processor').setLevel(logging.ERROR)
    unittest.main()