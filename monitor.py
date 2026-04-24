from app import app
from models import db, Device, Log, Alert, User, EmailConfig
from ping_engine import ping_device
from datetime import datetime
from email_alerts import send_alert_email


def run_monitoring():
    with app.app_context():
        devices = Device.query.all()

        if not devices:
            print("⚠️  No devices found in database")
            return

        print(f"\n🔍 Monitoring {len(devices)} devices...\n")

        # Get email config
        email_config = EmailConfig.query.filter_by(is_active=True).first()

        # Get all user emails
        recipient_emails = [u.email for u in User.query.all() if u.email]

        print(f"📧 Email config: {'Found - ' + email_config.sender_email if email_config else 'NOT FOUND'}")
        print(f"📧 Recipients: {recipient_emails}")

        up_count = 0
        down_count = 0
        alert_count = 0
        slow_count = 0

        for device in devices:

            # Skip inactive devices
            if device.location and device.location.startswith('[INACTIVE]'):
                continue

            old_status = device.current_status
            new_status, response_time = ping_device(device.ip)

            # Update device
            device.current_status = new_status
            device.last_checked = datetime.utcnow()

            # Save to log
            log = Log(device_id=device.id, status=new_status)
            db.session.add(log)

            # Count
            if new_status == "UP":
                up_count += 1
            else:
                down_count += 1

            # Check slow response
            if response_time is not None and response_time > 100:
                slow_count += 1
                print(f"  ⚠️  {device.ip} → UP but SLOW ({response_time}ms)")

                if email_config and recipient_emails:
                    send_alert_email(
                        sender_email=email_config.sender_email,
                        sender_password=email_config.sender_password,
                        recipient_emails=recipient_emails,
                        device_ip=device.ip,
                        old_status=f"UP ({response_time}ms)",
                        new_status="SLOW RESPONSE"
                    )

            # Detect status change
            if old_status != new_status:
                message = f"⚠️  {device.ip} changed from {old_status} → {new_status}"
                alert = Alert(device_id=device.id, message=message)
                db.session.add(alert)
                alert_count += 1
                print(f"  🚨 ALERT: {message}")

                # Send email only when device goes DOWN
                if new_status == 'DOWN':
                    if email_config and recipient_emails:
                        print(f"  📧 Sending DOWN alert email...")
                        send_alert_email(
                            sender_email=email_config.sender_email,
                            sender_password=email_config.sender_password,
                            recipient_emails=recipient_emails,
                            device_ip=device.ip,
                            old_status=old_status,
                            new_status=new_status
                        )
                        print(f"  ✅ Email sent!")
                    else:
                        print(f"  ⚠️  No email config or no recipients!")
                else:
                    print(f"  ℹ️  Device came UP - no email sent")

            else:
                symbol = "🟢" if new_status == "UP" else "🔴"
                if response_time:
                    print(f"  {symbol} {device.ip} → {new_status} ({response_time}ms) (no change)")
                else:
                    print(f"  {symbol} {device.ip} → {new_status} (no change)")

        db.session.commit()
        print(f"\n✅ Monitoring complete!")
        print(f"   🟢 UP: {up_count} | 🔴 DOWN: {down_count} | 🚨 Alerts: {alert_count} | ⚠️  Slow: {slow_count}")


# ── Run directly to test ──
if __name__ == "__main__":
    run_monitoring()