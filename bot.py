from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import Update
import uuid
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import subprocess
import logging

# લોગિંગ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# રેન્ડમ એન્ક્રિપ્શન કી
key = get_random_bytes(16)

# બોટ ટોકન
TOKEN = os.getenv("TELEGRAM_TOKEN")

def txt_to_pdf(input_txt, output_pdf):
    try:
        c = canvas.Canvas(output_pdf, pagesize=letter)
        with open(input_txt, 'r', encoding='utf-8') as f:
            text = f.readlines()
        
        y = 750
        for line in text:
            c.drawString(100, y, line.strip())
            y -= 15
            if y < 50:
                c.showPage()
                y = 750
        c.save()
    except Exception as e:
        logger.error(f"PDF conversion failed: {e}")
        raise

def txt_to_video(input_txt, output_video):
    try:
        with open(input_txt, 'r', encoding='utf-8') as f:
            text = f.read()
        
        temp_image = f"temp_{uuid.uuid1()}.png"
        subprocess.run([
            "convert", "-background", "white", "-fill", "black",
            "-font", "DejaVu-Sans", "-pointsize", "24",
            f"label:{text}", temp_image
        ], check=True, capture_output=True, text=True)
        
        subprocess.run([
            "ffmpeg", "-loop", "1", "-i", temp_image,
            "-c:v", "libx264", "-t", "10", "-pix_fmt", "yuv420p",
            output_video, "-y"
        ], check=True, capture_output=True, text=True)
        
        os.remove(temp_image)
    except subprocess.CalledProcessError as e:
        logger.error(f"Video conversion failed: {e.stderr}")
        raise
    except Exception as e:
        logger.error(f"Video conversion failed: {e}")
        raise

def encrypt_file(input_file, output_file, key):
    try:
        if len(key) != 16:
            raise ValueError("Key must be 16 bytes long")
        
        cipher = AES.new(key, AES.MODE_EAX)
        with open(input_file, 'rb') as f:
            file_data = f.read()
        
        ciphertext, tag = cipher.encrypt_and_digest(file_data)
        
        with open(output_file, 'wb') as f:
            [f.write(x) for x in (cipher.nonce, tag, ciphertext)]
        
        return cipher.nonce, tag
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        raise

def start(update: Update, context):
    update.message.reply_text('Hello! Send /to_pdf or /to_video and reply to a TXT file to convert and upload with DRM.')

def to_pdf(update: Update, context):
    message = update.message
    try:
        if message.reply_to_message and message.reply_to_message.document:
            doc = message.reply_to_message.document
            if doc.mime_type == 'text/plain':
                file = context.bot.get_file(doc.file_id)
                txt_file = f"temp_{uuid.uuid1()}.txt"
                pdf_file = f"output_{uuid.uuid1()}.pdf"
                encrypted_file = f"encrypted_{pdf_file}"
                
                message.reply_text('Downloading TXT file...')
                file.download(txt_file)
                
                message.reply_text('Converting to PDF...')
                txt_to_pdf(txt_file, pdf_file)
                
                message.reply_text('Encrypting PDF...')
                nonce, tag = encrypt_file(pdf_file, encrypted_file, key)
                message.reply_text(f'PDF encrypted! Uploading...\nEncryption Key: {key.hex()}')
                
                context.bot.send_document(chat_id=message.chat_id, document=open(encrypted_file, 'rb'), caption='Encrypted PDF')
                
                os.remove(txt_file)
                os.remove(pdf_file)
                os.remove(encrypted_file)
            else:
                message.reply_text('Please reply to a TXT file.')
        else:
            message.reply_text('Please reply to a TXT file with /to_pdf.')
    except Exception as e:
        message.reply_text(f'Error occurred: {str(e)}')
        logger.error(f"PDF processing failed: {e}")

def to_video(update: Update, context):
    message = update.message
    try:
        if message.reply_to_message and message.reply_to_message.document:
            doc = message.reply_to_message.document
            if doc.mime_type == 'text/plain':
                file = context.bot.get_file(doc.file_id)
                txt_file = f"temp_{uuid.uuid1()}.txt"
                video_file = f"output_{uuid.uuid1()}.mp4"
                encrypted_file = f"encrypted_{video_file}"
                
                message.reply_text('Downloading TXT file...')
                file.download(txt_file)
                
                message.reply_text('Converting to Video...')
                txt_to_video(txt_file, video_file)
                
                message.reply_text('Encrypting Video...')
                nonce, tag = encrypt_file(video_file, encrypted_file, key)
                message.reply_text(f'Video encrypted! Uploading...\nEncryption Key: {key.hex()}')
                
                context.bot.send_document(chat_id=message.chat_id, document=open(encrypted_file, 'rb'), caption='Encrypted Video')
                
                os.remove(txt_file)
                os.remove(video_file)
                os.remove(encrypted_file)
            else:
                message.reply_text('Please reply to a TXT file.')
        else:
            message.reply_text('Please reply to a TXT file with /to_video.')
    except Exception as e:
        message.reply_text(f'Error occurred: {str(e)}')
        logger.error(f"Video processing failed: {e}")

def error_handler(update: Update, context):
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.message:
        update.message.reply_text('An error occurred. Please try again.')

def main():
    try:
        updater = Updater(TOKEN, use_context=True)
        dp = updater.dispatcher
        
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CommandHandler("to_pdf", to_pdf))
        dp.add_handler(CommandHandler("to_video", to_video))
        dp.add_error_handler(error_handler)
        
        updater.start_polling()
        updater.idle()
    except Exception as e:
        logger.error(f"Bot failed to start: {e}")
        print(f"Bot failed to start: {e}")

if __name__ == '__main__':
    main()
