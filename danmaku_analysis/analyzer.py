import re
import json
import jieba
import numpy as np
import pandas as pd
import logging
import time
from collections import Counter
from datetime import datetime, timedelta
from django.db.models import Count, Q, Max
from django.utils import timezone
from django.db import transaction
import random
import os
import collections

from danmaku_crawler.models import Video, Danmaku
from .models import DanmakuAnalysis
# 导入BERT情感分析器
from .bert_sentiment import bert_analyzer
from . import analyzer_config

logger = logging.getLogger(__name__)

# 加载结巴分词的停用词
STOPWORDS = set([
    '的', '了', '和', '是', '就', '都', '而', '及', '与', '这', '那', '你', '我', '他', '她',
    '它', '们', '啊', '呀', '哈', '哦', '呢', '吧', '吗', '啦', '呵', '阿', '呜', '哇', '哟',
    '嗯', '嘿', '哼', '咯', '噢', '喔', '唉', '嘛', '额', '诶'
])

# 简单情感词典
POSITIVE_WORDS = set([
    '好', '赞', '妙', '棒', '厉害', '强', '爱', '喜欢', '感动', '笑', '哈哈', '哈哈哈',
    '开心', '好看', '美', '漂亮', '帅', '酷', '牛', '牛逼', '牛批', '牛掰', '厉害了',
    '泪目', '威武', '666', '6', '真香', '支持'
])

NEGATIVE_WORDS = set([
    '差', '烂', '坏', '弱', '难过', '悲伤', '哭', '讨厌', '恨', '垃圾', '无聊', '尴尬',
    '尬', '难受', '倒胃口', '欺骗', '敷衍', '失望', '可惜', '不好', '差评', '恶心'
])

class DanmakuAnalyzer:
    """弹幕分析器类"""
    
    def __init__(self, video):
        """初始化分析器
        
        Args:
            video: Video对象或BV号
        """
        if isinstance(video, str):
            try:
                self.video = Video.objects.get(bvid=video)
            except Video.DoesNotExist:
                raise ValueError(f"视频不存在: {video}")
        else:
            self.video = video
        
        # 查询该视频的所有弹幕
        danmaku_queryset = Danmaku.objects.filter(video=self.video).order_by('progress')
        
        # 检查是否有弹幕数据
        if not danmaku_queryset.exists():
            logger.warning(f"视频没有弹幕数据: {self.video.title} (BV: {self.video.bvid})")
            raise ValueError(f"视频没有弹幕数据: {self.video.title}")
        
        # 获取弹幕数据，用于分析
        self.danmakus = list(danmaku_queryset)
        logger.info(f"成功初始化分析器: {self.video.title} (BV: {self.video.bvid}), 弹幕数: {len(self.danmakus)}")
        
        # 获取分P信息 (page_id 和 duration)
        # 从弹幕数据中聚合获取，避免额外查询或依赖爬虫逻辑
        page_info_query = danmaku_queryset.values('page_id').annotate(
            duration=Max('page_duration') # 获取每个 page_id 的最大时长
        ).order_by('page_id') # 按 page_id 排序

        self.page_info = list(page_info_query)
        if not self.page_info:
            logger.warning(f"无法从弹幕数据中获取分P信息 for video {self.video.bvid}")
            # 尝试创建一个默认的单P信息 (如果视频总时长已知)
            if self.video.duration > 0:
                 self.page_info = [{'page_id': 1, 'duration': self.video.duration}]
            else:
                 # 如果连视频总时长都未知，无法进行准确的时间线分析
                 logger.error(f"视频 {self.video.bvid} 总时长未知且无分P信息，时间线分析可能不准确")
                 # 可以给一个默认值，或者在 analyze_timeline 中处理
                 self.page_info = [{'page_id': 1, 'duration': 0}] # 至少保证 page_info 是列表

        logger.info(f"获取到分P信息: {self.page_info}")
        
        # 转换为DataFrame以便分析 - 先获取values再转为DataFrame
        self.df = pd.DataFrame(list(danmaku_queryset.values()))
    
    def segment_text(self, text):
        """中文分词并去除停用词"""
        words = jieba.cut(text)
        return [w for w in words if w not in STOPWORDS and len(w.strip()) > 1]
    
    def analyze_keywords(self, top_n=50):
        """关键词提取分析
        
        Args:
            top_n: 返回前N个关键词
            
        Returns:
            包含关键词和权重的字典
        """
        # 合并所有弹幕文本
        all_text = ' '.join([d.content for d in self.danmakus])
        
        # 分词
        words = self.segment_text(all_text)
        
        # 统计词频
        word_counts = Counter(words)
        total_words = sum(word_counts.values())
        
        # 计算TF值（词频/总词数）
        keywords = [{'keyword': word, 'frequency': count, 'weight': count/total_words} 
                   for word, count in word_counts.most_common(top_n)]
        
        # 保存分析结果
        DanmakuAnalysis.objects.update_or_create(
            video=self.video,
            analysis_type='keyword',
            defaults={'result_json': keywords}
        )
        
        return keywords
    
    def analyze_sentiment(self, use_bert=True, batch_size=None, max_text_length=128, max_processing_time=300):
        """分析弹幕情感倾向
        
        Args:
            use_bert: 是否使用BERT模型进行情感分析
            batch_size: BERT批处理大小，None为自动
            max_text_length: 最大文本长度
            max_processing_time: 最大处理时间(秒)
            
        Returns:
            情感分析结果字典
        """
        # 记录开始时间
        start_time = time.time()
        
        # 检查是否有弹幕
        if len(self.danmakus) == 0:
            return {
                'message': '没有可分析的弹幕',
                'sentiment_counts': {'positive': 0, 'neutral': 0, 'negative': 0},
                'sentiment_score': 0,
                'used_bert': False,
                'processing_time_ms': 0,
                'segments': []  # 添加空的segments数组
            }
        
        # 提取弹幕文本
        texts = [d.content for d in self.danmakus]
        
        # 对大量弹幕进行采样处理，避免处理时间过长
        max_sample_size = analyzer_config.SENTIMENT_ANALYSIS.get('max_sample_size', 15000)  # 从配置读取最大采样数量
        original_count = len(texts)
        
        # 记录是否进行了采样
        sampled = False
        
        if len(texts) > max_sample_size:
            logger.warning(f"弹幕数量过多({len(texts)}条)，进行随机采样(最大{max_sample_size}条)")
            # 保存原始数量用于记录
            # 进行随机采样
            random.seed(42)  # 设置随机种子确保结果可复现
            texts = random.sample(texts, max_sample_size)
            sampled = True
            logger.info(f"完成采样，从{original_count}条弹幕中随机选取{len(texts)}条进行分析")
        
        # 预处理文本 - 移除超长文本或进行截断
        processed_texts = []
        for text in texts:
            if not text or not isinstance(text, str):
                processed_texts.append("")
                continue
                
            # 去除空白
            text = text.strip()
            
            # 截断超长文本
            if len(text) > max_text_length:
                processed_texts.append(text[:max_text_length])
            else:
                processed_texts.append(text)
        
        # 初始化情感计数
        sentiment_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
        used_bert = False
        
        # 自动降级策略 - 根据文本量判断是否需要降级
        auto_downgrade = False
        
        # 超大数据量自动降级判断
        if use_bert and len(processed_texts) > analyzer_config.SENTIMENT_ANALYSIS.get('auto_downgrade_threshold', 100000):
            logger.warning(f"弹幕数量过多({len(processed_texts)}条)，自动降级为简单词汇分析")
            auto_downgrade = True
            use_bert = False
        
        # 存储每条弹幕的情感结果
        danmaku_sentiments = []
        
        # 如果需要使用BERT模型并且没有自动降级
        if use_bert and not auto_downgrade:
            try:
                # 尝试加载BERT模型(如果尚未加载)
                if not bert_analyzer.is_model_loaded():
                    logger.info("尝试加载BERT模型进行情感分析")
                    bert_analyzer.load_model()
                
                # 检查模型是否成功加载
                if bert_analyzer.is_model_loaded():
                    logger.info(f"使用BERT模型分析{len(processed_texts)}条弹幕")
                    
                    # 使用BERT模型进行情感分析
                    sentiment_results = bert_analyzer.analyze_batch(
                        processed_texts, 
                        batch_size=batch_size,
                        max_text_length=max_text_length,
                        max_processing_time=max_processing_time
                    )
                    
                    # 保存每条弹幕的情感和分数
                    for i, result in enumerate(sentiment_results):
                        sentiment_counts[result] += 1
                        # 保存情感结果和对应弹幕
                        if i < len(self.danmakus):
                            # 获取情感分数
                            score = 0.5  # 默认中性分数
                            if result == 'positive':
                                score = 0.75  # 积极情感分数
                            elif result == 'negative':
                                score = 0.25  # 消极情感分数
                                
                            danmaku_sentiments.append({
                                'danmaku': self.danmakus[i],
                                'sentiment': result,
                                'score': score
                            })
                    
                    used_bert = True
                    logger.info("BERT情感分析完成")
                else:
                    logger.warning("BERT模型未加载，回退到简单词汇情感分析")
                    # 使用简单的词汇情感分析
                    for i, text in enumerate(processed_texts):
                        sentiment = self._analyze_simple_sentiment(text)
                        sentiment_counts[sentiment] += 1
                        
                        # 保存情感结果和对应弹幕
                        if i < len(self.danmakus):
                            # 获取情感分数
                            score = 0.5  # 默认中性分数
                            if sentiment == 'positive':
                                score = 0.75  # 积极情感分数
                            elif sentiment == 'negative':
                                score = 0.25  # 消极情感分数
                                
                            danmaku_sentiments.append({
                                'danmaku': self.danmakus[i],
                                'sentiment': sentiment,
                                'score': score
                            })
            except Exception as e:
                # BERT分析失败，回退到简单分析
                logger.error(f"BERT情感分析失败: {str(e)}")
                for i, text in enumerate(processed_texts):
                    sentiment = self._analyze_simple_sentiment(text)
                    sentiment_counts[sentiment] += 1
                    
                    # 保存情感结果和对应弹幕
                    if i < len(self.danmakus):
                        # 获取情感分数
                        score = 0.5  # 默认中性分数
                        if sentiment == 'positive':
                            score = 0.75  # 积极情感分数
                        elif sentiment == 'negative':
                            score = 0.25  # 消极情感分数
                            
                        danmaku_sentiments.append({
                            'danmaku': self.danmakus[i],
                            'sentiment': sentiment,
                            'score': score
                        })
        else:
            # 使用简单的词汇情感分析
            logger.info(f"使用简单词汇表进行情感分析，共{len(processed_texts)}条弹幕")
            
            # 优化：使用多线程处理大量文本
            if len(processed_texts) > 5000:
                logger.info("使用并行处理来加速简单情感分析")
                try:
                    import concurrent.futures
                    
                    # 定义处理函数，返回情感和索引
                    def process_text(args):
                        idx, text = args
                        sentiment = self._analyze_simple_sentiment(text)
                        return idx, sentiment
                    
                    with concurrent.futures.ThreadPoolExecutor(max_workers=min(32, os.cpu_count() or 4)) as executor:
                        # 按批次处理，每批500条
                        batch_size = 500
                        all_results = []
                        
                        for i in range(0, len(processed_texts), batch_size):
                            batch_texts = processed_texts[i:i+batch_size]
                            # 提交任务给线程池，保留索引
                            futures = [executor.submit(process_text, (i+j, text)) for j, text in enumerate(batch_texts)]
                            # 收集结果
                            for future in concurrent.futures.as_completed(futures):
                                try:
                                    idx, sentiment = future.result()
                                    sentiment_counts[sentiment] += 1
                                    all_results.append((idx, sentiment))
                                except Exception as exc:
                                    logger.error(f"线程池处理失败: {str(exc)}")
                                    sentiment_counts['neutral'] += 1  # 错误时默认中性
                        
                        # 排序并填充danmaku_sentiments
                        all_results.sort(key=lambda x: x[0])  # 按索引排序
                        for idx, sentiment in all_results:
                            if idx < len(self.danmakus):
                                # 获取情感分数
                                score = 0.5  # 默认中性分数
                                if sentiment == 'positive':
                                    score = 0.75  # 积极情感分数
                                elif sentiment == 'negative':
                                    score = 0.25  # 消极情感分数
                                    
                                danmaku_sentiments.append({
                                    'danmaku': self.danmakus[idx],
                                    'sentiment': sentiment,
                                    'score': score
                                })
                except Exception as e:
                    logger.error(f"并行处理情感分析失败: {str(e)}，回退到顺序处理")
                    # 回退到顺序处理
                    for i, text in enumerate(processed_texts):
                        sentiment = self._analyze_simple_sentiment(text)
                        sentiment_counts[sentiment] += 1
                        
                        # 保存情感结果和对应弹幕
                        if i < len(self.danmakus):
                            # 获取情感分数
                            score = 0.5  # 默认中性分数
                            if sentiment == 'positive':
                                score = 0.75  # 积极情感分数
                            elif sentiment == 'negative':
                                score = 0.25  # 消极情感分数
                                
                            danmaku_sentiments.append({
                                'danmaku': self.danmakus[i],
                                'sentiment': sentiment,
                                'score': score
                            })
            else:
                # 少量文本直接顺序处理
                for i, text in enumerate(processed_texts):
                    sentiment = self._analyze_simple_sentiment(text)
                    sentiment_counts[sentiment] += 1
                    
                    # 保存情感结果和对应弹幕
                    if i < len(self.danmakus):
                        # 获取情感分数
                        score = 0.5  # 默认中性分数
                        if sentiment == 'positive':
                            score = 0.75  # 积极情感分数
                        elif sentiment == 'negative':
                            score = 0.25  # 消极情感分数
                            
                        danmaku_sentiments.append({
                            'danmaku': self.danmakus[i],
                            'sentiment': sentiment,
                            'score': score
                        })
        
        # 计算总体情感得分 (-1到1之间)
        total = sum(sentiment_counts.values())
        if total > 0:
            sentiment_score = (sentiment_counts['positive'] - sentiment_counts['negative']) / total
        else:
            sentiment_score = 0
        
        # 生成可视化数据
        visualization_data = self._generate_sentiment_visualization(sentiment_counts, sentiment_score)
        
        # 计算处理时间
        processing_time = time.time() - start_time
        processing_time_ms = int(processing_time * 1000)
        
        # 按时间段划分情感分析结果
        segments = self._generate_sentiment_segments(danmaku_sentiments)
        
        # 保存分析结果到数据库
        result = {
            'message': '情感分析完成',
            'sentiment_counts': sentiment_counts,
            'sentiment_score': sentiment_score,
            'used_bert': used_bert,
            'sampled': sampled,
            'sample_size': len(processed_texts),
            'original_size': original_count,
            'visualization': visualization_data,
            'processing_time_ms': processing_time_ms,
            'auto_downgraded': auto_downgrade,
            'segments': segments  # 添加分段情感结果
        }
        
        # 保存分析结果
        DanmakuAnalysis.objects.update_or_create(
            video=self.video,
            analysis_type='sentiment',
            defaults={'result_json': result}
        )
        
        return result
    
    def _generate_sentiment_segments(self, danmaku_sentiments):
        """按时间生成情感分析段落
        
        将弹幕按时间间隔分组，生成每个时间段的情感分析结果
        
        Args:
            danmaku_sentiments: 包含情感分析结果的弹幕列表
            
        Returns:
            时间段列表，每个段落包含开始时间、结束时间、情感和分数
        """
        if not danmaku_sentiments:
            return []
        
        # 获取配置中的时间段长度，默认30秒
        segment_duration = analyzer_config.SENTIMENT_ANALYSIS.get('segment_duration_seconds', 30) * 1000  # 转换为毫秒
        
        # 首先按页和进度排序弹幕
        sorted_danmakus = sorted(
            danmaku_sentiments,
            key=lambda x: (x['danmaku'].page_id, x['danmaku'].progress)
        )
        
        # 获取分P边界信息
        page_start_times = {}
        current_start_time = 0
        for page in self.page_info:
            page_id = page.get('page_id')
            duration = page.get('duration', 0)
            page_start_times[page_id] = current_start_time * 1000  # 转换为毫秒
            current_start_time += duration
        
        # 按照分段时长分组弹幕
        segments = []
        current_segment = None
        
        for item in sorted_danmakus:
            danmaku = item['danmaku']
            sentiment = item['sentiment']
            score = item['score']
            
            if danmaku.progress is None or danmaku.page_id is None:
                continue
            
            # 计算绝对时间（毫秒）
            absolute_time = page_start_times.get(danmaku.page_id, 0) + danmaku.progress
            
            # 确定当前弹幕所属的时间段
            segment_start = (absolute_time // segment_duration) * segment_duration
            segment_end = segment_start + segment_duration
            
            # 如果是新的时间段，创建新的段落
            if current_segment is None or current_segment['segment_start'] != segment_start:
                # 如果存在上一个段落，先计算其平均情感并添加
                if current_segment:
                    self._finalize_sentiment_segment(current_segment)
                    segments.append(current_segment)
                
                # 创建新的时间段
                current_segment = {
                    'segment_start': segment_start,
                    'segment_end': segment_end,
                    'positive_count': 0,
                    'neutral_count': 0,
                    'negative_count': 0,
                    'total_score': 0,
                    'danmaku_count': 0
                }
            
            # 添加当前弹幕到段落统计
            current_segment['danmaku_count'] += 1
            current_segment[f'{sentiment}_count'] += 1
            current_segment['total_score'] += score
        
        # 处理最后一个段落
        if current_segment:
            self._finalize_sentiment_segment(current_segment)
            segments.append(current_segment)
        
        return segments
    
    def _finalize_sentiment_segment(self, segment):
        """完成情感分析段落计算
        
        计算段落的情感类型和平均分数
        
        Args:
            segment: 需要完成计算的情感段落
        """
        # 计算段落平均分数
        if segment['danmaku_count'] > 0:
            segment['score'] = segment['total_score'] / segment['danmaku_count']
        else:
            segment['score'] = 0.5  # 默认中性
        
        # 确定主导情感
        if segment['positive_count'] > segment['negative_count'] and segment['positive_count'] > segment['neutral_count']:
            segment['sentiment'] = 'positive'
        elif segment['negative_count'] > segment['positive_count'] and segment['negative_count'] > segment['neutral_count']:
            segment['sentiment'] = 'negative'
        else:
            segment['sentiment'] = 'neutral'
        
        # 移除中间计算数据
        segment.pop('total_score', None)
    
    def _generate_sentiment_visualization(self, sentiment_counts, sentiment_score):
        """生成情感分析结果的可视化数据
        
        Args:
            sentiment_counts: 情感计数字典
            sentiment_score: 情感得分
            
        Returns:
            可视化数据字典
        """
        total = sum(sentiment_counts.values())
        if total == 0:
            return {
                'percentages': {'positive': 0, 'neutral': 0, 'negative': 0},
                'dominant': 'neutral',
                'score_level': 'neutral'
            }
        
        # 计算百分比
        percentages = {
            k: round(v / total * 100, 1) for k, v in sentiment_counts.items()
        }
        
        # 确定主导情感
        dominant = max(sentiment_counts.items(), key=lambda x: x[1])[0]
        
        # 情感强度等级
        score_level = 'neutral'
        if sentiment_score > 0.5:
            score_level = 'very_positive'
        elif sentiment_score > 0.1:
            score_level = 'positive'
        elif sentiment_score < -0.5:
            score_level = 'very_negative'
        elif sentiment_score < -0.1:
            score_level = 'negative'
        
        return {
            'percentages': percentages,
            'dominant': dominant,
            'score_level': score_level
        }
    
    def _analyze_simple_sentiment(self, text, custom_positive=None, custom_negative=None):
        """使用简单的词汇表进行情感分析
        
        Args:
            text: 待分析文本
            custom_positive: 自定义正面词汇集合
            custom_negative: 自定义负面词汇集合
            
        Returns:
            情感类别: 'positive', 'neutral', 或 'negative'
        """
        # 使用默认词汇表 + 自定义词汇表
        positive_words = POSITIVE_WORDS.union(custom_positive or set())
        negative_words = NEGATIVE_WORDS.union(custom_negative or set())
        
        # 计算正面词和负面词出现次数
        pos_count = sum(1 for word in positive_words if word in text)
        neg_count = sum(1 for word in negative_words if word in text)
        
        # 确定情感倾向
        if pos_count > neg_count:
            return 'positive'
        elif neg_count > pos_count:
            return 'negative'
        else:
            return 'neutral'
    
    def analyze_timeline(self):
        """时间线分析，处理分P视频
        
        使用相对于分P的 progress 计算绝对时间线，并返回分P边界。
        """
        if not self.danmakus:
            logger.warning(f"视频 {self.video.bvid} 没有弹幕数据，无法进行时间线分析")
            return { 'timeline': [], 'peaks': [], 'episode_boundaries': [], 'total_count': 0 }

        # --- 计算分P边界 ---
        episode_boundaries = []
        current_start_time = 0
        if self.page_info and all('page_id' in p and 'duration' in p for p in self.page_info):
            sorted_page_info = sorted(self.page_info, key=lambda p: p.get('page_id', 0))
            for page in sorted_page_info:
                 page_id = page.get('page_id')
                 duration = page.get('duration') if page.get('duration') is not None and page.get('duration') >= 0 else 0
                 if duration == 0: logger.warning(f"分P {page_id} 时长为 0 或无效")
                 end_time = current_start_time + duration
                 episode_boundaries.append({
                     'page_id': page_id,
                     'start_time_sec': current_start_time,
                     'end_time_sec': end_time,
                     'duration_sec': duration
                 })
                 current_start_time = end_time
        else:
             logger.error(f"无法计算分P边界: self.page_info 格式错误或为空: {self.page_info}")
             if self.video.duration > 0:
                  episode_boundaries = [{'page_id': 1, 'start_time_sec': 0, 'end_time_sec': self.video.duration, 'duration_sec': self.video.duration}]

        # 创建一个快速查找分P开始时间的字典
        page_start_times = {b['page_id']: b['start_time_sec'] for b in episode_boundaries}

        # --- 准备时间线数据  ---
        # 使用 defaultdict 按视频进度统计弹幕数量 (按计算出的绝对秒数)
        timeline_data = collections.defaultdict(int)
        valid_danmaku_count = 0
        for d in self.danmakus:
            if d.progress is not None and d.page_id is not None:
                try:
                    # 获取该弹幕所属分P的绝对开始时间
                    page_start_sec = page_start_times.get(d.page_id)
                    if page_start_sec is None:
                         logger.warning(f"弹幕 (dmid: {d.dmid}) 的 page_id ({d.page_id}) 未在 boundaries 中找到，跳过")
                         continue

                    # progress 是相对于分P的毫秒数
                    relative_sec = float(d.progress) / 1000

                    # 计算绝对秒数
                    absolute_sec = int(page_start_sec + relative_sec)

                    # 确保计算出的绝对秒数非负
                    if absolute_sec >= 0:
                        timeline_data[absolute_sec] += 1
                        valid_danmaku_count += 1
                    else:
                        # 这个情况理论上不应该发生，除非 page_start_sec 为负数？
                        logger.warning(f"计算出的绝对秒数 ({absolute_sec}) 为负数。Page Start: {page_start_sec}, Relative Sec: {relative_sec}. 跳过弹幕 dmid: {d.dmid}")

                except (ValueError, TypeError):
                    logger.warning(f"无法处理弹幕进度值: {d.progress} (dmid: {d.dmid})，跳过此弹幕") # 减少日志
                    continue
            else:
                #  缺少 progress 或 page_id 的弹幕无法定位
                 logger.warning(f"弹幕缺少 progress 或 page_id, dmid: {d.dmid}, page_id: {d.page_id}, progress: {d.progress}")
                 pass

        if not timeline_data:
            logger.warning(f"视频 {self.video.bvid} 计算后没有有效的弹幕时间数据 (timeline_data is empty)")
            return { 'timeline': [], 'peaks': [], 'episode_boundaries': episode_boundaries, 'total_count': len(self.danmakus) }

        # --- 准备 full_timeline (逻辑不变，因为 time 已经是绝对秒数) ---
        # 创建一个查找函数或字典 (复用之前的逻辑，用于添加 page_id 到 timeline 点)
        def get_page_id_for_abs_time(abs_sec):
            # 优先检查最后一个边界（因为时间点可能等于结束时间）
            last_boundary = episode_boundaries[-1] if episode_boundaries else None
            if last_boundary and abs_sec == last_boundary['end_time_sec']:
                return last_boundary['page_id']
            # 检查其他边界 [start, end)
            for boundary in episode_boundaries:
                if boundary['start_time_sec'] <= abs_sec < boundary['end_time_sec']:
                    return boundary['page_id']
            # 如果都不匹配（理论上不应发生），返回最后一个或默认值
            logger.warning(f"时间点 {abs_sec} 未匹配到任何分P边界，将归类到最后一个分P")
            return last_boundary['page_id'] if last_boundary else 1

        full_timeline = [
            {'time': t, 'count': c, 'page_id': get_page_id_for_abs_time(t)}
            for t, c in timeline_data.items()
        ]
        full_timeline.sort(key=lambda x: x['time'])

        # --- 峰值检测 (逻辑不变，基于绝对时间的 full_timeline) ---
        # ... (加载配置, 计算 avg, std, threshold, min_peak_count_dynamic) ...
        try:
            timeline_config = analyzer_config.TIMELINE_ANALYSIS
            peak_std_threshold = timeline_config.get('peak_std_threshold', 1.5)
            min_peak_count_abs = timeline_config.get('min_peak_count_abs', 5)
            min_peak_count_ratio = timeline_config.get('min_peak_count_ratio', 0.05)
            top_n_peaks_total = timeline_config.get('top_n_peaks_total', 20)
        except AttributeError:
            logger.warning("analyzer_config.py 中缺少 TIMELINE_ANALYSIS 配置, 使用默认值")
            peak_std_threshold = 1.5
            min_peak_count_abs = 5
            min_peak_count_ratio = 0.05
            top_n_peaks_total = 20

        counts = [item['count'] for item in full_timeline]
        all_peaks = []
        if counts:
            avg_count = np.mean(counts)
            std_count = np.std(counts) if len(counts) > 1 else 0.0
            threshold = avg_count + peak_std_threshold * std_count + 1e-6
            min_peak_count_dynamic = max(1, min_peak_count_abs, int(avg_count * min_peak_count_ratio))

            peak_candidates = [ item for item in full_timeline if item['count'] > threshold and item['count'] >= min_peak_count_dynamic ]
            peak_candidates.sort(key=lambda x: x['count'], reverse=True)
            all_peaks = peak_candidates[:top_n_peaks_total]


        # --- 准备最终结果 (结构不变) ---
        result = {
            'timeline': full_timeline,
            'peaks': all_peaks,
            'episode_boundaries': episode_boundaries,
            'total_count': len(self.danmakus) # 或者用 valid_danmaku_count 更准确? 但 total_count 可能指数据库总数
        }

        # --- 保存分析结果 (逻辑不变) ---
        DanmakuAnalysis.objects.update_or_create(
            video=self.video,
            analysis_type='timeline',
            defaults={'result_json': result}
        )

        return result
    
    def analyze_user_activity(self):
        """用户活跃度分析
        
        Returns:
            包含用户活跃度分析结果的字典
        """
        # 按用户哈希统计弹幕数量
        user_counts = {}
        for d in self.danmakus:
            if d.user_hash not in user_counts:
                user_counts[d.user_hash] = 0
            user_counts[d.user_hash] += 1
        
        # 转换为列表格式
        users = [{'user_hash': u, 'count': c} for u, c in user_counts.items()]
        users.sort(key=lambda x: x['count'], reverse=True)
        
        # 计算发送弹幕用户数
        total_users = len(users)
        
        # 计算平均每个用户发送弹幕数
        avg_per_user = len(self.danmakus) / total_users if total_users > 0 else 0
        
        result = {
            'top_users': users[:20],  # 取前20个活跃用户
            'total_users': total_users,
            'avg_per_user': avg_per_user,
            'user_distribution': {
                '1条': sum(1 for u in users if u['count'] == 1),
                '2-5条': sum(1 for u in users if 2 <= u['count'] <= 5),
                '6-10条': sum(1 for u in users if 6 <= u['count'] <= 10),
                '11-20条': sum(1 for u in users if 11 <= u['count'] <= 20),
                '20条以上': sum(1 for u in users if u['count'] > 20),
            }
        }
        
        # 保存分析结果
        DanmakuAnalysis.objects.update_or_create(
            video=self.video,
            analysis_type='user',
            defaults={'result_json': result}
        )
        
        return result
    
    def analyze_all(self, use_bert=True, batch_size=None, max_processing_time=300):
        """运行所有分析
        
        Args:
            use_bert: 是否使用BERT模型进行情感分析
            batch_size: BERT批处理大小
            max_processing_time: 最大处理时间(秒)
            
        Returns:
            包含所有分析结果的字典
        """
        start_time = time.time()
        logger.info(f"开始对视频 {self.video.title} (BV: {self.video.bvid}) 进行全面分析")
        
        try:
            # 关键词分析
            logger.info("开始关键词分析")
            keywords_result = self.analyze_keywords(top_n=analyzer_config.KEYWORD_ANALYSIS.get('default_top_n', 50))
            
            # 情感分析
            logger.info("开始情感分析")
            sentiment_result = self.analyze_sentiment(
                use_bert=use_bert, 
                batch_size=batch_size,
                max_processing_time=max_processing_time
            )
            
            # 时间线分析
            logger.info("开始时间线分析")
            timeline_result = self.analyze_timeline()
            
            # 用户活跃度分析
            logger.info("开始用户活跃度分析")
            user_activity_result = self.analyze_user_activity()
            
            # 计算总处理时间
            total_time_ms = int((time.time() - start_time) * 1000)
            
            # 构建最终结果
            result = {
                'message': f'分析完成: {self.video.title}',
                'video': {
                    'bvid': self.video.bvid,
                    'title': self.video.title,
                    'author': self.video.owner,
                    'duration': self.video.duration,
                    'danmaku_count': len(self.danmakus)
                },
                'keywords': keywords_result,
                'sentiment': sentiment_result,
                'timeline': timeline_result,
                'user_activity': user_activity_result,
                'processing_time_ms': total_time_ms
            }
            
            logger.info(f"全面分析完成，耗时: {total_time_ms/1000:.2f}秒")
            return result
            
        except Exception as e:
            logger.error(f"分析过程发生错误: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            return {
                'error': f'分析过程发生错误: {str(e)}',
                'message': '分析失败',
                'video': {
                    'bvid': self.video.bvid,
                    'title': self.video.title
                }
            }


# 便捷分析函数
def analyze_video_danmaku(video_bvid, analysis_type=None, use_bert=True, batch_size=None, max_processing_time=300):
    """分析视频弹幕
    
    Args:
        video_bvid: 视频BV号
        analysis_type: 分析类型，可选值: 'keyword', 'sentiment', 'timeline', 'user_activity'。
                      如果为None则进行所有分析
        use_bert: 是否使用BERT模型进行情感分析
        batch_size: BERT批处理大小
        max_processing_time: 最大处理时间(秒)
        
    Returns:
        分析结果字典
    """
    start_time = time.time()
    logger.info(f"开始分析视频 {video_bvid}, 分析类型: {analysis_type or '全部'}")
    
    # 缓存优化: 检查是否已有分析结果
    if analysis_type and analyzer_config.PERFORMANCE.get('cache_results', True):
        try:
            from django.utils import timezone
            cache_ttl = analyzer_config.PERFORMANCE.get('cache_ttl', 3600 * 24)  # 默认1天
            
            cached_analysis = DanmakuAnalysis.objects.filter(
                video__bvid=video_bvid,
                analysis_type=analysis_type
            ).first()
            
            if cached_analysis:
                time_diff = (timezone.now() - cached_analysis.updated_at).total_seconds()
                if time_diff < cache_ttl:
                    logger.info(f"使用缓存的分析结果，缓存时间: {time_diff:.0f}秒, TTL: {cache_ttl}秒")
                    return cached_analysis.result_json
                else:
                    logger.info(f"缓存已过期 ({time_diff:.0f}秒 > {cache_ttl}秒)，重新分析")
        except Exception as e:
            logger.warning(f"检查缓存时出错: {str(e)}")
    
    try:
        # 创建分析器实例
        analyzer = DanmakuAnalyzer(video_bvid)
        
        # 根据分析类型选择合适的分析方法
        if analysis_type == 'keyword':
            result = analyzer.analyze_keywords(top_n=analyzer_config.KEYWORD_ANALYSIS.get('default_top_n', 50))
        elif analysis_type == 'sentiment':
            result = analyzer.analyze_sentiment(
                use_bert=use_bert, 
                batch_size=batch_size,
                max_processing_time=max_processing_time
            )
        elif analysis_type == 'timeline':
            result = analyzer.analyze_timeline()
        elif analysis_type == 'user':
            result = analyzer.analyze_user_activity()
        else:
            # 运行所有分析
            result = analyzer.analyze_all(
                use_bert=use_bert, 
                batch_size=batch_size,
                max_processing_time=max_processing_time
            )
        
        total_time = time.time() - start_time
        logger.info(f"分析完成，耗时: {total_time:.2f}秒")
        
        # 额外添加性能信息
        if isinstance(result, dict) and not isinstance(result.get('processing_time_ms', None), int):
            result['processing_time_ms'] = int(total_time * 1000)
        
        return result
    
    except ValueError as ve:
        # 视频不存在或没有弹幕等错误
        error_message = str(ve)
        logger.error(f"分析错误 (ValueError): {error_message}")
        return {'error': error_message}
    
    except Exception as e:
        import traceback
        error_message = f"分析过程发生异常: {str(e)}"
        logger.error(error_message)
        logger.error(traceback.format_exc())
        return {'error': error_message} 