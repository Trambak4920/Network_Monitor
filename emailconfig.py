from app import app
from models import db, EmailConfig

with app.app_context():
    config = EmailConfig.query.first()
    config.is_active = True
    db.session.commit()
    print(f"✅ Fixed! is_active: {config.is_active}")