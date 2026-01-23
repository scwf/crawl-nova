"""
strategic_briefing_agent.py - 首席战略情报官 Agent

功能：
- 基于data目录下的情报报告，生成面向产品管理团队的战略分析简报
- 提炼关键趋势、商业洞察和战略建议

依赖：openai
"""
import os
import re
import glob
import configparser
from datetime import datetime
from openai import OpenAI

# ================= 配置加载 =================
config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), '..', 'config.ini'), encoding='utf-8')

client = OpenAI(
    api_key=config.get('llm', 'api_key'),
    base_url=config.get('llm', 'base_url')
)


def log(message):
    """带时间戳的日志输出"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")


def find_latest_report(data_dir: str) -> str:
    """
    查找data目录下最新的情报报告
    
    返回：
        str: 最新报告的完整路径
    """
    pattern = os.path.join(data_dir, "*.md")
    reports = glob.glob(pattern)
    
    if not reports:
        raise FileNotFoundError(f"在 {data_dir} 目录下没有找到任何情报报告")
    
    # 按修改时间排序，获取最新的
    latest_report = max(reports, key=os.path.getmtime)
    return latest_report


def read_report(report_path: str) -> str:
    """读取情报报告内容"""
    with open(report_path, 'r', encoding='utf-8') as f:
        return f.read()


def split_report_by_source(report_content: str) -> list:
    """
    按来源分割报告内容
    
    返回：
        list: [(来源名称, 内容), ...]
    """
    # 按 ### 标题分割（每个来源一个section）
    sections = re.split(r'\n### ', report_content)
    
    result = []
    for section in sections:
        if not section.strip():
            continue
        # 提取来源名称（第一行）
        lines = section.split('\n', 1)
        source_name = lines[0].strip()
        content = lines[1] if len(lines) > 1 else ""
        if content.strip():
            result.append((source_name, content))
    
    return result


def summarize_section(source_name: str, content: str) -> str:
    """
    对单个来源的内容进行摘要提取
    
    参数：
        source_name: 来源名称
        content: 该来源的完整内容
        
    返回：
        str: 关键信息摘要
    """
    prompt = f"""请从以下【{source_name}】的情报内容中，提取最重要的信息点。

要求：
1. 保留所有重大事件、技术发布、产品动态、商业资讯
2. 每条信息用一行概括，格式：[分类] 事件描述
3. 过滤掉广告招聘、无实质内容的条目
4. 保留原文中的关键数据和细节

内容：
{content}

请直接输出摘要列表，不要其他解释："""

    try:
        response = client.chat.completions.create(
            model=config.get('llm', 'model'),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000
        )
        return f"### {source_name}\n{response.choices[0].message.content.strip()}"
    except Exception as e:
        log(f"摘要 {source_name} 时出错: {e}")
        return f"### {source_name}\n[摘要失败]"


def process_report_content(report_content: str, max_length: int = 60000) -> str:
    """
    智能处理报告内容，确保完整覆盖所有情报
    
    策略：
    - 如果内容在限制内，直接返回
    - 如果超长，分段摘要后合并
    
    参数：
        report_content: 完整报告内容
        max_length: 单次请求的最大字符长度
        
    返回：
        str: 处理后的内容
    """
    if len(report_content) <= max_length:
        log(f"报告内容 {len(report_content)} 字符，直接处理")
        return report_content
    
    log(f"报告内容较长({len(report_content)}字符)，启用分段摘要模式...")
    
    # 分段处理
    sections = split_report_by_source(report_content)
    log(f"共分割为 {len(sections)} 个来源段落")
    
    # 对每个来源进行摘要
    summaries = []
    for i, (source_name, content) in enumerate(sections):
        log(f"  [{i+1}/{len(sections)}] 摘要: {source_name}")
        summary = summarize_section(source_name, content)
        summaries.append(summary)
    
    # 合并摘要
    combined = "# 情报摘要汇总\n\n" + "\n\n".join(summaries)
    log(f"摘要完成，合并后 {len(combined)} 字符")
    
    return combined


def generate_executive_briefing(report_content: str) -> str:
    """
    调用LLM生成高管战略简报
    
    参数：
        report_content: 情报报告内容
        
    返回：
        str: 战略分析简报
    """
    system_prompt = """你是一位首席数据&AI战略情报官（Chief Data & AI Strategy Intelligence Officer），
服务于一家科技公司的高管团队。你的职责是将技术情报转化为战略洞察，帮助高管团队做出数据驱动的决策。

你的分析风格：
- 简洁有力，直击要点
- 战略视角，关注业务影响
- 数据支撑，引用具体案例
- 前瞻性思维，预判趋势演变
- 可操作性强，提供明确建议"""

    user_prompt = f"""请基于以下Data&AI领域的情报周报，生成一份面向高管团队的战略分析简报。

## 输出格式要求

请严格按照以下Markdown格式输出：

```markdown
# 📊 首席数据&AI战略情报简报

**报告日期**: [今日日期]  
**情报周期**: [情报覆盖的时间范围]  
**编制**: AI战略情报官

---

## 🎯 核心要点速览（Executive Summary）

> [用3-5个要点概括本期最重要的战略信息，每个要点一句话]

---

## 🔥 本期热点追踪

### 重大事件 TOP 3
[列出本期最重要的3个事件，每个事件包含：事件名称、影响评估、我们的机会/风险]

---

## 📈 趋势洞察

### 技术趋势
[2-3个关键技术趋势，包含趋势描述和战略启示]

### 市场动态
[2-3个市场层面的重要动向]

### 竞争格局
[主要玩家的动态和竞争态势变化]

---

## 🎯 战略建议

### 短期行动项（1-4周）
1. [具体可执行的行动建议]
2. [具体可执行的行动建议]

### 中期关注（1-3个月）
1. [需要持续跟踪的方向]
2. [需要持续跟踪的方向]

### 长期布局（3-12个月）
1. [战略层面的布局建议]
2. [战略层面的布局建议]

---

## ⚠️ 风险预警

[列出2-3个需要高管团队关注的潜在风险点]

---

## 📎 附录：重点情报索引

[按重要性列出5-8条值得深入阅读的原始情报标题和简要说明]
```

---

## 原始情报数据

{report_content}
"""

    log("正在生成战略分析简报...")
    
    response = client.chat.completions.create(
        model=config.get('llm', 'model'),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=8000
    )
    
    return response.choices[0].message.content.strip()


def save_briefing(briefing: str, output_dir: str) -> str:
    """
    保存战略简报
    
    返回：
        str: 保存的文件路径
    """
    os.makedirs(output_dir, exist_ok=True)
    
    filename = f"executive_briefing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(briefing)
    
    return filepath


# ================= 主程序入口 =================
def main():
    """主函数：执行战略情报分析流程"""
    import time
    start_time = time.time()
    
    print("\n" + "="*60)
    print("🎖️  首席战略情报官 Agent 启动")
    print("="*60 + "\n")
    
    # 1. 定位数据目录
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    log(f"数据目录: {os.path.abspath(data_dir)}")
    
    # 2. 查找最新报告
    try:
        latest_report = find_latest_report(data_dir)
        log(f"找到最新情报报告: {os.path.basename(latest_report)}")
    except FileNotFoundError as e:
        log(f"错误: {e}")
        return
    
    # 3. 读取报告内容
    report_content = read_report(latest_report)
    log(f"报告内容已加载，共 {len(report_content)} 字符")
    
    # 4. 处理报告内容（完整覆盖，不截取）
    key_content = process_report_content(report_content)
    
    # 5. 生成战略简报
    briefing = generate_executive_briefing(key_content)
    
    # 6. 保存简报
    output_path = save_briefing(briefing, data_dir)
    log(f"战略简报已保存至: {output_path}")
    
    # 7. 打印简报
    print("\n" + "="*60)
    print("📊 战略分析简报")
    print("="*60 + "\n")
    print(briefing)
    
    # 8. 打印执行时间
    elapsed_time = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"✅ 执行完成，总耗时: {elapsed_time:.2f} 秒")
    print("="*60)


if __name__ == "__main__":
    main()
