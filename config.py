import os
from pathlib import Path

class Config:
    # Base directory of the application
    BASE_DIR = Path(__file__).parent.parent

    # Environment
    ENV = os.getenv('STREAMLIT_ENV', 'development')

    # Database
    if ENV == 'production':
        DB_PATH = os.getenv('DATABASE_URL', str(BASE_DIR / 'inventory.db'))
        UPLOADS_DIR = Path(os.getenv('UPLOADS_DIR', str(BASE_DIR / 'uploads')))
    else:
        DB_PATH = str(BASE_DIR / 'inventory.db')
        UPLOADS_DIR = BASE_DIR / 'uploads'

    # Create necessary directories
    UPLOADS_DIR.mkdir(exist_ok=True)
    (UPLOADS_DIR / 'inventory').mkdir(exist_ok=True)
    (UPLOADS_DIR / 'sales').mkdir(exist_ok=True)
    (UPLOADS_DIR / 'credit').mkdir(exist_ok=True)

    # App settings
    MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB
    ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.pdf', '.gif'} 