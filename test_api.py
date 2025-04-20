import requests
import json
import time

def test_create_task():
    url = "http://localhost:8000/api/tasks/create_task/"
    headers = {"Content-Type": "application/json"}
    
    # 选择一个更热门的视频
    data = {
        "video_url": "https://www.bilibili.com/video/BV1uT411G7Zn",  # 这是一个热门视频
        "cookie_str": "buvid3=5FA3F33C-88CE-DC24-D2A8-C4611AF6E10F13822infoc; buvid_fp=5FA3F33C-88CE-DC24-D2A8-C4611AF6E10F13822infoc"  # 请替换为自己的cookie
    }
    
    response = requests.post(url, headers=headers, json=data)
    print(f"状态码: {response.status_code}")
    print(f"响应内容: {response.text}")
    
    # 等待弹幕爬取
    time.sleep(5)

def get_videos():
    url = "http://localhost:8000/api/videos/"
    response = requests.get(url)
    print("\n获取视频列表:")
    print(f"状态码: {response.status_code}")
    videos = response.json()
    print(f"视频数量: {videos['count']}")
    
    for video in videos['results']:
        print(f"视频标题: {video['title']}, BV号: {video['bvid']}")
    
    return videos['results']

def get_danmakus(video_id):
    url = f"http://localhost:8000/api/videos/{video_id}/danmakus/"
    response = requests.get(url)
    print(f"\n获取视频ID {video_id} 的弹幕:")
    print(f"状态码: {response.status_code}")
    danmakus = response.json()
    print(f"弹幕数量: {danmakus['count']}")
    
    # 打印前10条弹幕
    print("前10条弹幕内容:")
    for i, danmaku in enumerate(danmakus['results'][:10], 1):
        print(f"{i}. 时间: {danmaku['progress']}秒, 内容: {danmaku['content']}")
    
    return danmakus['results']

def analyze_danmaku(bvid):
    url = "http://localhost:8000/api/analyses/analyze/"
    headers = {"Content-Type": "application/json"}
    data = {"bvid": bvid, "type": "keyword"}
    
    print(f"\n开始分析视频 {bvid} 的弹幕:")
    response = requests.post(url, headers=headers, json=data)
    print(f"状态码: {response.status_code}")
    print(f"关键词分析响应: {response.text}")
    
    # 情感分析
    data = {"bvid": bvid, "type": "sentiment"}
    response = requests.post(url, headers=headers, json=data)
    print(f"情感分析响应: {response.text}")
    
def get_all_tasks():
    url = "http://localhost:8000/api/tasks/"
    response = requests.get(url)
    print("\n获取所有爬取任务:")
    print(f"状态码: {response.status_code}")
    tasks = response.json()
    
    print(f"任务数量: {tasks['count']}")
    for task in tasks['results']:
        print(f"任务ID: {task['id']}, 视频: {task['video_title']}, 状态: {task['status']}, 弹幕数: {task['danmaku_count']}")
    
if __name__ == "__main__":
    test_create_task()  # 重新爬取弹幕
    get_all_tasks()     # 查看所有任务
    videos = get_videos()
    if videos:
        for video in videos:
            danmakus = get_danmakus(video['id'])
            if danmakus:
                analyze_danmaku(video['bvid']) 