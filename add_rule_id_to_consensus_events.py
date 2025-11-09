#!/usr/bin/env python3
"""
Migration: Add rule_id column to consensus_events table
Run this script to update your database schema.
"""
import sys
import os
from pathlib import Path

# Add tbot to path
sys.path.insert(0, str(Path(__file__).parent / "tbot"))

def main():
    print("=" * 60)
    print("🔧 Database Migration: Adding rule_id to consensus_events")
    print("=" * 60)

    try:
        from core.database.database import Database
        from core.database.migrations import create_tables
        from sqlalchemy import text

        # Use same database URL as the API
        database_url = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/trader_tracker")
        print(f"\n📚 Database: {database_url.split('@')[1] if '@' in database_url else database_url}")

        db = Database(database_url)

        # Step 1: Ensure consensus_rules table exists
        print("\n📋 Step 1: Checking/creating consensus_rules table...")
        create_tables(db.engine)
        print("   ✅ consensus_rules table ready")

        with db.session() as session:
            # Step 2: Check if rule_id column already exists
            print("\n📋 Step 2: Checking if rule_id column exists...")
            check_sql = text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='consensus_events'
                AND column_name='rule_id'
            """)

            result = session.execute(check_sql).fetchone()

            if result:
                print("   ℹ️  Column rule_id already exists")
                print("\n✅ Database is already up to date!")
                return 0

            # Step 3: Add the rule_id column
            print("   ⚠️  Column rule_id not found")
            print("\n📋 Step 3: Adding rule_id column...")
            alter_sql = text("""
                ALTER TABLE consensus_events
                ADD COLUMN rule_id INTEGER REFERENCES consensus_rules(id)
            """)
            session.execute(alter_sql)
            print("   ✅ Column added")

            # Step 4: Add index
            print("\n📋 Step 4: Creating index on rule_id...")
            index_sql = text("""
                CREATE INDEX IF NOT EXISTS idx_consensus_events_rule_id
                ON consensus_events(rule_id)
            """)
            session.execute(index_sql)
            print("   ✅ Index created")

            session.commit()

            print("\n" + "=" * 60)
            print("✅ Migration completed successfully!")
            print("=" * 60)
            print("\nChanges applied:")
            print("  • Added rule_id column to consensus_events table")
            print("  • Created foreign key to consensus_rules(id)")
            print("  • Created index idx_consensus_events_rule_id")
            print("\nYou can now restart your API server.")
            print("=" * 60)
            return 0

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        print("\n💡 Tip: Make sure your database is running and DATABASE_URL is set correctly")
        return 1

if __name__ == "__main__":
    sys.exit(main())
