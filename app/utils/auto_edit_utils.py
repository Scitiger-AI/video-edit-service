import os
import random
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
from ..core.config import settings
from ..core.logging import logger
from .video_utils import VideoUtils
from .music_utils import MusicUtils


class AutoEditUtils:
    """自动剪辑工具类"""
    
    @staticmethod
    async def analyze_video_clips(
        video_paths: List[str]
    ) -> List[Dict[str, Any]]:
        """
        分析视频片段
        
        Args:
            video_paths: 视频路径列表
            
        Returns:
            List[Dict[str, Any]]: 视频片段信息列表
        """
        video_clips = []
        
        for i, path in enumerate(video_paths):
            try:
                # 获取视频信息
                video_info = await VideoUtils.get_video_info(path)
                
                video_clips.append({
                    "index": i,
                    "path": path,
                    "duration": video_info["duration"],
                    "width": next((s.get("width", 0) for s in video_info["streams"] if s.get("codec_type") == "video"), 0),
                    "height": next((s.get("height", 0) for s in video_info["streams"] if s.get("codec_type") == "video"), 0),
                    "fps": next((s.get("fps", 0) for s in video_info["streams"] if s.get("codec_type") == "video"), 0),
                    "has_audio": any(s.get("codec_type") == "audio" for s in video_info["streams"]),
                    "video_info": video_info
                })
                
            except Exception as e:
                logger.error(f"Error analyzing video clip {path}: {str(e)}")
                # 跳过有问题的视频
                continue
                
        return video_clips
    
    @staticmethod
    def distribute_clips_by_rhythm(
        video_clips: List[Dict[str, Any]],
        rhythm_points: List[float],
        max_duration: Optional[float] = None,
        min_clip_duration: float = 2.0  # 最小片段时长，默认2秒
    ) -> List[Dict[str, Any]]:
        """
        根据节奏点分配视频片段
        
        Args:
            video_clips: 视频片段信息列表
            rhythm_points: 节奏时间点列表（秒）
            max_duration: 最大总时长（秒），None表示不限制
            min_clip_duration: 最小片段时长（秒）
            
        Returns:
            List[Dict[str, Any]]: 分配后的视频片段信息列表
        """
        if not video_clips or not rhythm_points:
            return []
            
        # 计算总视频时长
        total_video_duration = sum(clip["duration"] for clip in video_clips)
        
        # 如果没有指定最大时长，使用节奏点的最大值
        if max_duration is None:
            max_duration = rhythm_points[-1]
        
        # 预处理节奏点：过滤掉间隔太小的节奏点，确保至少间隔min_clip_duration
        filtered_rhythm_points = [rhythm_points[0]]
        for i in range(1, len(rhythm_points)):
            if rhythm_points[i] - filtered_rhythm_points[-1] >= min_clip_duration:
                filtered_rhythm_points.append(rhythm_points[i])
        
        # 如果过滤后节奏点太少，使用均匀分配
        if len(filtered_rhythm_points) < 3:
            logger.warning(f"Too few valid rhythm points ({len(filtered_rhythm_points)}), using even distribution instead")
            return AutoEditUtils.distribute_clips_evenly(
                video_clips=video_clips, 
                music_duration=max_duration,
                min_clip_duration=min_clip_duration
            )
        
        # 使用过滤后的节奏点
        rhythm_points = filtered_rhythm_points
        logger.info(f"Using {len(rhythm_points)} filtered rhythm points for clip distribution")
            
        # 如果视频总时长小于音乐时长，需要重复使用视频
        if total_video_duration < max_duration:
            # 计算需要重复的次数
            repeat_count = int(max_duration / total_video_duration) + 1
            # 重复视频列表
            extended_clips = []
            for _ in range(repeat_count):
                # 随机打乱顺序后添加
                shuffled = video_clips.copy()
                random.shuffle(shuffled)
                extended_clips.extend(shuffled)
            video_clips = extended_clips
            
        # 按节奏点分配视频片段
        distributed_clips = []
        current_video_index = 0
        
        # 遍历节奏点对（起始点和结束点）
        for i in range(len(rhythm_points) - 1):
            start_time = rhythm_points[i]
            end_time = rhythm_points[i+1]
            segment_duration = end_time - start_time
            
            # 如果片段时长小于最小时长，则跳过这个节奏点
            if segment_duration < min_clip_duration:
                continue
            
            # 选择视频片段
            clip = video_clips[current_video_index % len(video_clips)]
            current_video_index += 1
            
            # 如果视频长度大于片段时长，随机选择一个合适的起始点
            if clip["duration"] > segment_duration:
                # 可用于随机选择的范围
                available_range = clip["duration"] - segment_duration
                # 随机选择起始点，但避免总是从开头开始
                if available_range > 1.0:
                    start_offset = random.uniform(0, available_range)
                else:
                    start_offset = 0
                
                distributed_clips.append({
                    **clip,
                    "start_time": start_offset,
                    "end_time": start_offset + segment_duration,
                    "output_start_time": start_time,
                    "output_end_time": end_time
                })
            else:
                # 如果视频长度不足，使用完整视频并居中放置
                padding_before = (segment_duration - clip["duration"]) / 2
                if padding_before < 0:
                    padding_before = 0
                
                distributed_clips.append({
                    **clip,
                    "start_time": 0,
                    "end_time": clip["duration"],
                    "output_start_time": start_time + padding_before,
                    "output_end_time": start_time + padding_before + clip["duration"]
                })
                
            # 检查是否已达到最大时长
            if end_time >= max_duration:
                break
                
        # 如果没有分配任何片段（可能是因为节奏点都不满足最小时长要求），则使用均匀分配
        if not distributed_clips:
            logger.warning("No clips were distributed based on rhythm points, using even distribution instead")
            return AutoEditUtils.distribute_clips_evenly(
                video_clips=video_clips, 
                music_duration=max_duration,
                min_clip_duration=min_clip_duration
            )
                
        return distributed_clips
    
    @staticmethod
    def distribute_clips_evenly(
        video_clips: List[Dict[str, Any]],
        music_duration: float,
        min_clip_duration: float = 1.0
    ) -> List[Dict[str, Any]]:
        """
        均匀分配视频片段
        
        Args:
            video_clips: 视频片段信息列表
            music_duration: 音乐时长（秒）
            min_clip_duration: 最小片段时长（秒）
            
        Returns:
            List[Dict[str, Any]]: 分配后的视频片段信息列表
        """
        if not video_clips:
            return []
            
        # 计算总视频时长
        total_video_duration = sum(clip["duration"] for clip in video_clips)
        
        # 如果视频总时长小于音乐时长，需要重复使用视频
        if total_video_duration < music_duration:
            # 计算需要重复的次数
            repeat_count = int(music_duration / total_video_duration) + 1
            # 重复视频列表
            extended_clips = []
            for _ in range(repeat_count):
                # 随机打乱顺序后添加
                shuffled = video_clips.copy()
                random.shuffle(shuffled)
                extended_clips.extend(shuffled)
            video_clips = extended_clips
            
        # 计算每个片段的平均时长
        clip_count = len(video_clips)
        if clip_count > music_duration / min_clip_duration:
            # 如果片段数量过多，需要减少使用的片段数
            clip_count = int(music_duration / min_clip_duration)
            # 随机选择片段
            video_clips = random.sample(video_clips, clip_count)
            
        avg_duration = music_duration / clip_count
        
        # 均匀分配视频片段
        distributed_clips = []
        current_time = 0.0
        
        for clip in video_clips:
            # 如果已经达到音乐时长，停止分配
            if current_time >= music_duration:
                break
                
            # 计算片段时长
            clip_duration = min(clip["duration"], avg_duration, music_duration - current_time)
            
            # 添加分配信息
            distributed_clips.append({
                **clip,
                "start_time": 0,
                "end_time": clip_duration,
                "output_start_time": current_time,
                "output_end_time": current_time + clip_duration
            })
            
            # 更新当前时间
            current_time += clip_duration
            
        return distributed_clips
    
    @staticmethod
    def distribute_clips_by_energy(
        video_clips: List[Dict[str, Any]],
        music_segments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        根据音乐能量分配视频片段
        
        Args:
            video_clips: 视频片段信息列表
            music_segments: 音乐分段信息列表
            
        Returns:
            List[Dict[str, Any]]: 分配后的视频片段信息列表
        """
        if not video_clips or not music_segments:
            return []
            
        # 按时长排序视频片段
        sorted_clips = sorted(video_clips, key=lambda x: x["duration"])
        
        # 按能量排序音乐分段
        sorted_segments = sorted(music_segments, key=lambda x: x["energy"])
        
        # 分配视频片段
        distributed_clips = []
        
        # 确保有足够的视频片段
        if len(sorted_clips) < len(sorted_segments):
            # 不够的话，复制一些视频片段
            while len(sorted_clips) < len(sorted_segments):
                sorted_clips.extend(sorted_clips[:len(sorted_segments) - len(sorted_clips)])
        
        # 将视频片段与音乐分段匹配
        for i, segment in enumerate(sorted_segments):
            clip_index = i % len(sorted_clips)
            clip = sorted_clips[clip_index]
            
            # 计算片段时长
            clip_duration = min(clip["duration"], segment["duration"])
            
            # 添加分配信息
            distributed_clips.append({
                **clip,
                "start_time": 0,
                "end_time": clip_duration,
                "output_start_time": segment["start_time"],
                "output_end_time": segment["start_time"] + clip_duration,
                "segment_energy": segment["energy"],
                "segment_tempo": segment["tempo"]
            })
        
        # 按输出开始时间排序
        distributed_clips.sort(key=lambda x: x["output_start_time"])
        
        return distributed_clips
    
    @staticmethod
    async def create_edit_plan(
        video_paths: List[str],
        music_path: str,
        strategy: str = "rhythm",
        min_clip_duration: float = 2.0  # 添加最小片段时长参数
    ) -> Dict[str, Any]:
        """
        创建编辑计划
        
        Args:
            video_paths: 视频路径列表
            music_path: 背景音乐路径
            strategy: 剪辑策略（rhythm/even/energy）
            min_clip_duration: 最小片段时长（秒）
            
        Returns:
            Dict[str, Any]: 编辑计划
        """
        # 分析视频片段
        video_clips = await AutoEditUtils.analyze_video_clips(video_paths)
        
        if not video_clips:
            raise ValueError("No valid video clips found")
            
        # 获取音乐时长
        music_duration = MusicUtils.get_music_duration(music_path)
        
        # 根据不同策略创建编辑计划
        if strategy == "rhythm":
            # 检测音乐节奏点
            rhythm_points = MusicUtils.detect_rhythm_points(music_path)
            
            # 根据节奏点分配视频片段
            distributed_clips = AutoEditUtils.distribute_clips_by_rhythm(
                video_clips=video_clips,
                rhythm_points=rhythm_points,
                max_duration=music_duration,
                min_clip_duration=min_clip_duration  # 传递最小片段时长参数
            )
        elif strategy == "energy":
            # 分析音乐分段
            music_segments = MusicUtils.analyze_music_segments(music_path)
            
            # 根据音乐能量分配视频片段
            distributed_clips = AutoEditUtils.distribute_clips_by_energy(
                video_clips=video_clips,
                music_segments=music_segments
            )
        else:  # "even" 或其他
            # 均匀分配视频片段
            distributed_clips = AutoEditUtils.distribute_clips_evenly(
                video_clips=video_clips,
                music_duration=music_duration,
                min_clip_duration=min_clip_duration  # 传递最小片段时长参数
            )
            
        # 创建编辑计划
        edit_plan = {
            "video_clips": video_clips,
            "music_path": music_path,
            "music_duration": music_duration,
            "strategy": strategy,
            "distributed_clips": distributed_clips,
            "total_clips": len(distributed_clips)
        }
        
        return edit_plan
    
    @staticmethod
    async def execute_edit_plan(
        edit_plan: Dict[str, Any],
        output_path: str,
        transition_type: Optional[str] = None,
        transition_duration: float = 0.5
    ) -> Dict[str, Any]:
        """
        执行编辑计划
        
        Args:
            edit_plan: 编辑计划
            output_path: 输出视频路径
            transition_type: 转场类型（None/fade/dissolve/wipe/slide）
            transition_duration: 转场持续时间（秒）
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        # 获取分配后的视频片段
        distributed_clips = edit_plan["distributed_clips"]
        
        if not distributed_clips:
            raise ValueError("No distributed clips in edit plan")
            
        # 创建临时目录
        temp_dir = os.path.join(settings.DATA_DIR, "temp", f"auto_edit_{Path(output_path).stem}")
        os.makedirs(temp_dir, exist_ok=True)
        
        # 保存所有生成的临时文件路径
        all_temp_files = []
        
        try:
            # 裁剪每个视频片段
            trimmed_paths = []
            for i, clip in enumerate(distributed_clips):
                # 生成临时文件路径
                temp_path = os.path.join(temp_dir, f"clip_{i}.mp4")
                all_temp_files.append(temp_path)
                
                # 裁剪视频
                success = await VideoUtils.trim_video(
                    input_path=clip["path"],
                    output_path=temp_path,
                    start_time=clip["start_time"],
                    end_time=clip["end_time"],
                    copy_codec=False
                )
                
                if not success:
                    logger.error(f"Failed to trim video clip {i}")
                    continue
                    
                trimmed_paths.append(temp_path)
                
            if not trimmed_paths:
                raise RuntimeError("Failed to trim any video clips")
                
            # 合并视频片段
            if transition_type:
                # 使用转场效果合并
                # 由于转场需要一对一处理，需要逐步合并
                current_output = trimmed_paths[0]
                
                for i in range(1, len(trimmed_paths)):
                    # 生成临时文件路径
                    temp_output = os.path.join(temp_dir, f"merged_{i}.mp4")
                    all_temp_files.append(temp_output)
                    
                    # 应用转场效果
                    success = False
                    
                    if transition_type == "fade":
                        success = await VideoUtils.apply_fade_transition(
                            video1_path=current_output,
                            video2_path=trimmed_paths[i],
                            output_path=temp_output,
                            fade_type="fade",
                            duration=transition_duration
                        )
                    elif transition_type == "dissolve":
                        success = await VideoUtils.apply_fade_transition(
                            video1_path=current_output,
                            video2_path=trimmed_paths[i],
                            output_path=temp_output,
                            fade_type="dissolve",
                            duration=transition_duration
                        )
                    elif transition_type == "wipe":
                        success = await VideoUtils.apply_wipe_transition(
                            video1_path=current_output,
                            video2_path=trimmed_paths[i],
                            output_path=temp_output,
                            direction="left-to-right",
                            duration=transition_duration
                        )
                    elif transition_type == "slide":
                        success = await VideoUtils.apply_slide_transition(
                            video1_path=current_output,
                            video2_path=trimmed_paths[i],
                            output_path=temp_output,
                            direction="left",
                            duration=transition_duration
                        )
                    else:
                        # 默认使用淡入淡出
                        success = await VideoUtils.apply_fade_transition(
                            video1_path=current_output,
                            video2_path=trimmed_paths[i],
                            output_path=temp_output,
                            fade_type="fade",
                            duration=transition_duration
                        )
                    
                    if not success:
                        logger.error(f"Failed to apply transition between clips {i-1} and {i}")
                        # 如果转场失败，尝试直接合并
                        success = await VideoUtils.merge_videos(
                            input_paths=[current_output, trimmed_paths[i]],
                            output_path=temp_output
                        )
                        
                        if not success:
                            logger.error(f"Failed to merge clips {i-1} and {i}")
                            continue
                    
                    # 更新当前输出
                    current_output = temp_output
                
                # 最终输出
                merged_path = current_output
            else:
                # 直接合并所有片段
                merged_path = os.path.join(temp_dir, "merged.mp4")
                all_temp_files.append(merged_path)
                
                success = await VideoUtils.merge_videos(
                    input_paths=trimmed_paths,
                    output_path=merged_path
                )
                
                if not success:
                    raise RuntimeError("Failed to merge video clips")
            
            # 添加背景音乐
            # 构建FFmpeg命令
            cmd = [
                settings.FFMPEG_PATH,
                "-y",  # 覆盖输出文件
                "-i", merged_path,  # 视频输入
                "-i", edit_plan["music_path"],  # 音乐输入
                "-filter_complex", 
                # 将音乐裁剪到视频长度，并设置音量
                f"[1:a]atrim=0:{edit_plan['music_duration']},asetpts=PTS-STARTPTS,volume=0.8[a]",
                "-map", "0:v",  # 使用视频流
                "-map", "[a]",  # 使用处理后的音频流
                "-c:v", "copy",  # 复制视频编码
                "-c:a", "aac",  # 音频使用AAC编码
                "-shortest",  # 使用最短的流长度
                output_path
            ]
            
            # 执行命令
            success, _ = await VideoUtils.run_ffmpeg_command(cmd)
            
            if not success:
                raise RuntimeError("Failed to add background music")
                
            # 获取最终视频信息
            output_info = await VideoUtils.get_video_info(output_path)
            
            return {
                "status": "success",
                "output_path": output_path,
                "duration": output_info["duration"],
                "size": output_info["size"],
                "video_info": output_info,
                "clip_count": len(distributed_clips),
                "strategy": edit_plan["strategy"]
            }
        finally:
            # 清理所有临时文件，确保无论执行成功或失败都会清理
            logger.info(f"Cleaning up {len(all_temp_files)} temporary files")
            for temp_file in all_temp_files:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                        logger.debug(f"Removed temporary file: {temp_file}")
                    except Exception as e:
                        logger.warning(f"Failed to remove temporary file {temp_file}: {str(e)}")
            
            # 尝试删除临时目录
            try:
                # 检查目录是否为空
                if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                    os.rmdir(temp_dir)
                    logger.info(f"Removed temporary directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to remove temporary directory {temp_dir}: {str(e)}") 