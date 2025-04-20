from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch
import os

# 获取当前目录(bert文件夹)的路径
current_dir = os.path.dirname(os.path.abspath(__file__))

# 载入模型和分词器(从本地路径)
model = AutoModelForSequenceClassification.from_pretrained(current_dir)
tokenizer = AutoTokenizer.from_pretrained(current_dir)

# 测试文本
texts = [
    "這款 App 的界面設計非常直觀，使用起來很順暢！",
    "客服回應速度太慢，問題遲遲得不到解決，很失望。",
    "功能還算齊全，但偶爾會閃退，希望能改進。",
    "雖然有些小bug，但整體來說是個實用的工具App。",
    "完全不推薦下載，廣告太多而且耗電量驚人。"
]

# 进行预测
for text in texts:
    # 预处理文本
    inputs = tokenizer(text, return_tensors="pt")
    
    # 进行预测
    with torch.no_grad():
        outputs = model(**inputs)
        predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
        
        print(f"文本: {text}")
        
        # 获取预测结果
        label_names = ["负面", "正面", "中性"]
        predicted_class = torch.argmax(predictions, dim=1).item()
        
        print(f"预测情感: {label_names[predicted_class]} (分数: {predictions[0][predicted_class].item():.4f})")
        
        # 显示所有情感分数
        print("所有情感分数:")
        for i, label in enumerate(label_names):
            print(f"  {label}: {predictions[0][i].item():.4f}")
        print("-" * 50)
