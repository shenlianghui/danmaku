from .models import Video, Danmaku, Comment
from django.http import JsonResponse
import json
import time
from . import danmaku
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .comment import crawl_and_save_comments
from django.core.paginator import Paginator
from .signals import danmaku_post_bulk_create



@require_http_methods(["POST"])
@csrf_exempt
def fetch_and_save_danmu(request):
    if request.method == 'POST':
        try:
            # 根据 Content-Type 解析参数
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                video_url = data.get('url')
                cookie = data.get('cookie')
            else:
                video_url = request.POST.get('url')
                cookie = request.POST.get('cookie')

            if not video_url:
                return JsonResponse({'status': 'error', 'message': '视频 URL 不能为空'}, status=400)

            # 提取 BV 号
            bvid = danmaku.extract_bvid(video_url)
            if not bvid:
                return JsonResponse({'status': 'error', 'message': '无法从 URL 中提取 BV 号'}, status=400)

            # 检查视频是否已经存在
            try:
                video = Video.objects.get(video_id=bvid)  # 改为使用video_id字段
                # 如果视频已存在，删除相关弹幕数据
                Danmaku.objects.filter(video=video).delete()
            except Video.DoesNotExist:
                video = None

            # 获取视频信息
            video_info = danmaku.get_video_info(bvid)
            if not video_info:
                return JsonResponse({'status': 'error', 'message': '获取视频信息失败'}, status=500)

            # 保存或更新视频信息到数据库
            if not video:
                video = Video.objects.create(
                    video_id=bvid,  # 使用bvid作为video_id
                    title=video_info['title'],
                    url=video_url,
                    duration=video_info['duration'],
                    publish_time=timezone.datetime.fromtimestamp(
                        video_info['pubdate']),
                    view_count=video_info['stat']['view'],
                    danmaku_count=video_info['stat']['danmaku'],
                    comment_count=video_info['stat']['reply']
                )
            else:
                video.title = video_info['title']
                video.duration = video_info['duration']
                video.publish_time = timezone.datetime.fromtimestamp(video_info['pubdate'])
                video.view_count = video_info['stat']['view']
                video.danmaku_count = video_info['stat']['danmaku']
                video.comment_count = video_info['stat']['reply']
                video.save()

            # 获取全部弹幕数据（包含cid和duration）
            cid_info_list = danmaku.get_all_cids(bvid)
            pid = video_info['aid']
            total_danmu_count = 0
            cookies = danmaku.parse_bilibili_cookie(cookie) if cookie else None
            for index, cid_info in enumerate(cid_info_list, start=1):
                cid = cid_info['cid']
                duration = cid_info['duration']
                print(f'正在获取第 {index} 集弹幕数据(cid: {cid}, 时长: {duration}秒)')
                danmus = danmaku.get_all_danmu(cid, pid, cookies)
                if not danmus:
                    print(f'第 {index} 集没有获取到弹幕数据，继续处理下一集')
                    continue

                # 添加延时，避免请求过于频繁
                time.sleep(2)

                # 保存弹幕数据到数据库
                instances = danmaku.save_danmu_to_db(video, index, duration, danmus)  # 传入index作为video_page
                # 发送信号，传递发送者和批量创建的实例列表
                danmaku_post_bulk_create.send(sender=Danmaku, instances=instances, created=True)
                total_danmu_count += len(danmus)

            return JsonResponse({
                'status': 'success',
                'message': '弹幕数据已保存',
                'video_id': video.video_id,  # 改为返回video_id
                'danmu_count': total_danmu_count,
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@require_http_methods(["GET"])
def get_videos(request):
    """
    获取所有视频列表。
    """
    videos = Video.objects.all()
    video_list = []
    for video in videos:
        video_list.append({
            'video_id': video.video_id,  
            'title': video.title,
            'url': video.url,
            'created_at': video.created_at,
            'duration': video.duration,
            'view_count': video.view_count,
            'danmaku_count': video.danmaku_count,
            'comment_count': video.comment_count,
            'uploader_region': video.uploader_region,
            'uploader_level': video.uploader_level
        })
    return JsonResponse({'status': 'success', 'data': video_list})


@require_http_methods(["GET"])
def get_danmus(request):
    """
    根据视频 ID 获取弹幕列表。
    """
    video_id = request.GET.get('video_id')
    if not video_id:
        return JsonResponse({'status': 'error', 'message': '视频 ID 不能为空'}, status=400)

    try:
        danmus = Danmaku.objects.filter(video_id=video_id)
        danmu_list = []
        for danmu in danmus:
            danmu_list.append({
                'id': danmu.id,
                'content': danmu.content,
                'send_time': danmu.send_time,
                'color': danmu.color,
                'font_size': danmu.font_size,
                'type': danmu.type,
                'video_page': danmu.video_page,  # 添加video_page字段
                'position': danmu.position,  # 添加position字段
            })
        return JsonResponse({'status': 'success', 'data': danmu_list})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def fetch_comments(request):
    """
    接收前端请求，爬取并保存评论
    """
    try:
        # 根据 Content-Type 解析参数
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            video_url = data.get('url')
        else:
            video_url = request.POST.get('url')

        if not video_url:
            return JsonResponse({'status': 'error', 'message': '视频 URL 不能为空'}, status=400)
        

        # 调用爬取函数
        total_comments = crawl_and_save_comments(video_url)

        # 获取视频ID用于返回最新评论
        bvid = danmaku.extract_bvid(video_url)
        video = Video.objects.filter(video_id=bvid).first()
        if not video:
            return JsonResponse({'status': 'error', 'message': '视频不存在'}, status=404)

        return JsonResponse({
            'status': 'success',
            'message': '评论爬取完成',
            'video_id': video.video_id,
            'title': video.title,
            'total_comments': total_comments
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@require_http_methods(["GET"])
def get_comments(request):
    """
    获取已存储的评论数据（分页）
    参数: video_id, page=1, page_size=20
    """
    try:
        video_id = request.GET.get('video_id')
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))

        if not video_id:
            return JsonResponse({'status': 'error', 'message': '缺少 video_id 参数'}, status=400)

        # 获取评论并分页
        comments = Comment.objects.filter(
            video_id=video_id).order_by('-created_at')
        paginator = Paginator(comments, page_size)
        page_obj = paginator.get_page(page)

        # 构建返回数据
        comments_data = []
        for comment in page_obj:
            comments_data.append({
                'id': comment.id,
                'content': comment.content,
                'like_count': comment.like_count,
                'sentiment': comment.get_sentiment_display(),
                'is_uploader': comment.is_uploader,
                'commenter_level': comment.commenter_level_group,
                'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'is_reply': bool(comment.root_comment)
            })

        return JsonResponse({
            'status': 'success',
            'total': paginator.count,
            'page': page_obj.number,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
            'data': comments_data
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    



