import logging
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from database import Database
from mail_manager import MailManager
from config import BOT_TOKEN, ADMIN_IDS

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)

logger = logging.getLogger(__name__)

class FakeMailBot:
    def __init__(self):
        try:
            self.db = Database()
            self.mail_manager = MailManager()
            self.application = Application.builder().token(BOT_TOKEN).build()
            self.setup_handlers()
            logger.info("FakeMailBot initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            raise

    def setup_handlers(self):
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("id", self.show_id))
        self.application.add_handler(CommandHandler("create", self.create_premium_code))
        self.application.add_handler(CommandHandler("redeem", self.redeem_premium))
        self.application.add_handler(CommandHandler("stats", self.show_stats))
        self.application.add_handler(CommandHandler("inbox", self.show_inbox))
        self.application.add_handler(CommandHandler("help", self.help_command))
        
        # Message handlers for delete commands
        self.application.add_handler(MessageHandler(
            filters.Regex(r'^/delete_\d+$'), self.delete_email
        ))
        
        # Callback query handlers
        self.application.add_handler(CallbackQueryHandler(self.button_handler))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user = update.effective_user
            self.db.create_user(user.id, user.username)
            
            welcome_text = """
🤖 **Welcome to Fake Mail Bot!**

📧 Create temporary email addresses with @wizard.com domain
📨 Receive emails in your inbox
🔒 Secure and private

**Commands:**
/id - Show your fake emails
/inbox - Check all inbox messages
/stats - Show your statistics
/redeem - Redeem premium code
/help - Show help message

**Premium Features:**
• Create up to 500 fake emails (Free: 100)
• Priority support

**Menu Options Below:** 👇
            """
            
            keyboard = [
                [InlineKeyboardButton("📧 Create Fake Mail", callback_data="create_mail")],
                [InlineKeyboardButton("📨 Check Inbox", callback_data="check_inbox")],
                [InlineKeyboardButton("📊 Statistics", callback_data="show_stats")],
                [InlineKeyboardButton("💎 Premium Info", callback_data="premium_info")],
                [InlineKeyboardButton("❓ Help", callback_data="show_help")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
            logger.info(f"New user started: {user.id} - @{user.username}")
            
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """
🆘 **Help Guide**

**Basic Commands:**
/start - Start the bot
/id - List your fake emails
/inbox - Check received messages
/stats - Show your account statistics
/redeem <code> - Redeem premium code

**Email Management:**
• Use buttons below to create new emails
• Click on delete links to remove emails
• All emails use @wizard.com domain

**Premium Features:**
• 500 email limit (vs 100 for free)
• Priority processing
• Use /redeem with premium code

**Need Help?**
Contact admin for support with premium codes or issues.
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def create_premium_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user_id = update.effective_user.id
            
            if user_id not in ADMIN_IDS:
                await update.message.reply_text("❌ This command is for admins only.")
                return
            
            if not context.args:
                await update.message.reply_text("Usage: /create <premium_code>\nExample: /create WIZARD123")
                return
            
            code = context.args[0].upper()
            if len(code) < 4:
                await update.message.reply_text("❌ Premium code must be at least 4 characters long.")
                return
            
            if self.db.create_premium_code(code, user_id):
                await update.message.reply_text(
                    f"✅ Premium code created successfully!\n\n"
                    f"**Code:** `{code}`\n"
                    f"**Usage:** `/redeem {code}`\n\n"
                    f"Share this code with users to grant premium access.", 
                    parse_mode='Markdown'
                )
                logger.info(f"Admin {user_id} created premium code: {code}")
            else:
                await update.message.reply_text("❌ Failed to create premium code. It might already exist.")
                
        except Exception as e:
            logger.error(f"Error in create_premium_code: {e}")
            await update.message.reply_text("❌ An error occurred while creating premium code.")

    async def redeem_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user_id = update.effective_user.id
            
            if not context.args:
                await update.message.reply_text("Usage: /redeem <premium_code>\nExample: /redeem WIZARD123")
                return
            
            code = context.args[0].upper()
            premium_code = self.db.get_premium_code(code)
            
            if not premium_code:
                await update.message.reply_text("❌ Invalid premium code.")
                return
            
            if premium_code[2]:  # Check if already used
                await update.message.reply_text("❌ This premium code has already been used.")
                return
            
            if self.db.use_premium_code(code, user_id):
                self.db.update_user_premium(user_id, True, 30)  # 30 days premium
                await update.message.reply_text(
                    "🎉 **Premium activated successfully!**\n\n"
                    "✨ **You now have:**\n"
                    "• 30 days of premium access\n"
                    "• 500 email limit (instead of 100)\n"
                    "• Priority processing\n\n"
                    "Thank you for upgrading!",
                    parse_mode='Markdown'
                )
                logger.info(f"User {user_id} redeemed premium code: {code}")
            else:
                await update.message.reply_text("❌ Failed to redeem premium code.")
                
        except Exception as e:
            logger.error(f"Error in redeem_premium: {e}")
            await update.message.reply_text("❌ An error occurred while redeeming premium code.")

    # ... (other methods remain the same as previous version)

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            query = update.callback_query
            await query.answer()
            
            user_id = query.from_user.id
            data = query.data
            
            if data == "create_mail":
                email, password = self.mail_manager.create_fake_email(user_id)
                
                if email:
                    response = f"""
✅ **New Fake Email Created!**

📧 **Email:** `{email}`
🔑 **Password:** `{password}`

💡 Use this email to sign up for services. All received emails will appear in your inbox.
                    """
                    
                    # Update email list
                    email_list = self.mail_manager.get_user_emails_list(user_id)
                    response += f"\n\n**Your Fake Emails:**\n\n{email_list}"
                    
                    # Add create another button
                    keyboard = [
                        [InlineKeyboardButton("📧 Create Another", callback_data="create_mail")],
                        [InlineKeyboardButton("📨 Check Inbox", callback_data="check_inbox")],
                        [InlineKeyboardButton("📊 Statistics", callback_data="show_stats")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(response, parse_mode='Markdown', reply_markup=reply_markup)
                    logger.info(f"User {user_id} created new email: {email}")
                else:
                    await query.edit_message_text(f"❌ {password}", parse_mode='Markdown')
                
            elif data == "check_inbox":
                await self.show_inbox_for_query(query, user_id)
                
            elif data == "show_stats":
                stats = self.mail_manager.get_user_stats(user_id)
                premium_status = "✅ Premium User" if stats['is_premium'] else "❌ Free User"
                premium_expiry = "Lifetime" if stats['is_premium'] else "Not active"
                
                stats_text = f"""
**📊 Your Statistics**

**Account Status:** {premium_status}
**Premium Expiry:** {premium_expiry}
**Fake Emails Created:** {stats['email_count']}
**Email Limit:** {stats['limit']}
**Remaining:** {stats['remaining']}

{'⭐ Enjoy your premium benefits!' if stats['is_premium'] else '💎 Use /redeem to upgrade to premium!'}
                """
                await query.edit_message_text(stats_text, parse_mode='Markdown')
                
            elif data == "premium_info":
                premium_text = """
💎 **Premium Features**

✨ **Benefits:**
• Create up to 500 fake emails (Free: 100)
• Priority email processing
• Extended email retention
• Premium support

🔑 **How to get premium?**
Contact admin for premium codes and use `/redeem <code>` to activate premium.

**Current Premium Codes:**
Contact @admin for available codes
                """
                await query.edit_message_text(premium_text, parse_mode='Markdown')
                
            elif data == "show_help":
                await self.help_for_query(query)
                
        except Exception as e:
            logger.error(f"Error in button_handler: {e}")
            await query.edit_message_text("❌ An error occurred. Please try again.")

    async def help_for_query(self, query):
        help_text = """
🆘 **Help Guide**

**Quick Actions:**
• Use buttons to create emails and check inbox
• Click delete links to remove emails
• Check stats to see your limits

**Need Premium?**
Contact admin for premium codes that give you 500 email limit!
        """
        await query.edit_message_text(help_text, parse_mode='Markdown')

    def run(self):
        """Start the bot"""
        logger.info("🤖 Fake Mail Bot is starting...")
        logger.info(f"📧 Domain: wizard.com")
        logger.info(f"💎 Admin ID: {ADMIN_IDS[0]}")
        logger.info(f"🔑 Free limit: {FREE_USER_MAIL_LIMIT}")
        logger.info(f"⭐ Premium limit: {PREMIUM_USER_MAIL_LIMIT}")
        
        try:
            self.application.run_polling()
        except Exception as e:
            logger.error(f"Bot stopped with error: {e}")

if __name__ == "__main__":
    bot = FakeMailBot()
    bot.run()