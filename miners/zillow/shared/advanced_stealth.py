"""
Advanced Anti-Detection System for Zillow Scraping
Implements sophisticated techniques to avoid bot detection.
"""

import asyncio
import logging
import random
import time
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class AdvancedStealthManager:
    """Manages advanced anti-detection techniques"""
    
    def __init__(self):
        self.session_start_time = time.time()
        self.page_visit_count = 0
        self.last_action_time = time.time()
        self.human_behavior_enabled = True
        
        # Enhanced user agent pool with real browser fingerprints
        self.user_agents = [
            # Chrome on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.7339.133 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.7308.125 Safari/537.36',
            'Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.7339.133 Safari/537.36',
            
            # Chrome on Mac
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.7339.133 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.7339.133 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.7308.125 Safari/537.36',
            
            # Chrome on Linux
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.7339.133 Safari/537.36',
            'Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.7339.133 Safari/537.36',
        ]
        
        # Screen resolutions that match real devices
        self.screen_resolutions = [
            (1920, 1080),  # Full HD
            (1366, 768),   # HD
            (1440, 900),   # MacBook Pro 15"
            (1536, 864),   # HD+
            (2560, 1440),  # 2K
            (1680, 1050),  # 16:10
            (1600, 900),   # HD+
        ]
        
        # Realistic viewport sizes (slightly smaller than screen)
        self.viewport_offsets = [(100, 150), (80, 120), (60, 100), (120, 180)]
    
    def create_stealth_driver(self) -> Optional[uc.Chrome]:
        """Create a highly stealthy Chrome driver"""
        try:
            # Create fresh ChromeOptions for each driver (fixes reuse error)
            options = uc.ChromeOptions()
            
            # Basic stealth arguments
            stealth_args = [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-default-apps',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-features=TranslateUI',
                '--disable-ipc-flooding-protection',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-background-networking',
                '--disable-sync',
                '--disable-translate',
                '--hide-scrollbars',
                '--metrics-recording-only',
                '--mute-audio',
                '--no-reporting',
                '--no-zygote',
                '--use-mock-keychain',
                '--disable-web-security',
                '--allow-running-insecure-content',
            ]
            
            for arg in stealth_args:
                options.add_argument(arg)
            
            # Randomize screen size and viewport
            screen_width, screen_height = random.choice(self.screen_resolutions)
            offset_x, offset_y = random.choice(self.viewport_offsets)
            
            options.add_argument(f'--window-size={screen_width-offset_x},{screen_height-offset_y}')
            options.add_argument(f'--window-position={random.randint(0, offset_x)},{random.randint(0, offset_y)}')
            
            # Random user agent
            user_agent = random.choice(self.user_agents)
            options.add_argument(f'--user-agent={user_agent}')
            
            # Create driver with fallback approach for Chrome compatibility
            driver = None
            
            # Try with experimental options first
            try:
                options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
                options.add_experimental_option('useAutomationExtension', False)
                
                # Disable image loading for faster page loads
                prefs = {
                    "profile.managed_default_content_settings.images": 2,  # Block images
                    "profile.default_content_setting_values.notifications": 2,  # Block notifications
                    "profile.default_content_settings.popups": 0,  # Block popups
                    "profile.managed_default_content_settings.media_stream": 2,  # Block media
                }
                options.add_experimental_option("prefs", prefs)
                
                # Try with version detection
                driver = uc.Chrome(options=options, version_main=None)
                
            except Exception as e:
                logging.warning(f"Advanced options failed, trying basic approach: {e}")
                
                # Create new basic options without experimental features
                options = uc.ChromeOptions()
                for arg in stealth_args:
                    options.add_argument(arg)
                
                options.add_argument(f'--window-size={screen_width-offset_x},{screen_height-offset_y}')
                options.add_argument(f'--user-agent={user_agent}')
                
                try:
                    driver = uc.Chrome(options=options)
                except Exception as e2:
                    logging.error(f"Basic driver creation also failed: {e2}")
                    return None
            
            if driver:
                # Set realistic timeouts
                driver.set_page_load_timeout(45)
                driver.implicitly_wait(10)
                
                # Execute stealth scripts
                self._execute_stealth_scripts(driver)
                
                logging.info("Successfully created stealth Chrome driver")
                return driver
            else:
                logging.error("Failed to create Chrome driver")
                return None
            
        except Exception as e:
            logging.error(f"Failed to create stealth Chrome driver: {e}")
            return None
    
    def _execute_stealth_scripts(self, driver):
        """Execute JavaScript to make the browser more human-like"""
        try:
            # Remove webdriver property
            driver.execute_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
            """)
            
            # Override navigator.plugins
            driver.execute_script("""
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
            """)
            
            # Override navigator.languages
            driver.execute_script("""
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
            """)
            
            # Override screen properties
            driver.execute_script("""
                Object.defineProperty(screen, 'colorDepth', {
                    get: () => 24,
                });
                Object.defineProperty(screen, 'pixelDepth', {
                    get: () => 24,
                });
            """)
            
            # Add realistic mouse movements
            driver.execute_script("""
                let mouseX = 0;
                let mouseY = 0;
                document.addEventListener('mousemove', (e) => {
                    mouseX = e.clientX;
                    mouseY = e.clientY;
                });
                
                window.getMousePosition = () => ({ x: mouseX, y: mouseY });
            """)
            
        except Exception as e:
            logging.warning(f"Could not execute stealth scripts: {e}")
    
    async def simulate_human_behavior(self, driver, page_complexity: str = "medium"):
        """Simulate realistic human browsing behavior"""
        if not self.human_behavior_enabled:
            return
        
        try:
            # Random scroll behavior
            await self._simulate_scrolling(driver, page_complexity)
            
            # Random mouse movements
            await self._simulate_mouse_movement(driver)
            
            # Random reading pauses
            await self._simulate_reading_pause(page_complexity)
            
            self.page_visit_count += 1
            self.last_action_time = time.time()
            
        except Exception as e:
            logging.warning(f"Error simulating human behavior: {e}")
    
    async def _simulate_scrolling(self, driver, complexity: str):
        """Simulate natural scrolling patterns"""
        try:
            # Get page height
            page_height = driver.execute_script("return document.body.scrollHeight")
            viewport_height = driver.execute_script("return window.innerHeight")
            
            if page_height <= viewport_height:
                return  # No need to scroll
            
            # Determine scroll pattern based on complexity
            if complexity == "simple":
                scroll_steps = random.randint(2, 4)
            elif complexity == "medium":
                scroll_steps = random.randint(3, 6)
            else:  # complex
                scroll_steps = random.randint(4, 8)
            
            for i in range(scroll_steps):
                # Random scroll amount
                scroll_amount = random.randint(200, 500)
                
                # Smooth scroll with random speed
                driver.execute_script(f"""
                    window.scrollBy({{
                        top: {scroll_amount},
                        left: 0,
                        behavior: 'smooth'
                    }});
                """)
                
                # Random pause between scrolls
                await asyncio.sleep(random.uniform(0.8, 2.5))
            
            # Sometimes scroll back up
            if random.random() < 0.3:
                driver.execute_script("window.scrollTo({top: 0, behavior: 'smooth'});")
                await asyncio.sleep(random.uniform(1.0, 2.0))
                
        except Exception as e:
            logging.warning(f"Error simulating scrolling: {e}")
    
    async def _simulate_mouse_movement(self, driver):
        """Simulate realistic mouse movements"""
        try:
            actions = ActionChains(driver)
            
            # Random mouse movements
            for _ in range(random.randint(2, 5)):
                x_offset = random.randint(-100, 100)
                y_offset = random.randint(-50, 50)
                
                actions.move_by_offset(x_offset, y_offset)
                actions.perform()
                
                await asyncio.sleep(random.uniform(0.1, 0.5))
                
        except Exception as e:
            logging.warning(f"Error simulating mouse movement: {e}")
    
    async def _simulate_reading_pause(self, complexity: str):
        """Simulate realistic reading/processing time"""
        if complexity == "simple":
            base_time = random.uniform(2.0, 5.0)
        elif complexity == "medium":
            base_time = random.uniform(4.0, 8.0)
        else:  # complex
            base_time = random.uniform(6.0, 12.0)
        
        # Add random variation
        pause_time = base_time * random.uniform(0.8, 1.4)
        await asyncio.sleep(pause_time)
    
    def should_restart_session(self) -> bool:
        """Determine if we should restart the browser session - much more conservative"""
        session_age = time.time() - self.session_start_time
        
        # Restart after much longer time between 45-90 minutes  
        max_session_time = random.uniform(2700, 5400)  # 45-90 minutes
        
        # Or after many more pages (50-100)
        max_pages = random.randint(50, 100)
        
        return (session_age > max_session_time or 
                self.page_visit_count > max_pages)
    
    def reset_session(self):
        """Reset session tracking"""
        self.session_start_time = time.time()
        self.page_visit_count = 0
        self.last_action_time = time.time()


class AdvancedRateLimiter:
    """Advanced rate limiter with human-like timing patterns"""
    
    def __init__(self, base_rpm: int = 8):  # Much more conservative
        self.base_rpm = base_rpm
        self.requests = []
        self.consecutive_errors = 0
        self.session_start = time.time()
        
        # Human-like timing patterns
        self.timing_patterns = {
            "focused": (3.0, 8.0),      # Focused browsing: 3-8 seconds between requests
            "casual": (5.0, 15.0),      # Casual browsing: 5-15 seconds
            "distracted": (10.0, 30.0), # Distracted: 10-30 seconds
        }
        
        self.current_pattern = "casual"
        self.pattern_change_time = time.time() + random.uniform(300, 900)  # Change every 5-15 minutes
    
    async def wait_if_needed(self):
        """Advanced rate limiting with human-like patterns"""
        now = time.time()
        
        # Change browsing pattern periodically
        if now > self.pattern_change_time:
            self.current_pattern = random.choice(list(self.timing_patterns.keys()))
            self.pattern_change_time = now + random.uniform(300, 900)
            logging.info(f"Switched to {self.current_pattern} browsing pattern")
        
        # Remove old requests
        self.requests = [req_time for req_time in self.requests if now - req_time < 60]
        
        # Base rate limiting
        if len(self.requests) >= self.base_rpm:
            sleep_time = 60 - (now - self.requests[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time + random.uniform(1, 5))
        
        # Human-like delays based on current pattern
        min_delay, max_delay = self.timing_patterns[self.current_pattern]
        
        # Add error-based delays
        if self.consecutive_errors > 0:
            error_multiplier = min(self.consecutive_errors * 1.5, 5.0)
            min_delay *= error_multiplier
            max_delay *= error_multiplier
        
        # Random delay within pattern
        delay = random.uniform(min_delay, max_delay)
        
        # Add occasional longer pauses (simulating user getting distracted)
        if random.random() < 0.1:  # 10% chance
            delay += random.uniform(30, 120)  # 30 seconds to 2 minutes
            logging.info(f"Taking extended break: {delay:.1f} seconds")
        
        logging.debug(f"Rate limiting delay ({self.current_pattern}): {delay:.1f} seconds")
        await asyncio.sleep(delay)
        
        self.requests.append(now)
    
    def record_error(self):
        """Record an error and increase delays"""
        self.consecutive_errors += 1
        logging.warning(f"Error recorded. Consecutive errors: {self.consecutive_errors}")
    
    def record_success(self):
        """Record success and potentially reduce error delays"""
        if self.consecutive_errors > 0:
            self.consecutive_errors = max(0, self.consecutive_errors - 1)
    
    def is_session_too_long(self) -> bool:
        """Check if current session has been running too long - much more conservative"""
        session_duration = time.time() - self.session_start
        max_session = random.uniform(3600, 7200)  # 60-120 minutes
        return session_duration > max_session


class BotDetectionChecker:
    """Advanced bot detection checking"""
    
    @staticmethod
    def check_for_bot_indicators(driver) -> Dict[str, Any]:
        """Check for various bot detection indicators"""
        indicators = {
            "captcha_detected": False,
            "access_denied": False,
            "rate_limited": False,
            "suspicious_redirect": False,
            "anti_bot_service": False,
            "page_load_issues": False
        }
        
        try:
            page_source = driver.page_source.lower()
            current_url = driver.current_url.lower()
            page_title = driver.title.lower()
            
            # Check for CAPTCHA
            captcha_indicators = [
                'captcha', 'recaptcha', 'hcaptcha', 'cloudflare',
                'verify you are human', 'prove you are not a robot',
                'security check', 'unusual traffic'
            ]
            indicators["captcha_detected"] = any(indicator in page_source for indicator in captcha_indicators)
            
            # Check for access denied
            access_denied_indicators = [
                'access denied', 'access to this page has been denied',
                'blocked', 'forbidden', '403 error', 'not authorized'
            ]
            indicators["access_denied"] = any(indicator in page_source for indicator in access_denied_indicators)
            
            # Check for rate limiting
            rate_limit_indicators = [
                'rate limit', 'too many requests', 'slow down',
                'request limit exceeded', 'try again later'
            ]
            indicators["rate_limited"] = any(indicator in page_source for indicator in rate_limit_indicators)
            
            # Check for suspicious redirects
            if 'challenge' in current_url or 'verify' in current_url:
                indicators["suspicious_redirect"] = True
            
            # Check for anti-bot services
            anti_bot_services = [
                'perimeterx', 'distil', 'imperva', 'cloudflare',
                'datadome', 'kasada', 'akamai bot manager'
            ]
            indicators["anti_bot_service"] = any(service in page_source for service in anti_bot_services)
            
            # Check for page load issues
            if len(page_source) < 1000:  # Very small page
                indicators["page_load_issues"] = True
            
            # Check title for bot indicators
            bot_title_indicators = ['just a moment', 'checking your browser', 'please wait']
            if any(indicator in page_title for indicator in bot_title_indicators):
                indicators["captcha_detected"] = True
            
        except Exception as e:
            logging.warning(f"Error checking bot indicators: {e}")
            indicators["page_load_issues"] = True
        
        return indicators
    
    @staticmethod
    def is_blocked(indicators: Dict[str, Any]) -> bool:
        """Determine if we're blocked based on indicators"""
        blocking_indicators = [
            "captcha_detected", "access_denied", "rate_limited", 
            "suspicious_redirect", "anti_bot_service"
        ]
        return any(indicators.get(indicator, False) for indicator in blocking_indicators)
    
    @staticmethod
    def get_severity_score(indicators: Dict[str, Any]) -> float:
        """Get severity score (0-1) of detection"""
        weights = {
            "captcha_detected": 0.9,
            "access_denied": 1.0,
            "rate_limited": 0.7,
            "suspicious_redirect": 0.8,
            "anti_bot_service": 0.6,
            "page_load_issues": 0.3
        }
        
        total_score = sum(weights.get(key, 0) for key, value in indicators.items() if value)
        return min(total_score, 1.0)
