"""
Database module for managing the plants_data table.
"""

import sqlite3
from pathlib import Path
from typing import List, Tuple, Optional
from loguru import logger
import sys

# Configure loguru
logger.remove()
logger.add(sys.stderr, level="INFO")


class PlantsDatabase:
    """SQLite database manager for plants data."""
    
    def __init__(self, db_path: str):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.create_tables()
    
    def create_tables(self):
        """Create plants_data table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS plants_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url_source TEXT NOT NULL,
                    url_s3 TEXT,
                    label TEXT NOT NULL,
                    downloaded BOOLEAN DEFAULT 0,
                    processed BOOLEAN DEFAULT 0,
                    valid BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create index on label for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_label ON plants_data(label)
            """)
            
            conn.commit()
            logger.info("Database tables created/verified successfully")
    
    def insert_image(self, url_source: str, label: str, url_s3: Optional[str] = None) -> int:
        """
        Insert a new image record.
        
        Args:
            url_source: Source URL of the image
            label: Image label (dandelion or grass)
            url_s3: S3 URL where image is stored (optional)
        
        Returns:
            ID of inserted record
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO plants_data (url_source, url_s3, label)
                VALUES (?, ?, ?)
            """, (url_source, url_s3, label))
            conn.commit()
            return cursor.lastrowid
    
    def update_download_status(self, image_id: int, downloaded: bool = True):
        """Update download status for an image."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE plants_data 
                SET downloaded = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (downloaded, image_id))
            conn.commit()
    
    def update_s3_url(self, image_id: int, url_s3: str):
        """Update S3 URL for an image."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE plants_data 
                SET url_s3 = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (url_s3, image_id))
            conn.commit()
    
    def update_processed_status(self, image_id: int, processed: bool = True, valid: bool = True):
        """Update processing status for an image."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE plants_data 
                SET processed = ?, valid = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (processed, valid, image_id))
            conn.commit()
    
    def get_all_images(self) -> List[Tuple]:
        """Get all image records."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM plants_data")
            return cursor.fetchall()
    
    def get_images_by_label(self, label: str) -> List[Tuple]:
        """Get all images for a specific label."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM plants_data WHERE label = ?", (label,))
            return cursor.fetchall()
    
    def get_undownloaded_images(self) -> List[Tuple]:
        """Get images that haven't been downloaded yet."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM plants_data WHERE downloaded = 0")
            return cursor.fetchall()
    
    def get_unprocessed_images(self) -> List[Tuple]:
        """Get images that have been downloaded but not processed."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM plants_data WHERE downloaded = 1 AND processed = 0")
            return cursor.fetchall()
    
    def get_statistics(self) -> dict:
        """Get database statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total images
            cursor.execute("SELECT COUNT(*) FROM plants_data")
            total = cursor.fetchone()[0]
            
            # Downloaded images
            cursor.execute("SELECT COUNT(*) FROM plants_data WHERE downloaded = 1")
            downloaded = cursor.fetchone()[0]
            
            # Processed images
            cursor.execute("SELECT COUNT(*) FROM plants_data WHERE processed = 1")
            processed = cursor.fetchone()[0]
            
            # Valid images
            cursor.execute("SELECT COUNT(*) FROM plants_data WHERE valid = 1")
            valid = cursor.fetchone()[0]
            
            # By label
            cursor.execute("SELECT label, COUNT(*) FROM plants_data GROUP BY label")
            by_label = dict(cursor.fetchall())
            
            return {
                "total": total,
                "downloaded": downloaded,
                "processed": processed,
                "valid": valid,
                "by_label": by_label
            }
    
    def clear_table(self):
        """Clear all records from plants_data table."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM plants_data")
            conn.commit()
            logger.info("Cleared all records from plants_data table")
