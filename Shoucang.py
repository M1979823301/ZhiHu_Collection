import datetime
import time
import requests
import re
import os
import hashlib
import json
import random
from datetime import datetime
import urllib
from bs4 import BeautifulSoup


# 保存到当前文件夹下的"./Zhihu"文件夹（这里是绝对路径！！！）
BASE_DIR = "D:/Python/Zhihu"
REQUEST_DELAY = 1
HEADERS = {
    "user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36"
}
cookies = {
    #收藏夹网页的cookies
    #可以复制curl去https://curlconverter.com/转化为json
}
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)


#***************************************文件名转换符合windows命名法则******************************************
def sanitize_filename(filename):
    translation_map = str.maketrans({
        '：': ':', '？': '?', '！': '!', '（': '(', '）': ')', '【': '[', '】': ']', '｛': '{', '｝': '}',
        '“': '"', '”': '"', '‘': "'", '’': "'", '，': ',', '。': '.', '、': ',', '；': ';', '《': '<', '》': '>'
    })
    filename = filename.translate(translation_map)
    filename = re.sub(r'[\\/*?:"<>|]', '_', filename)
    return filename


#**********************************下载普通图片，然后将json图片路径替换为本地路径*********************************
def download_image(img_url, save_folder):
    global HEADERS
    try:
        img_name = os.path.basename(img_url.split("?")[0])
        local_path = os.path.join(save_folder, img_name)

        if os.path.exists(local_path):
            return local_path

        response = requests.get(img_url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            with open(local_path, 'wb') as f:
                f.write(response.content)
            time.sleep(REQUEST_DELAY)  # 降低爬虫请求频率
            return local_path
        else:
            print(f"❌ 下载失败: {img_url}，状态码: {response.status_code}")
            return None
    except Exception as e:
        print(f"⚠️ 下载出错: {img_url}, 错误: {e}")
        return None


#**********************************根据知乎video的路径得到真正的视频路径（HD版本）*********************************
def get_video_urls(url):
    # 获取答案url上的id
    answer_id = re.findall(r'/(\d+)', url)[0]
    url = "https://lens.zhihu.com/api/v4/videos/"+str(answer_id)
    res = requests.get(url, headers=headers).text
    res = json.loads(res)
    data = res["playlist"]["SD"]["play_url"]
    video_urls = data
    time.sleep(1)
    return video_urls


#**********************************下载普通视频，然后将json图片路径替换为本地路径*********************************
def download_video(video_url, save_folder):
    try:
        # 从 URL 获取视频文件名
        video_name = os.path.basename(video_url.split("?")[0])
        local_path = os.path.join(save_folder, video_name )

        # 如果文件已存在，返回该路径
        if os.path.exists(local_path):
            return local_path

        response = requests.get(video_url, headers=HEADERS, stream=True, timeout=10)

        if response.status_code == 200:
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024*1024):  # 每次下载 1MB
                    f.write(chunk)
            time.sleep(REQUEST_DELAY)  # 降低请求频率
            # print(f"视频已成功下载并保存为 {local_path}")
            return local_path
        else:
            print(f"❌ 下载失败: {video_url}，状态码: {response.status_code}")
            return None
    except Exception as e:
        print(f"⚠️ 下载出错: {video_url}, 错误: {e}")
        return None

    

#***********************************转换知乎equation为本地MathJax公式******************************************
def convert_equation_to_mathjax(content):
    def replace_equation(match):
        latex_code = urllib.parse.unquote(match.group(1).replace("+", "%20"))  # URL 解码
        latex_code = re.sub(r'<', r'\\lt ', latex_code)
        latex_code = re.sub(r'>', r'\\gt ', latex_code) 
        latex_code = re.sub(r'\\bm\s+([a-zA-Z0-9\{\}]+)', r'\\boldsymbol{\1}', latex_code)
        latex_code = re.sub(r'\\bm\s*{([a-zA-Z0-9]+)\}',r'\\boldsymbol{\1}', latex_code)
        pattern = r'^\\\[.*\\\]$'
        a = bool(re.match(pattern, latex_code))
        if(a == True):
            return f'{latex_code}'
        else:
            return f'\\({latex_code}\\)'

    # 处理知乎的 LaTeX 公式
    if isinstance(content, list):
        content = content[0]
        content = content.get("own_text",content.get("content", ""))
    content = re.sub(r'<img src="https://www\.zhihu\.com/equation\?tex=([^"]+)"[^>]*>', replace_equation, content)
    
    return content


#***********************************得到json，进行一系列处理，最终嵌入html***************************************
def process_zhihu_json(json_data,x):
    processed_data = json_data.copy()
    question_title = ""
    for idx, item in enumerate(processed_data.get("data", [])):
        content = item.get("content", {})
        question_title = sanitize_filename(content.get("question", {}).get("title", "未知标题"))
        if(question_title == "未知标题"):
            question_title = sanitize_filename(content.get("title", "未知标题"))
        if(question_title == "未知标题"):
            question_title = sanitize_filename(content.get("excerpt_title","未知标题"))

        content_folder = os.path.join(BASE_DIR, f"{x}_{question_title}")
        os.makedirs(content_folder, exist_ok=True)

        au = content.get("author","").get('avatar_url',"")
        # print(au)
        raw_content = content.get("content", "")

        # 处理 LaTeX 公式，转换为 MathJax
        raw_content = convert_equation_to_mathjax(raw_content)

        # 查找并下载普通图片
        img_urls = re.findall(r'<img\s+src=["\'](https?://.*?)[\"\']', raw_content)
        img_urls += re.findall(r'<src=["\'](https?://.*?)[\"\']', raw_content)
        # print(img_urls)
        # break
        video_urls = re.findall(r'https://www.zhihu.com/video/\d+',raw_content)
        # print(img_urls)
        # img_urls += re.findall(r'.*', au)
        # print(img_urls)
        #查找并下载作者头像
        if(au != ""):
            img_urls.append(au)
        # print(img_urls)
        img_local_map = {}
        video_local_map = {}
        for img_url in img_urls:
            local_path = download_image(img_url, content_folder)
            if local_path:
                img_local_map[img_url] = local_path

        # 替换普通图片路径
        for img_url, local_path in img_local_map.items():
            raw_content = raw_content.replace(img_url, local_path)
            if(img_url == au):
                au = au.replace(au,local_path)

        for video_url in video_urls:
            local_path = download_video(get_video_urls(video_url), content_folder)
            if local_path:
                video_local_map[video_url] = local_path

        for video_url, local_path in video_local_map.items():
            raw_content = raw_content.replace(video_url, local_path)

        # 更新 JSON
        content["content"] = raw_content
        content["author"]["avatar_url"] = au
        item["content"] = content

    print(x)
    return processed_data, question_title


#******************************************获取参考文献相关链接*********************************************
def extract_and_replace_references(html_text):
    soup = BeautifulSoup(html_text, "html.parser")
    references = []

    for ref in soup.find_all("sup", attrs={"data-url": True}):
        numero = ref.get("data-numero", "").strip()  # 获取编号
        url = ref.get("data-url", "").strip()  # 获取链接
        text = ref.get("data-text", "").strip()  # 获取说明文字（可能为空）

        reference_text = f"{text} {url}" if text else url
        references.append((numero, reference_text))

        new_tag = soup.new_tag("a", href=url, target="_blank", 
                               style="font-size: 0.75em; vertical-align: super; color: inherit; text-decoration: none;")
        new_tag.string = f"[{numero}]"
        ref.replace_with(new_tag)  

    if references:
        reference_section = soup.new_tag("div")  
        reference_section.append(soup.new_tag("h2"))
        reference_section.h2.string = "参考"  

        reference_list = soup.new_tag("ol", style="padding-left: 20px; font-size: 0.9em; line-height: 1.5;")  
        for numero, text in sorted(references, key=lambda x: int(x[0])):
            li = soup.new_tag("li", style="margin-bottom: 3px;")  
            
            ref_text = text.rsplit(" ", 1)  
            description = ref_text[0] if len(ref_text) > 1 else ""  
            link_url = ref_text[-1]  

            if description:
                li.append(soup.new_tag("span", style="color: inherit;"))  
                li.span.string = f"^ {description} "

            link = soup.new_tag("a", href=link_url, target="_blank", 
                                style="text-decoration: underline; color: inherit;")
            link.string = link_url
            li.append(link)

            reference_list.append(li)

        reference_section.append(reference_list)
        soup.append(reference_section)  

    return str(soup)


#******************************************完全更新视频相关链接*********************************************
def update_video_links(html_text):
    soup = BeautifulSoup(html_text, 'html.parser')

    for a_tag in soup.find_all('a', {'class': 'video-box'}):
        video_path = a_tag.find('span', class_='url').text.strip()
        video_tag = soup.new_tag('video', controls=True, width="640", height="360")
        video_source = soup.new_tag('source', src=video_path, type="video/mp4")
        video_tag.append(video_source)
        a_tag.clear()
        a_tag.append(video_tag)

    return str(soup)


#******************************************生成最终的知乎html**********************************************
def generate_zhihu_html(json_data, output_file='zhihu_output.html'):
    html_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>知乎内容聚合</title>
    
    <script src="https://polyfill.alicdn.com/v3/polyfill.min.js?features=es6"></script>
    <!-- KaTeX CDN -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.15.2/dist/katex.min.css">
    <script src="https://cdn.jsdelivr.net/npm/katex@0.15.2/dist/katex.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/katex@0.15.2/dist/contrib/auto-render.min.js"></script>
    
    <style>
        :root {{
            --zhihu-blue: #0084ff;
            --zhihu-gray: #8590a6;
            --border-color: #f0f2f7;
        }}
        figcaption {{
            text-align: center;     
            color: gray;            
            font-size: 0.9em;      
            margin-top: 5px;        
        }}
   
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            max-width: 688px;
            margin: 0 auto;
            padding: 20px 16px;
            line-height: 1.67;
            color: #1a1a1a;
            background: #ffffff;
        }}
        .question-title {{
            font-size: 22px;
            font-weight: 600;
            margin: 0 0 20px 0;
            line-height: 1.3;
            color: #1a1a1a;
        }}
        .author-info {{
            display: flex;
            align-items: center;
            margin-bottom: 12px;
        }}
        .author-avatar {{
            width: 32px;
            height: 32px;
            border-radius: 50%;
            object-fit: cover;
            border: 1px solid #f0f0f0;
            margin-right: 8px;
        }}
        .content {{
            font-size: 15px;
            line-height: 1.67;
            overflow-wrap: break-word;
        }}
        .content img {{
            max-width: 100% !important;
            height: auto !important;
            border-radius: 4px;
            margin: 12px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            vertical-align: middle;
        }}
        .divider {{
            height: 1px;
            background: var(--border-color);
            margin: 24px 0;
        }}
        .footer-info {{
            display: flex;
            align-items: center;
            color: var(--zhihu-gray);
            font-size: 14px;
            margin-top: 16px;
        }}
        .vote-btn {{
            color: var(--zhihu-blue);
            margin-right: 20px;
        }}
        .eqn-num {{
             display: none !important; 
        }}
        blockquote {{
            background-color: #f8f8f8;
            border-left: 4px solid #ccc;
            padding: 10px 15px;
            margin: 10px 0;
            font-style: normal;
            color: #333;
            line-height: 1.6;
            text-align: left; /* 保持左对齐的标号 */
            font-size: 1em;
            max-width: 100%;
            word-wrap: break-word;
            white-space: normal;
        }}

        .katex-display {{
            display: block;
            text-align: right; /* 右对齐公式 */
            margin-top: 0;
            max-width: 100%;
        }}    
        mjx-container[display="true"] {{
            text-align: left !important; /* 左对齐 */
            display: block;
        }}
        pre {{
            background: #f5f5f5;
            color: #2d2d2d;
            padding: 12px;
            border-radius: 6px;
            font-family: 'Fira Code', 'Source Code Pro', 'Roboto Mono', monospace;
            font-size: 16px;
            font-weight: 1000;
            overflow-x: auto;
            line-height: 1.6;
            border: 1px solid #ddd;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            white-space: pre;
            word-wrap: normal;
            overflow-wrap: normal;
        }}

        pre.code {{
            white-space: pre;
            overflow-x: auto;
            background: #f5f5f5;
            word-wrap: break-word; 
            word-break: break-word;
            font-family: 'Fira Code', 'Source Code Pro', 'Roboto Mono', monospace;
        }}

        code:not(pre code) {{
            overflow-x: auto;
            background: #f5f5f5;
            word-wrap: break-word; 
            word-break: break-word;
            font-family: 'Fira Code', 'Source Code Pro', 'Roboto Mono', monospace;
        }}

        .token.keyword {{
            color: #d73a49;
            font-weight: bold;
        }}

        .token.function {{
            color: #005cc5;
            font-weight: bold;
        }}

        .token.string {{
            color: #22863a;
        }}

        .token.operator {{
            color: #6f42c1;
        }}

        .token.comment {{
            color: #6a737d;
            font-style: italic;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            color: #333;
        }}
        th {{
            background-color: #f5f5f5;
            color: #555;
            text-align: left;
            padding: 10px 15px;
            font-weight: bold;
            border: 1px solid #ddd;
        }}
        td {{
            padding: 10px 15px;
            border: 1px solid #ddd;
            text-align: left;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}

        tr:nth-child(odd) {{
            background-color: #fff;
        }}
        tr:hover {{
            background-color: #f1f1f1;
        }}

        table, th, td {{
            border: 1px solid #ddd;
            border-collapse: collapse;
        }}
        @media (max-width: 768px) {{
            table {{
                display: block;
                overflow-x: auto;
                white-space: nowrap;
            }}

            th, td {{
                white-space: nowrap;
            }}
        }}

    </style>
</head>
<body>

    {content_body}

    <script>
        // KaTeX configuration
        window.MathJax = {{
            loader: {{load: ['input/tex', 'output/svg']}},
            options: {{
                enableMenu: false
            }},
            tex: {{
                packages: {{'[+]': ['physics']}},
            }}
        }};
    </script>
    <script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/prismjs@1.24.1/prism.min.js"></script>
    <script>
        document.addEventListener("DOMContentLoaded", function() {{
            Prism.highlightAll();
        }}),
    </script>

</body>
</html>
"""

    # def process_content(raw_content):
    #     """深度处理内容结构"""
    #     def recursive_process(item):
    #         if isinstance(item, dict):
    #             # 处理富文本对象
    #             if item.get('type') == 'text':
    #                 return item.get('content', '')
    #             elif item.get('type') == 'image':
    #                 return f'<img src="{item.get("url")}" loading="lazy">'
    #             elif item.get('type') == 'code':
    #                 return f'<pre class="code-block"><code class="language-{item.get("lang", "")}">{item.get("content")}</code></pre>'
    #             return ''
    #         elif isinstance(item, list):
    #             return ''.join(recursive_process(i) for i in item)
    #         return str(item).replace('', '<pre class="code-block"><code>').replace('', '</code></pre>')

    #     return recursive_process(raw_content)

    content_body = []
    data_list = json_data.get('data', [])
    
    for idx, item in enumerate(data_list):
        content = item.get('content', {})
        
        # 问题标题处理
        question = content.get("question", {}).get("title", "未知标题")
        if(question == "未知标题"):
            question = content.get("title", "未知标题")
        if(question == "未知标题"):
            question = content.get("excerpt_title","未知标题")
        question_html = f'<div class="question-title">{question}</div>' if question else ''
        
        # 作者信息处理
        author = content.get('author', {})
        author_html = f'''
        <div class="author-info">
            <img src="{author.get('avatar_url', '')}" 
                 class="author-avatar"
                 alt="{author.get('name', '匿名用户')}">
            <div>
                <div style="font-weight:500;color:#1a1a1a">{author.get('name', '匿名用户')}</div>
                <div style="color:var(--zhihu-gray);font-size:14px;">
                    {author.get('headline', '')}
                </div>
            </div>
        </div>
        '''
        
        # 内容处理
        # processed_content = process_content(content.get('content', ''))
        processed_content = content.get('content','')
        processed_content = extract_and_replace_references(processed_content)
        processed_content = update_video_links(processed_content)
        # 底部信息
        voteup_count = content.get('voteup_count', 0)
        try:
            created_time = datetime.fromtimestamp(content.get('created_time', 0)).strftime('%Y-%m-%d %H:%M')
        except:
            created_time = ''
        
        # 构建卡片
        card = f'''
        <div class="answer-card">
            {question_html}
            {author_html}
            <div class="content">
                {processed_content}
            </div>
            <div class="footer-info">
                <span class="vote-btn">▲ {voteup_count} 赞同</span>
                <span>{created_time}</span>
            </div>
        </div>
        '''
        
        content_body.append(card)
        if idx < len(data_list) - 1:
            content_body.append('<div class="divider"></div>')

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_template.format(content_body='\n'.join(content_body)))
    
    return f"生成成功：{output_file}"



# 收藏夹的编号
collections=str(1)
# 从第几页文章开始
start=2
start*=20
# 第几页文章结束              
end=4
end*=20
name_=str("mama")

# 时间获取（似乎不是太重要？）
now_time = int(time.time())
timeArray = time.localtime(now_time)
otherStyleTime = str(time.strftime("%Y-%m-%d %H:%M:%S", timeArray))


#******************************************进行处理，生成最终html**********************************************
for x in range(int(start)+1,int(end)+1):
    url=f"https://www.zhihu.com/api/v4/collections/{collections}/items?offset={str((int(x))*1)}&limit=1"
    headers={
        "refer":f"https://www.zhihu.com/collection/{collections}",
        "user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36"
    }
    res=requests.get(url=url,headers=headers,cookies=cookies).text
    with open("data.json","w",encoding="utf-8") as f:
        f.write(res)
    # print(res)  
    save_folder = ".\\folder\\"
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)
    parse = json.loads(res)
    modified, title = process_zhihu_json(parse,x)
    # print(modified)
    # print(parse)
    generate_zhihu_html(modified,save_folder+str(x)+"_"+str(title)+".html")