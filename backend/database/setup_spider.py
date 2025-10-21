"""
Setup script for Spider database (SQLite3 version).
Downloads and extracts the Spider dataset with SQLite databases.
"""

import zipfile
from pathlib import Path

# Spider dataset - Use direct GitHub release or manual download
SPIDER_GITHUB_RELEASE = "https://github.com/taoyds/spider/archive/refs/heads/master.zip"
# Official Spider website
SPIDER_WEBSITE = "https://yale-lily.github.io/spider"

DATABASE_DIR = Path(__file__).parent
SPIDER_DIR = DATABASE_DIR / "spider"


def extract_zip(zip_path: Path, extract_to: Path):
    """Extract zip file."""
    print(f"Extracting {zip_path}...")
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_to)
    print(f"Extracted to {extract_to}")


def manual_setup_instructions():
    """Print manual setup instructions."""
    print("\n" + "=" * 60)
    print("MANUAL SETUP REQUIRED")
    print("=" * 60)
    print("\nPlease follow these steps:")
    print("\n1. Visit the Spider dataset website:")
    print(f"   {SPIDER_WEBSITE}")
    print("\n2. Download the dataset:")
    print("   - Click 'Download' button")
    print("   - Save as 'spider.zip'")
    print("\n3. Place the file:")
    print(f"   {DATABASE_DIR / 'spider.zip'}")
    print("\n4. Extract manually or run this script again")
    print("\nAlternatively, download from Google Drive:")
    print("   https://drive.google.com/uc?id=1TqleXec_OykOYFREKKtschzY29dUcVAQ")
    print("=" * 60)


def setup_spider():
    """Main setup function."""
    print("=" * 60)
    print("Spider Database Setup")
    print("=" * 60)

    # Check if already exists
    if SPIDER_DIR.exists() and (SPIDER_DIR / "database").exists():
        print("✅ Spider database already exists!")
        print(f"📁 Location: {SPIDER_DIR}")

        # List available databases
        db_dir = SPIDER_DIR / "database"
        if db_dir.exists():
            databases = sorted([f.stem for f in db_dir.glob("*/*.sqlite")])
            print(f"\nFound {len(databases)} databases:")
            for i, db in enumerate(databases[:10], 1):
                print(f"  {i}. {db}")
            if len(databases) > 10:
                print(f"  ... and {len(databases) - 10} more")
        return

    # Create directories
    DATABASE_DIR.mkdir(exist_ok=True)

    # Check for spider.zip
    spider_zip = DATABASE_DIR / "spider.zip"

    if spider_zip.exists():
        # Verify it's a valid zip file
        try:
            with zipfile.ZipFile(spider_zip, "r"):
                print(
                    f"✅ Found valid spider.zip ({spider_zip.stat().st_size // 1024 // 1024} MB)"
                )
        except zipfile.BadZipFile:
            print(f"❌ Invalid zip file: {spider_zip}")
            print("Please download a valid spider.zip file.")
            spider_zip.unlink()  # Remove invalid file
            manual_setup_instructions()
            return

        # Extract
        print(f"\nExtracting to {DATABASE_DIR}...")
        extract_zip(spider_zip, DATABASE_DIR)

        # Check extraction
        if SPIDER_DIR.exists():
            print("✅ Extraction successful!")
        else:
            # Sometimes it extracts to a subdirectory
            extracted_dirs = [
                d for d in DATABASE_DIR.iterdir() if d.is_dir() and d.name != "spider"
            ]
            if extracted_dirs:
                print(f"Moving {extracted_dirs[0]} to {SPIDER_DIR}...")
                extracted_dirs[0].rename(SPIDER_DIR)

        # Verify databases
        db_dir = SPIDER_DIR / "database"
        if db_dir.exists():
            databases = list(db_dir.glob("*/*.sqlite"))
            print(f"\n✅ Setup complete! Found {len(databases)} databases.")
            print(f"📁 Database location: {SPIDER_DIR}")
        else:
            print("\n⚠️  Warning: database directory not found in extracted files.")
            print("Please verify the spider.zip contents.")
    else:
        manual_setup_instructions()


if __name__ == "__main__":
    setup_spider()
