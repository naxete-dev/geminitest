import asyncio
import os
import shutil
from playwright.async_api import async_playwright

async def record_demo():
    video_dir = os.path.join(os.path.dirname(__file__), "demo_video_raw")
    os.makedirs(video_dir, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=video_dir,
            record_video_size={"width": 1280, "height": 720}
        )
        page = await context.new_page()

        print("1. Navigating to FitCoach AI Frontend...")
        await page.goto("https://fitcoach-ai-frontend-496783553911.us-east1.run.app", wait_until="networkidle")
        await page.wait_for_timeout(2000)

        print("2. Sending first prompt (4-day workout routine)...")
        await page.click("button:has-text('💪 4-Day Routine')")
        
        # Wait for agent response to appear
        await page.wait_for_selector("#log .msg.agent .bubble:not(:has-text('…'))", timeout=30000)
        await page.wait_for_timeout(4000)

        print("3. Sending second prompt (BMR/TDEE calculation + image generation)...")
        input_el = page.locator("#input")
        await input_el.fill("Calculate my BMR and TDEE: 28yo, 75kg, 180cm, male and generate a workout badge image for my progress!")
        await page.wait_for_timeout(1000)
        await page.click("form button:has-text('Send')")

        # Wait for second response (tool call + image generation)
        # We wait for the second agent bubble to finish loading
        await page.wait_for_function(
            "() => document.querySelectorAll('#log .msg.agent').length >= 2 && !document.querySelectorAll('#log .msg.agent')[1].textContent.includes('…')",
            timeout=60000
        )
        await page.wait_for_timeout(6000)

        print("4. Closing context to save video...")
        path = await page.video.path()
        await context.close()
        await browser.close()

        final_video_path = os.path.abspath("fitcoach_ai_demo.webm")
        shutil.copy(path, final_video_path)
        print(f"SUCCESS: Demo video saved to {final_video_path}")
        return final_video_path

if __name__ == "__main__":
    asyncio.run(record_demo())
