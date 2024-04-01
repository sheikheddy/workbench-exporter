import os
import json
from tqdm import tqdm
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import time


def main(output_format="json", headless=False, timeout=3000000):
    print("Starting export of workbench chats...")
    with sync_playwright() as p:
        print("Launching browser...")
        browser = p.firefox.launch(headless=headless)
        print("Browser launched.")
        page = browser.new_page()
        print("New page created.")
        try:
            print("Navigating to Anthropic...")
            page.goto("https://console.anthropic.com")
            print("Anthropic loaded.")
            print("Logging in...")

            page.wait_for_selector("input#email", timeout=timeout)
            page.fill("input#email", value=os.environ["ANTHROPIC_EMAIL"])
            print("Email entered.")
            page.wait_for_selector("button:has-text('Continue')", timeout=timeout)
            page.click("button:has-text('Continue')")
            print("Clicked 'Continue'.")
            print("Waiting for login code input...")
            page.wait_for_url(
                "https://console.anthropic.com/dashboard", timeout=timeout
            )
            print("Dashboard loaded.")
            page.goto("https://console.anthropic.com/workbench")
            print("Workbench loaded.")

            max_retries = 3
            retry_delay = 5  # Delay in seconds between retries
            for retry in tqdm(range(max_retries), desc="Retrying"):
                try:
                    page.wait_for_selector(
                        "button[aria-label='Your prompts']", timeout=timeout
                    )
                    print("'your prompts' button found.")
                    break
                except TimeoutError:
                    if retry == max_retries - 1:
                        raise
                    print(
                        f"Selector not found. Retrying in {retry_delay} seconds... (Attempt {retry + 1})"
                    )
                    time.sleep(retry_delay)
            page.click("button[aria-label='Your prompts']")
            print("Clicked 'your prompts'.")

            # ==================================================================================
            # IMPORTANT: This script is currently in development.
            # This repo is a homework problem for my project in berkeley ai safety's supervised program for alignment research.
            # The script is not yet complete and is not guaranteed to work as expected from this point onwards.
            # ==================================================================================

            page.wait_for_selector("ul.flex.flex-col.gap-1", timeout=timeout)
            print("Prompt list loaded.")
            conversations = page.query_selector_all(
                "button.inline-flex.items-center.justify-center.relative"
            )
            print("Conversations found.")
            for i, conversation in tqdm(
                enumerate(conversations), total=len(conversations)
            ):
                print(f"Exporting conversation {i+1}...")
                conversation.click()
                page.wait_for_selector(".message-list", timeout=timeout)
                print("Conversation loaded.")
                # Get conversation title, handle potential missing title
                title_element = conversation.query_selector(
                    "div.font-bold.text-left.truncate.w-full.min-w-\[0px\]"
                )
                title = (
                    title_element.inner_text()
                    if title_element
                    else f"conversation_{i+1}"
                )
                print("Title found.")
                folder_name = f"conversation_{i+1}_{title}"
                os.makedirs(folder_name, exist_ok=True)
                print("Folder created.")
                prompts = []
                for prompt in tqdm(
                    page.query_selector_all(".user-message"),
                    total=len(page.query_selector_all(".user-message")),
                ):
                    content_element = prompt.query_selector(".message-content")
                    timestamp_element = prompt.query_selector(".message-timestamp")

                    # Handle potential missing content or timestamp
                    content = content_element.inner_text() if content_element else ""
                    timestamp = (
                        timestamp_element.inner_text() if timestamp_element else ""
                    )

                    prompts.append({"content": content, "timestamp": timestamp})
                print("Prompts extracted.")
                if output_format == "json":
                    with open(f"{folder_name}/prompts.json", "w") as f:
                        json.dump(prompts, f, indent=2)
                else:
                    with open(f"{folder_name}/prompts.txt", "w") as f:
                        for prompt in prompts:
                            f.write(
                                f"Content: {prompt['content']}\nTimestamp: {prompt['timestamp']}\n\n"
                            )
                print("Prompts written to file.")
                # Handle potential missing "get code" button
                get_code_button = page.query_selector("text=get code")
                if get_code_button:
                    get_code_button.click()
                    page.wait_for_selector(".api-code-modal", timeout=timeout)

                    api_code_element = page.query_selector(".api-code-content")
                    api_code = api_code_element.inner_text() if api_code_element else ""

                    with open(f"{folder_name}/api_code.txt", "w") as f:
                        f.write(api_code)
                    print("API code written to file.")
                    close_button = page.query_selector(".api-code-modal .close-button")
                    if close_button:
                        close_button.click()
                else:
                    print(f"Warning: 'get code' button not found for {folder_name}")
                print(f"Conversation {i+1} exported.")
        except Exception as e:
            print(f"An error occurred: {str(e)}")
        finally:
            browser.close()
            print("Browser closed.")


if __name__ == "__main__":
    load_dotenv()
    main(output_format="json", headless=False, timeout=3000000)
