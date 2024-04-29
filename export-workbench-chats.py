import os
import json
from tqdm import tqdm
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import time
import re
import argparse
import pyperclip

def parse_args():
    parser = argparse.ArgumentParser(description="Export Workbench Chats with Optional Browser Storage Management")
    parser.add_argument('--save-storage', type=str, help='Path to save browser storage')
    parser.add_argument('--load-storage', type=str, help='Path to load browser storage')
    return parser.parse_args()

def setup_browser(headless=False):
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=headless)
    page = browser.new_page()
    return browser, page
        
def login_and_navigate(page, timeout):
    print("Navigating to Anthropic...")
    page.goto("https://console.anthropic.com")
    print("Anthropic loaded.")
    print("Logging in...")
    page.get_by_test_id("email").click()
    page.get_by_test_id("email").fill(os.environ["ANTHROPIC_EMAIL"])
    print("Email entered.")
    page.get_by_test_id("code").click()
    print("Clicked 'Continue'.")
    print("Waiting for login code input...")
    page.wait_for_url("https://console.anthropic.com/dashboard", timeout=timeout)
    print("Dashboard loaded.")
    context = page.context()
    context.storage_state(path="auth.json")

def main(output_format="json", headless=False, timeout=10000000, load_storage_path="auth.json"):
    print("Starting export of workbench chats...")
    browser, page = setup_browser(headless)
    if load_storage_path and os.path.exists(load_storage_path):
        browser.new_context(storage_state=load_storage_path)
        context = browser.new_context(storage_state="auth.json")
        page = context.new_page()
    else:
        login_and_navigate(page, timeout)
    
    page.goto("https://console.anthropic.com/workbench")
    page.get_by_label("Your prompts").click()
    unnamed_chats_list = page.get_by_role("button", name=re.compile(r"Untitled - \d{4}-\d{2}-\d{2} \d{1,2}:\d{2}(:\d{2})?( (AM|PM|a\.m\.|p\.m\.))?"))
    unnamed_chats_count = unnamed_chats_list.count()
    print(unnamed_chats_list.all_inner_texts())
    print("Number of unnamed chats: ", unnamed_chats_count)
    chat_names = []
    for i in range(unnamed_chats_count):
        chat = unnamed_chats_list.nth(i)
        chat_name = re.search(r"Untitled - \d{4}-\d{2}-\d{2} \d{1,2}:\d{2}:\d{2}", chat.inner_text()).group()
        print(chat_name)
        chat_names.append(chat_name)    

    for chat_name in chat_names:
        page.get_by_role("button", name=chat_name).click()
        print(f"Getting conversation code for {chat_name}...")
        page.get_by_role("button", name="Get Code").click()
        print("Conversation code gotten.")
        page.get_by_role("button", name="Copy Code").click()
        print("Conversation code copied.")
        page.get_by_role("button").nth(2).click()
        print("Exporting conversation code...")
        chat_code = pyperclip.paste()
        print(chat_code)
        
        file_path = f"chats/{chat_name}.txt"
        with open(file_path, "w") as file:
            file.write(chat_code)
        print(f"Saved conversation code for {chat_name} to {file_path}")

        page.goto("https://console.anthropic.com/workbench")
        page.get_by_label("Your prompts").click()

if __name__ == "__main__":
    args = parse_args()
    load_dotenv()
    main(output_format="json", headless=False, timeout=10000000, load_storage_path=args.load_storage)
