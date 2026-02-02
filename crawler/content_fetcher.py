"""
content_fetcher.py - 嵌入内容爬取模块

功能：
- 从文本中提取博客和YouTube链接
- 爬取博客页面正文内容
- 获取YouTube视频字幕和元数据

设计原则：
- 单一职责：每个类只负责一种类型的内容获取
- 易于扩展：新增内容类型只需添加新的Fetcher类
- 解耦清晰：rss_crawler.py 只需调用 ContentFetcher，不关心内部实现
"""
import re
from urllib.parse import urlparse, parse_qs
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from common import config, setup_logger

logger = setup_logger("content_fetcher")

@dataclass
class EmbeddedContent:
    """嵌入内容数据结构"""
    url: str
    content_type: str  # 'blog' | 'subtitle'
    title: str = ''
    content: str = ''
    metadata: Dict = field(default_factory=dict)


def _shorten_url(url: str, length: int = 60) -> str:
    """Helper: Truncate long URLs for logging"""
    if not url: return ""
    return url[:length] + "..." if len(url) > length else url



class LinkExtractor:
    """从文本中提取和分类URL"""
    
    # 需要跳过的域名（社交媒体自身的链接，不作为博客处理）
    SKIP_DOMAINS = ['twitter.com', 'x.com', 't.co', 'pic.twitter.com']
    
    # YouTube相关域名
    YOUTUBE_DOMAINS = ['youtube.com', 'youtu.be', 'www.youtube.com', 'm.youtube.com']
    
    # 通用视频域名/扩展名
    VIDEO_DOMAINS = ['video.twimg.com']
    VIDEO_EXTENSIONS = ['.mp4', '.mov', '.webm', '.mkv']
    
    # 媒体资源域名（图片、视频等）
    MEDIA_DOMAINS = ['twimg.com', 'pbs.twimg.com']
    
    @staticmethod
    def extract_urls(text: str) -> List[str]:
        """
        提取文本中的所有URL
        
        参数:
            text: 要解析的文本内容
        
        返回:
            提取到的URL列表
        """
        if not text:
            return []
        
        # URL匹配正则表达式
        pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(pattern, text)
        
        # 去重并保持顺序
        seen = set()
        unique_urls = []
        for url in urls:
            # 清理URL末尾可能的标点符号
            url = url.rstrip('.,;:!?')
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
        
        return unique_urls
    
    @classmethod
    def categorize(cls, text: str) -> Tuple[List[str], List[str], List[str]]:
        """
        分类提取博客链接、视频链接（含YouTube）和媒体链接
        
        参数:
            text: 要解析的文本内容
        
        返回:
            (blog_links, video_links, media_urls) 三元组
        """
        urls = cls.extract_urls(text)
        blog_links = []
        video_links = []
        media_urls = []
        
        for url in urls:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            path = parsed.path.lower()
            
            # 1. 视频链接 (YouTube 或 通用视频)
            is_youtube = any(yt in domain for yt in cls.YOUTUBE_DOMAINS)
            is_generic_video = (
                any(v in domain for v in cls.VIDEO_DOMAINS) or 
                any(path.endswith(ext) for ext in cls.VIDEO_EXTENSIONS)
            )
            
            if is_youtube or is_generic_video:
                video_links.append(url)
            
            # 2. 其他媒体资源链接（图片等）
            elif any(media in domain for media in cls.MEDIA_DOMAINS):
                media_urls.append(url)
            
            # 3. 博客/网页链接 (排除跳过的域名)
            elif domain and not any(skip in domain for skip in cls.SKIP_DOMAINS):
                blog_links.append(url)
        
        return blog_links, video_links, media_urls



class GenericVideoFetcher:
    """通用视频信息获取器 (支持YouTube, Twitter视频等)"""
    
    def _parse_video_info(self, url: str) -> Tuple[Optional[str], str]:
        """
        解析视频信息
        
        返回:
            (video_id, video_url)
            - video_id: 用于文件存储的唯一标识
            - video_url: 用于下载的实际URL
        """
        if not url:
            return None, ""
            
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # === 策略1: YouTube ===
        if any(d in domain for d in ['youtube.com', 'youtu.be']):
            # copy from original extra_video_id logic
            try:
                # youtu.be/ID
                if 'youtu.be' in domain:
                    vid = parsed.path.lstrip('/').split('?')[0]
                    if vid: return vid, f"https://www.youtube.com/watch?v={vid}"
                    
                # youtube.com/watch?v=ID
                if 'youtube.com' in domain:
                    if '/watch' in parsed.path:
                        query = parse_qs(parsed.query)
                        vids = query.get('v', [])
                        if vids: return vids[0], f"https://www.youtube.com/watch?v={vids[0]}"
                    if '/embed/' in parsed.path:
                        parts = parsed.path.split('/embed/')
                        if len(parts) > 1:
                            vid = parts[1].split('/')[0].split('?')[0]
                            return vid, f"https://www.youtube.com/watch?v={vid}"
            except:
                pass
                
        # === 策略2: 通用视频 (基于文件名或哈希) ===
        # 使用URL路径最后一部分作为文件名基础，如果太长或非法则hash
        try:
            filename = os.path.basename(parsed.path)
            if not filename or '.' not in filename:
                # 如果没有明确文件名，使用整个URL的hash
                import hashlib
                video_id = hashlib.md5(url.encode()).hexdigest()[:12]
            else:
                # 清理文件名
                name_part = os.path.splitext(filename)[0]
                safe_name = "".join(c if c.isalnum() else '_' for c in name_part)
                # 加上hash前缀防止重名
                import hashlib
                url_hash = hashlib.md5(url.encode()).hexdigest()[:6]
                video_id = f"{safe_name}_{url_hash}"
                
            return video_id, url
        except:
            return None, ""

    def fetch_transcript(self, video_id: str, video_url: str, context: str = "") -> str:
        """
        获取视频字幕，并保存 srt/txt 到 raw 目录
        
        使用 video_scribe 模块自动处理（下载+转录）
        
        参数:
            video_id: 视频ID (也是目录名)
            video_url: 视频可下载链接
        
        返回:
            视频字幕文本
        """
        import os
        import sys
        
        # 确保能导入 video_scribe
        # video_scribe 在项目根目录， content_fetcher.py 在 crawler/ 目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        if project_root not in sys.path:
            sys.path.append(project_root)
            
        try:
            # 构造输出目录: data/raw/{video_id}/
            output_dir = os.path.join(project_root, 'data', 'raw', video_id)
            os.makedirs(output_dir, exist_ok=True)
            
            logger.info(f"开始转录视频 [ID: {video_id}] -> {output_dir}")
            
            # 调用 video_scribe 处理
            # process_video 会自动保存 .srt, .txt, .json 到 output_dir
            from video_scribe.core import process_video, optimize_subtitle
            
            asr_data = process_video(
                video_url_or_path=video_url,
                output_dir=output_dir,
                device="cuda", # 默认使用CUDA，如果失败 video_scribe 可能会报错，需确保环境
                language=None  # 自动检测
            )
            
            # --- LLM 字幕优化 ---
            final_data = asr_data  # 默认为原始数据
            try:
                logger.info(f"开始优化字幕 [ID: {video_id}]...")
                api_key = config.get('llm', 'api_key')
                base_url = config.get('llm', 'base_url')
                model = config.get('llm', 'model', fallback='deepseek-reasoner')
                
                # 使用视频标题/上下文作为背景信息
                custom_prompt = ""
                if context:
                    custom_prompt = f"视频背景信息: {context}\n请利用此信息来优化字幕。"

                optimized_data = optimize_subtitle(
                    subtitle_data=asr_data,
                    model=model,
                    api_key=api_key,
                    base_url=base_url,
                    custom_prompt=custom_prompt
                )
                
                # 保存优化后的字幕
                save_base = os.path.join(output_dir, f"{video_id}_optimized")
                optimized_data.save(save_base + ".srt")
                optimized_data.save(save_base + ".txt")
                
                final_data = optimized_data
                
            except Exception as opt_e:
                logger.warning(f"字幕优化失败，回退到原始字幕 [ID: {video_id}]: {opt_e}")
                # 即使优化失败，也继续返回原始字幕
            
            # 返回最终文本（优化后或原始）
            return final_data.to_txt()
            
        except Exception as e:
            logger.error(f"视频转录流程严重失败 [ID: {video_id}]: {e}")
            import traceback
            traceback.print_exc()
            return ''
    
    def fetch(self, url: str, context: str = "") -> Optional[EmbeddedContent]:
        """
        获取视频的完整信息
        
        参数:
            url: 视频URL
        
        返回:
            EmbeddedContent对象，如果无法提取则返回None
        """
        video_id, video_url = self._parse_video_info(url)
        if not video_id:
            logger.info(f"无法解析视频信息: {_shorten_url(url)}")
            return None
        
        transcript = self.fetch_transcript(video_id, video_url, context=context)
        
        return EmbeddedContent(
            url=url,
            content_type='subtitle',
            title='',  # 可后续扩展获取标题
            content=transcript,
            metadata={'video_id': video_id, 'video_url': video_url}
        )


class BlogFetcher:
    """博客页面内容获取器（复用Selenium逻辑）"""
    
    # 内容最大长度限制
    MAX_CONTENT_LENGTH = 50000
    
    def fetch(self, url: str) -> Optional[EmbeddedContent]:
        """
        爬取博客页面内容
        
        使用 Selenium 进行动态渲染，复用 web_crawler.py 的逻辑
        
        参数:
            url: 博客页面URL
        
        返回:
            EmbeddedContent对象，如果爬取失败则返回None
        """
        try:
            # 延迟导入，避免不使用时加载 Selenium
            from web_crawler import fetch_web_content
            
            result = fetch_web_content(url)
            
            if result:
                content = result.get('content', '')
                
                # 截断过长内容
                if len(content) > self.MAX_CONTENT_LENGTH:
                    content = content[:self.MAX_CONTENT_LENGTH] + '...'
                
                return EmbeddedContent(
                    url=url,
                    content_type='blog',
                    title=result.get('title', ''),
                    content=content,
                    metadata={
                        'original_length': len(result.get('content', ''))
                    }
                )
            
            logger.info(f"博客爬取返回空结果: {_shorten_url(url)}")
            return None
            
        except Exception as e:
            logger.info(f"博客爬取失败 [{_shorten_url(url)}]: {e}")
            return None


class ContentFetcher:
    """
    内容爬取统一入口（门面模式）
    
    提供简洁的API，隐藏内部的链接提取和分类爬取逻辑
    """
    
    def __init__(self):
        self.video_fetcher = GenericVideoFetcher()
        self.blog_fetcher = BlogFetcher()
    
    def fetch_embedded_content(self, text: str) -> Tuple[List[EmbeddedContent], List[str]]:
        """
        从文本中提取并爬取所有嵌入内容
        
        参数:
            text: 包含URL的文本内容（如推文正文）
        
        返回:
            (embedded_contents, all_urls) 元组
            - embedded_contents: 爬取到的嵌入内容列表（博客、YouTube）
            - all_urls: 所有外部资源链接（博客URL、YouTube URL、媒体URL）
        """
        if not text:
            return [], []
        
        # 提取并分类URL
        blog_links, video_links, media_urls = LinkExtractor.categorize(text)
        results = []
        
        # 处理视频链接 (YouTube + Generic)
        for url in video_links:
            try:
                logger.info(f"正在获取视频内容: {_shorten_url(url)}")
                content = self.video_fetcher.fetch(url)
                if content:
                    results.append(content)
            except Exception as e:
                logger.info(f"视频内容获取失败 [{_shorten_url(url)}]: {e}")
        
        # 处理博客链接
        for url in blog_links:
            try:
                logger.info(f"正在获取博客内容: {_shorten_url(url)}")
                content = self.blog_fetcher.fetch(url)
                if content:
                    results.append(content)
            except Exception as e:
                logger.info(f"博客内容获取失败 [{_shorten_url(url)}]: {e}")
        
        # 合并所有外部资源链接（博客、YouTube、媒体）
        all_urls = blog_links + video_links + media_urls
        
        return results, all_urls
    

