# Project TODOs

## User Experience & Interaction (用户体验与交互)

- [ ] **Configurable Prompts (Prompt 模版化与配置)**
  - **目前的状况**: Prompt 硬编码在 `llm_organizer.py` 中。
  - **改进方案**: 将 Prompt 提取到外部文件（如 `prompts/organizer_prompt.md`）或配置文件中。这样用户可以在不修改代码的情况下，调整 AI 的“人设”或关注点（比如从“AI技术专家”改为“投资分析师”）。

- [ ] **Interactive Review (交互式审核)**
  - **目前的状况**: 全自动流水线，结果好坏全看 LLM。
  - **改进方案**: 在 `Writer` 之前增加一个 CLI 交互环节或简单的 Web UI，列出 LLM 整理好的条目，允许人工进行 `Keep/Delete/Edit` 操作，然后再生成最终报告。

## Consumption Experience (沉浸式消费体验)

- [ ] **AI Audio Briefing (AI 播客生成)**
  - **痛点**: 用户没时间阅读长文报告。
  - **功能**: 将 Markdown 报告转化为 5-10 分钟的 AI 播客（单人播报或双人对话），支持通勤场景收听。

- [ ] **Knowledge Base Sync (Notion/Obsidian 集成)**
  - **痛点**: 情报缺乏沉淀，难以二次利用。
  - **功能**: 支持自动同步结构化数据到 Notion Database 或生成 Obsidian 兼容的 Markdown 笔记。

## Accessibility & Ecosystem (极简易用与生态)

- [ ] **Curated Source Packs (预置情报包)**
  - **痛点**: 寻找高质量 RSS 源门槛高。
  - **功能**: 提供开箱即用的订阅包（如 `Crypto Pack`, `Indie Hacker Pack`, `Finance Pack`），用户一键启用。

- [ ] **Visual Web Dashboard (Web 控制台)**
  - **痛点**: 命令行工具劝退非技术用户。
  - **功能**: 基于 Streamlit/Gradio 提供图形化界面，支持订阅管理、手动触发抓取、历史报告浏览。

## Deep Intelligence (深度智能)

- [ ] **Chat with Intel (RAG 问答)**
  - **功能**: 基于历史抓取数据构建本地知识库，允许用户通过自然语言查询（如“总结上个月关于 DeepSeek 的所有动态”）。

- [ ] **Customizable Personas (个性化分析师人格)**
  - **功能**: 允许用户配置 AI 的关注侧重（如 VC模式、工程师模式、猎头模式），从不同角度解读同一份情报。

## Strategic & Analytic Intelligence (战略与深度分析)

- [ ] **Event Timeline & Context Linking (事件脉络自动追踪)**
  - **痛点**: 信息碎片化，看不清事件的前因后果。
  - **功能**: Agent 在处理新情报时，自动检索历史向量库，生成“相关背景”小节（例如：“此事件是 [2周前某事件] 的后续发展”），将离散新闻串联成连续的故事线。

- [ ] **360° Community Sentiment (全景舆情分析)**
  - **痛点**: 官方通稿往往报喜不报忧，缺乏客观的市场反馈。
  - **功能**: 抓取 X/Reddit/HackerNews 的高赞评论，分析社区的真实态度（如“技术虽强但定价被吐槽”），提供客观的第三方视角。

## Visual & Actionable (可视化与行动转化)

- [ ] **Auto-Generated Mindmap (自动思维导图/图谱)**
  - **痛点**: 纯文本报告在展示复杂行业格局时不够直观。
  - **功能**: 自动生成 Mermaid.js 或 Graphviz 代码，绘制本周的“行业关系图”或“技术演进时间轴”，提供上帝视角。

- [ ] **Content Repurposing Agent (一键内容转写)**
  - **痛点**: 看完情报后，需要手动再创作才能分享。
  - **功能**: 提供“转写”指令，将选中的情报转化为不同平台的内容（如“基于这三条新闻写一篇 LinkedIn 深度评论”或“生成 Twitter Thread”）。
