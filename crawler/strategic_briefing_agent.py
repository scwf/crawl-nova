"""
strategic_briefing_agent.py - 首席战略情报官 Agent

功能：
- 基于data目录下的情报报告，生成面向产品管理团队的战略分析简报
- 提炼关键趋势、商业洞察和战略建议

依赖：openai
"""
import os
import re
import configparser
from datetime import datetime
from openai import OpenAI
from common import load_batch_manifest, get_domain_report_paths

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


def find_domain_reports(data_dir: str) -> dict:
    """
    从清单文件读取最新一批的领域报告
    
    返回：
        dict: {领域名称: 报告文件路径}
    
    异常：
        FileNotFoundError: 清单文件不存在或无有效领域报告
    """
    manifest = load_batch_manifest(data_dir)
    if not manifest:
        raise FileNotFoundError(f"在 {data_dir} 目录下没有找到批次清单文件 (latest_batch.json)")
    
    log(f"从清单文件读取批次: {manifest.get('batch_id', 'unknown')}")
    domain_reports = get_domain_report_paths(data_dir, manifest)
    
    if not domain_reports:
        raise FileNotFoundError(f"清单文件中没有有效的领域报告")
    
    return domain_reports


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


# ================= 领域专属提示词配置 =================
DOMAIN_PROMPTS = {
    "大模型技术和产品": {
        "focus": "大语言模型技术发展、模型能力评测、训练技术突破、推理优化、多模态能力、开源模型动态",
        "keywords": "模型参数、上下文长度、推理速度、训练成本、Benchmark评测、开源vs闭源、模型架构",
        "competitors": "OpenAI、Anthropic、Google DeepMind、Meta AI、Mistral、阿里通义、百度文心、字节豆包、DeepSeek、Kimi、MiniMax、Qwen"
    },
    "数据平台和框架": {
        "focus": "数据基础设施、数据湖仓、实时数据处理、ETL/ELT、数据治理、数据目录、数据质量",
        "keywords": "Lakehouse、Delta Lake、Iceberg、Hudi、Spark、Flink、Kafka、数据血缘、数据资产",
        "competitors": "Databricks、Snowflake、阿里云MaxCompute、字节火山引擎、AWS、Google BigQuery"
    },
    "AI平台和框架": {
        "focus": "MLOps平台、模型训练框架、模型服务部署、特征工程、实验管理、模型监控、模型推理、强化学习、模型微调",
        "keywords": "PyTorch、TensorFlow、Ray、vLLM、MLflow、Kubeflow、模型推理、GPU调度、分布式训练",
        "competitors": "PAI、百炼、方舟、火山机器学习平台、Anyscale、火山引擎、SageMaker、Vertex AI"
    },
    "智能体平台和框架": {
        "focus": "AI Agent框架、多智能体协作、工具调用、记忆系统、规划与推理、Agent编排",
        "keywords": "LangChain、LlamaIndex、AutoGPT、CrewAI、Agent协议、Function Calling、ReAct、CoT",
        "competitors": "LangChain、LlamaIndex、Microsoft AutoGen、OpenAI Assistants API、Anthropic Claude"
    },
    "代码智能体（IDE）": {
        "focus": "AI代码助手、代码生成、代码补全、代码审查、IDE集成、开发者体验",
        "keywords": "Copilot、Cursor、代码生成准确率、上下文理解、多文件编辑、Terminal集成",
        "competitors": "GitHub Copilot、Cursor、Windsurf、Amazon CodeWhisperer、Tabnine、通义灵码"
    },
    "数据智能体": {
        "focus": "数据分析Agent、Text-to-SQL、自动化报表、数据洞察生成、对话式BI",
        "keywords": "自然语言查询、数据可视化、自动分析、数据故事、BI智能化",
        "competitors": "Tableau、PowerBI、ThoughtSpot、阿里DataWorks、字节DataLeap"
    },
    "行业或领域智能体": {
        "focus": "垂直领域AI应用、行业解决方案、领域大模型、专业知识库",
        "keywords": "医疗AI、法律AI、金融AI、教育AI、企业知识管理、RAG应用",
        "competitors": "各行业领先玩家和垂直领域AI创业公司"
    },
    "具身智能": {
        "focus": "机器人AI、自动驾驶、物理世界交互、传感器融合、运动控制",
        "keywords": "机器人大模型、世界模型、Sim-to-Real、端到端控制、多模态感知",
        "competitors": "Tesla、Figure、1X、Boston Dynamics、宇树科技、智元机器人"
    },
    "其他": {
        "focus": "通用技术趋势、行业动态、政策法规、投融资事件",
        "keywords": "AI治理、开源生态、技术社区、行业会议、人才动向",
        "competitors": "各领域主要玩家"
    }
}


def get_domain_system_prompt(domain: str) -> str:
    """
    获取领域专属的系统提示词
    """
    domain_info = DOMAIN_PROMPTS.get(domain, DOMAIN_PROMPTS["其他"])
    
    return f"""你是一位专注于【{domain}】领域的首席战略情报官（Chief Strategy Intelligence Officer），
服务于一家科技公司的产品管理团队。你的职责是将该领域的技术情报转化为战略洞察，帮助产品管理团队做出数据驱动的决策。

领域专业背景：
- 核心关注点：{domain_info['focus']}
- 关键术语：{domain_info['keywords']}
- 主要竞争者：{domain_info['competitors']}

你的分析风格：
- 简洁有力，直击要点
- 战略视角，关注业务影响
- 数据支撑，引用具体案例
- 前瞻性思维，预判趋势演变
- 可操作性强，提供明确建议
- 突出该领域的专业深度"""


def generate_domain_briefing(domain: str, report_content: str) -> str:
    """
    生成领域专属的战略简报
    
    参数：
        domain: 领域名称
        report_content: 该领域的情报报告内容
        
    返回：
        str: 领域战略分析简报
    """
    system_prompt = get_domain_system_prompt(domain)
    
    user_prompt = f"""请基于以下【{domain}】领域的情报数据，生成一份面向产品管理团队的战略分析简报。

## 输出格式要求

请严格按照以下Markdown格式输出：

```markdown
# 📊 {domain} 领域战略情报简报

**报告日期**: [今日日期]  
**情报周期**: [情报覆盖的时间范围]  

---

## 🎯 核心要点速览

> [用3-5个要点概括本期该领域最重要的战略信息，每个要点一句话]

---

## 🔥 本期热点事件

### 重大事件 TOP 3
[列出本期该领域最重要的3个事件，每个事件包含：]
1. **事件名称**
   - 事件描述
   - 影响评估
   - 对我们的机会/风险

---

## 📈 领域趋势洞察

### 技术演进
[2-3个该领域的关键技术趋势]

### 市场格局
[该领域的市场动态和竞争态势变化]

### 产品创新
[值得关注的产品创新和用户体验趋势]

---

## 🎯 战略建议

### 短期行动项（1-4周）
1. [针对该领域的具体可执行建议]
2. [针对该领域的具体可执行建议]

### 中期布局（1-3个月）
1. [该领域需要持续投入的方向]
2. [该领域需要持续投入的方向]

---

## ⚠️ 风险与挑战

[列出该领域2-3个需要关注的风险点或技术挑战]

---

## 📎 重点情报索引

[列出3-5条该领域值得深入阅读的原始情报]
```

---

## 原始情报数据

{report_content}
"""

    log(f"正在生成【{domain}】领域战略简报...")
    
    # 处理内容长度
    processed_content = process_report_content(report_content)
    if processed_content != report_content:
        user_prompt = user_prompt.replace(report_content, processed_content)
    
    response = client.chat.completions.create(
        model=config.get('llm', 'model'),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=6000
    )
    
    return response.choices[0].message.content.strip()


def generate_cross_domain_briefing(domain_briefings: dict) -> str:
    """
    生成跨领域综合战略简报
    
    参数：
        domain_briefings: {领域名称: 领域简报内容}
        
    返回：
        str: 跨领域综合战略简报
    """
    system_prompt = """你是一位首席数据&AI战略情报官（Chief Data & AI Strategy Intelligence Officer），
服务于一家科技公司的产品管理团队。你的职责是整合各个技术领域的情报，提供跨领域的战略视角，
帮助产品管理团队理解技术趋势的全貌并做出前瞻性决策。

你的分析风格：
- 全局视角，把握技术发展大势
- 跨领域洞察，发现技术融合机会
- 战略高度，关注长期布局
- 可操作性强，提供明确优先级建议"""

    # 构建各领域摘要
    domain_summaries = []
    for domain, briefing in domain_briefings.items():
        # 提取每个领域简报的核心要点部分
        domain_summaries.append(f"### {domain}\n{briefing}")
    
    combined_briefings = "\n\n---\n\n".join(domain_summaries)
    
    user_prompt = f"""请基于以下各领域的战略情报简报，生成一份跨领域的综合战略分析报告。

## 输出格式要求

请严格按照以下Markdown格式输出：

```markdown
# 📊 Data&AI 综合战略情报简报

**报告日期**: [今日日期]  
**情报周期**: [情报覆盖的时间范围]  
**编制**: 首席战略情报官

---

## 🎯 全局战略要点

> [用5-7个要点概括本期最重要的跨领域战略信息，每个要点标注所属领域]

---

## 🌐 跨领域趋势分析

### 技术融合趋势
[识别2-3个正在发生的跨领域技术融合趋势，说明其战略意义]

### 产业链演进
[分析技术栈上下游的演进趋势，从底层基础设施到上层应用]

### 生态格局变化
[主要科技巨头和创业公司在各领域的布局变化]

---

## 🔥 本期最重要事件 TOP 5

[从所有领域中选出最重要的5个事件，说明其跨领域影响]

---

## 🎯 综合战略建议

### 优先投入领域
[根据各领域动态，建议当前应优先投入的1-2个领域及理由]

### 技术栈布局建议
[从全栈视角，建议如何构建技术能力组合]

### 短期行动项（1-4周）
1. [跨领域的具体可执行建议]
2. [跨领域的具体可执行建议]
3. [跨领域的具体可执行建议]

### 中长期布局（1-6个月）
1. [战略层面的布局建议]
2. [战略层面的布局建议]

---

## ⚠️ 综合风险评估

### 技术风险
[跨领域的技术风险点]

### 市场风险
[市场层面的风险点]

### 竞争风险
[竞争格局层面的风险点]

---

## 📊 各领域热度评估

| 领域 | 本期热度 | 趋势 | 关注优先级 |
|------|----------|------|------------|
[为每个领域评估热度(高/中/低)、趋势(↑/→/↓)和关注优先级(P0/P1/P2)]

```

---

## 各领域情报简报

{combined_briefings}
"""

    log("正在生成跨领域综合战略简报...")
    
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


def save_briefing(briefing: str, output_dir: str, domain: str = None) -> str:
    """
    保存战略简报
    
    参数：
        briefing: 简报内容
        output_dir: 输出目录
        domain: 领域名称（可选，用于生成文件名）
    
    返回：
        str: 保存的文件路径
    """
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    if domain:
        # 生成安全的文件名
        safe_domain = "".join(c if c.isalnum() or c in ('-', '_', '（', '）') else '_' for c in domain)
        filename = f"executive_briefing_{safe_domain}_{timestamp}.md"
    else:
        filename = f"executive_briefing_{timestamp}.md"
    
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(briefing)
    
    return filepath


# ================= 主程序入口 =================
def main():
    """主函数：执行战略情报分析流程（按领域分别生成简报）"""
    import time
    start_time = time.time()
    
    print("\n" + "="*60)
    print("🎖️  首席战略情报官 Agent 启动")
    print("="*60 + "\n")
    
    # 1. 定位数据目录
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    log(f"数据目录: {os.path.abspath(data_dir)}")
    
    # 2. 查找最新一批的领域报告
    try:
        domain_reports = find_domain_reports(data_dir)
        log(f"找到 {len(domain_reports)} 个领域报告:")
        for domain, path in domain_reports.items():
            log(f"  - {domain}: {os.path.basename(path)}")
    except FileNotFoundError as e:
        log(f"错误: {e}")
        return
    
    # 3. 为每个领域生成专属简报
    domain_briefings = {}
    saved_files = []
    
    for domain, report_path in domain_reports.items():
        log(f"\n{'='*40}")
        log(f"📂 处理领域: {domain}")
        log(f"{'='*40}")
        
        # 读取领域报告内容
        report_content = read_report(report_path)
        log(f"报告内容已加载，共 {len(report_content)} 字符")
        
        # 生成领域专属简报
        briefing = generate_domain_briefing(domain, report_content)
        domain_briefings[domain] = briefing
        
        # 保存领域简报
        output_path = save_briefing(briefing, data_dir, domain)
        saved_files.append((domain, output_path))
        log(f"✅ 【{domain}】简报已保存: {os.path.basename(output_path)}")
    
    # 4. 生成跨领域综合战略简报
    if len(domain_briefings) > 1:
        log(f"\n{'='*40}")
        log("🌐 生成跨领域综合战略简报")
        log(f"{'='*40}")
        
        cross_domain_briefing = generate_cross_domain_briefing(domain_briefings)
        output_path = save_briefing(cross_domain_briefing, data_dir, "综合战略")
        saved_files.append(("综合战略", output_path))
        log(f"✅ 综合战略简报已保存: {os.path.basename(output_path)}")
    
    # 5. 打印执行结果摘要
    print("\n" + "="*60)
    print("📊 执行结果摘要")
    print("="*60)
    print(f"处理领域数量: {len(domain_reports)}")
    print(f"生成简报数量: {len(saved_files)}")
    print("\n生成的简报文件:")
    for domain, path in saved_files:
        print(f"  - [{domain}] {os.path.basename(path)}")
    
    # 6. 打印执行时间
    elapsed_time = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"✅ 执行完成，总耗时: {elapsed_time:.2f} 秒")
    print("="*60)


if __name__ == "__main__":
    main()
