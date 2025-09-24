#!/usr/bin/env python3
"""
Simple script to switch between different ChromaDB databases.
Usage: python switch_database.py [meeting_logs|fiqa|combined]
"""

import sys
import os
import shutil
from pathlib import Path

def switch_database(db_type):
    """Switch the active ChromaDB database."""
    
    # Define database paths
    current_db = Path("chroma_db")
    meeting_logs_db = Path("chroma_db_backup")  # Backup of meeting logs
    fiqa_db = Path("fiqa_chroma")
    combined_db = Path("chroma_db_combined")  # Combined database
    
    print(f"🔄 Switching to {db_type} database...")
    
    if db_type == "meeting_logs":
        # Switch to meeting logs
        if not meeting_logs_db.exists():
            print(f"❌ Meeting logs database not found at {meeting_logs_db}")
            return False
            
        # Backup current database
        if current_db.exists():
            print(f"📦 Backing up current database to chroma_db_current_backup...")
            shutil.rmtree("chroma_db_current_backup", ignore_errors=True)
            shutil.copytree(current_db, "chroma_db_current_backup")
            
        # Switch to meeting logs
        shutil.rmtree(current_db, ignore_errors=True)
        shutil.copytree(meeting_logs_db, current_db)
        print(f"✅ Switched to meeting logs database")
        
    elif db_type == "fiqa":
        # Switch to FiQA
        if not fiqa_db.exists() or not any(fiqa_db.iterdir()):
            print(f"❌ FiQA database not found or empty at {fiqa_db}")
            print("Please copy your FiQA ChromaDB files into the fiqa_chroma folder first.")
            return False
            
        # Backup current database
        if current_db.exists():
            print(f"📦 Backing up current database to chroma_db_current_backup...")
            shutil.rmtree("chroma_db_current_backup", ignore_errors=True)
            shutil.copytree(current_db, "chroma_db_current_backup")
            
        # Switch to FiQA
        shutil.rmtree(current_db, ignore_errors=True)
        shutil.copytree(fiqa_db, current_db)
        print(f"✅ Switched to FiQA database")
        
    elif db_type == "combined":
        # Switch to combined database
        if not combined_db.exists():
            print(f"❌ Combined database not found at {combined_db}")
            print("Please run 'python create_combined_database.py' first to create the combined database.")
            return False
            
        # Backup current database
        if current_db.exists():
            print(f"📦 Backing up current database to chroma_db_current_backup...")
            shutil.rmtree("chroma_db_current_backup", ignore_errors=True)
            shutil.copytree(current_db, "chroma_db_current_backup")
            
        # Switch to combined database
        shutil.rmtree(current_db, ignore_errors=True)
        shutil.copytree(combined_db, current_db)
        print(f"✅ Switched to combined database")
        
    else:
        print(f"❌ Unknown database type: {db_type}")
        print("Available options: meeting_logs, fiqa, combined")
        return False
        
    return True

def show_status():
    """Show current database status."""
    current_db = Path("chroma_db")
    meeting_logs_db = Path("chroma_db_backup")
    fiqa_db = Path("fiqa_chroma")
    combined_db = Path("chroma_db_combined")
    
    print("📊 Database Status:")
    print(f"  Current active: {current_db} ({'✅ exists' if current_db.exists() else '❌ missing'})")
    print(f"  Meeting logs backup: {meeting_logs_db} ({'✅ exists' if meeting_logs_db.exists() else '❌ missing'})")
    print(f"  FiQA database: {fiqa_db} ({'✅ exists' if fiqa_db.exists() and any(fiqa_db.iterdir()) else '❌ missing/empty'})")
    print(f"  Combined database: {combined_db} ({'✅ exists' if combined_db.exists() and any(combined_db.iterdir()) else '❌ missing/empty'})")
    
    if current_db.exists():
        print(f"\n📁 Current database contents:")
        try:
            for item in current_db.iterdir():
                if item.is_dir():
                    print(f"    📁 {item.name}/")
                else:
                    print(f"    📄 {item.name}")
        except Exception as e:
            print(f"    ❌ Error reading database: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python switch_database.py [meeting_logs|fiqa|combined|status]")
        print("\nOptions:")
        print("  meeting_logs  - Switch to meeting logs database")
        print("  fiqa          - Switch to FiQA database")
        print("  combined      - Switch to combined database (meeting logs + FiQA)")
        print("  status        - Show current database status")
        show_status()
        sys.exit(1)
        
    command = sys.argv[1].lower()
    
    if command == "status":
        show_status()
    else:
        success = switch_database(command)
        if success:
            print(f"\n🎉 Database switch completed!")
            print("💡 Remember to restart the server: python run.py --port 8001")
        else:
            sys.exit(1)
