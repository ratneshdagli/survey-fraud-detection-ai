import asyncio
import requests
import subprocess
import os
from playwright.async_api import async_playwright

CHROME_DEBUG_PORT = 9222
# 2 minutes max wait for a long fraud analysis to finish generating
CHATGPT_RESPONSE_TIMEOUT = 120000 
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CHROME_USER_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chrome_profile")

def _launch_chrome():
    """Launch Chrome with remote debugging enabled using an isolated profile."""
    # Ensure the directory exists
    os.makedirs(CHROME_USER_DATA_DIR, exist_ok=True)
    
    cmd = [
        CHROME_PATH,
        f"--remote-debugging-port={CHROME_DEBUG_PORT}",
        "--no-first-run",
        "--no-default-browser-check",
        f"--user-data-dir={CHROME_USER_DATA_DIR}",
    ]
    print(f"[ChatGPT Browser] Launching Chrome with isolated profile: {' '.join(cmd)}")
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

async def get_ws_url():
    """Get the WebSocket debugger URL from Chrome's /json/version endpoint."""
    try:
        resp = requests.get(f"http://127.0.0.1:{CHROME_DEBUG_PORT}/json/version", timeout=3)
        data = resp.json()
        return data.get("webSocketDebuggerUrl", "")
    except Exception:
        return None

async def run_chatgpt_analysis(prompt: str) -> str:
    """
    Connects to a local Chrome instance via CDP, opens/finds ChatGPT,
    pastes the prompt, waits for the response, and returns the result text.
    """
    ws_url = await get_ws_url()
    
    if not ws_url:
        print(f"[ChatGPT Browser] Chrome debug instance not found on port {CHROME_DEBUG_PORT}. Auto-launching...")
        if os.path.exists(CHROME_PATH):
            _launch_chrome()
            await asyncio.sleep(4)  # Wait for Chrome to fully launch
            ws_url = await get_ws_url()
            
        if not ws_url:
            raise ConnectionError(
                f"Chrome is not running with remote debugging on port {CHROME_DEBUG_PORT} and auto-launch failed.\n"
                f"Please close all Chrome windows and launch it with: google-chrome --remote-debugging-port={CHROME_DEBUG_PORT}"
            )
    
    print(f"[ChatGPT Browser] Connecting to Chrome CDP...")
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(ws_url)
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Chrome CDP: {e}")
        
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        
        # Look for an existing ChatGPT tab
        chatgpt_page = None
        for page in context.pages:
            if "chatgpt.com" in page.url:
                chatgpt_page = page
                await chatgpt_page.bring_to_front()
                print("[ChatGPT Browser] Found existing ChatGPT tab.")
                break
        
        # Open a new tab if not found
        if not chatgpt_page:
            print("[ChatGPT Browser] Opening a new ChatGPT tab...")
            chatgpt_page = await context.new_page()
            await chatgpt_page.goto("https://chatgpt.com/", wait_until="domcontentloaded")
            await chatgpt_page.wait_for_timeout(3000)
            
        try:
            response_text = await _automate_chatgpt_page(chatgpt_page, prompt)
            return response_text
        finally:
            # Done, disconnect but do not close the user's browser
            await browser.close()

async def _automate_chatgpt_page(page, prompt: str) -> str:
    """Internal automation flow for the ChatGPT page."""
    
    print("[ChatGPT Browser] Waiting for ChatGPT to be ready...")
    
    # Wait for the prompt textarea or contenteditable div
    max_attempts = 15
    input_el = None
    for attempt in range(max_attempts):
        await page.wait_for_timeout(2000)
        
        # Check for login requirement
        login_btn = page.locator('button:has-text("Log in"), a:has-text("Log in")')
        if await login_btn.count() > 0 and await login_btn.first.is_visible():
            raise RuntimeError("You need to log into ChatGPT in the Chrome window first.")
            
        prosemirror = page.locator('div.ProseMirror[contenteditable="true"]')
        if await prosemirror.count() > 0 and await prosemirror.first.is_visible():
            input_el = prosemirror.first
            break
            
        editable = page.locator('div[contenteditable="true"]:visible')
        if await editable.count() > 0:
            input_el = editable.first
            break
            
        textarea = page.locator('textarea[placeholder="Ask anything"]:visible, textarea[id="prompt-textarea"]:visible')
        if await textarea.count() > 0:
            input_el = textarea.first
            break
            
        print(f"[ChatGPT Browser] Waiting for chat input ({attempt+1}/{max_attempts})...")
        
    if not input_el:
        raise TimeoutError("Could not find ChatGPT input area.")
        
    print("[ChatGPT Browser] Pasting prompt...")
    # Using JS clipboard approach to handle large prompts effortlessly
    await page.evaluate("(text) => { navigator.clipboard.writeText(text); }", prompt)
    await page.wait_for_timeout(500)
    
    await input_el.click()
    await page.keyboard.press("Control+KeyV")
    await page.wait_for_timeout(1000)
    
    # Click send button or press enter
    send_btn = page.locator('button[data-testid="send-button"]')
    if await send_btn.count() > 0 and await send_btn.first.is_enabled():
        await send_btn.first.click()
    else:
        await page.keyboard.press("Enter")
        
    print("[ChatGPT Browser] Prompt sent. Waiting for response...")
    
    # Wait for response to start streaming
    await page.wait_for_timeout(5000)
    
    # Wait until generation finishes (streaming indicator disappears)
    waited = 0
    poll_interval = 2000
    while waited < CHATGPT_RESPONSE_TIMEOUT:
        await page.wait_for_timeout(poll_interval)
        waited += poll_interval
        
        still_generating = page.locator('.result-streaming, button[aria-label*="Stop"]')
        if await still_generating.count() == 0:
            await page.wait_for_timeout(2000) # double check
            if await still_generating.count() == 0:
                print("[ChatGPT Browser] ✓ Response finished streaming.")
                break
                
        if waited % 10000 == 0:
            print(f"[ChatGPT Browser] Still generating... ({waited//1000}s)")
            
    # Extract the response text
    response_elements = page.locator('[data-message-author-role="assistant"] .markdown')
    if await response_elements.count() > 0:
        text = await response_elements.last.inner_text()
        return text
        
    # Fallbacks for extraction
    articles = page.locator('article[data-testid*="assistant-message"]')
    if await articles.count() > 0:
        return await articles.last.inner_text()
        
    raise RuntimeError("Could not extract response from ChatGPT.")

# Test harness
if __name__ == "__main__":
    text = asyncio.run(run_chatgpt_analysis("Respond with a JSON object { \"hello\": \"world\" }"))
    print("OUTPUT:\n", text)
