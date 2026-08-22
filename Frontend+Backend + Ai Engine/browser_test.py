import os
import time
from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        print("Launching browser...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        requests = []
        responses = []
        
        page.on("request", lambda request: requests.append(request))
        page.on("response", lambda response: responses.append(response))

        print("Navigating to login page...")
        page.goto("http://localhost:5173/login")
        time.sleep(2)
        
        print("Filling form...")
        page.fill('input[type="email"]', 'employee@demo.com')
        page.fill('input[type="password"]', 'demo123')
        
        print("Clicking submit...")
        page.click('button[type="submit"]')
        
        time.sleep(3)
        
        print("\n--- BROWSER REQUEST EVIDENCE ---")
        for req in requests:
            if "login" in req.url and req.method != "OPTIONS":
                print(f"Request URL: {req.url}")
                print(f"Request Method: {req.method}")
                print(f"Request Payload: {req.post_data}")
                
        for res in responses:
            if "login" in res.url and res.request.method != "OPTIONS":
                print(f"Response Status: {res.status}")
                try:
                    print(f"Response Body: {res.body().decode('utf-8')[:200]}...")
                except Exception as e:
                    print(f"Response Body: [Could not decode - {e}]")
                    
        # Check current URL to see if it redirected
        print(f"\nCurrent URL after login: {page.url}")
        
        # Check for error text in the DOM
        try:
            error_el = page.locator('text="Invalid email or password."')
            if error_el.count() > 0:
                print("UI ERROR DETECTED: 'Invalid email or password.' is visible on the page.")
        except Exception:
            pass

        print("\n--- AUTHENTICATED API REQUESTS ---")
        for req in requests:
            if "login" not in req.url and "localhost:5173" not in req.url and "127.0.0.1:5173" not in req.url and req.method != "OPTIONS":
                print(f"Auth Request URL: {req.url}")
                print(f"Auth Request Headers: Authorization -> {req.headers.get('authorization', 'NONE')}")

        browser.close()

if __name__ == "__main__":
    run()
