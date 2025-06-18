import os
import re
import csv
from pathlib import Path
from pdfminer.high_level import extract_text
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import time

CONTACTS_FILE = 'contacts.csv'
PDF_FOLDER = 'guias'
WHATSAPP_URL = 'https://web.whatsapp.com/'

def load_contacts():
    contacts = {}
    if not os.path.exists(CONTACTS_FILE):
        return contacts
    with open(CONTACTS_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            doc = re.sub(r'\D', '', row.get('document', ''))
            phone = row.get('phone', '')
            if doc and phone:
                contacts[doc] = phone
    return contacts

def find_document_in_pdf(pdf_path):
    text = extract_text(pdf_path)
    matches = re.findall(r'(\d{11}|\d{14})', text)
    return matches[0] if matches else None

def send_file_via_whatsapp(phone, filepath, driver):
    driver.get(WHATSAPP_URL)
    print('Scan the QR code if required...')
    # Wait for login
    while 'login' in driver.current_url:
        time.sleep(2)
    search_box = driver.find_element(By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]')
    search_box.click()
    search_box.send_keys(phone)
    search_box.send_keys(Keys.ENTER)
    time.sleep(2)
    attach_btn = driver.find_element(By.CSS_SELECTOR, 'span[data-testid="clip"]')
    attach_btn.click()
    time.sleep(1)
    file_input = driver.find_element(By.CSS_SELECTOR, 'input[type="file"]')
    file_input.send_keys(str(Path(filepath).resolve()))
    time.sleep(2)
    send_btn = driver.find_element(By.CSS_SELECTOR, 'span[data-icon="send"]')
    send_btn.click()
    time.sleep(2)

def process_pdfs():
    contacts = load_contacts()
    if not contacts:
        print('No contacts found.')
        return
    chrome_options = Options()
    chrome_options.add_argument('--user-data-dir=./user_data')
    driver = webdriver.Chrome(options=chrome_options)
    try:
        for pdf_file in Path(PDF_FOLDER).glob('*.pdf'):
            doc = find_document_in_pdf(pdf_file)
            if not doc:
                print(f'No document found in {pdf_file}')
                continue
            phone = contacts.get(doc)
            if not phone:
                print(f'No phone for document {doc}')
                continue
            send_file_via_whatsapp(phone, pdf_file, driver)
    finally:
        driver.quit()

if __name__ == '__main__':
    process_pdfs()
