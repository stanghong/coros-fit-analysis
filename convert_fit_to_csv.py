#!/usr/bin/env python3
"""
Convert Coros FIT files to CSV format for analysis.
"""

import os
import glob
import csv
from datetime import datetime
from fitparse import FitFile
from typing import List, Dict, Optional
import pandas as pd


def parse_fit_to_csv(fit_file_path: str, output_dir: str) -> Optional[str]:
    """
    Parse a FIT file and convert it to CSV format.
    
    Args:
        fit_file_path: Path to the input FIT file
        output_dir: Directory to save the CSV file
        
    Returns:
        Path to the created CSV file, or None if parsing failed
    """
    try:
        # Try to open and parse the FIT file
        try:
            fitfile = FitFile(fit_file_path)
        except Exception as e:
            # Skip files that can't be opened
            print(f"⚠ Skipped {os.path.basename(fit_file_path)}: Cannot open file - {str(e)[:50]}")
            return None
        base_name = os.path.splitext(os.path.basename(fit_file_path))[0]
        csv_file_path = os.path.join(output_dir, f"{base_name}.csv")
        
        # Lists to store data
        records = []
        session_data = {}
        file_id_data = {}
        
        # Parse file_id messages
        for record in fitfile.get_messages('file_id'):
            for field in record:
                file_id_data[field.name] = field.value
        
        # Parse session data (summary)
        for record in fitfile.get_messages('session'):
            for field in record:
                session_data[field.name] = field.value
        
        # Parse record data (detailed track points)
        for record in fitfile.get_messages('record'):
            record_dict = {}
            for field in record:
                record_dict[field.name] = field.value
            if record_dict:
                records.append(record_dict)
        
        # Parse lap data if available
        laps = []
        for record in fitfile.get_messages('lap'):
            lap_dict = {}
            for field in record:
                lap_dict[field.name] = field.value
            if lap_dict:
                laps.append(lap_dict)
        
        # If we have record data, save it as the main CSV
        if records:
            # Convert records to DataFrame for easier handling
            df_records = pd.DataFrame(records)
            
            # Add session summary as metadata columns (repeat for each record)
            if session_data:
                for key, value in session_data.items():
                    if key not in df_records.columns:
                        df_records[f'session_{key}'] = value
            
            # Add file_id metadata
            if file_id_data:
                for key, value in file_id_data.items():
                    if key not in df_records.columns:
                        df_records[f'file_{key}'] = value
            
            # Save to CSV
            df_records.to_csv(csv_file_path, index=False)
            print(f"✓ Converted {os.path.basename(fit_file_path)} -> {os.path.basename(csv_file_path)} ({len(records)} records)")
            return csv_file_path
        
        # If no records but we have session data, create a summary CSV
        elif session_data:
            df_session = pd.DataFrame([session_data])
            
            # Add file_id metadata
            if file_id_data:
                for key, value in file_id_data.items():
                    df_session[f'file_{key}'] = value
            
            df_session.to_csv(csv_file_path, index=False)
            print(f"✓ Converted {os.path.basename(fit_file_path)} -> {os.path.basename(csv_file_path)} (session summary only)")
            return csv_file_path
        
        else:
            print(f"⚠ Skipped {os.path.basename(fit_file_path)}: No data found")
            return None
            
    except Exception as e:
        print(f"✗ Error parsing {os.path.basename(fit_file_path)}: {e}")
        return None


def convert_all_fit_files(input_dir: str, output_dir: str) -> Dict[str, int]:
    """
    Convert all FIT files in a directory to CSV format.
    
    Args:
        input_dir: Directory containing FIT files
        output_dir: Directory to save CSV files
        
    Returns:
        Dictionary with conversion statistics
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all FIT files
    fit_files = glob.glob(os.path.join(input_dir, "*.fit"))
    fit_files.sort()
    
    print(f"Found {len(fit_files)} FIT files to convert")
    print(f"Output directory: {output_dir}")
    print("=" * 80)
    
    stats = {
        'total': len(fit_files),
        'successful': 0,
        'failed': 0,
        'skipped': 0
    }
    
    # Convert each file
    for fit_file in fit_files:
        result = parse_fit_to_csv(fit_file, output_dir)
        if result:
            stats['successful'] += 1
        else:
            stats['failed'] += 1
    
    return stats


def create_summary_csv(output_dir: str) -> None:
    """
    Create a summary CSV file listing all converted workouts.
    
    Args:
        output_dir: Directory containing CSV files
    """
    csv_files = glob.glob(os.path.join(output_dir, "*.csv"))
    
    if not csv_files:
        print("No CSV files found for summary")
        return
    
    summary_data = []
    
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file, nrows=1)  # Read just the header and first row
            
            summary = {
                'filename': os.path.basename(csv_file),
                'file_id': csv_file,
            }
            
            # Extract key metrics if available
            if 'timestamp' in df.columns:
                summary['timestamp'] = df['timestamp'].iloc[0] if len(df) > 0 else None
            
            # Session data
            session_cols = [col for col in df.columns if col.startswith('session_')]
            for col in session_cols:
                key = col.replace('session_', '')
                summary[key] = df[col].iloc[0] if len(df) > 0 else None
            
            # Count total records
            df_full = pd.read_csv(csv_file)
            summary['total_records'] = len(df_full)
            
            summary_data.append(summary)
            
        except Exception as e:
            print(f"Error reading {csv_file}: {e}")
    
    if summary_data:
        df_summary = pd.DataFrame(summary_data)
        summary_file = os.path.join(output_dir, "_summary.csv")
        df_summary.to_csv(summary_file, index=False)
        print(f"\n✓ Created summary file: {summary_file}")


if __name__ == "__main__":
    input_directory = "/Users/hongtang/Documents/coros_fit/corosfitdata"
    output_directory = "/Users/hongtang/Documents/coros_fit/csv_folder"
    
    print("🔄 Converting FIT files to CSV format")
    print("=" * 80)
    
    stats = convert_all_fit_files(input_directory, output_directory)
    
    print("\n" + "=" * 80)
    print("📊 Conversion Statistics:")
    print(f"  Total files: {stats['total']}")
    print(f"  Successful: {stats['successful']}")
    print(f"  Failed: {stats['failed']}")
    
    # Create summary CSV
    print("\n" + "=" * 80)
    print("📝 Creating summary file...")
    create_summary_csv(output_directory)
    
    print("\n✅ Conversion complete!")
    print(f"📁 CSV files saved in: {output_directory}")
