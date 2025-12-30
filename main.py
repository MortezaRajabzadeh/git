import time
import random
import string
import json
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import re
from pynput.mouse import Controller
import screeninfo
import threading
import os
from pynput import mouse as ms
from fp.fp import FreeProxy
import secrets
from fake_useragent import UserAgent
import pytz
from datetime import datetime

#Login for ending the script with middle mouse button click
def on_click(x, y, button, pressed):
    global stop_flag
    if pressed and button == ms.Button.middle:
        print("Middle mouse button clicked! Exiting...")
        os._exit(0)
def listen_for_middle_click():
    with ms.Listener(on_click=on_click) as listener:
        listener.join()

created_count = 0

mouse = Controller()
screen = screeninfo.get_monitors()[0]
width, height = screen.width, screen.height
threshold = 10

class ProxyManager:
    def __init__(self, config_path='proxy_config.json'):
        self.config_path = config_path
        self.config = self.load_config()
        self.proxy_pool = []
        self.geo_cache = {}
        self.build_proxy_pool()
    
    def load_config(self):
        """Load proxy configuration from JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            print(f"✓ Loaded proxy configuration from {self.config_path}")
            return config
        except FileNotFoundError:
            print(f"⚠️ Config file {self.config_path} not found, using defaults")
            return {
                'proxy_enabled': False,
                'providers': {'free_proxy': {'enabled': True}},
                'rotation': {'enabled': False},
                'validation': {'test_url': 'https://api.ipify.org?format=json', 'timeout_seconds': 10},
                'geolocation': {'match_timezone': False}
            }
        except Exception as e:
            print(f"✗ Error loading config: {e}")
            return {'proxy_enabled': False}
    
    def build_proxy_pool(self):
        """Build proxy pool from enabled providers"""
        self.proxy_pool = []
        providers = self.config.get('providers', {})
        
        # BrightData
        if providers.get('brightdata', {}).get('enabled'):
            bd = providers['brightdata']
            proxy_url = f"http://{bd['username']}:{bd['password']}@{bd['host']}:{bd['port']}"
            self.proxy_pool.append({
                'proxy': proxy_url,
                'provider': 'brightdata',
                'usage_count': 0,
                'last_used': None,
                'health_score': 100,
                'country': None
            })
            print(f"✓ Added BrightData proxy to pool")
        
        # SmartProxy
        if providers.get('smartproxy', {}).get('enabled'):
            sp = providers['smartproxy']
            proxy_url = f"http://{sp['username']}:{sp['password']}@{sp['host']}:{sp['port']}"
            self.proxy_pool.append({
                'proxy': proxy_url,
                'provider': 'smartproxy',
                'usage_count': 0,
                'last_used': None,
                'health_score': 100,
                'country': None
            })
            print(f"✓ Added SmartProxy proxy to pool")
        
        # Oxylabs
        if providers.get('oxylabs', {}).get('enabled'):
            ox = providers['oxylabs']
            proxy_url = f"http://{ox['username']}:{ox['password']}@{ox['host']}:{ox['port']}"
            self.proxy_pool.append({
                'proxy': proxy_url,
                'provider': 'oxylabs',
                'usage_count': 0,
                'last_used': None,
                'health_score': 100,
                'country': None
            })
            print(f"✓ Added Oxylabs proxy to pool")
        
        # Custom list
        if providers.get('custom_list', {}).get('enabled'):
            custom_proxies = providers['custom_list'].get('proxies', [])
            for proxy_url in custom_proxies:
                self.proxy_pool.append({
                    'proxy': proxy_url,
                    'provider': 'custom',
                    'usage_count': 0,
                    'last_used': None,
                    'health_score': 100,
                    'country': None
                })
            print(f"✓ Added {len(custom_proxies)} custom proxies to pool")
        
        print(f"📊 Total proxies in pool: {len(self.proxy_pool)}")
    
    def get_next_proxy(self):
        """Get next available proxy with rotation logic"""
        if not self.proxy_pool:
            # Fallback to free proxy
            if self.config.get('providers', {}).get('free_proxy', {}).get('enabled'):
                print("⚠️ No proxies in pool, trying free proxy...")
                try:
                    proxy_url = FreeProxy(rand=True, timeout=2).get()
                    return {
                        'proxy': proxy_url,
                        'provider': 'free',
                        'usage_count': 0,
                        'last_used': None,
                        'health_score': 50,
                        'country': None
                    }
                except:
                    return None
            return None
        
        rotation_config = self.config.get('rotation', {})
        if not rotation_config.get('enabled'):
            # No rotation, return first proxy
            return self.proxy_pool[0]
        
        # Filter available proxies
        available_proxies = []
        now = datetime.now()
        cooldown_minutes = rotation_config.get('cooldown_minutes', 30)
        max_uses = rotation_config.get('max_uses_per_proxy', 3)
        
        for proxy_data in self.proxy_pool:
            # Check health score
            if proxy_data['health_score'] < 50:
                continue
            
            # Check max uses
            if proxy_data['usage_count'] >= max_uses:
                # Check if cooldown period passed
                if proxy_data['last_used']:
                    time_since_use = (now - proxy_data['last_used']).total_seconds() / 60
                    if time_since_use < cooldown_minutes:
                        continue
                    else:
                        # Reset usage count after cooldown
                        proxy_data['usage_count'] = 0
            
            available_proxies.append(proxy_data)
        
        if not available_proxies:
            print("⚠️ No available proxies (all in cooldown or unhealthy)")
            # Try free proxy as fallback
            if self.config.get('providers', {}).get('free_proxy', {}).get('enabled'):
                try:
                    proxy_url = FreeProxy(rand=True, timeout=2).get()
                    return {
                        'proxy': proxy_url,
                        'provider': 'free',
                        'usage_count': 0,
                        'last_used': None,
                        'health_score': 50,
                        'country': None
                    }
                except:
                    pass
            return None
        
        # Select proxy with lowest usage count
        selected_proxy = min(available_proxies, key=lambda x: x['usage_count'])
        selected_proxy['usage_count'] += 1
        selected_proxy['last_used'] = now
        
        return selected_proxy
    
    def validate_proxy(self, proxy_url):
        """Validate proxy by testing connection"""
        test_url = self.config.get('validation', {}).get('test_url', 'https://api.ipify.org?format=json')
        timeout = self.config.get('validation', {}).get('timeout_seconds', 10)
        
        try:
            proxies = {'http': proxy_url, 'https': proxy_url}
            start_time = time.time()
            response = requests.get(test_url, proxies=proxies, timeout=timeout)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                ip_address = response.json().get('ip', 'unknown')
                return (True, response_time, ip_address)
            return (False, 0, None)
        except Exception as e:
            print(f"Proxy validation error: {e}")
            return (False, 0, None)
    
    def get_proxy_geolocation(self, ip_address):
        """Get geolocation data for IP address"""
        # Check cache first
        if ip_address in self.geo_cache:
            return self.geo_cache[ip_address]
        
        try:
            # Use free IP geolocation API
            response = requests.get(f"http://ip-api.com/json/{ip_address}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    geo_data = {
                        'country': data.get('countryCode', 'US'),
                        'timezone': data.get('timezone', 'America/New_York'),
                        'city': data.get('city', 'Unknown'),
                        'region': data.get('regionName', 'Unknown')
                    }
                    # Cache result
                    self.geo_cache[ip_address] = geo_data
                    return geo_data
        except Exception as e:
            print(f"Geolocation lookup error: {e}")
        
        # Default fallback
        return {
            'country': 'US',
            'timezone': 'America/New_York',
            'city': 'Unknown',
            'region': 'Unknown'
        }
    
    def match_fingerprint_to_proxy(self, proxy_ip):
        """Generate fingerprint matching proxy geolocation"""
        geo_data = self.get_proxy_geolocation(proxy_ip)
        
        # Determine language based on country
        country = geo_data['country']
        if country in ['US', 'CA', 'AU']:
            language = 'en-US'
        elif country == 'GB':
            language = 'en-GB'
        elif country == 'DE':
            language = 'de-DE'
        elif country == 'FR':
            language = 'fr-FR'
        else:
            language = 'en-US'
        
        # Use timezone from geolocation
        timezone = geo_data['timezone']
        
        return {
            'timezone': timezone,
            'language': language,
            'country': country
        }
    
    def mark_proxy_failed(self, proxy_url):
        """Mark proxy as failed and decrease health score"""
        for proxy_data in self.proxy_pool:
            if proxy_data['proxy'] == proxy_url:
                proxy_data['health_score'] = max(0, proxy_data['health_score'] - 20)
                print(f"⚠️ Proxy health decreased: {proxy_data['health_score']}")
                if proxy_data['health_score'] < 20:
                    print(f"✗ Proxy disabled due to low health")
                break
    
    def mark_proxy_success(self, proxy_url):
        """Mark proxy as successful and increase health score"""
        for proxy_data in self.proxy_pool:
            if proxy_data['proxy'] == proxy_url:
                proxy_data['health_score'] = min(100, proxy_data['health_score'] + 5)
                break
    
    def log_proxy_stats(self):
        """Log proxy pool statistics"""
        if not self.proxy_pool:
            print("📊 Proxy Stats: No proxies in pool")
            return
        
        available = sum(1 for p in self.proxy_pool if p['health_score'] >= 50)
        avg_health = sum(p['health_score'] for p in self.proxy_pool) / len(self.proxy_pool)
        in_cooldown = sum(1 for p in self.proxy_pool if p['usage_count'] >= self.config.get('rotation', {}).get('max_uses_per_proxy', 3))
        
        print(f"\n📊 Proxy Pool Statistics:")
        print(f"   Total proxies: {len(self.proxy_pool)}")
        print(f"   Available: {available}")
        print(f"   In cooldown: {in_cooldown}")
        print(f"   Average health: {avg_health:.1f}")

class ProfileManager:
    def __init__(self, config_path='profile_config.json'):
        self.config_path = config_path
        self.config = self.load_config()
        self.metadata_file = 'profile_metadata.json'
        self.profile_metadata = self.load_profile_metadata()
        self.create_profile_directory()
    
    def load_config(self):
        """Load profile configuration from JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            print(f"✓ Loaded profile configuration from {self.config_path}")
            return config
        except FileNotFoundError:
            print(f"⚠️ Profile config file {self.config_path} not found, using defaults")
            return {
                'profile_enabled': True,
                'profile_directory': 'browser_profiles',
                'max_profiles': 10,
                'rotation': {'enabled': True, 'max_uses_per_profile': 5, 'cooldown_hours': 24},
                'cleanup': {'auto_cleanup': True, 'max_age_days': 30}
            }
        except Exception as e:
            print(f"✗ Error loading profile config: {e}")
            return {'profile_enabled': False}
    
    def load_profile_metadata(self):
        """Load profile usage statistics from JSON file"""
        try:
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {'profiles': {}}
        except Exception as e:
            print(f"⚠️ Error loading profile metadata: {e}")
            return {'profiles': {}}
    
    def save_profile_metadata(self):
        """Persist profile metadata to JSON file"""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.profile_metadata, f, indent=2)
        except Exception as e:
            print(f"✗ Error saving profile metadata: {e}")
    
    def create_profile_directory(self):
        """Create base directory for storing browser profiles"""
        profile_dir = self.config.get('profile_directory', 'browser_profiles')
        try:
            if not os.path.exists(profile_dir):
                os.makedirs(profile_dir)
                print(f"✓ Created profile directory: {profile_dir}")
        except Exception as e:
            print(f"✗ Error creating profile directory: {e}")
    
    def get_available_profile(self):
        """Select profile based on rotation strategy"""
        if not self.config.get('profile_enabled'):
            return None
        
        rotation_config = self.config.get('rotation', {})
        if not rotation_config.get('enabled'):
            # Return first profile or create new
            if self.profile_metadata['profiles']:
                return list(self.profile_metadata['profiles'].keys())[0]
            return self.create_new_profile()
        
        now = datetime.now()
        max_uses = rotation_config.get('max_uses_per_profile', 5)
        cooldown_hours = rotation_config.get('cooldown_hours', 24)
        
        available_profiles = []
        for profile_id, metadata in self.profile_metadata['profiles'].items():
            # Check if profile is active
            if metadata.get('status') != 'active':
                continue
            
            # Check usage count
            usage_count = metadata.get('usage_count', 0)
            if usage_count >= max_uses:
                # Check cooldown
                last_used = datetime.fromisoformat(metadata.get('last_used', now.isoformat()))
                hours_since_use = (now - last_used).total_seconds() / 3600
                if hours_since_use < cooldown_hours:
                    continue
                # Reset usage after cooldown
                metadata['usage_count'] = 0
            
            available_profiles.append((profile_id, metadata))
        
        if available_profiles:
            # Select least recently used profile
            selected = min(available_profiles, key=lambda x: x[1].get('usage_count', 0))
            return selected[0]
        
        # No available profiles, create new
        return self.create_new_profile()
    
    def create_new_profile(self):
        """Generate new profile directory with unique identifier"""
        # Check if we've reached max profiles
        max_profiles = self.config.get('max_profiles', 10)
        if len(self.profile_metadata['profiles']) >= max_profiles:
            # Remove oldest unused profile
            self.cleanup_old_profiles(force_one=True)
        
        # Generate unique profile ID
        profile_id = f"profile_{len(self.profile_metadata['profiles']) + 1:03d}"
        while profile_id in self.profile_metadata['profiles']:
            profile_id = f"profile_{random.randint(1000, 9999)}"
        
        # Create profile directory
        profile_path = self.get_profile_path(profile_id)
        try:
            os.makedirs(profile_path, exist_ok=True)
            print(f"✓ Created new profile: {profile_id}")
        except Exception as e:
            print(f"✗ Error creating profile directory: {e}")
            return None
        
        # Add to metadata
        self.profile_metadata['profiles'][profile_id] = {
            'created_at': datetime.now().isoformat(),
            'last_used': None,
            'usage_count': 0,
            'successful_accounts': 0,
            'status': 'active'
        }
        self.save_profile_metadata()
        
        return profile_id
    
    def update_profile_usage(self, profile_id, success=True):
        """Increment usage count and update last used timestamp"""
        if profile_id not in self.profile_metadata['profiles']:
            return
        
        metadata = self.profile_metadata['profiles'][profile_id]
        metadata['usage_count'] = metadata.get('usage_count', 0) + 1
        metadata['last_used'] = datetime.now().isoformat()
        
        if success:
            metadata['successful_accounts'] = metadata.get('successful_accounts', 0) + 1
        
        self.save_profile_metadata()
        print(f"✓ Updated profile {profile_id}: {metadata['usage_count']} uses, {metadata['successful_accounts']} successful")
    
    def cleanup_old_profiles(self, force_one=False):
        """Remove profiles exceeding max age or usage limits"""
        if not self.config.get('cleanup', {}).get('auto_cleanup'):
            return
        
        max_age_days = self.config.get('cleanup', {}).get('max_age_days', 30)
        keep_successful = self.config.get('cleanup', {}).get('keep_successful_profiles', True)
        now = datetime.now()
        
        profiles_to_delete = []
        
        for profile_id, metadata in self.profile_metadata['profiles'].items():
            # Check age
            created_at = datetime.fromisoformat(metadata.get('created_at', now.isoformat()))
            age_days = (now - created_at).days
            
            if age_days > max_age_days:
                # Keep successful profiles if configured
                if keep_successful and metadata.get('successful_accounts', 0) > 0:
                    continue
                profiles_to_delete.append(profile_id)
        
        # If force_one, delete oldest profile
        if force_one and not profiles_to_delete:
            oldest = min(self.profile_metadata['profiles'].items(), 
                        key=lambda x: x[1].get('created_at', ''))
            profiles_to_delete.append(oldest[0])
        
        # Delete profiles
        for profile_id in profiles_to_delete:
            profile_path = self.get_profile_path(profile_id)
            try:
                import shutil
                if os.path.exists(profile_path):
                    shutil.rmtree(profile_path)
                del self.profile_metadata['profiles'][profile_id]
                print(f"🗑️ Deleted old profile: {profile_id}")
            except Exception as e:
                print(f"✗ Error deleting profile {profile_id}: {e}")
        
        if profiles_to_delete:
            self.save_profile_metadata()
    
    def get_profile_path(self, profile_id):
        """Return absolute path to profile directory"""
        profile_dir = self.config.get('profile_directory', 'browser_profiles')
        return os.path.abspath(os.path.join(profile_dir, profile_id))

class CaptchaResolver:
    def __init__(self, config):
        self.config = config.get('captcha_services', {})
        self.solver_2captcha = None
        self.solver_anticaptcha = None
        self.stats = {'attempts': 0, 'successes': 0, 'failures': 0, 'service_used': {}}
        
        # Initialize 2Captcha if enabled
        if self.config.get('2captcha', {}).get('enabled'):
            try:
                from twocaptcha import TwoCaptcha
                api_key = self.config['2captcha'].get('api_key')
                if api_key and api_key != 'your_2captcha_api_key_here':
                    self.solver_2captcha = TwoCaptcha(api_key)
                    print("✓ 2Captcha service initialized")
            except Exception as e:
                print(f"⚠️ Failed to initialize 2Captcha: {e}")
        
        # Initialize Anti-Captcha if enabled
        if self.config.get('anticaptcha', {}).get('enabled'):
            try:
                api_key = self.config['anticaptcha'].get('api_key')
                if api_key and api_key != 'your_anticaptcha_api_key_here':
                    self.anticaptcha_key = api_key
                    print("✓ Anti-Captcha service initialized")
            except Exception as e:
                print(f"⚠️ Failed to initialize Anti-Captcha: {e}")
    
    def detect_captcha_type(self, driver):
        """Detect CAPTCHA type present on page"""
        try:
            # Check for hCaptcha
            hcaptcha_iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='hcaptcha']")
            if hcaptcha_iframes:
                return ('hcaptcha', None, driver.current_url)
            
            # Check for reCAPTCHA
            recaptcha_iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha']")
            if recaptcha_iframes:
                # Determine v2 or v3
                recaptcha_v3 = driver.find_elements(By.CSS_SELECTOR, "[data-action]")
                if recaptcha_v3:
                    return ('recaptcha_v3', None, driver.current_url)
                return ('recaptcha_v2', None, driver.current_url)
            
            # Check for custom GitHub puzzle
            custom_puzzle = driver.find_elements(By.CSS_SELECTOR, "[data-testid*='puzzle'], [class*='captcha']")
            if custom_puzzle:
                return ('custom', None, driver.current_url)
            
            return (None, None, None)
        except Exception as e:
            print(f"Error detecting CAPTCHA: {e}")
            return (None, None, None)
    
    def extract_sitekey(self, driver, captcha_type):
        """Extract sitekey from page"""
        try:
            if captcha_type == 'hcaptcha':
                # Try iframe src
                iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='hcaptcha']")
                if iframes:
                    src = iframes[0].get_attribute('src')
                    match = re.search(r'sitekey=([^&]+)', src)
                    if match:
                        return match.group(1)
                
                # Try data-sitekey attribute
                elements = driver.find_elements(By.CSS_SELECTOR, "[data-sitekey]")
                if elements:
                    return elements[0].get_attribute('data-sitekey')
            
            elif captcha_type in ['recaptcha_v2', 'recaptcha_v3']:
                # Try iframe src
                iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha']")
                if iframes:
                    src = iframes[0].get_attribute('src')
                    match = re.search(r'k=([^&]+)', src)
                    if match:
                        return match.group(1)
                
                # Try data-sitekey attribute
                elements = driver.find_elements(By.CSS_SELECTOR, "[data-sitekey]")
                if elements:
                    return elements[0].get_attribute('data-sitekey')
                
                # Try page source
                page_source = driver.page_source
                match = re.search(r'data-sitekey="([^"]+)"', page_source)
                if match:
                    return match.group(1)
            
            return None
        except Exception as e:
            print(f"Error extracting sitekey: {e}")
            return None
    
    def solve_with_2captcha(self, captcha_type, sitekey, page_url):
        """Solve CAPTCHA using 2Captcha service"""
        if not self.solver_2captcha:
            return None
        
        try:
            print(f"🔄 Solving {captcha_type} with 2Captcha...")
            self.stats['attempts'] += 1
            
            if captcha_type == 'hcaptcha':
                result = self.solver_2captcha.hcaptcha(sitekey=sitekey, url=page_url)
            elif captcha_type == 'recaptcha_v2':
                result = self.solver_2captcha.recaptcha(sitekey=sitekey, url=page_url)
            elif captcha_type == 'recaptcha_v3':
                result = self.solver_2captcha.recaptcha(sitekey=sitekey, url=page_url, version='v3')
            else:
                return None
            
            if result and 'code' in result:
                self.stats['successes'] += 1
                self.stats['service_used']['2captcha'] = self.stats['service_used'].get('2captcha', 0) + 1
                print(f"✓ 2Captcha solved successfully")
                return result['code']
            
            return None
        except Exception as e:
            print(f"✗ 2Captcha error: {e}")
            self.stats['failures'] += 1
            return None
    
    def solve_with_anticaptcha(self, captcha_type, sitekey, page_url):
        """Solve CAPTCHA using Anti-Captcha service"""
        if not hasattr(self, 'anticaptcha_key'):
            return None
        
        try:
            print(f"🔄 Solving {captcha_type} with Anti-Captcha...")
            self.stats['attempts'] += 1
            
            if captcha_type == 'hcaptcha':
                from anticaptchaofficial.hcaptchaproxyless import hCaptchaProxyless
                solver = hCaptchaProxyless()
                solver.set_key(self.anticaptcha_key)
                solver.set_website_url(page_url)
                solver.set_website_key(sitekey)
                token = solver.solve_and_return_solution()
            elif captcha_type == 'recaptcha_v2':
                from anticaptchaofficial.recaptchav2proxyless import recaptchaV2Proxyless
                solver = recaptchaV2Proxyless()
                solver.set_key(self.anticaptcha_key)
                solver.set_website_url(page_url)
                solver.set_website_key(sitekey)
                token = solver.solve_and_return_solution()
            elif captcha_type == 'recaptcha_v3':
                from anticaptchaofficial.recaptchav3proxyless import recaptchaV3Proxyless
                solver = recaptchaV3Proxyless()
                solver.set_key(self.anticaptcha_key)
                solver.set_website_url(page_url)
                solver.set_website_key(sitekey)
                solver.set_page_action('submit')
                token = solver.solve_and_return_solution()
            else:
                return None
            
            if token:
                self.stats['successes'] += 1
                self.stats['service_used']['anticaptcha'] = self.stats['service_used'].get('anticaptcha', 0) + 1
                print(f"✓ Anti-Captcha solved successfully")
                return token
            
            return None
        except Exception as e:
            print(f"✗ Anti-Captcha error: {e}")
            self.stats['failures'] += 1
            return None
    
    def solve_captcha(self, driver, page_url):
        """Main method to solve CAPTCHA"""
        # Detect CAPTCHA type
        captcha_type, _, _ = self.detect_captcha_type(driver)
        
        if not captcha_type:
            return (True, None, "No CAPTCHA detected")
        
        print(f"🔍 Detected CAPTCHA type: {captcha_type}")
        
        # Extract sitekey
        sitekey = self.extract_sitekey(driver, captcha_type)
        if not sitekey:
            return (False, None, f"Could not extract sitekey for {captcha_type}")
        
        print(f"🔑 Extracted sitekey: {sitekey[:20]}...")
        
        # Try primary service
        primary_service = self.config.get('primary_service', '2captcha')
        solution_token = None
        
        if primary_service == '2captcha' and self.solver_2captcha:
            solution_token = self.solve_with_2captcha(captcha_type, sitekey, page_url)
        elif primary_service == 'anticaptcha' and hasattr(self, 'anticaptcha_key'):
            solution_token = self.solve_with_anticaptcha(captcha_type, sitekey, page_url)
        
        # Try fallback service if primary failed
        if not solution_token:
            print("⚠️ Primary service failed, trying fallback...")
            if primary_service == '2captcha' and hasattr(self, 'anticaptcha_key'):
                solution_token = self.solve_with_anticaptcha(captcha_type, sitekey, page_url)
            elif primary_service == 'anticaptcha' and self.solver_2captcha:
                solution_token = self.solve_with_2captcha(captcha_type, sitekey, page_url)
        
        if solution_token:
            return (True, solution_token, f"CAPTCHA solved with token")
        
        return (False, None, "All CAPTCHA services failed")
    
    def inject_captcha_solution(self, driver, captcha_type, solution_token):
        """Inject CAPTCHA solution into page"""
        try:
            if captcha_type == 'hcaptcha':
                # Inject into h-captcha-response textarea
                driver.execute_script(f"""
                    document.querySelector('[name="h-captcha-response"]').innerHTML = '{solution_token}';
                """)
                # Trigger callback if exists
                driver.execute_script("""
                    if (window.hcaptcha && window.hcaptcha.callback) {
                        window.hcaptcha.callback();
                    }
                """)
                print("✓ hCaptcha solution injected")
                return True
            
            elif captcha_type in ['recaptcha_v2', 'recaptcha_v3']:
                # Inject into g-recaptcha-response textarea
                driver.execute_script(f"""
                    document.getElementById('g-recaptcha-response').innerHTML = '{solution_token}';
                """)
                # Trigger callback
                driver.execute_script(f"""
                    if (typeof ___grecaptcha_cfg !== 'undefined') {{
                        var clients = ___grecaptcha_cfg.clients;
                        for (var id in clients) {{
                            if (clients[id].callback) {{
                                clients[id].callback('{solution_token}');
                            }}
                        }}
                    }}
                """)
                print("✓ reCAPTCHA solution injected")
                return True
            
            return False
        except Exception as e:
            print(f"✗ Error injecting solution: {e}")
            return False
    
    def log_captcha_stats(self):
        """Log CAPTCHA solving statistics"""
        print(f"\n📊 CAPTCHA Statistics:")
        print(f"   Total attempts: {self.stats['attempts']}")
        print(f"   Successes: {self.stats['successes']}")
        print(f"   Failures: {self.stats['failures']}")
        if self.stats['service_used']:
            print(f"   Services used: {self.stats['service_used']}")

class GitHubAutoSignup:
    def __init__(self):
        self.password = self.generate_random_password()
        self.driver = None
        self.wait = None
        self.temp_email = None
        self.temp_password = None
        self.username = None
        self.accounts_file = "github_accounts.txt"
        self.proxy_manager = ProxyManager()
        self.profile_manager = ProfileManager()
        self.current_profile_id = None
        
        # Initialize CAPTCHA resolver
        self.captcha_resolver = None
        captcha_config = self.proxy_manager.config.get('captcha_services', {})
        if captcha_config.get('enabled'):
            try:
                self.captcha_resolver = CaptchaResolver(self.proxy_manager.config)
                print("✓ CAPTCHA resolver initialized")
            except Exception as e:
                print(f"⚠️ Failed to initialize CAPTCHA resolver: {e}")
                self.captcha_resolver = None

    def log_current_ip(self):
        """Log current IP address to verify proxy is working"""
        try:
            response = requests.get("https://api.ipify.org?format=json", timeout=10, proxies={})
            ip = response.json()["ip"]
            print(f"Current IP: {ip}")
            
            # Log User-Agent
            try:
                user_agent = self.driver.execute_script("return navigator.userAgent")
                print(f"Current User-Agent: {user_agent[:80]}...")
            except:
                pass
            
            return ip
        except Exception as e:
            print(f"Failed to get IP: {e}")
            return None

    def generate_realistic_fingerprint(self):
        """Generate realistic browser fingerprint"""
        # Generate realistic User-Agent
        ua = UserAgent(browsers=['chrome'])
        user_agent = ua.random
        
        # Determine platform from User-Agent
        if 'Windows' in user_agent:
            platform = 'Win32'
            timezone = random.choice(['America/New_York', 'America/Chicago', 'America/Los_Angeles', 'Europe/London', 'Europe/Paris'])
        elif 'Macintosh' in user_agent or 'Mac OS X' in user_agent:
            platform = 'MacIntel'
            timezone = random.choice(['America/New_York', 'America/Los_Angeles', 'America/Chicago'])
        else:
            platform = 'Linux x86_64'
            timezone = random.choice(['America/New_York', 'Europe/London', 'Asia/Tokyo'])
        
        # Determine language based on timezone
        if 'America' in timezone:
            language = 'en-US'
        elif 'Europe' in timezone:
            language = random.choice(['en-GB', 'en-US', 'de-DE', 'fr-FR'])
        else:
            language = 'en-US'
        
        # Hardware specs
        hardware_concurrency = random.choice([4, 6, 8, 12, 16])
        device_memory = random.choice([8, 16])
        
        # Screen resolution
        resolutions = [
            (1920, 1080),
            (1366, 768),
            (2560, 1440),
            (1440, 900),
            (1536, 864)
        ]
        screen_width, screen_height = random.choice(resolutions)
        
        # WebGL vendor and renderer
        if platform == 'Win32':
            webgl_vendor = 'Google Inc. (Intel)'
            webgl_renderer = random.choice([
                'ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0)',
                'ANGLE (Intel, Intel(R) HD Graphics 620 Direct3D11 vs_5_0 ps_5_0)',
                'ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0)'
            ])
        elif platform == 'MacIntel':
            webgl_vendor = 'Apple Inc.'
            webgl_renderer = 'Apple M1'
        else:
            webgl_vendor = 'Google Inc. (Intel)'
            webgl_renderer = 'ANGLE (Intel, Mesa Intel(R) UHD Graphics 620 (KBL GT2), OpenGL 4.6)'
        
        return {
            'user_agent': user_agent,
            'platform': platform,
            'timezone': timezone,
            'language': language,
            'hardware_concurrency': hardware_concurrency,
            'device_memory': device_memory,
            'screen_width': screen_width,
            'screen_height': screen_height,
            'webgl_vendor': webgl_vendor,
            'webgl_renderer': webgl_renderer
        }

    def setup_firefox_driver(self, use_proxy=True, proxy_fingerprint=None, headless=False):
        """Setup undetected Chrome driver with advanced stealth options"""
        # Generate realistic fingerprint (or use proxy-matched one)
        if proxy_fingerprint:
            # Merge proxy fingerprint with generated one
            fingerprint = self.generate_realistic_fingerprint()
            fingerprint.update(proxy_fingerprint)
        else:
            fingerprint = self.generate_realistic_fingerprint()
        
        print(f"\n🎭 Generated Fingerprint:")
        print(f"   Platform: {fingerprint['platform']}")
        print(f"   Timezone: {fingerprint['timezone']}")
        print(f"   Language: {fingerprint['language']}")
        print(f"   Screen: {fingerprint['screen_width']}x{fingerprint['screen_height']}")
        print(f"   User-Agent: {fingerprint['user_agent'][:80]}...")
        
        # Get proxy with new ProxyManager
        proxy = None
        proxy_ip = None
        if use_proxy and self.proxy_manager.config.get('proxy_enabled'):
            proxy_data = self.proxy_manager.get_next_proxy()
            if proxy_data:
                proxy = proxy_data['proxy']
                print(f"🔄 Testing proxy: {proxy[:50]}...")
                
                # Validate proxy
                is_valid, response_time, proxy_ip = self.proxy_manager.validate_proxy(proxy)
                if is_valid:
                    print(f"✓ Proxy validated: {proxy[:50]}... (Response time: {response_time:.2f}s, IP: {proxy_ip})")
                    
                    # Match fingerprint to proxy geolocation
                    if self.proxy_manager.config.get('geolocation', {}).get('match_timezone'):
                        proxy_fingerprint_data = self.proxy_manager.match_fingerprint_to_proxy(proxy_ip)
                        fingerprint['timezone'] = proxy_fingerprint_data['timezone']
                        fingerprint['language'] = proxy_fingerprint_data['language']
                        print(f"✓ Fingerprint matched to proxy location: {proxy_fingerprint_data['country']} - {proxy_fingerprint_data['timezone']}")
                    
                    self.proxy_manager.mark_proxy_success(proxy)
                else:
                    print(f"✗ Proxy validation failed, trying another...")
                    self.proxy_manager.mark_proxy_failed(proxy)
                    # Retry with another proxy
                    return self.setup_firefox_driver(use_proxy=use_proxy, proxy_fingerprint=proxy_fingerprint, headless=headless)
            else:
                print("⚠️ No proxy available, using direct connection")
        else:
            print("🔓 Proxy disabled, using direct connection")

        # Profile Management
        self.profile_manager.cleanup_old_profiles()
        profile_id = self.profile_manager.get_available_profile()
        if not profile_id:
            profile_id = self.profile_manager.create_new_profile()
        
        if profile_id:
            profile_path = self.profile_manager.get_profile_path(profile_id)
            self.current_profile_id = profile_id
            print(f"🗂️ Using profile: {profile_id}")
        else:
            profile_path = None
            print("⚠️ No profile available, using temporary session")

        options = Options()
        
        # Headless mode for VPS (no GUI)
        if headless:
            options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-software-rasterizer')
            print("🖥️ Running in headless mode (no GUI)")
        
        # Use persistent profile instead of incognito
        if profile_path:
            options.add_argument(f'--user-data-dir={profile_path}')
            options.add_argument('--profile-directory=Default')
        
        # Set User-Agent
        options.add_argument(f'--user-agent={fingerprint["user_agent"]}')
        
        # Set Language
        options.add_argument(f'--lang={fingerprint["language"]}')
        
        # Chrome preferences for realism
        prefs = {
            'intl.accept_languages': fingerprint["language"],
            'credentials_enable_service': False,
            'profile.password_manager_enabled': False,
            'profile.default_content_setting_values.notifications': 2,
            'profile.default_content_setting_values.geolocation': 2,
            'download.prompt_for_download': False,
            'download.default_directory': '/tmp',
            'safebrowsing.enabled': True,
            'plugins.always_open_pdf_externally': True
        }
        options.add_experimental_option('prefs', prefs)
        
        # Chrome flags for realism and stealth
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-first-run')
        options.add_argument('--no-default-browser-check')
        options.add_argument('--disable-popup-blocking')
        
        # Add proxy if available
        if proxy:
            options.add_argument(f'--proxy-server={proxy}')

        self.driver = uc.Chrome(options=options)

        # Advanced JavaScript injections for stealth
        # 1. WebDriver property
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # 2. Plugins
        self.driver.execute_script(f"Object.defineProperty(navigator, 'plugins', {{get: () => [{', '.join(['1'] * random.randint(3, 5))}]}})")
        
        # 3. Languages
        self.driver.execute_script(f"Object.defineProperty(navigator, 'languages', {{get: () => ['{fingerprint['language']}', 'en']}})")
        
        # 4. Platform
        self.driver.execute_script(f"Object.defineProperty(navigator, 'platform', {{get: () => '{fingerprint['platform']}'}})") 
        
        # 5. Hardware Concurrency
        self.driver.execute_script(f"Object.defineProperty(navigator, 'hardwareConcurrency', {{get: () => {fingerprint['hardware_concurrency']}}})")
        
        # 6. Device Memory
        self.driver.execute_script(f"Object.defineProperty(navigator, 'deviceMemory', {{get: () => {fingerprint['device_memory']}}})")
        
        # 7. WebGL Vendor and Renderer
        self.driver.execute_script(f"""
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {{
                if (parameter === 37445) {{
                    return '{fingerprint['webgl_vendor']}';
                }}
                if (parameter === 37446) {{
                    return '{fingerprint['webgl_renderer']}';
                }}
                return getParameter.apply(this, arguments);
            }};
        """)
        
        # 8. Canvas Fingerprinting - add noise
        self.driver.execute_script("""
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function() {
                const context = this.getContext('2d');
                const imageData = context.getImageData(0, 0, this.width, this.height);
                for (let i = 0; i < imageData.data.length; i += 4) {
                    imageData.data[i] += Math.floor(Math.random() * 3) - 1;
                }
                context.putImageData(imageData, 0, 0);
                return originalToDataURL.apply(this, arguments);
            };
        """)
        
        # 9. Timezone
        self.driver.execute_script(f"""
            Intl.DateTimeFormat = function() {{
                return {{
                    resolvedOptions: function() {{
                        return {{timeZone: '{fingerprint['timezone']}'}};
                    }}
                }};
            }};
        """)
        
        # 10. Chrome runtime
        self.driver.execute_script("window.chrome = { runtime: {} }")

        # Set window size from fingerprint
        self.driver.set_window_size(fingerprint['screen_width'], fingerprint['screen_height'])

        self.wait = WebDriverWait(self.driver, 30)
        
        # Log current IP to verify proxy
        self.log_current_ip()


    def human_like_delay(self, min_delay=1, max_delay=3):
        """Add human-like random delays with exponential distribution"""
        # Use exponential distribution for more realistic timing
        lambda_param = 1.0
        delay = random.expovariate(lambda_param)
        # Scale and bound the delay
        delay = min(max_delay, max(min_delay, delay * (max_delay - min_delay) / 2 + min_delay))
        time.sleep(delay)

    def human_like_typing(self, element, text, typo_probability=0.07, pause_probability=0.15, burst_typing_probability=0.20):
        """Type text with human-like delays, typos, and corrections"""
        element.clear()
        time.sleep(random.uniform(0.2, 0.5))  # Delay after clearing
        
        common_words = ['the', 'and', 'com', 'net', 'org', 'www', 'http', 'https']
        words = text.split()
        
        for word_idx, word in enumerate(words):
            # Check if it's a common word for burst typing
            is_common = any(common in word.lower() for common in common_words)
            
            for char_idx, char in enumerate(word):
                # Simulate typo
                if random.random() < typo_probability and char.isalnum():
                    # Type wrong character
                    wrong_chars = string.ascii_lowercase if char.islower() else string.ascii_uppercase
                    wrong_char = random.choice(wrong_chars.replace(char, ''))
                    element.send_keys(wrong_char)
                    time.sleep(random.uniform(0.3, 0.6))  # Realization delay
                    element.send_keys('\b')  # Backspace
                    time.sleep(random.uniform(0.1, 0.2))
                
                # Type correct character
                element.send_keys(char)
                
                # Variable typing speed based on character type
                if is_common and random.random() < burst_typing_probability:
                    # Burst typing for common words
                    delay = random.uniform(0.04, 0.08)
                elif char.isalnum():
                    delay = random.uniform(0.08, 0.18)
                else:
                    # Special characters are slower
                    delay = random.uniform(0.15, 0.30)
                
                time.sleep(delay)
                
                # Random micro-pauses
                if random.random() < pause_probability and char in '.,@-_':
                    time.sleep(random.uniform(0.4, 1.2))
            
            # Add space between words (except last word)
            if word_idx < len(words) - 1:
                element.send_keys(' ')
                time.sleep(random.uniform(0.1, 0.2))
                
                # Occasional pause between words
                if random.random() < pause_probability:
                    time.sleep(random.uniform(0.4, 1.2))

    def simulate_mouse_movement(self, target_x=None, target_y=None, duration=0.5):
        """Simulate natural mouse movement with curved path"""
        current_x, current_y = mouse.position
        
        # If no target specified, move to random position
        if target_x is None or target_y is None:
            target_x = random.randint(100, width - 100)
            target_y = random.randint(100, height - 100)
        
        # Calculate number of steps based on distance and duration
        distance = ((target_x - current_x) ** 2 + (target_y - current_y) ** 2) ** 0.5
        steps = int(distance / 3)  # ~3 pixels per step
        steps = max(10, min(steps, 100))  # Bound between 10 and 100 steps
        
        for i in range(steps):
            # Bezier curve simulation with random variation
            t = i / steps
            # Add curve and randomness
            curve_offset_x = random.randint(-5, 5)
            curve_offset_y = random.randint(-5, 5)
            
            new_x = int(current_x + (target_x - current_x) * t + curve_offset_x)
            new_y = int(current_y + (target_y - current_y) * t + curve_offset_y)
            
            # Keep within bounds
            new_x = max(0, min(width - 1, new_x))
            new_y = max(0, min(height - 1, new_y))
            
            mouse.position = (new_x, new_y)
            
            # Variable speed
            time.sleep(random.uniform(0.001, 0.003))
            
            # Occasional mid-movement pause
            if random.random() < 0.1:
                time.sleep(random.uniform(0.1, 0.3))

    def random_scroll_behavior(self, pattern='exploration'):
        """Simulate natural scrolling behavior"""
        try:
            if pattern == 'exploration':
                # Initial page scan
                scroll_amount = random.randint(200, 400)
                self.driver.execute_script(f"window.scrollBy({{top: {scroll_amount}, behavior: 'smooth'}})")
                time.sleep(random.uniform(0.5, 1.5))
                
                # Scroll back up partially
                scroll_back = random.randint(100, scroll_amount // 2)
                self.driver.execute_script(f"window.scrollBy({{top: -{scroll_back}, behavior: 'smooth'}})")
                time.sleep(random.uniform(0.3, 0.8))
                
            elif pattern == 'form':
                # Small scrolls to read form fields
                scroll_amount = random.randint(50, 150)
                self.driver.execute_script(f"window.scrollBy({{top: {scroll_amount}, behavior: 'smooth'}})")
                time.sleep(random.uniform(0.3, 1.0))
                
            elif pattern == 'jitter':
                # Natural jitter
                scroll_amount = random.randint(-30, 30)
                self.driver.execute_script(f"window.scrollBy({{top: {scroll_amount}, behavior: 'smooth'}})")
                time.sleep(random.uniform(0.2, 0.5))
                
        except Exception as e:
            # Silently fail if scrolling not possible
            pass

    def simulate_interaction_pattern(self, element, text):
        """Simulate complete human-like interaction with element"""
        try:
            # Get element location for mouse movement
            location = element.location
            size = element.size
            target_x = location['x'] + size['width'] // 2 + random.randint(-20, 20)
            target_y = location['y'] + size['height'] // 2 + random.randint(-10, 10)
            
            # Move mouse near element
            self.simulate_mouse_movement(target_x, target_y, duration=random.uniform(0.3, 0.7))
            
            # Trigger mouseover event
            self.driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('mouseover', {bubbles: true}))", element)
            time.sleep(random.uniform(0.3, 0.8))  # Hover delay
            
            # Focus element
            self.driver.execute_script("arguments[0].focus()", element)
            time.sleep(random.uniform(0.2, 0.4))  # Focus delay
            
            # Type content with human-like behavior
            self.human_like_typing(element, text)
            
            # Review delay
            time.sleep(random.uniform(0.3, 0.6))
            
            # Blur element
            self.driver.execute_script("arguments[0].blur()", element)
            
            # Move mouse away slightly
            away_x = target_x + random.randint(-50, 50)
            away_y = target_y + random.randint(-30, 30)
            self.simulate_mouse_movement(away_x, away_y, duration=random.uniform(0.2, 0.4))
            
        except Exception as e:
            # Fallback to simple typing if interaction pattern fails
            print(f"   Interaction pattern failed, using fallback: {e}")
            self.human_like_typing(element, text)

    def generate_random_username(self, length=8):
        """Generate random username"""
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
        return f"user{username}"

    def generate_random_password(self, length=15):
        """Generate random password with guaranteed character diversity"""
        # Define character categories
        uppercase = string.ascii_uppercase
        lowercase = string.ascii_lowercase
        digits = string.digits
        special = "!@#$%^&*"
        
        # Ensure at least one character from each category
        password_chars = [
            secrets.choice(uppercase),
            secrets.choice(lowercase),
            secrets.choice(digits),
            secrets.choice(special)
        ]
        
        # Fill remaining characters randomly from all categories
        all_chars = uppercase + lowercase + digits + special
        for _ in range(length - 4):
            password_chars.append(secrets.choice(all_chars))
        
        # Shuffle to avoid predictable patterns
        random.shuffle(password_chars)
        
        return ''.join(password_chars)

    def create_temp_email(self):
        """Create temporary email using mail.tm API"""
        try:
            # Get available domains
            domains_response = requests.get("https://api.mail.tm/domains")
            domains = domains_response.json()["hydra:member"]
            domain = domains[0]["domain"]

            # Generate random email
            email_local = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
            email = f"{email_local}@{domain}"

            # Create account
            account_data = {
                "address": email,
                "password": "temppassword123"
            }

            create_response = requests.post("https://api.mail.tm/accounts", json=account_data)

            if create_response.status_code == 201:
                self.temp_email = email
                self.temp_password = "temppassword123"
                print(f"Created temporary email: {email}")
                return True
            else:
                print(f"Failed to create email: {create_response.text}")
                return False

        except Exception as e:
            print(f"Error creating temp email: {e}")
            return False

    def get_email_token(self):
        """Get authentication token for email access"""
        try:
            auth_data = {
                "address": self.temp_email,
                "password": self.temp_password
            }

            response = requests.post("https://api.mail.tm/token", json=auth_data)
            if response.status_code == 200:
                return response.json()["token"]
            return None
        except Exception as e:
            print(f"Error getting email token: {e}")
            return None

    def get_verification_code_from_email(self, token):
        """Get verification code from GitHub email"""
        headers = {"Authorization": f"Bearer {token}"}

        # Wait for email to arrive
        for attempt in range(30):  # Wait up to 5 minutes
            try:
                response = requests.get("https://api.mail.tm/messages", headers=headers)
                if response.status_code == 200:
                    messages = response.json()["hydra:member"]

                    for message in messages:
                        if "github" in message["subject"].lower() or "verification" in message["subject"].lower():
                            # Get message content
                            msg_response = requests.get(f"https://api.mail.tm/messages/{message['id']}", headers=headers)
                            if msg_response.status_code == 200:
                                content = msg_response.json()["text"]

                                # Extract verification code (6-digit number)
                                code_match = re.search(r'\b\d{6}\b', content)
                                if code_match:
                                    return code_match.group()

                print(f"Waiting for email... attempt {attempt + 1}/30")
                time.sleep(10)

            except Exception as e:
                print(f"Error checking emails: {e}")
                time.sleep(10)

        return None

    def navigate_to_github_signup(self):
        """Navigate to GitHub signup page with human-like behavior"""

        print("\n📍 Navigation Step: Going to GitHub signup...")
        # Try direct signup URL first
        self.driver.get("https://github.com/signup?source=login")
        print(f"   Current URL: {self.driver.current_url}")
        print(f"   Page Title: {self.driver.title}")
        self.human_like_delay(2, 3)
        
        # Simulate human exploration - random mouse movements
        print("   🖱️  Simulating mouse exploration...")
        for _ in range(random.randint(2, 4)):
            self.simulate_mouse_movement()
            time.sleep(random.uniform(0.2, 0.5))
        
        # Simulate page scanning with scroll
        print("   📜 Simulating page scan...")
        self.random_scroll_behavior(pattern='exploration')
        
        # Check if we're on the right page by looking for email field
        try:
            self.driver.find_element(By.ID, "email")
            print("   ✓ Successfully navigated to signup page (email field found)")
        except:
            # If not found, try alternative method - go to homepage and click signup
            print("   ✗ Email field not found, trying homepage method...")
            self.driver.get("https://github.com")
            print(f"   Current URL: {self.driver.current_url}")
            self.human_like_delay(1, 2)
            try:
                signup_button = self.wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//a[contains(@href, '/signup') or contains(text(), 'Sign up')]")
                ))
                print(f"   Found signup button: {signup_button.text}")
                
                # Move mouse to button before clicking
                self.simulate_mouse_movement()
                
                signup_button.click()
                self.human_like_delay(2, 3)
                print(f"   Current URL after click: {self.driver.current_url}")
                print("   ✓ Clicked signup button from homepage")
            except Exception as e:
                print(f"   ✗ Failed to find signup button: {e}")
                self.driver.save_screenshot("error_navigation.png")

    def fill_signup_form(self):
        """Fill GitHub signup form - all fields in one page"""
        try:
            # Generate username
            self.username = self.generate_random_username()
            print(f"\n📝 Form Filling: Generated username: {self.username}")

            print("\n📧 Filling all signup fields...")
            print(f"   Current URL: {self.driver.current_url}")
            print(f"   Page Title: {self.driver.title}")
            
            # Simulate reading the form with scroll
            print("   📜 Simulating form exploration...")
            self.random_scroll_behavior(pattern='form')
            
            try:
                # Fill email with interaction pattern
                email_field = self.wait.until(EC.presence_of_element_located((By.ID, "email")))
                print(f"   ✓ Found email field")
                print(f"   Entering email: {self.temp_email}")
                
                # Small scroll to bring field into view
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'})", email_field)
                time.sleep(random.uniform(0.3, 0.6))
                
                self.simulate_interaction_pattern(email_field, self.temp_email)
                self.human_like_delay(1, 2)
                
                # Random mouse movement between fields
                self.simulate_mouse_movement()

                # Fill password with interaction pattern
                password_field = self.wait.until(EC.presence_of_element_located((By.ID, "password")))
                print(f"   ✓ Found password field")
                print(f"   Entering password: {'*' * len(self.password)}")
                
                # Small scroll adjustment
                self.random_scroll_behavior(pattern='jitter')
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'})", password_field)
                time.sleep(random.uniform(0.3, 0.6))
                
                self.simulate_interaction_pattern(password_field, self.password)
                self.human_like_delay(1, 2)
                
                # Random mouse movement between fields
                self.simulate_mouse_movement()

                # Fill username with interaction pattern
                username_field = self.wait.until(EC.presence_of_element_located((By.ID, "login")))
                print(f"   ✓ Found username field")
                print(f"   Entering username: {self.username}")
                
                # Small scroll adjustment
                self.random_scroll_behavior(pattern='jitter')
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'})", username_field)
                time.sleep(random.uniform(0.3, 0.6))
                
                self.simulate_interaction_pattern(username_field, self.username)
                self.human_like_delay(2, 3)

                # Move mouse near button before clicking
                print("   Looking for 'Create account' button...")
                create_button = self.wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button.signup-form-fields__button, button[type='submit']:not([data-disable-with*='Google']):not([data-disable-with*='Apple'])")
                ))
                print(f"   Found button: {create_button.text}")
                
                # Scroll to button
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'})", create_button)
                time.sleep(random.uniform(0.5, 1.0))
                
                # Move mouse to button area
                button_location = create_button.location
                button_size = create_button.size
                button_x = button_location['x'] + button_size['width'] // 2 + random.randint(-10, 10)
                button_y = button_location['y'] + button_size['height'] // 2 + random.randint(-5, 5)
                self.simulate_mouse_movement(button_x, button_y, duration=random.uniform(0.4, 0.8))
                
                # Hover over button
                self.driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('mouseover', {bubbles: true}))", create_button)
                time.sleep(random.uniform(0.3, 0.6))
                
                # Click button
                self.driver.execute_script("arguments[0].click();", create_button)
                self.human_like_delay(3, 4)
                print(f"   Current URL after click: {self.driver.current_url}")
                print("   ✓ Form submitted successfully")
                
            except Exception as e:
                print(f"   ✗ Error filling form: {e}")
                self.driver.save_screenshot("error_form_filling.png")
                print(f"   Screenshot saved: error_form_filling.png")
                print(f"   Current URL: {self.driver.current_url}")
                return False

            print("\n✅ All form fields completed successfully")
            return True

        except Exception as e:
            print(f"\n❌ Error filling signup form: {e}")
            try:
                self.driver.save_screenshot("error_signup_form.png")
                print(f"   Screenshot saved: error_signup_form.png")
                print(f"   Current URL: {self.driver.current_url}")
            except:
                pass
            return False

    def handle_email_already_exists(self):
        """Handle case where email already exists"""
        try:
            error_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'already taken') or contains(text(), 'already exists')]")
            if error_elements:
                print("Email already exists, creating new temp email...")
                if self.create_temp_email():
                    return self.fill_signup_form()
            return True
        except:
            return True

    def wait_for_manual_puzzle_completion(self):
        """Wait for user to manually complete the visual puzzle or solve automatically"""
        print("\n" + "="*50)
        
        # Try automatic CAPTCHA solving if enabled
        if self.captcha_resolver:
            print("🤖 CAPTCHA services enabled - attempting automatic solving...")
            print("="*50)
            
            max_retries = self.proxy_manager.config.get('captcha_services', {}).get('retry_attempts', 2)
            timeout = self.proxy_manager.config.get('captcha_services', {}).get('timeout_seconds', 120)
            
            for attempt in range(1, max_retries + 1):
                try:
                    print(f"\n🔄 CAPTCHA solving attempt {attempt}/{max_retries}...")
                    
                    # Wait a bit for CAPTCHA to load
                    time.sleep(3)
                    
                    # Attempt to solve
                    success, solution_token, message = self.captcha_resolver.solve_captcha(
                        self.driver, 
                        self.driver.current_url
                    )
                    
                    if success and solution_token:
                        # Inject solution
                        captcha_type, _, _ = self.captcha_resolver.detect_captcha_type(self.driver)
                        if self.captcha_resolver.inject_captcha_solution(self.driver, captcha_type, solution_token):
                            print("✅ CAPTCHA solved and injected successfully!")
                            
                            # Wait for page transition
                            time.sleep(5)
                            
                            # Check if we've moved to verification code screen
                            try:
                                self.driver.find_element(By.ID, "launch-code-0")
                                print("✓ Successfully bypassed CAPTCHA - reached verification screen")
                                self.captcha_resolver.log_captcha_stats()
                                return
                            except:
                                # Check if still on CAPTCHA page
                                captcha_still_present, _, _ = self.captcha_resolver.detect_captcha_type(self.driver)
                                if not captcha_still_present:
                                    print("✓ CAPTCHA bypassed successfully")
                                    self.captcha_resolver.log_captcha_stats()
                                    return
                                else:
                                    print("⚠️ CAPTCHA still present, retrying...")
                        else:
                            print("✗ Failed to inject CAPTCHA solution")
                    elif success and not solution_token:
                        print(f"ℹ️ {message}")
                        # No CAPTCHA detected, continue
                        return
                    else:
                        print(f"✗ CAPTCHA solving failed: {message}")
                        
                        # Save screenshot for debugging
                        try:
                            self.driver.save_screenshot(f"captcha_failed_attempt_{attempt}.png")
                            print(f"   Screenshot saved: captcha_failed_attempt_{attempt}.png")
                        except:
                            pass
                    
                    if attempt < max_retries:
                        print(f"   Waiting before retry...")
                        time.sleep(5)
                        
                except Exception as e:
                    print(f"✗ Error during CAPTCHA solving: {e}")
                    import traceback
                    traceback.print_exc()
            
            # All automatic attempts failed
            print("\n⚠️ Automatic CAPTCHA solving failed after all attempts")
            self.captcha_resolver.log_captcha_stats()
            
            # Check if fallback to manual is enabled
            if not self.proxy_manager.config.get('captcha_services', {}).get('fallback_to_manual', True):
                print("❌ Manual fallback disabled - stopping")
                return
            
            print("🔄 Falling back to manual CAPTCHA solving...")
        
        # Manual CAPTCHA solving
        print("MANUAL ACTION REQUIRED!")
        print("Please complete the visual puzzle in the browser.")
        print("Once you reach the 'Enter code sent to your email' screen,")
        print("Bring your mouse to bottom right of the screen to continue...")
        print("="*50)

        start_time = time.time()
        timeout = 180  # 3 minutes for manual solving
        
        while True:
            # Check timeout
            if time.time() - start_time > timeout:
                print("⚠️ Manual CAPTCHA solving timeout!")
                break
            
            x, y = mouse.position
            if x >= width - threshold and y >= height - threshold:
                print("Mouse reached the bottom-right corner of the screen!")
                break
            
            time.sleep(0.5)

        # Wait a moment for page to load
        time.sleep(3)

    def enter_verification_code(self):
        """Get verification code from email and enter it"""
        print("\n📬 Getting verification code from email...")

        token = self.get_email_token()
        if not token:
            print("   ✗ Failed to get email token")
            return False

        verification_code = self.get_verification_code_from_email(token)
        if not verification_code:
            print("   ✗ Failed to get verification code from email")
            return False

        print(f"   ✓ Found verification code: {verification_code}")
        print(f"\n🔢 Entering verification code...")
        print(f"   Current URL: {self.driver.current_url}")
        print(f"   Page Title: {self.driver.title}")
        
        # Random mouse movement before entering code
        print("   🖱️  Simulating mouse movement...")
        self.simulate_mouse_movement()
        time.sleep(random.uniform(0.3, 0.6))

        # Enter verification code with human-like behavior
        try:
            # Try separate fields first (launch-code-0 to launch-code-5)
            try:
                print("   Trying separate code fields...")
                code_field0 = self.wait.until(EC.presence_of_element_located(
                    (By.ID, "launch-code-0")
                ))
                print("   ✓ Found separate code fields")
                
                # Enter each digit with interaction pattern
                code_fields = []
                for i in range(6):
                    field = self.driver.find_element(By.ID, f"launch-code-{i}")
                    code_fields.append(field)
                
                for i, field in enumerate(code_fields):
                    # Small mouse movement to field
                    location = field.location
                    size = field.size
                    field_x = location['x'] + size['width'] // 2 + random.randint(-5, 5)
                    field_y = location['y'] + size['height'] // 2 + random.randint(-3, 3)
                    self.simulate_mouse_movement(field_x, field_y, duration=random.uniform(0.2, 0.4))
                    
                    # Focus and type
                    self.driver.execute_script("arguments[0].focus()", field)
                    time.sleep(random.uniform(0.1, 0.3))
                    field.send_keys(verification_code[i])
                    time.sleep(random.uniform(0.15, 0.35))

                print("   ✓ Entered code in separate fields")
            except:
                # If separate fields don't exist, try single field
                print("   Separate fields not found, trying single field...")
                code_field = self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[type='text'], input[name='otp'], input[id*='code']")
                ))
                print("   ✓ Found single code field")
                self.simulate_interaction_pattern(code_field, verification_code)
                print("   ✓ Entered code in single field")

            self.human_like_delay(2, 2)
            print(f"   Current URL after entering code: {self.driver.current_url}")
            return True

        except Exception as e:
            print(f"   ✗ Error entering verification code: {e}")
            try:
                self.driver.save_screenshot("error_verification_code.png")
                print(f"   Screenshot saved: error_verification_code.png")
                print(f"   Current URL: {self.driver.current_url}")
            except:
                pass
            return False

    def sign_in_with_github(self):
        """Completing Signing in"""
        print("\n🔐 Completing sign in process...")
        print(f"   Current URL: {self.driver.current_url}")
        print(f"   Page Title: {self.driver.title}")
        try:

            # Fill in sign up form
            print("   Looking for login fields...")
            self.driver.find_element(By.ID, "login_field").send_keys(self.username)
            print(f"   ✓ Entered username: {self.username}")
            self.driver.find_element(By.ID, "password").send_keys(self.password)
            print(f"   ✓ Entered password")
            self.human_like_delay(1, 2)

            # Look for sign in button
            print("   Looking for sign in button...")
            sign_in_button = self.driver.find_element(By.XPATH, "//input[@type='submit' or contains(@class, 'btn-primary')]")
            print(f"   Found button, clicking...")
            self.driver.execute_script("arguments[0].click();", sign_in_button)
            self.human_like_delay(2, 3)
            print(f"   Current URL after sign in: {self.driver.current_url}")
            print("   ✓ Sign in completed")
            return True

        except Exception as e:
            print(f"   ✗ Error completing signin: {e}")
            try:
                self.driver.save_screenshot("error_signin.png")
                print(f"   Screenshot saved: error_signin.png")
            except:
                pass
            return False

    def save_account_details(self):
        """Save account details to file"""
        account_info = {
            "email": self.temp_email,
            "username": self.username,
            "password": self.password,
            "temp_email_password": self.temp_password,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        with open(self.accounts_file, "a") as f:
            f.write(json.dumps(account_info) + "\n")

        print(f"Account details saved: {self.username} - {self.temp_email}")

    def cleanup_current_profile(self, delete_profile=False):
        """Close driver and optionally delete current profile"""
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
        except Exception as e:
            print(f"⚠️ Error closing driver: {e}")
        
        if delete_profile and self.current_profile_id:
            try:
                import shutil
                profile_path = self.profile_manager.get_profile_path(self.current_profile_id)
                if os.path.exists(profile_path):
                    shutil.rmtree(profile_path)
                    print(f"🗑️ Deleted profile: {self.current_profile_id}")
                
                # Remove from metadata
                if self.current_profile_id in self.profile_manager.profile_metadata['profiles']:
                    del self.profile_manager.profile_metadata['profiles'][self.current_profile_id]
                    self.profile_manager.save_profile_metadata()
            except Exception as e:
                print(f"✗ Error deleting profile: {e}")
        
        self.current_profile_id = None

    def create_single_account(self):
        """Create a single GitHub account"""
        print(f"\n{'='*60}")
        print("Starting new GitHub account creation...")
        print(f"{'='*60}")
        global created_count

        # Setup new browser instance
        if created_count > 0 and self.driver:
            try:
                self.driver.quit()
            except:
                pass

        print("\n🔄 Setting up new browser with fresh proxy...")
        # Enable proxy - set to False to disable proxy
        # Headless mode for VPS (set to True if running on server without GUI)
        headless_mode = os.environ.get('HEADLESS', 'false').lower() == 'true'
        
        try:
            self.setup_firefox_driver(use_proxy=True, headless=headless_mode)
        except Exception as e:
            print(f"✗ Failed to setup driver with proxy: {e}")
            print("Retrying with fallback proxy or direct connection...")
            # Try with free proxy as fallback
            self.proxy_manager.config['providers']['free_proxy']['enabled'] = True
            try:
                self.setup_firefox_driver(use_proxy=True, headless=headless_mode)
            except:
                print("✗ All proxy attempts failed, using direct connection")
                self.setup_firefox_driver(use_proxy=False, headless=headless_mode)

        try:
            # Step 1: Create temporary email
            if not self.create_temp_email():
                print("Failed to create temporary email")
                return False

            # Step 2: Navigate to GitHub signup
            self.navigate_to_github_signup()

            # Step 3: Fill signup form
            if not self.fill_signup_form():
                print("Failed to fill signup form")
                return False

            # Step 3: Handle email already exists
            if not self.handle_email_already_exists():
                print("Failed to handle email conflict")
                return False

            # Step 4: Wait for manual puzzle completion
            self.wait_for_manual_puzzle_completion()

            # Step 5: Enter verification code
            if not self.enter_verification_code():
                print("Failed to enter verification code")
                return False

            # Step 6: Sign in with GitHub
            if not self.sign_in_with_github():
                print("Failed to sign in with GitHub")
                return False

            # Step 7: Save account details
            self.save_account_details()

            print(f"✅ Successfully created account: {self.username}")
            
            # Update profile usage with success
            if self.current_profile_id:
                self.profile_manager.update_profile_usage(self.current_profile_id, success=True)
            
            # Log proxy statistics
            self.proxy_manager.log_proxy_stats()
            
            return True

        except Exception as e:
            print(f"Error creating account: {e}")
            import traceback
            traceback.print_exc()
            
            # Mark profile usage as failed
            if self.current_profile_id:
                self.profile_manager.update_profile_usage(self.current_profile_id, success=False)
            
            return False

    def run_continuous_creation(self, num_accounts=None):
        """Run continuous account creation"""
        global created_count

        try:
            while True:
                if num_accounts and created_count >= num_accounts:
                    break

                success = self.create_single_account()
                if success:
                    created_count += 1

                print(f"\nAccounts created so far: {created_count}")
                
                # Log proxy stats after each attempt
                self.proxy_manager.log_proxy_stats()

        except KeyboardInterrupt:
            print(f"\nStopped by user. Total accounts created: {created_count}")
        finally:
            print("DONEEEEEEEEEEEEEEEEEEE!!!")

def main():
    creator = GitHubAutoSignup()

    print("GitHub Account Auto-Creator")
    print("This script will create GitHub accounts using temporary emails from mail.tm")
    print("\nPress Ctrl+C to stop the script at any time")

    try:
        num_accounts = input("\nHow many accounts to create? (Press Enter for unlimited): ").strip()
        num_accounts = int(num_accounts) if num_accounts else None
    except:
        num_accounts = None

    creator.run_continuous_creation(num_accounts)

if __name__ == "__main__":
    listener_thread = threading.Thread(target=listen_for_middle_click, daemon=True)
    listener_thread.start()
    main()
