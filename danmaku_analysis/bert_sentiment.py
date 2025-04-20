"""
BERT中文情感分析模型封装
用于弹幕情感分析
"""

import os
import torch
import logging
import time
import sys
import importlib
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from datetime import datetime
import traceback

# 声明全局变量
transformers = None
MODEL_CLASS = None
TOKENIZER_CLASS = None

# 用于确保所有必要的模块都能正确导入
def ensure_modules_imported():
    """确保所有必要的模块都能正确导入"""
    # 明确声明全局变量
    global transformers, MODEL_CLASS, TOKENIZER_CLASS
    
    try:
        # 导入主模块
        import transformers
        # 导入必要的类
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        # 给全局变量赋值
        MODEL_CLASS = AutoModelForSequenceClassification
        TOKENIZER_CLASS = AutoTokenizer
        return True
    except ImportError as e:
        logging.error(f"导入transformers模块失败: {str(e)}")
        
        try:
            # 尝试安装
            import subprocess
            logging.info("尝试安装transformers...")
            subprocess.run([sys.executable, "-m", "pip", "install", "transformers", "torch", "-i", "https://mirrors.aliyun.com/pypi/simple/"],
                          check=True, timeout=300)
            
            # 在安装成功后重新导入
            import transformers
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            # 在导入成功后给全局变量赋值
            MODEL_CLASS = AutoModelForSequenceClassification
            TOKENIZER_CLASS = AutoTokenizer
            return True
        except Exception as install_err:
            logging.error(f"安装transformers失败: {str(install_err)}")
            transformers = None
            MODEL_CLASS = None
            TOKENIZER_CLASS = None
            return False

# 尝试导入transformers包
try:
    import transformers
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    MODEL_CLASS = AutoModelForSequenceClassification
    TOKENIZER_CLASS = AutoTokenizer
except ImportError:
    transformers = None
    MODEL_CLASS = None
    TOKENIZER_CLASS = None
    # 尝试自动修复导入
    ensure_modules_imported()

from django.conf import settings
from . import analyzer_config

logger = logging.getLogger(__name__)

class BertPerformanceMonitor:
    """BERT模型性能监控"""
    
    def __init__(self):
        self.total_calls = 0
        self.successful_calls = 0
        self.failed_calls = 0
        self.total_processing_time = 0
        self.total_processed_texts = 0
        self.last_reset_time = datetime.now()
        self.lock = Lock()  # 添加线程锁
    
    def record_call(self, successful, text_count, processing_time):
        """记录一次调用"""
        with self.lock:  # 使用线程锁保护数据更新
            self.total_calls += 1
            if successful:
                self.successful_calls += 1
            else:
                self.failed_calls += 1
            self.total_processed_texts += text_count
            self.total_processing_time += processing_time
    
    def get_stats(self):
        """获取统计信息"""
        with self.lock:  # 使用线程锁保护数据读取
            avg_time_per_text = 0
            if self.total_processed_texts > 0:
                avg_time_per_text = self.total_processing_time / self.total_processed_texts
            
            success_rate = 0
            if self.total_calls > 0:
                success_rate = (self.successful_calls / self.total_calls) * 100
            
            texts_per_second = 0
            if self.total_processing_time > 0:
                texts_per_second = self.total_processed_texts / self.total_processing_time
            
            return {
                'total_calls': self.total_calls,
                'successful_calls': self.successful_calls,
                'failed_calls': self.failed_calls,
                'success_rate': round(success_rate, 2),
                'avg_time_per_text': round(avg_time_per_text, 4),
                'texts_per_second': round(texts_per_second, 2),
                'total_processed_texts': self.total_processed_texts,
                'uptime_seconds': (datetime.now() - self.last_reset_time).total_seconds()
            }
    
    def reset(self):
        """重置统计信息"""
        with self.lock:  # 使用线程锁保护数据重置
            self.total_calls = 0
            self.successful_calls = 0
            self.failed_calls = 0
            self.total_processing_time = 0
            self.total_processed_texts = 0
            self.last_reset_time = datetime.now()

class BertSentimentAnalyzer:
    """BERT情感分析器类"""
    
    # 情感标签映射
    LABEL_MAP = {
        0: "negative",  # 负面
        1: "positive",  # 正面
        2: "neutral"    # 中性
    }
    
    # 情感得分权重（用于转换为-1到1的范围）
    SCORE_WEIGHTS = {
        "negative": -1.0,
        "positive": 1.0,
        "neutral": 0.0
    }
    
    def __init__(self):
        """初始化BERT情感分析模型"""
        # 确保所有必要的模块都已导入
        if MODEL_CLASS is None or TOKENIZER_CLASS is None:
            logger.info("初始化时发现必要模块未导入，尝试重新导入")
            ensure_modules_imported()
            
        self.model = None
        self.tokenizer = None
        self.model_loaded = False
        self.load_lock = Lock()  # 添加模型加载锁
        
        # 获取可用的最佳设备
        self.device = self._get_best_device()
        logger.info(f"BERT模型将使用设备: {self.device}")
        
        self.label_map = self.LABEL_MAP
        
        # 从配置文件加载设置
        config = analyzer_config.BERT_CONFIG
        
        # 添加缓存机制
        self.cache_enabled = config.get('enable_cache', True)
        self.cache_size = config.get('cache_size', 10000)  # 最大缓存条目数
        self.result_cache = {}  # 文本到情感结果的映射
        self.cache_lock = Lock()  # 添加缓存锁
        
        # 性能监控
        self.monitor = BertPerformanceMonitor()
        
        # 模型路径
        self.model_path = os.path.join(settings.BASE_DIR, 'danmaku_analysis', 'bert')
        
        # 线程池用于并行处理
        self.max_workers = min(32, (os.cpu_count() or 4) + 4)  # 根据CPU数量设置合理的线程数
        logger.info(f"初始化线程池，最大工作线程数: {self.max_workers}")
    
    def _get_best_device(self):
        """选择最佳设备"""
        # 检查CUDA是否可用
        if torch.cuda.is_available():
            # 获取GPU内存情况
            try:
                free_memory = []
                for i in range(torch.cuda.device_count()):
                    prop = torch.cuda.get_device_properties(i)
                    total_memory = prop.total_memory / 1024 / 1024  # MB
                    # 尝试获取已用内存
                    try:
                        reserved = torch.cuda.memory_reserved(i) / 1024 / 1024
                        allocated = torch.cuda.memory_allocated(i) / 1024 / 1024
                        free = total_memory - reserved
                        logger.info(f"GPU {i}: {prop.name}, 总内存: {total_memory:.0f}MB, "
                                   f"已保留: {reserved:.0f}MB, 已分配: {allocated:.0f}MB, "
                                   f"可用: {free:.0f}MB")
                        free_memory.append((i, free))
                    except Exception as e:
                        logger.warning(f"无法获取GPU {i}的内存信息: {str(e)}")
                        free_memory.append((i, 0))
                
                # 如果有GPU可用且内存足够，选择内存最大的GPU
                if free_memory:
                    best_gpu, best_free = max(free_memory, key=lambda x: x[1])
                    # 只有当可用内存大于1GB时才使用GPU
                    if best_free > 1024:
                        return torch.device(f'cuda:{best_gpu}')
                    else:
                        logger.warning(f"GPU内存不足(最大可用: {best_free:.0f}MB)，使用CPU")
                        return torch.device('cpu')
            except Exception as e:
                logger.warning(f"检查GPU内存时出错: {str(e)}，将使用CPU")
                return torch.device('cpu')
            
            # 如果上面的检查出错，但CUDA可用，使用默认CUDA设备
            return torch.device('cuda')
        else:
            return torch.device('cpu')
    
    def load_model(self, force_reload=False, quantize=True):
        """加载BERT模型
        
        Args:
            force_reload: 是否强制重新加载模型
            quantize: 是否对模型进行量化以减少内存占用
        
        Returns:
            加载是否成功
        """
        # 声明使用到的全局变量
        global transformers, MODEL_CLASS, TOKENIZER_CLASS
        
        # 使用锁确保只有一个线程能加载模型
        with self.load_lock:
            if self.model_loaded and not force_reload:
                return True
                
            try:
                logger.info(f"正在从{self.model_path}加载BERT模型...")
                logger.info(f"当前Python路径: {sys.executable}")
                logger.info(f"transformers版本: {transformers.__version__ if transformers else 'None'}")
                logger.info(f"MODEL_CLASS: {MODEL_CLASS}")
                logger.info(f"TOKENIZER_CLASS: {TOKENIZER_CLASS}")
                
                start_time = time.time()
                
                try:
                    # 先确保已导入必要类
                    if TOKENIZER_CLASS is None or MODEL_CLASS is None:
                        logger.error("transformers类未正确导入，尝试重新导入")
                        import transformers
                        from transformers import AutoModelForSequenceClassification, AutoTokenizer
                        MODEL_CLASS = AutoModelForSequenceClassification
                        TOKENIZER_CLASS = AutoTokenizer
                        logger.info(f"重新导入后: MODEL_CLASS={MODEL_CLASS}, TOKENIZER_CLASS={TOKENIZER_CLASS}")
                    
                    # 验证模型路径是否存在
                    if not os.path.exists(self.model_path):
                        logger.error(f"模型路径不存在: {self.model_path}")
                        raise FileNotFoundError(f"模型路径不存在: {self.model_path}")
                    
                    # 检查模型文件
                    model_files = os.listdir(self.model_path)
                    logger.info(f"模型文件夹内容: {model_files}")
                    
                    logger.info("开始加载tokenizer...")
                    self.tokenizer = TOKENIZER_CLASS.from_pretrained(self.model_path)
                    logger.info("tokenizer加载成功！")
                    
                    logger.info("开始加载model...")
                    self.model = MODEL_CLASS.from_pretrained(self.model_path)
                    logger.info("model加载成功！")
                except Exception as load_err:
                    logger.error(f"首次尝试加载模型失败: {str(load_err)}")
                    logger.info("尝试使用pip安装transformers...")
                    
                    import subprocess
                    try:
                        # 尝试安装transformers
                        subprocess.run([sys.executable, "-m", "pip", "install", "transformers", "-i", "https://mirrors.aliyun.com/pypi/simple/"], 
                            check=True, timeout=300)
                        logger.info("transformers安装成功，重新尝试加载模型")
                        
                        # 重新导入
                        if 'transformers' in sys.modules:
                            importlib.reload(transformers)
                        else:
                            import transformers
                            
                        # 从transformers导入必要的类
                        from transformers import AutoModelForSequenceClassification, AutoTokenizer
                        
                        # 更新全局引用
                        MODEL_CLASS = AutoModelForSequenceClassification
                        TOKENIZER_CLASS = AutoTokenizer
                        
                        # 再次尝试加载模型
                        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
                        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_path)
                    except Exception as install_err:
                        logger.error(f"安装transformers失败: {str(install_err)}")
                        raise
                
                # 模型量化 - 仅在CPU上执行，可减少内存占用最高达75%
                if quantize and self.device.type == 'cpu' and analyzer_config.BERT_CONFIG.get('enable_quantization', True):
                    try:
                        logger.info("对模型进行int8量化以提高性能...")
                        self.model = torch.quantization.quantize_dynamic(
                            self.model, {torch.nn.Linear}, dtype=torch.qint8
                        )
                    except Exception as quantize_err:
                        logger.warning(f"模型量化失败（不影响主要功能）: {str(quantize_err)}")
                    
                # 将模型移动到设备
                try:
                    self.model.to(self.device)
                except Exception as device_err:
                    logger.error(f"无法将模型移至 {self.device}: {str(device_err)}")
                    logger.info("回退到CPU")
                    self.device = torch.device('cpu')
                    self.model.to(self.device)
                
                # 设置为评估模式
                self.model.eval()
                self.model_loaded = True
                
                # 进行垃圾回收，防止内存泄漏
                import gc
                gc.collect()
                if self.device.type == 'cuda':
                    torch.cuda.empty_cache()
                
                load_time = time.time() - start_time
                logger.info(f"BERT模型加载成功，耗时：{load_time:.2f}秒，设备: {self.device}")
                
                # 加载后立即预热
                self.warm_up_cache()
                
                return True
            except Exception as e:
                self.model_loaded = False
                logger.error(f"BERT模型加载失败: {str(e)}")
                return False
    
    def is_model_loaded(self):
        """检查模型是否已加载
        
        Returns:
            布尔值表示模型是否已加载
        """
        return self.model_loaded
    
    def fallback_sentiment_analysis(self, texts):
        """当BERT模型不可用时的后备情感分析
        
        Args:
            texts: 文本列表
            
        Returns:
            情感分析结果列表
        """
        logger.info(f"使用基于词表的后备情感分析处理{len(texts)}条文本")
        
        # 正面词汇表
        positive_words = set([
            '好', '赞', '妙', '棒', '厉害', '强', '爱', '喜欢', '感动', '笑', '哈哈', '哈哈哈',
            '开心', '好看', '美', '漂亮', '帅', '酷', '牛', '牛逼', '牛批', '牛掰', '厉害了',
            '泪目', '威武', '666', '6', '真香', '支持'
        ])
        
        # 负面词汇表
        negative_words = set([
            '差', '烂', '坏', '弱', '难过', '悲伤', '哭', '讨厌', '恨', '垃圾', '无聊', '尴尬',
            '尬', '难受', '倒胃口', '欺骗', '敷衍', '失望', '可惜', '不好', '差评', '恶心'
        ])
        
        results = []
        for text in texts:
            # 计算正面词和负面词出现次数
            pos_count = sum(1 for word in positive_words if word in text)
            neg_count = sum(1 for word in negative_words if word in text)
            
            # 确定情感倾向
            if pos_count > neg_count:
                results.append('positive')
            elif neg_count > pos_count:
                results.append('negative')
            else:
                results.append('neutral')
        
        return results
    
    def warm_up_cache(self):
        """预热模型缓存，避免首次请求延迟
        
        Returns:
            是否预热成功
        """
        if not self.is_model_loaded():
            logger.warning("模型未加载，无法预热")
            return False
            
        warm_up_texts = analyzer_config.BERT_CONFIG.get('warmup_texts', [
            "这个视频很棒", "这个视频很差", "这个视频一般般"
        ])
        
        try:
            logger.info("开始预热BERT模型...")
            start_time = time.time()
            
            # 如果设备是CUDA，先运行一次小批量预测来初始化CUDA上下文
            if self.device.type == 'cuda':
                logger.info("预热CUDA内核...")
                with torch.no_grad():
                    dummy_texts = ["预热文本"] * 4
                    inputs = self.tokenizer(dummy_texts, return_tensors="pt", padding=True, truncation=True)
                    inputs = {k: v.to(self.device) for k, v in inputs.items()}
                    _ = self.model(**inputs)
            
            # 正式预热
            results = self.analyze_batch(warm_up_texts, batch_size=len(warm_up_texts))
            
            warm_time = time.time() - start_time
            logger.info(f"BERT模型预热完成，耗时: {warm_time:.2f}秒")
            return True
        
        except Exception as e:
            logger.error(f"BERT模型预热失败: {str(e)}")
            return False
    
    def preprocess_text(self, text, max_length=128):
        """预处理文本
        
        Args:
            text: 原始文本
            max_length: 最大文本长度
            
        Returns:
            处理后的文本
        """
        if not text:
            return ""
        
        # 转换为字符串
        if not isinstance(text, str):
            text = str(text)
        
        # 去除空白
        text = text.strip()
        
        # 截断过长文本
        if len(text) > max_length:
            text = text[:max_length]
        
        return text
    
    def analyze_text(self, text):
        """分析单条文本情感
        
        Args:
            text: 待分析文本
            
        Returns:
            情感标签: 'positive', 'neutral', 或 'negative'
        """
        # 如果文本为空，直接返回中性
        if not text or len(text.strip()) == 0:
            return 'neutral'
        
        # 检查缓存
        if self.cache_enabled:
            with self.cache_lock:
                if text in self.result_cache:
                    return self.result_cache[text]
        
        # 模型未加载时使用备用方案
        if not self.is_model_loaded():
            if not self.load_model():
                return self._analyze_simple_sentiment(text)
        
        try:
            # 调用预测函数
            result = self.predict(text)
            
            # 从结果中获取情感标签
            if 'error' in result:
                logger.warning(f"情感分析失败: {result['error']}，使用备用方案")
                sentiment = self._analyze_simple_sentiment(text)
            else:
                sentiment = result['sentiment']
            
            # 更新缓存
            if self.cache_enabled:
                with self.cache_lock:
                    # 控制缓存大小
                    if len(self.result_cache) >= self.cache_size:
                        # 随机删除10%的缓存项
                        keys_to_remove = list(self.result_cache.keys())[:int(self.cache_size * 0.1)]
                        for key in keys_to_remove:
                            del self.result_cache[key]
                    # 添加到缓存
                    self.result_cache[text] = sentiment
            
            return sentiment
        
        except Exception as e:
            logger.error(f"分析文本情感失败: {str(e)}")
            # 使用简单情感分析作为后备
            return self._analyze_simple_sentiment(text)
    
    def analyze_batch(self, texts, batch_size=None, max_text_length=128, max_processing_time=300):
        """批量分析多条文本的情感
        
        Args:
            texts: 待分析文本列表
            batch_size: 批处理大小，若为None则自动调整
            max_text_length: 最大文本长度
            max_processing_time: 最大处理时间(秒)，超过此时间将自动降级
            
        Returns:
            情感类别列表: 每项为 'positive', 'neutral', 或 'negative'
        """
        if not texts:
            return []
            
        # 设置最大处理时间
        max_processing_time = max(10, min(max_processing_time, 600))
        
        if not self.is_model_loaded():
            model_loaded = self.load_model()
            if not model_loaded:
                logger.warning("BERT模型加载失败，使用基于词表的后备情感分析")
                return self.fallback_sentiment_analysis(texts)
        
        # 根据设备和文本数量自动调整批大小
        if batch_size is None:
            if self.device.type == 'cuda':
                # CUDA设备根据文本数量调整批大小
                if len(texts) > 10000:
                    batch_size = 256
                elif len(texts) > 5000:
                    batch_size = 192
                elif len(texts) > 1000:
                    batch_size = 128
                else:
                    batch_size = 64
            else:
                # CPU设备使用较小的批大小
                if len(texts) > 10000:
                    batch_size = 64
                elif len(texts) > 5000:
                    batch_size = 48
                elif len(texts) > 1000:
                    batch_size = 32
                else:
                    batch_size = 16
        
        # 预处理文本，截断过长文本
        processed_texts = []
        for text in texts:
            processed_text = self.preprocess_text(text, max_text_length)
            processed_texts.append(processed_text)
        
        # 检查缓存，创建结果列表
        results = [None] * len(processed_texts)
        texts_to_process = []
        text_indices = []
        
        # 先处理缓存
        if self.cache_enabled:
            with self.cache_lock:
                for i, text in enumerate(processed_texts):
                    if not text:  # 空文本直接置为中性
                        results[i] = 'neutral'
                    elif text in self.result_cache:
                        results[i] = self.result_cache[text]
                    else:
                        texts_to_process.append(text)
                        text_indices.append(i)
        else:
            # 不使用缓存，处理所有非空文本
            for i, text in enumerate(processed_texts):
                if not text:  # 空文本直接置为中性
                    results[i] = 'neutral'
                else:
                    texts_to_process.append(text)
                    text_indices.append(i)
        
        # 如果所有文本都已处理(都为空或都在缓存中)
        if not texts_to_process:
            return results
        
        try:
            total_start_time = time.time()
            logger.info(f"开始处理{len(texts_to_process)}条文本，批大小: {batch_size}")
            
            # 检查tokenizer和model是否可用
            if self.tokenizer is None or self.model is None:
                logger.error("分批处理时tokenizer或model为None，尝试重新加载")
                self.load_model(force_reload=True)
                if self.tokenizer is None or self.model is None:
                    logger.error("模型重新加载失败，使用备用方案")
                    return self.fallback_sentiment_analysis(texts)
            
            # 分批处理
            batch_results = []
            total_batches = (len(texts_to_process) + batch_size - 1) // batch_size
            processed_count = 0
            
            # 进度记录变量
            last_progress_log = 0
            progress_log_interval = max(1, total_batches // 10)  # 最多记录10次进度
            
            for i in range(0, len(texts_to_process), batch_size):
                # 检查是否已超时
                elapsed_time = time.time() - total_start_time
                if elapsed_time > max_processing_time:
                    logger.warning(f"处理时间超过{max_processing_time}秒，已处理{processed_count}/{len(texts_to_process)}条，自动降级")
                    # 处理剩余文本
                    remaining_texts = texts_to_process[i:]
                    fallback_results = self.fallback_sentiment_analysis(remaining_texts)
                    batch_results.extend(fallback_results)
                    break
                
                # 当前批次
                current_batch = i // batch_size + 1
                
                # 记录进度
                if current_batch - last_progress_log >= progress_log_interval or current_batch == total_batches:
                    progress_pct = min(100, int(100 * processed_count / len(texts_to_process)))
                    logger.info(f"处理进度: {progress_pct}%，批次 {current_batch}/{total_batches}，已用时: {elapsed_time:.1f}秒")
                    last_progress_log = current_batch
                
                batch_texts = texts_to_process[i:i+batch_size]
                batch_start_time = time.time()
                
                try:
                    # 文本预处理
                    inputs = self.tokenizer(
                        batch_texts, 
                        return_tensors="pt", 
                        truncation=True, 
                        padding=True, 
                        max_length=max_text_length
                    )
                    
                    # 将输入移至设备
                    inputs = {k: v.to(self.device) for k, v in inputs.items()}
                    
                    # 预测
                    with torch.no_grad():
                        outputs = self.model(**inputs)
                        
                    # 获取预测标签
                    logits = outputs.logits
                    predictions = torch.nn.functional.softmax(logits, dim=-1)
                    preds = torch.argmax(predictions, dim=1).tolist()
                    
                    # 添加到结果
                    current_batch_results = [self.label_map[pred] for pred in preds]
                    batch_results.extend(current_batch_results)
                    
                    # 更新缓存
                    if self.cache_enabled:
                        with self.cache_lock:
                            # 每批次检查一次缓存大小
                            if len(self.result_cache) >= self.cache_size:
                                # 随机删除10%的缓存项
                                keys_to_remove = list(self.result_cache.keys())[:int(self.cache_size * 0.1)]
                                for key in keys_to_remove:
                                    del self.result_cache[key]
                            
                            # 更新缓存
                            for text, result in zip(batch_texts, current_batch_results):
                                self.result_cache[text] = result
                    
                    # 更新进度
                    processed_count += len(batch_texts)
                    
                except Exception as batch_err:
                    logger.error(f"批次处理错误: {str(batch_err)}，使用后备方案")
                    # 使用后备方法处理当前批次
                    fallback_results = self.fallback_sentiment_analysis(batch_texts)
                    batch_results.extend(fallback_results)
                    # 更新进度
                    processed_count += len(batch_texts)
                
                # 批处理时间监控
                batch_time = time.time() - batch_start_time
                if batch_time > 2.0:  # 如果批处理时间较长，打印日志
                    texts_per_second = len(batch_texts) / batch_time
                    memory_info = ""
                    if self.device.type == 'cuda':
                        try:
                            allocated = torch.cuda.memory_allocated(self.device) / 1024 / 1024
                            memory_info = f", GPU内存: {allocated:.0f}MB"
                        except:
                            pass
                    logger.info(f"批次 {current_batch}/{total_batches} 处理: {batch_time:.1f}秒 ({texts_per_second:.1f}条/秒{memory_info})")
            
            # 将结果填入原始位置
            for i, result in zip(text_indices, batch_results):
                results[i] = result
            
            # 确保所有结果都有值（用中性填充未处理的）
            for i in range(len(results)):
                if results[i] is None:
                    results[i] = 'neutral'
            
            # 记录性能
            processing_time = time.time() - total_start_time
            self.monitor.record_call(True, len(texts_to_process), processing_time)
            
            # 执行内存清理
            if self.device.type == 'cuda':
                try:
                    torch.cuda.empty_cache()
                except:
                    pass
            
            logger.info(f"批量处理完成，共{len(texts)}条文本，耗时: {processing_time:.2f}秒")
            return results
                
        except Exception as e:
            logger.error(f"BERT批量情感分析错误: {str(e)}")
            self.monitor.record_call(False, len(texts_to_process), 0)
            # 使用后备方案
            return self.fallback_sentiment_analysis(texts)
    
    def _analyze_simple_sentiment(self, text, custom_positive=None, custom_negative=None):
        """基于简单词表的情感分析
        
        Args:
            text: 待分析文本
            custom_positive: 自定义正面词表
            custom_negative: 自定义负面词表
            
        Returns:
            情感标签: 'positive', 'neutral', 或 'negative'
        """
        # 如果文本为空，返回中性
        if not text or len(text.strip()) == 0:
            return 'neutral'
            
        # 使用定义好的情感词典或自定义词典
        positive_words = custom_positive or analyzer_config.POSITIVE_WORDS or POSITIVE_WORDS
        negative_words = custom_negative or analyzer_config.NEGATIVE_WORDS or NEGATIVE_WORDS
        
        # 计算正面和负面词语出现次数
        positive_score = sum(1 for word in positive_words if word in text)
        negative_score = sum(1 for word in negative_words if word in text)
        
        # 根据得分判断情感倾向
        if positive_score > negative_score:
            return 'positive'
        elif negative_score > positive_score:
            return 'negative'
        else:
            # 如果得分相同或都为0，返回中性
            return 'neutral'
    
    def predict(self, text, return_all_scores=False):
        """
        对单条文本进行情感分析
        
        Args:
            text: 要分析的文本
            return_all_scores: 是否返回所有类别的得分
            
        Returns:
            如果return_all_scores为True，返回所有类别的得分字典；
            否则返回预测的情感标签和得分
        """
        if not self.is_model_loaded():
            logger.info("模型未加载，尝试加载模型")
            if not self.load_model():
                logger.error("模型加载失败，返回错误")
                return {"error": "模型未加载"}
        
        # 对输入文本进行预处理
        processed_text = self.preprocess_text(text)
        
        try:
            # 检查tokenizer和model是否可用
            if self.tokenizer is None or self.model is None:
                logger.error("tokenizer或model为None，尝试重新加载")
                self.load_model(force_reload=True)
                if self.tokenizer is None or self.model is None:
                    return {"error": "tokenizer或model加载失败"}
            
            logger.debug(f"开始预测文本: {processed_text[:50]}...")
            # 预处理文本
            inputs = self.tokenizer(processed_text, return_tensors="pt", truncation=True, max_length=128)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # 预测
            with torch.no_grad():
                outputs = self.model(**inputs)
                predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
                
                # 获取预测结果
                predicted_class = torch.argmax(predictions, dim=1).item()
                sentiment_label = self.label_map.get(predicted_class, 'unknown') # 使用 get 防止 KeyErrror
                confidence = predictions[0][predicted_class].item()
                
                # 添加日志，打印原始预测类别和置信度
                logger.info(f"原始预测 => 文本: '{processed_text[:50]}...', 类别ID: {predicted_class}, 置信度: {confidence:.4f}, 映射标签: {sentiment_label}")
                
                if return_all_scores:
                    # 返回所有类别的得分
                    scores = {}
                    for i, label in enumerate(self.label_map.values()):
                        scores[label] = predictions[0][i].item()
                    return scores
                else:
                    # 仅返回预测标签和得分
                    return {
                        "sentiment": sentiment_label,
                        "confidence": confidence
                    }
        
        except Exception as e:
            logger.error(f"预测失败: {str(e)}")
            logger.error(f"异常详情: {traceback.format_exc()}")
            return {"error": f"预测失败: {str(e)}"}
    
    def batch_predict(self, texts, batch_size=16):
        """
        批量分析多条文本的情感
        
        Args:
            texts: 文本列表
            batch_size: 批处理大小
            
        Returns:
            情感分析结果列表
        """
        if not self.is_model_loaded():
            if not self.load_model():
                return [{"error": "模型未加载"} for _ in texts]
        
        # 根据设备自动调整批大小
        if batch_size is None:
            batch_size = 32 if self.device.type == 'cuda' else 16
            
        # 预处理文本
        processed_texts = [self.preprocess_text(text) for text in texts]
        
        results = []
        
        for i in range(0, len(processed_texts), batch_size):
            batch_texts = processed_texts[i:i+batch_size]
            
            try:
                # 预处理批量文本
                encoded = self.tokenizer(
                    batch_texts, 
                    padding=True, 
                    truncation=True, 
                    max_length=128, 
                    return_tensors="pt"
                )
                encoded = {k: v.to(self.device) for k, v in encoded.items()}
                
                # 批量预测
                with torch.no_grad():
                    outputs = self.model(**encoded)
                    predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
                    
                    for j in range(len(batch_texts)):
                        # 获取当前文本的预测结果
                        probs = predictions[j]
                        predicted_class = torch.argmax(probs).item()
                        sentiment_label = self.label_map[predicted_class]
                        confidence = probs[predicted_class].item()
                        
                        # 添加到结果列表
                        results.append({
                            "sentiment": sentiment_label,
                            "confidence": confidence
                        })
            
            except Exception as e:
                # 出错时，为该批次的所有文本添加错误信息
                for _ in batch_texts:
                    results.append({"error": f"批处理预测失败: {str(e)}"})
        
        return results
    
    def convert_to_score(self, sentiment_result):
        """
        将情感预测结果转换为-1到1之间的得分
        
        Args:
            sentiment_result: 情感预测结果字典，包含sentiment和confidence
            
        Returns:
            -1到1之间的情感得分，-1表示极度负面，1表示极度正面，0表示中性
        """
        if "error" in sentiment_result:
            return 0.0
        
        sentiment = sentiment_result["sentiment"]
        confidence = sentiment_result["confidence"]
        
        # 根据情感类型乘以相应的权重，并根据置信度调整
        base_score = self.SCORE_WEIGHTS.get(sentiment, 0.0)
        return base_score * confidence
    
    def get_performance_stats(self):
        """获取性能统计信息"""
        stats = self.monitor.get_stats()
        stats['device'] = self.device.type
        stats['cache_enabled'] = self.cache_enabled
        stats['cache_size'] = len(self.result_cache) if self.cache_enabled else 0
        stats['cache_limit'] = self.cache_size
        return stats
    
    def clear_cache(self):
        """清除结果缓存"""
        if self.cache_enabled:
            self.result_cache.clear()
            return True
        return False

# 创建全局单例实例
bert_analyzer = BertSentimentAnalyzer() 