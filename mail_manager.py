import random
import string
from database import Database
from config import DOMAIN

class MailManager:
    def __init__(self):
        self.db = Database()

    def generate_random_email(self):
        """Generate a random email address with wizard.com domain"""
        username_length = random.randint(6, 10)
        username = ''.join(random.choices(string.ascii_lowercase, k=username_length))
        return f"{username}@{DOMAIN}"

    def generate_password(self):
        """Generate a random password"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

    def create_fake_email(self, user_id):
        """Create a new fake email for user"""
        # Check user's email limit
        user = self.db.get_user(user_id)
        email_count = self.db.get_email_count(user_id)
        
        is_premium = user[2] if user else False
        limit = 500 if is_premium else 100
        
        if email_count >= limit:
            return None, f"Limit reached! Free users: 100 emails, Premium: 500 emails. You have {email_count}/{limit}"

        # Generate unique email
        max_attempts = 10
        for _ in range(max_attempts):
            email = self.generate_random_email()
            password = self.generate_password()
            
            if self.db.create_fake_email(user_id, email, password):
                return email, password
        
        return None, "Failed to generate unique email. Please try again."

    def get_user_emails_list(self, user_id):
        """Get formatted list of user's fake emails"""
        emails = self.db.get_user_emails(user_id)
        email_list = []
        
        for i, email in enumerate(emails, 1):
            email_list.append(f"{i}. {email[2]} | /delete_{email[0]}")
        
        return "\n".join(email_list) if email_list else "No fake emails created yet."

    def delete_email(self, email_id, user_id):
        """Delete a fake email"""
        return self.db.delete_fake_email(email_id, user_id)

    def get_user_stats(self, user_id):
        """Get user statistics"""
        user = self.db.get_user(user_id)
        email_count = self.db.get_email_count(user_id)
        is_premium = user[2] if user else False
        limit = 500 if is_premium else 100
        
        return {
            'email_count': email_count,
            'is_premium': is_premium,
            'limit': limit,
            'remaining': limit - email_count
        }