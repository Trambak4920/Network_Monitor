# forcefully up to check email
from app import app
from models import db, Device

with app.app_context():
    device = Device.query.filter_by(ip='10.36.59.254').first()
    device.current_status = 'UP'
    db.session.commit()
    print("Done! Set to UP")