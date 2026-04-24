import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_alert_email(sender_email, sender_password,recipient_emails, device_ip,old_status,new_status):
    # create email sub and body
    subject = f"Network Alert: {device_ip} is {new_status}"
    body = f"""
    NETWORK MONITOR ALERT
    
    Device IP: {device_ip}
    Old Status: {old_status}
    New Status: {new_status}
    
    Please Check the device immediately if it is down
    
    ***
    This is an automated alert from network monitor 
    """
    try:
        # Connect to email
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)

        # Send email to each user
        for recipient in recipient_emails:
            if recipient:
                msg = MIMEMultipart()
                msg['From'] = sender_email
                msg['To'] = recipient
                msg['Subject'] = subject
                msg.attach(MIMEText(body, 'plain'))
                server.sendmail(sender_email, recipient, msg.as_string())
                print(f"Email sent to {recipient}")

        server.quit()
        print(f"Email sent to {recipient_emails}")
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False
    

