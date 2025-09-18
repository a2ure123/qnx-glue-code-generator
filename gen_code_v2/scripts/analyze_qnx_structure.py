#!/usr/bin/env python3
"""
分析QNX HTML文档结构，找出编写规律
"""

import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, quote
import json

def analyze_sample_pages():
    """分析几个示例页面的结构"""
    
    # 示例函数页面
    sample_functions = [
        "malloc",
        "printf", 
        "pthread_create",
        "open",
        "close"
    ]
    
    base_url = "https://www.qnx.com/developers/docs/7.1/com.qnx.doc.neutrino.lib_ref/topic/"
    
    structure_analysis = {}
    
    for func_name in sample_functions:
        print(f"\n=== 分析函数: {func_name} ===")
        
        # 尝试不同的URL格式
        possible_urls = [
            f"{base_url}m/{func_name}.html",  # 按首字母分组
            f"{base_url}{func_name[0]}/{func_name}.html",
            f"{base_url}{func_name}.html",
        ]
        
        for url in possible_urls:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    print(f"成功访问: {url}")
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 分析页面结构
                    analysis = analyze_page_structure(soup, func_name, url)
                    structure_analysis[func_name] = analysis
                    
                    break
            except Exception as e:
                print(f"访问失败 {url}: {e}")
                continue
    
    return structure_analysis

def analyze_page_structure(soup, func_name, url):
    """分析单个页面的结构"""
    analysis = {
        "function_name": func_name,
        "url": url,
        "title": "",
        "synopsis": "",
        "description": "",
        "parameters": [],
        "return_values": [],
        "code_examples": [],
        "headers": [],
        "html_structure": {}
    }
    
    # 提取标题
    title = soup.find('title')
    if title:
        analysis["title"] = title.get_text().strip()
    
    # 查找Synopsis/函数签名部分
    synopsis_section = soup.find('div', class_='section refsyn')
    if synopsis_section:
        # 提取头文件
        for pre in synopsis_section.find_all('pre', class_='pre codeblock'):
            code_text = pre.get_text()
            for line in code_text.splitlines():
                line = line.strip()
                if line.startswith('#include'):
                    analysis["headers"].append(line)
                elif func_name in line and '(' in line:
                    analysis["synopsis"] = line
    
    # 查找描述
    shortdesc = soup.find('div', class_='shortdesc')
    if shortdesc:
        analysis["description"] = shortdesc.get_text().strip()
    
    # 查找参数部分
    sections = soup.find_all('div', class_='section')
    for section in sections:
        h2 = section.find('h2', class_='title sectiontitle')
        if h2:
            section_title = h2.get_text().strip().lower()
            
            if 'arguments' in section_title or 'parameters' in section_title:
                # 提取参数信息
                dl = section.find('dl', class_='dl')
                if dl:
                    for dt, dd in zip(dl.find_all('dt', class_='dlterm'), 
                                    dl.find_all('dd', class_='dd')):
                        param_name = dt.get_text().strip()
                        param_desc = dd.get_text().strip()
                        analysis["parameters"].append({
                            "name": param_name,
                            "description": param_desc
                        })
            
            elif 'returns' in section_title or 'return' in section_title:
                # 提取返回值信息
                dl_list = section.find_all('dl', class_='dl')
                for dl in dl_list:
                    for dt, dd in zip(dl.find_all('dt', class_='dlterm'),
                                    dl.find_all('dd', class_='dd')):
                        return_val = dt.get_text().strip()
                        return_desc = dd.get_text().strip()
                        analysis["return_values"].append({
                            "value": return_val,
                            "description": return_desc
                        })
    
    # 查找代码示例
    for pre in soup.find_all('pre'):
        code_text = pre.get_text().strip()
        if len(code_text) > 20 and func_name in code_text:
            analysis["code_examples"].append(code_text)
    
    # 分析HTML结构
    analysis["html_structure"] = {
        "has_refsyn_section": bool(soup.find('div', class_='section refsyn')),
        "has_shortdesc": bool(soup.find('div', class_='shortdesc')),
        "section_count": len(soup.find_all('div', class_='section')),
        "has_dl_elements": bool(soup.find('dl', class_='dl')),
        "code_block_count": len(soup.find_all('pre', class_='pre codeblock'))
    }
    
    return analysis

def discover_url_patterns():
    """发现URL模式"""
    base_url = "https://www.qnx.com/developers/docs/7.1/com.qnx.doc.neutrino.lib_ref/topic/"
    
    # 检查字母索引页面
    import string
    url_patterns = {}
    
    for letter in ['a', 'b', 'c', 'm', 'p']:  # 测试几个字母
        list_url = f"{base_url}lib-{letter}.html"
        print(f"\n检查字母页面: {list_url}")
        
        try:
            response = requests.get(list_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找函数链接
                links = []
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if href.endswith('.html') and '/' in href:
                        full_url = urljoin(list_url, href)
                        link_text = link.get_text().strip()
                        if '()' in link_text:
                            func_names = link_text.replace('()', '').split(',')
                            for func_name in func_names:
                                func_name = func_name.strip()
                                links.append({
                                    "function_name": func_name,
                                    "url": full_url,
                                    "href": href
                                })
                
                url_patterns[letter] = links[:5]  # 只取前5个作为样本
                
        except Exception as e:
            print(f"访问失败: {e}")
    
    return url_patterns

if __name__ == "__main__":
    print("=== QNX HTML文档结构分析 ===")
    
    # 1. 发现URL模式
    print("\n1. 发现URL模式...")
    url_patterns = discover_url_patterns()
    
    print("\nURL模式分析:")
    for letter, links in url_patterns.items():
        print(f"\n字母 {letter}:")
        for link in links:
            print(f"  函数: {link['function_name']}")
            print(f"  URL: {link['url']}")
            print(f"  HREF: {link['href']}")
    
    # 2. 分析页面结构
    print("\n\n2. 分析页面结构...")
    structure_analysis = analyze_sample_pages()
    
    # 保存分析结果
    with open('./data/qnx_structure_analysis.json', 'w', encoding='utf-8') as f:
        json.dump({
            "url_patterns": url_patterns,
            "structure_analysis": structure_analysis
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n分析完成，结果保存到: ./data/qnx_structure_analysis.json")
    
    # 打印结构摘要
    print("\n=== 结构摘要 ===")
    for func_name, analysis in structure_analysis.items():
        print(f"\n函数: {func_name}")
        print(f"  标题: {analysis['title']}")
        print(f"  签名: {analysis['synopsis']}")
        print(f"  描述: {analysis['description'][:100]}...")
        print(f"  参数数量: {len(analysis['parameters'])}")
        print(f"  返回值数量: {len(analysis['return_values'])}")
        print(f"  代码示例数量: {len(analysis['code_examples'])}")