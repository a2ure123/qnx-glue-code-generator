#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Gemini 2.5 Flash JSON提取器
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gemini_flash_json_extractor import GeminiFlashJSONExtractor

def test_json_extractor():
    """测试JSON提取器基本功能"""
    try:
        print("=== 测试Gemini 2.5 Flash JSON提取器 ===")
        
        # 初始化提取器
        extractor = GeminiFlashJSONExtractor()
        print("✓ JSON提取器初始化成功")
        
        # 测试HTML内容
        test_html = """
        <html>
        <head><title>sprintf function</title></head>
        <body>
        <div class="content">
        <h1>sprintf</h1>
        <h2>Synopsis</h2>
        <pre><code>int sprintf(char *s, const char *format, ...);</code></pre>
        
        <h2>Description</h2>
        <p>The sprintf() function formats and stores a series of characters and values in the array pointed to by s. Each argument (if any) is converted and output according to the corresponding format specifier in the format string.</p>
        
        <h2>Arguments</h2>
        <dl>
        <dt>s</dt>
        <dd>Pointer to a buffer where the resulting C-string is stored.</dd>
        <dt>format</dt>
        <dd>C string that contains a format string that follows the same specifications as format in printf.</dd>
        </dl>
        
        <h2>Returns</h2>
        <p>On success, the total number of characters written is returned. This count does not include the additional null-character automatically appended at the end of the string.</p>
        
        <h2>Header Files</h2>
        <p><code>#include &lt;stdio.h&gt;</code></p>
        
        <h2>Library</h2>
        <p>libc</p>
        
        <h2>Classification</h2>
        <p>ANSI, POSIX 1003.1</p>
        
        <h2>Safety</h2>
        <p>Cancellation point: No<br/>
        Interrupt handler: Yes<br/>
        Signal handler: Yes<br/>
        Thread safe: Yes</p>
        
        <h2>See also</h2>
        <p>printf(), fprintf(), snprintf(), vprintf(), vfprintf(), vsprintf(), vsnprintf()</p>
        </div>
        </body>
        </html>
        """
        
        # 提取函数信息
        print("开始提取函数信息...")
        function_info = extractor.extract_function_info(test_html, "sprintf")
        
        if function_info:
            print("✓ 函数信息提取成功!")
            
            print(f"\n=== 提取结果 ===")
            print(f"函数名: {function_info.name}")
            print(f"声明: {function_info.synopsis}")
            print(f"描述: {function_info.description[:100]}...")
            print(f"返回类型: {function_info.return_type}")
            print(f"参数数量: {len(function_info.parameters)}")
            
            if function_info.parameters:
                print("\n参数:")
                for i, param in enumerate(function_info.parameters):
                    print(f"  {i+1}. {param.name} ({param.type}): {param.description}")
            
            if function_info.headers:
                print(f"\n头文件: {[h.filename for h in function_info.headers]}")
            
            if function_info.libraries:
                print(f"库: {function_info.libraries}")
            
            print(f"分类: {function_info.classification}")
            print(f"安全性: {function_info.safety}")
            
            if function_info.see_also:
                print(f"相关函数: {function_info.see_also}")
            
            # 保存测试结果
            output_path = "./tests/test_sprintf_output.json"
            extractor.save_function_info_json(function_info, output_path)
            print(f"✓ 结果已保存到: {output_path}")
            
        else:
            print("✗ 函数信息提取失败")
            return False
        
        print("\n✓ 所有测试通过!")
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_json_extractor()
    sys.exit(0 if success else 1)