from dataclasses import dataclass
from typing import List, Dict, Optional
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DataValidator:
    """Validates data against schema requirements."""
    
    def validate_variants(self, df: pd.DataFrame) -> bool:
        """Validate variants data."""
        required_columns = [
            'id', 'chr', 'pos', 'a1', 'a2', 'causal',
            'sas_freq', 'eas_freq', 'eur_freq', 'afr_freq', 'his_freq',
            'sas_ldscore', 'eas_ldscore', 'eur_ldscore', 'afr_ldscore', 'his_ldscore'
        ]
        
        # Check required columns
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            logger.error(f"Missing required columns: {missing}")
            return False
            
        # Validate data types
        try:
            df['id'] = df['id'].astype('int64')
            df[['chr', 'pos']] = df[['chr', 'pos']].astype('int64')
            df[['a1', 'a2']] = df[['a1', 'a2']].astype('str')
            df['causal'] = df['causal'].astype('bool')
            freq_cols = [col for col in required_columns if 'freq' in col]
            ldscore_cols = [col for col in required_columns if 'ldscore' in col]
            df[freq_cols + ldscore_cols] = df[freq_cols + ldscore_cols].astype('float64')
        except Exception as e:
            logger.error(f"Data type validation failed: {str(e)}")
            return False
            
        return True

    def validate_traits(self, df: pd.DataFrame) -> bool:
        """Validate traits data."""
        required_columns = [
            'trait_name', 'study', 'ontology', 'sample_size',
            'ncase', 'ncontrol', 'units', 'ancestry', 'type', 'id'
        ]
        
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            logger.error(f"Missing required columns: {missing}")
            return False
            
        try:
            numeric_cols = ['study', 'sample_size', 'ncase', 'ncontrol', 'ancestry', 'id']
            df[numeric_cols] = df[numeric_cols].astype('int64')
            string_cols = ['trait_name', 'ontology', 'units', 'type']
            df[string_cols] = df[string_cols].astype('str')
        except Exception as e:
            logger.error(f"Data type validation failed: {str(e)}")
            return False
            
        return True

class DataProcessor:
    """Processes and loads data into the database."""
    
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
        self.validator = DataValidator()
        
    def process_file(self, file_path: str, table_name: str) -> Optional[pd.DataFrame]:
        """Process a file and return validated DataFrame."""
        try:
            # Determine file type and read accordingly
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_path.endswith('.tsv'):
                df = pd.read_csv(file_path, sep='\t')
            else:
                logger.error(f"Unsupported file type: {file_path}")
                return None
                
            # Validate based on table type
            if table_name == 'variants':
                is_valid = self.validator.validate_variants(df)
            elif table_name == 'traits':
                is_valid = self.validator.validate_traits(df)
            else:
                logger.error(f"Validation not implemented for table: {table_name}")
                return None
                
            if not is_valid:
                return None
                
            return df
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            return None
            
    def load_to_database(self, df: pd.DataFrame, table_name: str) -> bool:
        """Load validated DataFrame to database."""
        try:
            with self.engine.begin() as conn:
                df.to_sql(table_name, conn, if_exists='append', index=False)
            logger.info(f"Successfully loaded {len(df)} rows to {table_name}")
            return True
        except Exception as e:
            logger.error(f"Error loading to database: {str(e)}")
            return False

    def process_and_load(self, file_path: str, table_name: str) -> bool:
        """Complete pipeline to process and load data."""
        df = self.process_file(file_path, table_name)
        if df is not None:
            return self.load_to_database(df, table_name)
        return False
