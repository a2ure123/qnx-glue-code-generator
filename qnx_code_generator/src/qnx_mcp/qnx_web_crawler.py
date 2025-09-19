#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QNX Web Crawler for Function Documentation
Crawls QNX official documentation and extracts function information
"""

import os
import sys
import json
import logging
import time
import hashlib
import requests
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from dataclasses import dataclass
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class QNXFunction:
    """QNX function information"""
    name: str
    url: str
    html_content: str
    category: str = ""
    
class QNXWebCrawler:
    """QNX official documentation web crawler"""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize crawler"""
        self.base_url = "https://www.qnx.com/developers/docs/7.1/"
        self.lib_ref_base = "com.qnx.doc.neutrino.lib_ref/topic/"
        
        # Load config
        self.config = self._load_config(config_path)
        
        # Request config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Proxy config
        proxy_config = self.config.get("network_settings", {}).get("proxy", {})
        if proxy_config.get("enabled", False):
            proxies = {}
            if proxy_config.get("http_proxy"):
                proxies["http"] = proxy_config["http_proxy"]
            if proxy_config.get("https_proxy"):
                proxies["https"] = proxy_config["https_proxy"]
            
            if proxies:
                self.session.proxies.update(proxies)
                logger.info(f"QNX crawler using proxy: {proxies}")
        
        # Timeout and retry config
        request_settings = self.config.get("network_settings", {}).get("request_settings", {})
        self.timeout = request_settings.get("timeout", 30)
        self.max_retries = request_settings.get("max_retries", 3)
        
        # Cache settings
        self.cache_dir = Path("./data/qnx_web_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Rate limiting
        self.request_delay = 1.0  # 1 second delay to avoid being blocked
        
        logger.info("QNX Web Crawler initialized")
        logger.info(f"Base URL: {self.base_url}")
        logger.info(f"Cache directory: {self.cache_dir}")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load config file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load config file: {e}")
            return {}
    
    def get_function_url_patterns(self) -> Dict[str, List[str]]:
        """Get function URL patterns
        
        QNX documentation is categorized by alphabet:
        - a: abort, abs, accept, access, ...
        - b: basename, bcmp, bcopy, bind, ...
        - c: calloc, ceil, chmod, close, ...
        etc.
        """
        # Common function initial letter categories
        patterns = {}
        
        # Standard C library functions
        c_functions = [
            # A
            "abort", "abs", "accept", "access", "acos", "alarm", "asctime", "asin", "atan", "atexit", "atof", "atoi", "atol",
            # B  
            "basename", "bcmp", "bcopy", "bind", "bsearch",
            # C
            "calloc", "ceil", "chmod", "chown", "close", "connect", "cos", "cosh", "creat",
            # D
            "difftime", "dirname", "div", "dup", "dup2",
            # E
            "exit", "exp", "fabs", "fclose", "fdopen", "feof", "ferror", "fflush", "fgetc", "fgets", "fileno",
            # F
            "floor", "fmod", "fopen", "fprintf", "fputc", "fputs", "fread", "free", "freopen", "frexp", "fscanf", "fseek", "ftell", "fwrite",
            # G
            "getc", "getchar", "getenv", "getpid", "gets", "gmtime",
            # L
            "labs", "ldexp", "listen", "localtime", "log", "log10", "longjmp", "lseek",
            # M
            "malloc", "memchr", "memcmp", "memcpy", "memmove", "memset", "mkdir", "mktime", "modf",
            # O
            "open",
            # P
            "perror", "pow", "printf", "putc", "putchar", "puts",
            # Q
            "qsort",
            # R
            "rand", "read", "realloc", "recv", "remove", "rename", "rewind",
            # S
            "scanf", "send", "setjmp", "sin", "sinh", "sleep", "socket", "sprintf", "sqrt", "srand", "sscanf", "strcat", "strchr", "strcmp", "strcpy", "strlen", "strncat", "strncmp", "strncpy", "strstr", "strtod", "strtol", "system",
            # T
            "tan", "tanh", "time", "tmpfile", "tmpnam",
            # U
            "ungetc", "unlink",
            # W
            "write"
        ]
        
        # Group by initial letter
        for func in c_functions:
            first_letter = func[0].lower()
            if first_letter not in patterns:
                patterns[first_letter] = []
            patterns[first_letter].append(func)
        
        return patterns
    
    def build_function_url(self, function_name: str) -> str:
        """Build function documentation URL"""
        first_letter = function_name[0].lower()
        # URL format: https://www.qnx.com/developers/docs/7.1/#com.qnx.doc.neutrino.lib_ref/topic/a/abort.html
        url = f"{self.base_url}#{self.lib_ref_base}{first_letter}/{function_name}.html"
        return url
    
    def fetch_function_page(self, function_name: str) -> Optional[QNXFunction]:
        """Fetch single function page"""
        url = self.build_function_url(function_name)
        
        # Check cache
        cache_file = self.cache_dir / f"{function_name}.html"
        if cache_file.exists():
            logger.debug(f"Loading from cache: {function_name}")
            try:
                html_content = cache_file.read_text(encoding='utf-8')
                return QNXFunction(
                    name=function_name,
                    url=url,
                    html_content=html_content,
                    category=function_name[0].lower()
                )
            except Exception as e:
                logger.warning(f"Failed to load cache for {function_name}: {e}")
        
        # Fetch from network
        try:
            logger.info(f"Fetching: {function_name} -> {url}")
            
            # Actual URL to fetch (remove #)
            actual_url = f"{self.base_url}{self.lib_ref_base}{function_name[0].lower()}/{function_name}.html"
            
            response = self.session.get(actual_url, timeout=30)
            response.raise_for_status()
            
            html_content = response.text
            
            # Validate content (contains function name)
            if function_name.lower() in html_content.lower():
                # Cache result
                try:
                    cache_file.write_text(html_content, encoding='utf-8')
                    logger.debug(f"Cached: {function_name}")
                except Exception as e:
                    logger.warning(f"Failed to cache {function_name}: {e}")
                
                return QNXFunction(
                    name=function_name,
                    url=url,
                    html_content=html_content,
                    category=function_name[0].lower()
                )
            else:
                logger.warning(f"Invalid content for {function_name}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {function_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching {function_name}: {e}")
            return None
        finally:
            # Rate limiting
            time.sleep(self.request_delay)
    
    def fetch_functions_batch(self, function_names: List[str]) -> List[QNXFunction]:
        """Fetch function pages in batch"""
        functions = []
        
        logger.info(f"Fetching batch of {len(function_names)} functions")
        
        for i, name in enumerate(function_names):
            logger.info(f"Progress: {i+1}/{len(function_names)} - {name}")
            
            func = self.fetch_function_page(name)
            if func:
                functions.append(func)
            else:
                logger.warning(f"Failed to fetch function: {name}")
        
        logger.info(f"Successfully fetched {len(functions)}/{len(function_names)} functions")
        return functions
    
    def discover_functions_from_alphabetic_pages(self) -> List[str]:
        """从QNX文档的字母索引页面发现所有函数"""
        all_functions = []
        
        # 对每个字母进行爬取
        for letter in 'abcdefghijklmnopqrstuvwxyz':
            logger.info(f"正在发现字母 '{letter}' 下的函数...")
            
            try:
                # QNX按字母组织的目录页面URL
                index_url = f"{self.base_url}{self.lib_ref_base}lib-{letter}.html"
                
                response = self.session.get(index_url, timeout=30)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 查找函数链接
                    functions_in_letter = self._extract_functions_from_index_page(soup, letter)
                    all_functions.extend(functions_in_letter)
                    
                    logger.info(f"字母 '{letter}': 发现 {len(functions_in_letter)} 个函数")
                else:
                    logger.warning(f"无法访问字母 '{letter}' 的索引页面: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"处理字母 '{letter}' 时出错: {e}")
                # 如果网络失败，使用预定义的函数列表作为备用
                backup_functions = self._get_backup_functions_for_letter(letter)
                if backup_functions:
                    all_functions.extend(backup_functions)
                    logger.info(f"字母 '{letter}': 使用备用列表 {len(backup_functions)} 个函数")
            
            # Rate limiting
            time.sleep(self.request_delay)
        
        # 去重并排序
        unique_functions = sorted(list(set(all_functions)))
        logger.info(f"总共发现 {len(unique_functions)} 个唯一函数")
        
        return unique_functions
    
    def _extract_functions_from_index_page(self, soup: BeautifulSoup, letter: str) -> List[str]:
        """从索引页面提取函数名列表"""
        functions = []
        
        # 方法1: 从meta标签的DC.Relation中提取函数链接
        for meta in soup.find_all('meta', {'name': 'DC.Relation'}):
            content = meta.get('content', '')
            if f'/topic/{letter}/' in content and content.endswith('.html'):
                # 提取函数名: ../../com.qnx.doc.neutrino.lib_ref/topic/a/abort.html -> abort
                function_name = content.split('/')[-1].replace('.html', '')
                if function_name and function_name[0].lower() == letter:
                    functions.append(function_name)
        
        # 方法2: 查找所有.html链接（备用方案）
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if href.endswith('.html') and f'/{letter}/' in href:
                function_name = href.split('/')[-1].replace('.html', '')
                if function_name and function_name[0].lower() == letter:
                    functions.append(function_name)
        
        # 方法3: 查找包含函数名的特定结构（备用方案）
        for element in soup.find_all(['dt', 'li', 'td']):
            text = element.get_text().strip()
            # 匹配看起来像函数名的文本 (字母开头，可能包含下划线)
            if re.match(rf'^{letter}[a-zA-Z_][a-zA-Z0-9_]*$', text):
                functions.append(text)
        
        return list(set(functions))  # 去重
    
    def _get_backup_functions_for_letter(self, letter: str) -> List[str]:
        """获取指定字母的备用函数列表"""
        backup_functions = {
            'a': ["abort", "abs", "accept", "access", "acos", "alarm", "asctime", "asin", "atan", "atexit", "atof", "atoi", "atol"],
            'b': ["basename", "bcmp", "bcopy", "bind", "bsearch"],
            'c': ["calloc", "ceil", "chmod", "chown", "close", "connect", "cos", "cosh", "creat"],
            'd': ["difftime", "dirname", "div", "dup", "dup2"],
            'e': ["exit", "exp"],
            'f': ["fabs", "fclose", "fdopen", "feof", "ferror", "fflush", "fgetc", "fgets", "fileno", "floor", "fmod", "fopen", "fprintf", "fputc", "fputs", "fread", "free", "freopen", "frexp", "fscanf", "fseek", "ftell", "fwrite"],
            'g': ["getc", "getchar", "getenv", "getpid", "gets", "gmtime"],
            'h': ["htonl", "htons"],
            'i': ["inet_addr", "inet_ntoa"],
            'j': [],
            'k': ["kill"],
            'l': ["labs", "ldexp", "listen", "localtime", "log", "log10", "longjmp", "lseek"],
            'm': ["malloc", "memchr", "memcmp", "memcpy", "memmove", "memset", "mkdir", "mktime", "modf"],
            'n': ["ntohl", "ntohs"],
            'o': ["open"],
            'p': ["perror", "pow", "printf", "putc", "putchar", "puts", "pthread_create", "pthread_join", "pthread_mutex_init"],
            'q': ["qsort"],
            'r': ["rand", "read", "realloc", "recv", "remove", "rename", "rewind"],
            's': ["scanf", "send", "setjmp", "sin", "sinh", "sleep", "socket", "sprintf", "sqrt", "srand", "sscanf", "strcat", "strchr", "strcmp", "strcpy", "strlen", "strncat", "strncmp", "strncpy", "strstr", "strtod", "strtol", "system"],
            't': ["tan", "tanh", "time", "tmpfile", "tmpnam"],
            'u': ["ungetc", "unlink"],
            'v': [],
            'w': ["wait", "waitpid", "write"],
            'x': [],
            'y': [],
            'z': []
        }
        
        return backup_functions.get(letter, [])
    
    def discover_functions_from_index(self) -> List[str]:
        """Discover function list from QNX documentation index pages - full crawling functionality"""
        logger.info("Starting to discover all functions from QNX documentation...")
        
        # First try to discover from alphabetic index pages
        try:
            functions = self.discover_functions_from_alphabetic_pages()
            if len(functions) > 50:  # If enough functions were discovered
                return functions
        except Exception as e:
            logger.error(f"Failed to discover functions from alphabetic index pages: {e}")
        
        # Backup plan: use predefined list
        logger.info("Using backup function list...")
        all_functions = []
        for letter in 'abcdefghijklmnopqrstuvwxyz':
            backup_functions = self._get_backup_functions_for_letter(letter)
            all_functions.extend(backup_functions)
        
        unique_functions = sorted(list(set(all_functions)))
        logger.info(f"Backup plan discovered {len(unique_functions)} functions")
        return unique_functions
    
    def validate_function_content(self, func: QNXFunction) -> bool:
        """Validate if the function content is valid"""
        if not func.html_content:
            return False
        
        # Check if function name is present
        if func.name.lower() not in func.html_content.lower():
            return False
        
        # Check for typical function documentation elements
        soup = BeautifulSoup(func.html_content, 'html.parser')
        
        # Check for function syntax or signature
        has_syntax = bool(
            soup.find(text=re.compile(r'synopsis|syntax|prototype', re.I)) or
            soup.find('code') or
            soup.find('pre') or
            func.name + '(' in func.html_content
        )
        
        return has_syntax
    
    def get_cached_functions(self) -> List[str]:
        """Get list of cached functions"""
        if not self.cache_dir.exists():
            return []
        
        cached = []
        for file in self.cache_dir.glob("*.html"):
            cached.append(file.stem)
        
        return sorted(cached)
    
    def crawl_functions(self, function_names: Optional[List[str]] = None, max_functions: Optional[int] = None) -> List[QNXFunction]:
        """Crawl function documentation
        
        Args:
            function_names: List of function names to crawl. If None, crawl all discovered functions.
            max_functions: Maximum number of functions to crawl.
        """
        if function_names is None:
            function_names = self.discover_functions_from_index()
        
        if max_functions:
            function_names = function_names[:max_functions]
        
        logger.info(f"Starting to crawl {len(function_names)} functions")
        
        # Check cached functions
        cached_functions = self.get_cached_functions()
        logger.info(f"Found {len(cached_functions)} cached functions")
        
        # Separate functions to fetch
        to_fetch = [name for name in function_names if name not in cached_functions]
        logger.info(f"Need to fetch {len(to_fetch)} new functions")
        
        # Fetch new functions
        functions = []
        if to_fetch:
            new_functions = self.fetch_functions_batch(to_fetch)
            functions.extend(new_functions)
        
        # Load cached functions
        for name in function_names:
            if name in cached_functions:
                func = self.fetch_function_page(name)  # Load from cache
                if func and self.validate_function_content(func):
                    functions.append(func)
        
        logger.info(f"Total collected functions: {len(functions)}")
        
        # Validate and filter
        valid_functions = []
        for func in functions:
            if self.validate_function_content(func):
                valid_functions.append(func)
            else:
                logger.warning(f"Invalid content for function: {func.name}")
        
        logger.info(f"Valid functions: {len(valid_functions)}")
        return valid_functions


def main():
    """Test crawler functionality"""
    crawler = QNXWebCrawler()
    
    # Test single functions
    test_functions = ["abort", "malloc", "printf", "sprintf", "strlen"]
    
    logger.info("Testing crawler with sample functions...")
    functions = crawler.crawl_functions(test_functions, max_functions=5)
    
    for func in functions:
        print(f"Function: {func.name}")
        print(f"URL: {func.url}")
        print(f"Content length: {len(func.html_content)}")
        print(f"Valid: {crawler.validate_function_content(func)}")
        print("-" * 50)


if __name__ == "__main__":
    main()