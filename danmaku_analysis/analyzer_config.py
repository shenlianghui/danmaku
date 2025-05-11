"""
弹幕分析器配置文件
包含各种分析任务的配置参数
"""

# 情感分析配置
SENTIMENT_ANALYSIS = {
    'default_use_bert': True,       # 默认是否使用BERT模型
    'default_batch_size': 64,       # 默认批处理大小
    'max_text_length': 128,         # 最大文本长度
    'max_sample_size': 15000,       # 最大采样数量，超过此数量将进行随机采样
    'auto_downgrade_threshold': 100000,  # 自动降级阈值，超过此数量将使用简单分析
    'max_processing_time': 300,     # 最大处理时间（秒）
    'segment_duration_seconds': 300,  # 情感分析时间段长度（秒）
    'score_thresholds': {           # 情感得分阈值
        'very_positive': 0.5,       # 非常正面
        'positive': 0.1,            # 正面
        'neutral': 0.0,             # 中性
        'negative': -0.1,           # 负面
        'very_negative': -0.5,      # 非常负面
    }
}

# 关键词分析配置
KEYWORD_ANALYSIS = {
    'default_top_n': 50,            # 默认返回前N个关键词
    'min_word_length': 2,           # 最小词语长度
    'min_frequency': 2,             # 最小出现频率
    'max_sample_size': 30000,       # 最大采样数量，超过此数量将进行随机采样
}

# 时间线分析配置
TIMELINE_ANALYSIS = {
    'time_unit': 'second',          # 时间单位: 'second', 'minute'
    'peak_threshold_factor': 1.0,   # 峰值阈值因子(标准差倍数)
    'max_peaks': 10,                # 最大峰值数量
    'smoothing_window': 5,          # 平滑窗口大小
    'max_data_points': 500,         # 最大数据点数量，超过将进行降采样
}

# 用户活跃度分析配置
USER_ACTIVITY = {
    'top_users_count': 20,          # 返回前N个活跃用户
    'max_sample_size': 50000,       # 最大采样用户数，超过将进行随机采样
    'user_distribution_ranges': [   # 用户分布范围
        {'name': '1条', 'min': 1, 'max': 1},
        {'name': '2-5条', 'min': 2, 'max': 5},
        {'name': '6-10条', 'min': 6, 'max': 10},
        {'name': '11-20条', 'min': 11, 'max': 20},
        {'name': '20条以上', 'min': 21, 'max': float('inf')},
    ]
}

# BERT模型配置
BERT_CONFIG = {
    'cache_size': 20000,            # 缓存大小
    'enable_cache': True,           # 启用缓存
    'enable_quantization': True,    # 启用模型量化
    'batch_size_cpu': 32,           # CPU默认批大小
    'batch_size_gpu': 64,           # GPU默认批大小
    'warmup_texts': [               # 预热文本
        "这个视频很棒",
        "这个视频很差",
        "这个视频一般般",
        "我非常喜欢这个UP主",
        "这弹幕真搞笑",
        "笑死我了",
        "太感人了",
        "泪目",
        "主播真厉害",
        "不喜欢这个剧情"
    ]
}

# 词汇表配置
POSITIVE_WORDS = set([
    '好', '赞', '妙', '棒', '厉害', '强', '爱', '喜欢', '感动', '笑', '哈哈', '哈哈哈',
    '开心', '好看', '美', '漂亮', '帅', '酷', '牛', '牛逼', '牛批', '牛掰', '厉害了',
    '泪目', '威武', '666', '6', '真香', '支持', '可爱', '萌', '太强了', '优秀', '高端',
    '专业', '精彩', '感谢', '膜拜', '太好了', '感谢', '感恩', '点赞', '搞笑', '逗死我了',
    '惊艳', '震撼', '精品', '完美', '赞赞赞', '期待', '回味', '精致', '鬼斧神工'
])

NEGATIVE_WORDS = set([
    '差', '烂', '坏', '弱', '难过', '悲伤', '哭', '讨厌', '恨', '垃圾', '无聊', '尴尬',
    '尬', '难受', '倒胃口', '欺骗', '敷衍', '失望', '可惜', '不好', '差评', '恶心',
    '难看', '劣质', '虚假', '受不了', '坑', '踩', '毁', '辣眼睛', '毒瘤', '忍不了',
    '吐了', '崩溃', '智障', '废物', '糟糕', '墨迹', '拖沓', '浪费', '愚蠢', '看不下去',
    '恼火', '智障', '缺德', '滥竽充数', '浮夸', '难听', '难吃', '难用', '难学', '欠揍'
])

# 性能调优配置
PERFORMANCE = {
    'use_multiprocessing': True,    # 是否使用多进程
    'max_workers': 8,               # 最大工作进程/线程数
    'async_analysis': True,         # 是否支持异步分析
    'memory_limit_mb': 2048,        # 内存限制(MB)
    'cache_results': True,          # 是否缓存分析结果
    'cache_ttl': 3600 * 24,         # 缓存有效期(秒)，默认1天
    'batch_processing': True,       # 是否使用批处理
    'timeout_seconds': 600,         # 分析超时时间(秒)
} 