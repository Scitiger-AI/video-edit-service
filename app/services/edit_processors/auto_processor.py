from typing import Dict, Any, List
import os
from . import register_processor
from .base import EditProcessor
from ...core.logging import logger
from ...core.config import settings
from ...utils.video_utils import VideoUtils
from ...utils.music_utils import MusicUtils
from ...utils.auto_edit_utils import AutoEditUtils


@register_processor
class AutoProcessor(EditProcessor):
    """自动剪辑处理器"""
    
    @property
    def processor_name(self) -> str:
        return "auto"
    
    @property
    def supported_operations(self) -> List[str]:
        return [
            "music_edit",      # 基于音乐的自动剪辑
            "smart_edit",      # 智能剪辑
            "highlight_edit"   # 精彩片段剪辑
        ]
    
    async def validate_parameters(self, operation: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证操作参数
        
        Args:
            operation: 操作类型
            parameters: 操作参数
            
        Returns:
            Dict[str, Any]: 验证后的参数
        """
        if operation not in self.supported_operations:
            raise ValueError(f"Unsupported operation: {operation}")
        
        # 验证通用参数
        if "video_paths" not in parameters or not parameters["video_paths"]:
            raise ValueError("Missing required parameter: video_paths")
        
        if not isinstance(parameters["video_paths"], list):
            raise ValueError("video_paths must be a list")
            
        # 视频路径验证将在process_video中进行
        
        # 根据不同操作类型验证参数
        if operation == "music_edit":
            # 验证音乐编辑参数
            if "music_path" not in parameters:
                raise ValueError("Missing required parameter: music_path")
                
            # 音乐文件验证将在process_video中进行
                
            # 设置默认值
            if "strategy" not in parameters:
                parameters["strategy"] = "rhythm"
            elif parameters["strategy"] not in ["rhythm", "energy", "even"]:
                raise ValueError("Invalid strategy, must be one of: rhythm, energy, even")
                
            if "transition_type" not in parameters:
                parameters["transition_type"] = "fade"
            elif parameters["transition_type"] not in [None, "fade", "dissolve", "wipe", "slide"]:
                raise ValueError("Invalid transition_type")
                
            if "transition_duration" not in parameters:
                parameters["transition_duration"] = 0.5
            else:
                try:
                    parameters["transition_duration"] = float(parameters["transition_duration"])
                    if parameters["transition_duration"] < 0 or parameters["transition_duration"] > 2.0:
                        raise ValueError("transition_duration must be between 0 and 2.0 seconds")
                except (ValueError, TypeError):
                    raise ValueError("transition_duration must be a number")
            
            # 验证最小片段时长参数
            if "min_clip_duration" not in parameters:
                parameters["min_clip_duration"] = 2.0  # 默认2秒
            else:
                try:
                    parameters["min_clip_duration"] = float(parameters["min_clip_duration"])
                    if parameters["min_clip_duration"] < 0.5 or parameters["min_clip_duration"] > 10.0:
                        raise ValueError("min_clip_duration must be between 0.5 and 10.0 seconds")
                except (ValueError, TypeError):
                    raise ValueError("min_clip_duration must be a number")
                
        elif operation == "smart_edit":
            # 验证智能剪辑参数
            if "target_duration" not in parameters:
                parameters["target_duration"] = 30.0  # 默认30秒
            else:
                try:
                    parameters["target_duration"] = float(parameters["target_duration"])
                    if parameters["target_duration"] <= 0:
                        raise ValueError("target_duration must be positive")
                except (ValueError, TypeError):
                    raise ValueError("target_duration must be a number")
                    
            # 如果提供了音乐路径，在process_video中验证
                    
            if "transition_type" not in parameters:
                parameters["transition_type"] = "fade"
            elif parameters["transition_type"] not in [None, "fade", "dissolve", "wipe", "slide"]:
                raise ValueError("Invalid transition_type")
                
            if "transition_duration" not in parameters:
                parameters["transition_duration"] = 0.5
                
        elif operation == "highlight_edit":
            # 验证精彩片段剪辑参数
            # 如果提供了音乐路径，在process_video中验证
                    
            if "highlight_count" not in parameters:
                parameters["highlight_count"] = 5  # 默认5个精彩片段
            else:
                try:
                    parameters["highlight_count"] = int(parameters["highlight_count"])
                    if parameters["highlight_count"] <= 0:
                        raise ValueError("highlight_count must be positive")
                except (ValueError, TypeError):
                    raise ValueError("highlight_count must be an integer")
                    
            if "clip_duration" not in parameters:
                parameters["clip_duration"] = 3.0  # 默认每个片段3秒
            else:
                try:
                    parameters["clip_duration"] = float(parameters["clip_duration"])
                    if parameters["clip_duration"] <= 0:
                        raise ValueError("clip_duration must be positive")
                except (ValueError, TypeError):
                    raise ValueError("clip_duration must be a number")
                    
            if "transition_type" not in parameters:
                parameters["transition_type"] = "fade"
                
        return parameters
    
    async def process_video(self, operation: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理视频
        
        Args:
            operation: 操作类型
            parameters: 操作参数
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        logger.info(f"Processing video with {operation} operation")
        
        # 处理视频路径列表
        if "video_paths" in parameters:
            parameters["video_paths"] = await self.process_file_paths(parameters["video_paths"], "video")
            logger.info(f"已处理视频路径列表: {parameters['video_paths']}")
        
        # 处理音乐路径
        if "music_path" in parameters:
            parameters["music_path"] = await self.process_audio_path(parameters["music_path"])
            logger.info(f"已处理音乐路径: {parameters['music_path']}")
        
        # 实现自动剪辑逻辑
        if operation == "music_edit":
            # 实现基于音乐的自动剪辑
            return await self._music_edit(parameters)
        elif operation == "smart_edit":
            # 实现智能剪辑
            return await self._smart_edit(parameters)
        elif operation == "highlight_edit":
            # 实现精彩片段剪辑
            return await self._highlight_edit(parameters)
        else:
            raise ValueError(f"Unsupported operation: {operation}")
    
    async def _music_edit(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """基于音乐的自动剪辑"""
        video_paths = parameters["video_paths"]
        music_path = parameters["music_path"]
        strategy = parameters.get("strategy", "rhythm")
        transition_type = parameters.get("transition_type", "fade")
        transition_duration = parameters.get("transition_duration", 0.5)
        # 获取最小片段时长参数，默认为2.0秒
        min_clip_duration = parameters.get("min_clip_duration", 2.0)
        
        logger.info(f"Performing music-based auto edit with {len(video_paths)} videos and strategy: {strategy}")
        
        # 获取输出路径
        output_path = VideoUtils.get_output_path(self.processor_name, "music_edit")
        
        # 创建编辑计划
        edit_plan = await AutoEditUtils.create_edit_plan(
            video_paths=video_paths,
            music_path=music_path,
            strategy=strategy,
            min_clip_duration=min_clip_duration  # 传递最小片段时长参数
        )
        
        # 执行编辑计划
        result = await AutoEditUtils.execute_edit_plan(
            edit_plan=edit_plan,
            output_path=output_path,
            transition_type=transition_type,
            transition_duration=transition_duration
        )
        
        # 添加额外信息
        result["operation"] = "music_edit"
        result["strategy"] = strategy
        result["music_path"] = music_path
        result["video_count"] = len(video_paths)
        
        return result
    
    async def _smart_edit(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """智能剪辑"""
        video_paths = parameters["video_paths"]
        target_duration = parameters.get("target_duration", 30.0)
        music_path = parameters.get("music_path")
        transition_type = parameters.get("transition_type", "fade")
        transition_duration = parameters.get("transition_duration", 0.5)
        
        logger.info(f"Performing smart edit with {len(video_paths)} videos, target duration: {target_duration}s")
        
        # 获取输出路径
        output_path = VideoUtils.get_output_path(self.processor_name, "smart_edit")
        
        # 分析视频片段
        video_clips = await AutoEditUtils.analyze_video_clips(video_paths)
        
        if not video_clips:
            raise ValueError("No valid video clips found")
        
        # 如果提供了音乐，使用音乐编辑模式
        if music_path:
            # 获取音乐时长
            music_duration = MusicUtils.get_music_duration(music_path)
            
            # 如果目标时长大于音乐时长，使用音乐时长
            if target_duration > music_duration:
                target_duration = music_duration
                logger.info(f"Adjusted target duration to match music: {target_duration}s")
                
            # 创建编辑计划
            edit_plan = {
                "video_clips": video_clips,
                "music_path": music_path,
                "music_duration": target_duration,
                "strategy": "even",
                "distributed_clips": AutoEditUtils.distribute_clips_evenly(
                    video_clips=video_clips,
                    music_duration=target_duration
                ),
                "total_clips": len(video_clips)
            }
        else:
            # 不使用音乐，直接均匀分配视频片段
            total_video_duration = sum(clip["duration"] for clip in video_clips)
            
            # 如果视频总时长小于目标时长，使用视频总时长
            if total_video_duration < target_duration:
                target_duration = total_video_duration
                logger.info(f"Adjusted target duration to match total video duration: {target_duration}s")
                
            # 创建编辑计划
            edit_plan = {
                "video_clips": video_clips,
                "music_path": None,
                "music_duration": target_duration,
                "strategy": "even",
                "distributed_clips": AutoEditUtils.distribute_clips_evenly(
                    video_clips=video_clips,
                    music_duration=target_duration
                ),
                "total_clips": len(video_clips)
            }
            
        # 执行编辑计划
        result = await AutoEditUtils.execute_edit_plan(
            edit_plan=edit_plan,
            output_path=output_path,
            transition_type=transition_type,
            transition_duration=transition_duration
        )
        
        # 添加额外信息
        result["operation"] = "smart_edit"
        result["target_duration"] = target_duration
        result["video_count"] = len(video_paths)
        
        return result
    
    async def _highlight_edit(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """精彩片段剪辑"""
        video_paths = parameters["video_paths"]
        highlight_count = parameters.get("highlight_count", 5)
        clip_duration = parameters.get("clip_duration", 3.0)
        music_path = parameters.get("music_path")
        transition_type = parameters.get("transition_type", "fade")
        transition_duration = parameters.get("transition_duration", 0.5)
        
        logger.info(f"Performing highlight edit with {len(video_paths)} videos, {highlight_count} highlights")
        
        # 获取输出路径
        output_path = VideoUtils.get_output_path(self.processor_name, "highlight_edit")
        
        # 分析视频片段
        video_clips = await AutoEditUtils.analyze_video_clips(video_paths)
        
        if not video_clips:
            raise ValueError("No valid video clips found")
            
        # 从每个视频中选择一个随机位置作为精彩片段
        # 实际应用中，这里可以使用更复杂的算法来检测精彩片段
        highlight_clips = []
        
        for clip in video_clips:
            # 如果视频时长小于片段时长，使用整个视频
            if clip["duration"] <= clip_duration:
                highlight_clips.append({
                    **clip,
                    "start_time": 0,
                    "end_time": clip["duration"]
                })
            else:
                # 随机选择一个起始点
                import random
                start_time = random.uniform(0, clip["duration"] - clip_duration)
                highlight_clips.append({
                    **clip,
                    "start_time": start_time,
                    "end_time": start_time + clip_duration
                })
                
        # 如果精彩片段数量超过要求，随机选择
        if len(highlight_clips) > highlight_count:
            highlight_clips = random.sample(highlight_clips, highlight_count)
            
        # 计算总时长
        total_duration = sum(clip["end_time"] - clip["start_time"] for clip in highlight_clips)
        
        # 创建编辑计划
        if music_path:
            # 获取音乐时长
            music_duration = MusicUtils.get_music_duration(music_path)
            
            # 如果音乐时长小于视频总时长，调整视频片段
            if music_duration < total_duration:
                # 按比例缩短每个片段
                ratio = music_duration / total_duration
                for clip in highlight_clips:
                    duration = (clip["end_time"] - clip["start_time"]) * ratio
                    clip["end_time"] = clip["start_time"] + duration
                    
                total_duration = music_duration
                
            edit_plan = {
                "video_clips": video_clips,
                "music_path": music_path,
                "music_duration": total_duration,
                "strategy": "highlight",
                "distributed_clips": [],
                "total_clips": len(highlight_clips)
            }
        else:
            edit_plan = {
                "video_clips": video_clips,
                "music_path": None,
                "music_duration": total_duration,
                "strategy": "highlight",
                "distributed_clips": [],
                "total_clips": len(highlight_clips)
            }
            
        # 设置分布信息
        current_time = 0.0
        for clip in highlight_clips:
            duration = clip["end_time"] - clip["start_time"]
            clip["output_start_time"] = current_time
            clip["output_end_time"] = current_time + duration
            current_time += duration
            edit_plan["distributed_clips"].append(clip)
            
        # 执行编辑计划
        result = await AutoEditUtils.execute_edit_plan(
            edit_plan=edit_plan,
            output_path=output_path,
            transition_type=transition_type,
            transition_duration=transition_duration
        )
        
        # 添加额外信息
        result["operation"] = "highlight_edit"
        result["highlight_count"] = len(highlight_clips)
        result["video_count"] = len(video_paths)
        
        return result 