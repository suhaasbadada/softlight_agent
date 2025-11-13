import asyncio
from typing import List, Dict, Any
from playwright.async_api import Page

class PageAnalyzer:
    async def analyze_page(self, page: Page) -> Dict[str, Any]:
        try:
            url = page.url
            title = await page.title()

            interactive_elements = await self._get_notion_elements(page)
            page_structure = await self._analyze_notion_structure(page)
            navigation_elements = await self._get_notion_navigation(page)
            
            return {
                "url": url,
                "title": title,
                "interactive_elements": interactive_elements,
                "page_structure": page_structure,
                "navigation_elements": navigation_elements,
                "suggested_actions": await self._suggest_notion_actions(interactive_elements),
                "has_login_form": await self._has_notion_login(page)
            }
        except Exception as e:
            print(f"Notion page analysis error: {e}")
            return self._get_fallback_analysis()

    async def _get_notion_elements(self, page: Page) -> List[Dict[str, Any]]:
        elements = []

        notion_selectors = [
            "button", "[role='button']", "[data-testid]", "[aria-label]",
            ".notion-sidebar [role='button']", "[class*='notion'] button"
        ]
        
        for selector in notion_selectors:
            try:
                found_elements = await page.query_selector_all(selector)
                for element in found_elements:
                    if await element.is_visible():
                        element_info = await self._extract_notion_element_info(element, selector)
                        if element_info:
                            elements.append(element_info)
            except Exception:
                continue

        seen = set()
        unique_elements = []
        for elem in elements:
            key = (elem.get("text", ""), elem.get("role", ""))
            if key not in seen and key != ("", ""):
                seen.add(key)
                unique_elements.append(elem)
        
        return unique_elements

    async def _extract_notion_element_info(self, element, selector_type: str) -> Dict[str, Any]:
        try:
            text = await element.inner_text()
            text = text.strip() if text else ""
            
            aria_label = await element.get_attribute("aria-label") or ""
            data_testid = await element.get_attribute("data-testid") or ""
            classes = await element.get_attribute("class") or ""

            role = await self._determine_notion_element_role(text, aria_label, data_testid)
            
            return {
                "text": text,
                "aria_label": aria_label,
                "data_testid": data_testid,
                "classes": classes,
                "role": role,
                "is_clickable": await self._is_element_clickable(element),
            }
        except Exception:
            return None

    async def _determine_notion_element_role(self, text: str, aria_label: str, data_testid: str) -> str:
        combined_text = (text + " " + aria_label + " " + data_testid).lower()

        if any(word in combined_text for word in ["settings", "setting", "members"]):
            return "settings"
        elif any(word in combined_text for word in ["theme", "mode", "appearance", "dark", "light"]):
            return "theme"
        elif any(word in combined_text for word in ["new", "create", "add"]):
            return "create_action"
        elif any(word in combined_text for word in ["database", "table"]):
            return "database"
        elif any(word in combined_text for word in ["page", "document"]):
            return "page"
        elif any(word in combined_text for word in ["search", "find"]):
            return "search"
        elif any(word in combined_text for word in ["login", "sign in"]):
            return "login"
        else:
            return "interactive_element"

    async def _is_element_clickable(self, element) -> bool:
        try:
            is_visible = await element.is_visible()
            is_disabled = await element.get_attribute("disabled") is not None
            return is_visible and not is_disabled
        except Exception:
            return False

    async def _analyze_notion_structure(self, page: Page) -> Dict[str, bool]:
        return {
            "has_sidebar": await self._has_element(page, ".notion-sidebar"),
            "has_header": await self._has_element(page, ".notion-header"),
            "has_page_content": await self._has_element(page, ".notion-page-content"),
            "has_create_button": await self._has_element(page, "[data-testid*='create']"),
        }

    async def _has_element(self, page: Page, selector: str) -> bool:
        try:
            element = await page.query_selector(selector)
            return element is not None and await element.is_visible()
        except Exception:
            return False

    async def _get_notion_navigation(self, page: Page) -> List[Dict[str, Any]]:
        navigation_elements = []

        nav_selectors = [
            "[class*='sidebar'] [role='button']",
            "[data-testid*='menu']",
            "[aria-label*='menu']"
        ]
        
        for selector in nav_selectors:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    if await element.is_visible():
                        text = await element.inner_text()
                        aria_label = await element.get_attribute("aria-label") or ""
                        if text.strip() or aria_label:
                            navigation_elements.append({
                                "text": text.strip(),
                                "aria_label": aria_label,
                            })
            except Exception:
                continue
        
        return navigation_elements

    async def _suggest_notion_actions(self, interactive_elements: List[Dict]) -> List[str]:
        actions = []

        create_elements = [e for e in interactive_elements if e.get("role") == "create_action"]
        for elem in create_elements:
            text = elem.get("text", "") or elem.get("aria_label", "")
            if text:
                actions.append(f"Create: {text}")

        settings_elements = [e for e in interactive_elements if e.get("role") in ["settings", "theme"]]
        for elem in settings_elements:
            text = elem.get("text", "") or elem.get("aria_label", "")
            if text:
                actions.append(f"Settings: {text}")
        
        return actions[:3]

    async def _has_notion_login(self, page: Page) -> bool:
        try:
            return bool(await page.query_selector("input[type='password']"))
        except:
            return False

    def _get_fallback_analysis(self) -> Dict[str, Any]:
        return {
            "url": "unknown",
            "title": "unknown", 
            "interactive_elements": [],
            "page_structure": {},
            "navigation_elements": [],
            "suggested_actions": [],
            "has_login_form": False
        }

page_analyzer = PageAnalyzer()