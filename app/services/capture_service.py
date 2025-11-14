import os
import asyncio
from typing import List, Dict, Any
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from app.utils.config import settings
from app.services.page_analyzer import page_analyzer
from app.services.llm_agent import llm_agent

class CaptureService:
    async def execute_steps(self, app: str, instruction: str) -> List[Dict[str, Any]]:
        base_dir = f"app/dataset/notion_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(base_dir, exist_ok=True)
        captured_steps = []

        async with async_playwright() as p:
            browser = None
            context = None
            page = None
            
            try:
                profile_path = "./playwright_profile"
                print(f"Using dedicated Playwright profile: {profile_path}")
                
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=profile_path,
                    headless=False,
                    viewport={"width": 1280, "height": 720}
                )
                page = await context.new_page()
                
                page.set_default_navigation_timeout(45000)
                page.set_default_timeout(30000)

                initial_url = "https://www.notion.so/"
                try:
                    print(f"Navigating to {initial_url}...")
                    await page.goto(initial_url, wait_until="domcontentloaded", timeout=45000)
                    await asyncio.sleep(2)
                    print(f"Loaded: {page.url}")
                except PlaywrightTimeoutError:
                    print(f"Timeout navigating to {initial_url}, continuing")
                except Exception as e:
                    print(f"Navigation error: {e}")

                page_context = {}
                try:
                    page_context = await page_analyzer.analyze_page(page)
                    print(f"Notion page analysis: Found {len(page_context.get('interactive_elements', []))} interactive elements")
                except Exception as e:
                    print(f"Page analysis failed: {e}")
                    page_context = {
                        "url": page.url if page else "unknown",
                        "title": await page.title() if page else "unknown"
                    }

                page_state = await self._detect_notion_page_state(page)
                print(f"Notion page state: {page_state}")

                if page_state == "login_required":
                    print("Notion login required. Please log in manually...")
                    print("Waiting for workspace detection (3 minutes max)...")
                    
                    try:
                        await page.wait_for_function(
                            """() => {
                                return document.querySelector('.notion-sidebar') || 
                                    document.querySelector('[data-block-id]') ||
                                    document.querySelector('[data-testid*=\"create\"]') ||
                                    document.querySelector('.notion-frame') ||
                                    document.querySelector('[aria-label*=\"New\"]') ||
                                    document.body.innerText.includes('New page') ||
                                    document.body.innerText.includes('Search') ||
                                    document.body.innerText.includes('Workspace');
                            }""",
                            timeout=180000
                        )
                        
                        print("Notion workspace detected. Login successful. Proceeding...")
                        
                    except Exception as e:
                        print(f"Notion authentication timeout: {e}")
                        screenshot_path = os.path.join(base_dir, "login_timeout.png")
                        await page.screenshot(path=screenshot_path)
                        page_text = await page.evaluate("() => document.body.innerText")
                        print(f"Current page content: {page_text[:200]}...")
                        
                        return [{
                            "action": "error",
                            "selector_hint": "authentication",
                            "description": "Notion login timeout",
                            "value": None,
                            "url": page.url,
                            "screenshot_path": screenshot_path,
                            "error": f"Could not detect Notion workspace. Content: {page_text[:100]}..."
                        }]

                elif page_state == "authenticated":
                    print("Notion authenticated. Proceeding with task...")
                else:
                    print("Unknown Notion page state. Proceeding cautiously...")
                    page_content = await page.content()
                    if len(page_content) > 3000:
                        print("Page has content, proceeding...")
                    else:
                        print("Page seems empty, cannot proceed.")
                        return [{
                            "action": "error",
                            "selector_hint": "page_analysis", 
                            "description": "Notion page state unclear",
                            "value": None,
                            "url": page.url,
                            "error": "Could not determine Notion page state"
                        }]

                steps_raw = []
                try:
                    steps_raw = await llm_agent.analyze_page_and_generate_steps(
                        "Notion", instruction, page_context
                    )
                    print(f"Generated {len(steps_raw)} steps for Notion")
                except Exception as e:
                    print(f"Notion step generation failed: {e}")
                    steps_raw = [
                        {
                            "action": "click",
                            "selector_hint": "New",
                            "description": "Find new/create button",
                            "value": None,
                            "url": None
                        },
                        {
                            "action": "fill", 
                            "selector_hint": "Untitled",
                            "description": "Enter title",
                            "value": "Notion Page",
                            "url": None
                        }
                    ]

                for i, step in enumerate(steps_raw, start=1):
                    try:
                        print(f"Executing Notion step {i}/{len(steps_raw)}: {step.get('action')} '{step.get('selector_hint')}'")
                        
                        before_screenshot = await page.screenshot()

                        step_success = await self._execute_single_step(page, step, i, "Notion")
                        
                        if not step_success:
                            print(f"Step {i} failed, stopping execution")
                            error_screenshot = os.path.join(base_dir, f"error_step_{i}.png")
                            await page.screenshot(path=error_screenshot)
                            captured_steps.append({
                                **step, 
                                "screenshot_path": error_screenshot, 
                                "error": "Step execution failed",
                                "url": page.url if page else "unknown",
                                "verified": False
                            })
                            break
                        
                        action_verified = await self._verify_action(page, step, before_screenshot)
                        if not action_verified:
                            print(f"Action verification uncertain for step {i}")
                        
                        screenshot_path = os.path.join(base_dir, f"step_{i}.png")
                        await page.screenshot(path=screenshot_path)
                        
                        try:
                            page_context = await page_analyzer.analyze_page(page)
                        except Exception as e:
                            print(f"Page analysis update failed: {e}")
                        
                        captured_steps.append({
                            **step, 
                            "screenshot_path": screenshot_path, 
                            "url": page.url,
                            "page_state": page_context,
                            "verified": action_verified
                        })
                        
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        print(f"Error in Notion step {i}: {e}")
                        error_screenshot = os.path.join(base_dir, f"error_step_{i}.png")
                        try:
                            await page.screenshot(path=error_screenshot)
                        except:
                            error_screenshot = None
                        
                        captured_steps.append({
                            **step, 
                            "screenshot_path": error_screenshot, 
                            "error": str(e),
                            "url": page.url if page else "unknown",
                            "verified": False
                        })
                        break

            except Exception as e:
                print(f"Notion browser setup error: {e}")
                captured_steps.append({
                    "action": "error",
                    "selector_hint": "browser_setup",
                    "description": f"Notion browser failed: {e}",
                    "screenshot_path": None,
                    "error": str(e)
                })
            finally:
                try:
                    if page:
                        await page.close()
                    if context:
                        await context.close()
                    if browser:
                        await browser.close()
                    print("Notion browser closed")
                except Exception as e:
                    print(f"Error closing Notion browser: {e}")

        return captured_steps

    async def _execute_single_step(self, page, step: Dict[str, Any], step_num: int, app: str) -> bool:
        """Execute a single step and return True if successful, False otherwise"""
        action = step.get("action")
        selector_hint = step.get("selector_hint", "")
        value = step.get("value")
        
        try:
            if action == "navigate" and step.get("url"):
                try:
                    print(f"Navigating to {step['url']}...")
                    await page.goto(step["url"], wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(2)
                    return True
                except PlaywrightTimeoutError:
                    print(f"Navigation timeout to {step['url']}")
                    return False
                    
            elif action == "wait":
                wait_time = int(value or 2)
                print(f"Waiting for {wait_time} seconds...")
                await asyncio.sleep(wait_time)
                return True
                
            elif action == "click":
                return await self._smart_click(page, selector_hint, "Notion")
                
            elif action == "fill":
                return await self._smart_fill(page, selector_hint, value, "Notion")
                
            elif action == "press":
                return await self._smart_press(page, selector_hint, value)
                
            await asyncio.sleep(1)
            return True
            
        except Exception as e:
            print(f"Step execution error: {e}")
            return False

    async def _smart_click(self, page, selector_hint: str, app: str) -> bool:
        """Click an element and return True if successful"""
        if not selector_hint or selector_hint.strip() == "":
            print("No selector hint for click")
            return False
        if selector_hint.lower() in ["database", "page", "new database"]:
            try:
                selector = f".notion-overlay-container [role='button']:has-text('{selector_hint}')"
                await page.click(selector, timeout=5000)
                print(f"Clicked dropdown option: '{selector_hint}'")
                return True
            except Exception as e:
                print(f"Dropdown click failed: {e}")
        
        element = await self._find_notion_element(page, selector_hint)
        if element:
            try:
                await element.click(timeout=10000)
                print(f"Clicked using contextual search: '{selector_hint}'")
                if "more options" in selector_hint.lower() or "v" in selector_hint.lower():
                    return True
                    
            except Exception as e:
                print(f"Contextual click failed: {e}")
            
        strategies = self._get_notion_click_strategies(selector_hint)
        
        last_error = None
        for strategy in strategies:
            try:
                print(f"Trying click: {strategy['type']} -> '{strategy['value']}'")
                
                if strategy["type"] == "text":
                    await page.click(f"text={strategy['value']}", timeout=10000)
                    print(f"Clicked: '{strategy['value']}'")
                    if "more options" in selector_hint.lower() or "v" in selector_hint.lower():
                        await asyncio.sleep(1)
                        
                    return True
                elif strategy["type"] == "css":
                    await page.click(strategy["value"], timeout=10000)
                    print(f"Clicked CSS: {strategy['value']}")

                    if "more options" in selector_hint.lower() or "v" in selector_hint.lower():
                        await asyncio.sleep(1)
                        
                    return True
                elif strategy["type"] == "xpath":
                    await page.click(f"xpath={strategy['value']}", timeout=10000)
                    print(f"Clicked XPath: {strategy['value']}")

                    if "more options" in selector_hint.lower() or "v" in selector_hint.lower():
                        await asyncio.sleep(1)
                        
                    return True
            except Exception as e:
                last_error = e
                print(f"Click failed: {e}")
                continue
                
        print(f"Notion element not found: {selector_hint}. Error: {last_error}")
        return False

    async def _smart_fill(self, page, selector_hint: str, value: str, app: str) -> bool:
        """Fill a field and return True if successful"""
        if not selector_hint or selector_hint.strip() == "":
            return False
            
        strategies = self._get_notion_fill_strategies(selector_hint)
        
        last_error = None
        for strategy in strategies:
            try:
                print(f"Trying fill: {strategy['type']} -> '{strategy['value']}'")
                
                if strategy["type"] == "css":
                    await page.fill(strategy["value"], value, timeout=10000)
                    print(f"Filled CSS: {strategy['value']}")
                    return True
                elif strategy["type"] == "placeholder":
                    selector = f"input[placeholder*='{strategy['value']}'], textarea[placeholder*='{strategy['value']}']"
                    await page.fill(selector, value, timeout=10000)
                    print(f"Filled placeholder: {strategy['value']}")
                    return True
                elif strategy["type"] == "contenteditable":
                    title_selectors = [
                        ".notion-page-block .notranslate[contenteditable='true']",
                        "[data-placeholder*='Untitled']",
                        "[data-placeholder*='Title']",
                        ".page-title [contenteditable='true']",
                        ".notion-page-content [contenteditable='true']:first-child"
                    ]
                    
                    for title_selector in title_selectors:
                        try:
                            element = await page.query_selector(title_selector)
                            if element:
                                await element.click()
                                await element.evaluate("(el) => el.innerText = ''")
                                await element.type(value, delay=50)
                                print(f"Filled title field: {value}")
                                return True
                        except Exception as e:
                            continue
                    element = await page.query_selector("[contenteditable='true']")
                    if element:
                        placeholder = await element.get_attribute("data-placeholder") or ""
                        if "untitled" in placeholder.lower() or "title" in placeholder.lower():
                            await element.click()
                            await element.evaluate("(el) => el.innerText = ''")
                            await element.type(value, delay=50)
                            print(f"Filled contenteditable title: {value}")
                            return True
            except Exception as e:
                last_error = e
                print(f"Fill failed: {e}")
                continue
                
        print(f"Notion input not found: {selector_hint}. Error: {last_error}")
        return False

    def _get_notion_click_strategies(self, selector_hint: str) -> List[Dict]:
        strategies = []
        hint_lower = selector_hint.lower()
        
        if not selector_hint.strip():
            return strategies

        if "search" in hint_lower:
            strategies.extend([
                {"type": "css", "value": "input[placeholder*='Search']"},
                {"type": "css", "value": "input[placeholder*='Quick find']"},
                {"type": "css", "value": "[data-testid*='search']"},
                {"type": "text", "value": "Search"},
                {"type": "text", "value": "Quick Find"},
            ])

        if "more options" in hint_lower or "v" in selector_hint or "v shaped" in hint_lower:
            strategies.extend([
                {"type": "css", "value": "[aria-label*='More options']"},
                {"type": "css", "value": "[aria-label*='Create']"},
                {"type": "css", "value": "[data-testid*='create']"},
                {"type": "css", "value": "[aria-label*='New']"},
                {"type": "css", "value": ".notion-sidebar [role='button']:last-child"},
            ])

        if "database" in hint_lower:
            strategies.extend([
                {"type": "text", "value": "Database"},
                {"type": "css", "value": "[role='menuitem']:has-text('Database')"},
                {"type": "css", "value": ".notion-overlay-container [role='button']:has-text('Database')"},
                {"type": "xpath", "value": f"//*[contains(text(), 'Database')]"},
            ])
        
        if "page" in hint_lower:
            strategies.extend([
                {"type": "text", "value": "Page"},
                {"type": "css", "value": "[role='menuitem']:has-text('Page')"},
                {"type": "css", "value": ".notion-overlay-container [role='button']:has-text('Page')"},
            ])

        if "new database" in hint_lower:
            strategies.extend([
                {"type": "text", "value": "New database"},
                {"type": "css", "value": "[role='menuitem']:has-text('New database')"},
            ])
        
        if "settings" in hint_lower:
            strategies.extend([
                {"type": "css", "value": "[aria-label*='Settings']"},
                {"type": "css", "value": "[data-testid*='settings']"},
                {"type": "text", "value": "Settings & members"},
                {"type": "text", "value": "Settings"},
            ])
        
        if "appearance" in hint_lower or "theme" in hint_lower:
            strategies.extend([
                {"type": "text", "value": "Appearance"},
                {"type": "text", "value": "Theme"},
                {"type": "text", "value": "Dark mode"},
                {"type": "text", "value": "Light mode"},
            ])
        
        if "new" in hint_lower:
            strategies.extend([
                {"type": "css", "value": "[aria-label*='New']"},
                {"type": "css", "value": "[data-testid*='create']"},
                {"type": "text", "value": "New page"},
                {"type": "text", "value": "New"},
            ])
            
        strategies.append({"type": "text", "value": selector_hint})
        strategies.extend([
            {"type": "css", "value": f"button:has-text('{selector_hint}')"},
            {"type": "css", "value": f"[aria-label*='{selector_hint}']"},
            {"type": "xpath", "value": f"//*[contains(text(), '{selector_hint}')]"},
        ])
        
        return strategies

    def _get_notion_fill_strategies(self, selector_hint: str) -> List[Dict]:
        strategies = []
        hint_lower = selector_hint.lower()
        
        if not selector_hint.strip():
            return strategies
            
        if "title" in hint_lower or "untitled" in hint_lower:
            strategies.extend([
                {"type": "css", "value": "[data-placeholder*='Untitled']"},
                {"type": "css", "value": "[data-placeholder*='Title']"},
                {"type": "css", "value": ".notion-page-block .notranslate[contenteditable='true']"},
                {"type": "css", "value": ".page-title [contenteditable='true']"},
                {"type": "css", "value": ".notion-page-content [contenteditable='true']:first-child"},
                {"type": "css", "value": ".notion-frame [contenteditable='true']:first-child"},  # Database title
            ])
        
        strategies.extend([
            {"type": "placeholder", "value": selector_hint},
            {"type": "css", "value": f"input[placeholder*='{selector_hint}']"},
            {"type": "css", "value": "input[type='text']:visible"},
        ])
        
        return strategies

    async def _smart_press(self, page, selector_hint: str, value: str) -> bool:
        try:
            key = value.upper() if value else "ENTER"
            print(f"Pressing key: {key}")
            await page.keyboard.press(key)
            return True
        except Exception as e:
            print(f"Key press failed: {e}")
            return False

    async def _find_notion_element(self, page, hint: str):
        elements = await page.query_selector_all("button, [role='button'], a, [onclick], input, textarea")
        
        for element in elements:
            try:
                if not await element.is_visible():
                    continue

                text = await element.inner_text()
                aria_label = await element.get_attribute('aria-label') or ""
                placeholder = await element.get_attribute('placeholder') or ""
                classes = await element.get_attribute('class') or ""
                data_testid = await element.get_attribute('data-testid') or ""

                combined_context = (text + " " + aria_label + " " + placeholder + " " + classes + " " + data_testid).lower()
                hint_lower = hint.lower()
                
                if any(word in combined_context for word in hint_lower.split()):
                    return element

                if (hint_lower in text.lower() or 
                    hint_lower in aria_label.lower() or 
                    hint_lower in placeholder.lower()):
                    return element
                    
            except:
                continue
        
        return None

    async def _verify_action(self, page, step: Dict, previous_screenshot: bytes = None) -> bool:
        try:
            await asyncio.sleep(1)

            if step.get("action") == "navigate" and step.get("url"):
                return step["url"] in page.url

            current_url = page.url
            if current_url and current_url != "about:blank":
                return True
                
            return False
        except:
            return False

    async def _detect_notion_page_state(self, page) -> str:
        page_content = await page.content()
        page_text = page_content.lower()

        otp_indicators = [
            "enter authentication code", "two-factor", "2fa", "verification code",
            "enter the code", "check your email", "enter code"
        ]
        
        if any(phrase in page_text for phrase in otp_indicators):
            return "authenticating"

        if await self._is_notion_login_page(page):
            return "login_required"

        if await self._is_notion_workspace(page):
            return "authenticated"

        if len(page_content) > 5000:
            div_count = page_content.count('<div')
            if div_count > 20:
                return "authenticated"
        
        return "unknown"

    async def _is_notion_login_page(self, page) -> bool:
        if await page.query_selector("input[type='password'], input[type='email']"):
            return True

        page_text = (await page.content()).lower()
        login_phrases = [
            "sign in to notion", "log in to notion", "continue with email",
            "continue with google", "enter your email", "welcome to notion",
            "already authenticated", "continue as", "choose an account"
        ]
        
        if any(phrase in page_text for phrase in login_phrases):
            return True

        login_buttons = await page.query_selector_all("button, [role='button'], a")
        for btn in login_buttons:
            try:
                text = (await btn.inner_text()).lower()
                if any(phrase in text for phrase in ["sign in", "log in", "continue with"]):
                    return True
            except:
                continue
                    
        return False

    async def _is_notion_workspace(self, page) -> bool:
        if await self._is_notion_login_page(page):
            return False

        workspace_indicators = [
            ".notion-sidebar",
            "[data-block-id]",
            ".notion-page-content",
            "[data-testid*='create']",
            "[aria-label*='New']",
        ]
        
        for selector in workspace_indicators:
            if await page.query_selector(selector):
                return True
            
        page_text = (await page.content()).lower()
        workspace_phrases = [
            "new page", "search", "quick find", "workspace", "settings & members"
        ]
        
        found_phrases = sum(1 for phrase in workspace_phrases if phrase in page_text)
        if found_phrases >= 2:
            return True
                
        return False

capture_service = CaptureService()