from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from apscheduler.schedulers.background import BackgroundScheduler
from models import db, User, Device, Log, Alert,EmailConfig
import os
import csv

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this-later'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///network_monitor.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def scheduled_monitor():
    print("⏰ Scheduler triggered - running monitor...")
    with app.app_context():
        from monitor import run_monitoring
        run_monitoring()
    print("✅ Monitor run complete!")

scheduler = BackgroundScheduler()
scheduler.add_job(func=scheduled_monitor, trigger='interval', minutes=10) # to change schedular duration
scheduler.start()
print("📅 Scheduler started - monitor will run every 15 minutes")


@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    page = request.args.get('page', 1, type=int)
    per_page = 20

    all_devices = Device.query.all()
    up_count = sum(1 for d in all_devices if d.current_status == 'UP')
    down_count = sum(1 for d in all_devices if d.current_status == 'DOWN')

    # Paginate
    total = len(all_devices)
    start = (page - 1) * per_page
    end = start + per_page
    devices_page = all_devices[start:end]
    total_pages = (total + per_page - 1) // per_page

    return render_template('dashboard.html',
                           devices=devices_page,
                           all_devices=all_devices,
                           up_count=up_count,
                           down_count=down_count,
                           role=session.get('role'),
                           page=page,
                           total_pages=total_pages,
                           total=total)


@app.route('/monitor')
def monitor():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    print("🔍 Manual monitor triggered from dashboard...")
    from monitor import run_monitoring
    run_monitoring()
    flash('✅ Monitor run complete!')
    return redirect(url_for('index'))


@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admins only!')
        return redirect(url_for('index'))

    file = request.files['csv_file']
    if not file:
        flash('No file selected!')
        return redirect(url_for('index'))

    added = 0
    skipped = 0
    stream = file.stream.read().decode('utf-8').splitlines()
    reader = csv.DictReader(stream)

    for row in reader:
        ip = row['ip'].strip()
        device_type = row['device_type'].strip()
        location = row['location'].strip()

        existing = Device.query.filter_by(ip=ip).first()
        if existing:
            skipped += 1
        else:
            device = Device(ip=ip, device_type=device_type, location=location)
            db.session.add(device)
            added += 1

    db.session.commit()
    flash(f'✅ CSV uploaded! Added: {added}, Skipped: {skipped}')
    return redirect(url_for('index'))


@app.route('/test_ping')
def test_ping():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admins only!')
        return redirect(url_for('index'))

    from ping_engine import ping_device
    result = ping_device('8.8.8.8')
    flash(f'🧪 Test ping to 8.8.8.8 → {result}')
    return redirect(url_for('index'))


@app.route('/users')
def users():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admins only!')
        return redirect(url_for('index'))
    all_users = User.query.all()
    return render_template('users.html', users=all_users)


@app.route('/add_user', methods=['POST'])
def add_user():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admins only!')
        return redirect(url_for('index'))

    username = request.form['username']
    password = request.form['password']
    email = request.form['email']
    role = request.form['role']

    existing = User.query.filter_by(username=username).first()
    if existing:
        flash(f'❌ User {username} already exists!')
    else:
        new_user = User(
            username=username,
            password=generate_password_hash(password),
            email=email,
            role=role
        )
        db.session.add(new_user)
        db.session.commit()
        flash(f'✅ User {username} added successfully!')

    return redirect(url_for('users'))


@app.route('/delete_user/<int:user_id>')
def delete_user(user_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admins only!')
        return redirect(url_for('index'))

    user = User.query.get(user_id)
    if user.username == 'admin':
        flash('❌ Cannot delete admin!')
    else:
        db.session.delete(user)
        db.session.commit()
        flash(f'✅ User {user.username} deleted!')

    return redirect(url_for('users'))

@app.route('/email_config', methods=['GET', 'POST'])
def email_config():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admins only!')
        return redirect(url_for('index'))

    config = EmailConfig.query.first()

    if request.method == 'POST':
        sender_email = request.form['sender_email']
        sender_password = request.form['sender_password']

        if config:
            config.sender_email = sender_email
            config.sender_password = sender_password
            config.is_active = True
        else:
            # Create new config
            config = EmailConfig(
                sender_email=sender_email,
                sender_password=sender_password,
                is_active=True
            )
            db.session.add(config)

        db.session.commit()
        flash('✅ Email settings saved!')
        return redirect(url_for('email_config'))

    return render_template('email_config.html', config=config)

@app.route('/delete_device/<int:device_id>')
def delete_device(device_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admins only!')
        return redirect(url_for('index'))

    device = Device.query.get(device_id)
    if device:
        db.session.delete(device)
        db.session.commit()
        flash(f'✅ Device {device.ip} deleted!')
    else:
        flash('❌ Device not found!')

    return redirect(url_for('index'))


@app.route('/add_device', methods=['POST'])
def add_device():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admins only!')
        return redirect(url_for('index'))

    ip = request.form['ip'].strip()
    device_type = request.form['device_type'].strip()
    location = request.form['location'].strip()

    existing = Device.query.filter_by(ip=ip).first()
    if existing:
        flash(f'❌ Device {ip} already exists!')
    else:
        device = Device(ip=ip, device_type=device_type, location=location)
        db.session.add(device)
        db.session.commit()
        flash(f'✅ Device {ip} added!')

    return redirect(url_for('index'))


@app.route('/edit_admin', methods=['GET', 'POST'])
def edit_admin():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admins only!')
        return redirect(url_for('index'))

    admin = User.query.filter_by(username='admin').first()

    if request.method == 'POST':
        new_email = request.form['email'].strip()
        new_password = request.form['password'].strip()

        admin.email = new_email
        if new_password:
            admin.password = generate_password_hash(new_password)

        db.session.commit()
        flash('✅ Admin profile updated!')
        return redirect(url_for('edit_admin'))

    return render_template('edit_admin.html', admin=admin)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash('Login successful!')
            return redirect(url_for('index'))
        flash('Invalid credentials!')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!')
    return redirect(url_for('login'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password=generate_password_hash('admin123'),
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin CREATED: admin/admin123")
        else:
            print("✅ Admin exists")

    print("🚀 Ready!")
    app.run(debug=True, use_reloader=False)