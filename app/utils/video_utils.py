import os
import uuid
import asyncio
import subprocess
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from pathlib import Path
from ..core.config import settings
from ..core.logging import logger


class VideoUtils:
    """视频处理工具类"""
    
    @staticmethod
    def get_output_path(processor: str, operation: str, extension: str = "mp4") -> str:
        """
        生成输出文件路径
        
        Args:
            processor: 处理器名称
            operation: 操作类型
            extension: 文件扩展名
            
        Returns:
            str: 输出文件路径
        """
        # 确保数据目录存在
        data_dir = Path(settings.DATA_DIR) / "videos"
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_id = str(uuid.uuid4())[:8]
        filename = f"{processor}_{operation}_{timestamp}_{random_id}.{extension}"
        
        return str(data_dir / filename)
    
    @staticmethod
    async def get_video_info(video_path: str) -> Dict[str, Any]:
        """
        获取视频信息
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            Dict[str, Any]: 视频信息
        """
        # 构建FFprobe命令
        cmd = [
            settings.FFPROBE_PATH,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path
        ]
        
        try:
            # 执行命令
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"FFprobe error: {stderr.decode()}")
                raise RuntimeError(f"Failed to get video info: {stderr.decode()}")
            
            # 解析JSON输出
            import json
            info = json.loads(stdout.decode())
            
            # 提取关键信息
            result = {
                "format": info.get("format", {}),
                "duration": float(info.get("format", {}).get("duration", 0)),
                "size": int(info.get("format", {}).get("size", 0)),
                "bit_rate": int(info.get("format", {}).get("bit_rate", 0)),
                "streams": []
            }
            
            # 提取流信息
            for stream in info.get("streams", []):
                if stream.get("codec_type") == "video":
                    result["streams"].append({
                        "codec": stream.get("codec_name"),
                        "width": stream.get("width"),
                        "height": stream.get("height"),
                        "fps": eval(stream.get("avg_frame_rate", "0/1")),
                        "codec_type": "video"
                    })
                elif stream.get("codec_type") == "audio":
                    result["streams"].append({
                        "codec": stream.get("codec_name"),
                        "channels": stream.get("channels"),
                        "sample_rate": stream.get("sample_rate"),
                        "codec_type": "audio"
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting video info: {str(e)}")
            raise
    
    @staticmethod
    async def run_ffmpeg_command(cmd: List[str], log_output: bool = True) -> Tuple[bool, str]:
        """
        执行FFmpeg命令
        
        Args:
            cmd: FFmpeg命令参数列表
            log_output: 是否记录输出
            
        Returns:
            Tuple[bool, str]: (是否成功, 错误信息)
        """
        try:
            # 执行命令
            logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode()
                logger.error(f"FFmpeg error: {error_msg}")
                return False, error_msg
            
            if log_output and stderr:
                logger.info(f"FFmpeg output: {stderr.decode()}")
            
            return True, ""
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error running FFmpeg command: {error_msg}")
            return False, error_msg
    
    @staticmethod
    async def trim_video(
        input_path: str,
        output_path: str,
        start_time: float,
        end_time: float,
        copy_codec: bool = True
    ) -> bool:
        """
        裁剪视频
        
        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            start_time: 开始时间（秒）
            end_time: 结束时间（秒）
            copy_codec: 是否复制编解码器（不重新编码）
            
        Returns:
            bool: 是否成功
        """
        # 检查输入文件是否存在
        if not os.path.exists(input_path):
            logger.error(f"Input video file not found: {input_path}")
            return False
        
        # 获取视频信息，检查时长
        try:
            video_info = await VideoUtils.get_video_info(input_path)
            total_duration = video_info["duration"]
            
            # 检查裁剪范围是否有效
            if start_time >= total_duration:
                logger.error(f"Start time ({start_time}s) exceeds video duration ({total_duration}s)")
                return False
                
            if end_time > total_duration:
                logger.warning(f"End time ({end_time}s) exceeds video duration ({total_duration}s), using video duration instead")
                end_time = total_duration
        except Exception as e:
            logger.error(f"Failed to get video info: {str(e)}")
            # 继续执行，不中断流程
        
        # 构建FFmpeg命令
        cmd = [
            settings.FFMPEG_PATH,
            "-y",  # 覆盖输出文件
            "-i", input_path
        ]
        
        # 注意：先指定起始位置，再指定持续时间，这样更准确
        cmd.extend(["-ss", str(start_time)])
        cmd.extend(["-t", str(end_time - start_time)])
        
        if copy_codec:
            # 对于短视频片段，使用-c copy可能会导致精度问题，因为需要关键帧
            # 但我们仍然提供这个选项，因为它处理速度快
            cmd.extend(["-c", "copy"])
        else:
            # 重新编码，更精确但更慢
            cmd.extend(["-c:v", "libx264", "-c:a", "aac", "-strict", "experimental"])
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        cmd.append(output_path)
        
        # 执行命令
        success, error = await VideoUtils.run_ffmpeg_command(cmd)
        
        # 验证输出文件
        if success and os.path.exists(output_path):
            try:
                # 检查输出文件是否有效
                output_info = await VideoUtils.get_video_info(output_path)
                if output_info["duration"] == 0 or not output_info["streams"]:
                    logger.error(f"Generated video file is invalid: {output_path}")
                    
                    # 尝试重新编码
                    if copy_codec:
                        logger.info("Retrying with re-encoding instead of stream copying")
                        return await VideoUtils.trim_video(
                            input_path=input_path,
                            output_path=output_path,
                            start_time=start_time,
                            end_time=end_time,
                            copy_codec=False
                        )
                    return False
            except Exception as e:
                logger.error(f"Error validating output file: {str(e)}")
                return False
                
            return True
        else:
            logger.error(f"Failed to create output file: {output_path}")
            return False
    
    @staticmethod
    async def split_video(
        input_path: str,
        output_dir: str,
        split_points: List[float],
        copy_codec: bool = True
    ) -> List[str]:
        """
        分割视频
        
        Args:
            input_path: 输入视频路径
            output_dir: 输出目录
            split_points: 分割点列表（秒）
            copy_codec: 是否复制编解码器（不重新编码）
            
        Returns:
            List[str]: 分段视频路径列表
        """
        # 获取视频信息
        video_info = await VideoUtils.get_video_info(input_path)
        total_duration = video_info["duration"]
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 排序分割点
        split_points = sorted(split_points)
        
        # 添加开始和结束点
        points = [0] + split_points + [total_duration]
        
        # 存储输出路径
        output_paths = []
        
        # 分割视频
        for i in range(len(points) - 1):
            start_time = points[i]
            end_time = points[i + 1]
            
            # 跳过过短的片段
            if end_time - start_time < 0.1:
                continue
            
            # 生成输出路径
            output_path = os.path.join(output_dir, f"part_{i}.mp4")
            output_paths.append(output_path)
            
            # 裁剪视频
            success = await VideoUtils.trim_video(
                input_path=input_path,
                output_path=output_path,
                start_time=start_time,
                end_time=end_time,
                copy_codec=copy_codec
            )
            
            if not success:
                logger.error(f"Failed to split video at {start_time}-{end_time}")
                return []
        
        return output_paths
    
    @staticmethod
    async def merge_videos(
        input_paths: List[str],
        output_path: str,
        transition: Optional[str] = None
    ) -> bool:
        """
        合并视频
        
        Args:
            input_paths: 输入视频路径列表
            output_path: 输出视频路径
            transition: 转场类型（可选）
            
        Returns:
            bool: 是否成功
        """
        if not input_paths:
            logger.error("No input videos to merge")
            return False
        
        # 检查所有输入文件是否存在
        for path in input_paths:
            if not os.path.exists(path):
                logger.error(f"Input video file not found: {path}")
                return False
        
        # 创建临时文件列表
        temp_list_path = f"{output_path}.txt"
        with open(temp_list_path, "w") as f:
            for path in input_paths:
                f.write(f"file '{os.path.abspath(path)}'\n")
        
        try:
            # 构建FFmpeg命令
            cmd = [
                settings.FFMPEG_PATH,
                "-y",  # 覆盖输出文件
                "-f", "concat",
                "-safe", "0",
                "-i", temp_list_path
            ]
            
            # 如果有转场效果，需要更复杂的处理
            if transition:
                # TODO: 实现转场效果
                pass
            else:
                # 简单合并
                cmd.extend(["-c", "copy", output_path])
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 执行命令
            success, _ = await VideoUtils.run_ffmpeg_command(cmd)
            
            # 删除临时文件
            os.remove(temp_list_path)
            
            return success
            
        except Exception as e:
            logger.error(f"Error merging videos: {str(e)}")
            
            # 清理临时文件
            if os.path.exists(temp_list_path):
                os.remove(temp_list_path)
                
            return False
    
    @staticmethod
    async def adjust_speed(
        input_path: str,
        output_path: str,
        speed_factor: float
    ) -> bool:
        """
        调整视频速度
        
        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            speed_factor: 速度因子（>1加速，<1减速）
            
        Returns:
            bool: 是否成功
        """
        # 检查输入文件是否存在
        if not os.path.exists(input_path):
            logger.error(f"Input video file not found: {input_path}")
            return False
        
        # 获取视频信息，检查是否有音频流
        has_audio = False
        try:
            video_info = await VideoUtils.get_video_info(input_path)
            for stream in video_info["streams"]:
                if stream.get("codec_type") == "audio":
                    has_audio = True
                    break
        except Exception as e:
            logger.error(f"Failed to get video info: {str(e)}")
            # 继续执行，假设没有音频
        
        # 根据是否有音频流构建不同的滤镜
        if has_audio:
            filter_complex = f"[0:v]setpts={1/speed_factor}*PTS[v];[0:a]atempo={speed_factor}[a]"
            map_options = ["-map", "[v]", "-map", "[a]"]
        else:
            # 只处理视频流
            filter_complex = f"[0:v]setpts={1/speed_factor}*PTS[v]"
            map_options = ["-map", "[v]"]
        
        # 构建FFmpeg命令
        cmd = [
            settings.FFMPEG_PATH,
            "-y",  # 覆盖输出文件
            "-i", input_path,
            "-filter_complex", filter_complex
        ]
        
        # 添加映射选项
        cmd.extend(map_options)
        
        # 添加编码器选项
        cmd.extend(["-c:v", "libx264"])
        if has_audio:
            cmd.extend(["-c:a", "aac"])
        
        # 添加输出路径
        cmd.append(output_path)
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 执行命令
        success, _ = await VideoUtils.run_ffmpeg_command(cmd)
        return success
    
    @staticmethod
    async def reverse_video(
        input_path: str,
        output_path: str,
        with_audio: bool = False
    ) -> bool:
        """
        视频倒放
        
        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            with_audio: 是否同时倒放音频
            
        Returns:
            bool: 是否成功
        """
        # 检查输入文件是否存在
        if not os.path.exists(input_path):
            logger.error(f"Input video file not found: {input_path}")
            return False
        
        # 获取视频信息，检查是否有音频流
        has_audio = False
        try:
            video_info = await VideoUtils.get_video_info(input_path)
            for stream in video_info["streams"]:
                if stream.get("codec_type") == "audio":
                    has_audio = True
                    break
        except Exception as e:
            logger.error(f"Failed to get video info: {str(e)}")
            # 继续执行，假设没有音频
        
        # 构建FFmpeg命令
        cmd = [
            settings.FFMPEG_PATH,
            "-y",  # 覆盖输出文件
            "-i", input_path,
            "-vf", "reverse",
            "-c:v", "libx264"
        ]
        
        # 处理音频（如果有且需要倒放）
        if has_audio:
            if with_audio:
                cmd.extend(["-af", "areverse", "-c:a", "aac"])
            else:
                cmd.extend(["-c:a", "copy"])
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        cmd.append(output_path)
        
        # 执行命令
        success, _ = await VideoUtils.run_ffmpeg_command(cmd)
        return success
        
    # 滤镜相关方法
    @staticmethod
    async def adjust_video_property(
        input_path: str, 
        output_path: str, 
        property_name: str, 
        level: float
    ) -> bool:
        """
        调整视频属性（亮度/对比度/饱和度）
        
        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            property_name: 属性名称（brightness/contrast/saturation）
            level: 调整级别（-100到100）
            
        Returns:
            bool: 是否成功
        """
        # 检查输入文件是否存在
        if not os.path.exists(input_path):
            logger.error(f"Input video file not found: {input_path}")
            return False
            
        # 将-100到100的值映射到FFmpeg参数范围
        if property_name == "brightness":
            # 亮度: -1.0到1.0
            value = level / 100
            filter_expr = f"eq=brightness={value}"
        elif property_name == "contrast":
            # 对比度: 0到2.0 (1.0是正常值)
            value = 1.0 + (level / 100)
            filter_expr = f"eq=contrast={value}"
        elif property_name == "saturation":
            # 饱和度: 0到3.0 (1.0是正常值)
            value = 1.0 + (level / 50)
            filter_expr = f"eq=saturation={value}"
        else:
            logger.error(f"Unsupported property: {property_name}")
            return False
            
        # 构建FFmpeg命令
        cmd = [
            settings.FFMPEG_PATH,
            "-y",  # 覆盖输出文件
            "-i", input_path,
            "-vf", filter_expr,
            "-c:v", "libx264",
            "-c:a", "copy",
            output_path
        ]
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 执行命令
        success, _ = await VideoUtils.run_ffmpeg_command(cmd)
        return success
        
    @staticmethod
    async def apply_blur(
        input_path: str, 
        output_path: str, 
        radius: float
    ) -> bool:
        """
        应用模糊效果
        
        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            radius: 模糊半径
            
        Returns:
            bool: 是否成功
        """
        # 检查输入文件是否存在
        if not os.path.exists(input_path):
            logger.error(f"Input video file not found: {input_path}")
            return False
            
        # 构建FFmpeg命令
        # 使用boxblur滤镜: luma_radius:luma_power:chroma_radius:chroma_power:alpha_radius:alpha_power
        filter_expr = f"boxblur={radius}:1"
        
        cmd = [
            settings.FFMPEG_PATH,
            "-y",  # 覆盖输出文件
            "-i", input_path,
            "-vf", filter_expr,
            "-c:v", "libx264",
            "-c:a", "copy",
            output_path
        ]
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 执行命令
        success, _ = await VideoUtils.run_ffmpeg_command(cmd)
        return success
        
    @staticmethod
    async def apply_sharpen(
        input_path: str, 
        output_path: str, 
        amount: float
    ) -> bool:
        """
        应用锐化效果
        
        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            amount: 锐化强度
            
        Returns:
            bool: 是否成功
        """
        # 检查输入文件是否存在
        if not os.path.exists(input_path):
            logger.error(f"Input video file not found: {input_path}")
            return False
            
        # 构建FFmpeg命令
        # 使用unsharp滤镜: lx:ly:la:cx:cy:ca
        # lx/ly是矩阵大小，la是亮度强度，cx/cy是色度矩阵大小，ca是色度强度
        filter_expr = f"unsharp=5:5:{amount}:5:5:{amount/2}"
        
        cmd = [
            settings.FFMPEG_PATH,
            "-y",  # 覆盖输出文件
            "-i", input_path,
            "-vf", filter_expr,
            "-c:v", "libx264",
            "-c:a", "copy",
            output_path
        ]
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 执行命令
        success, _ = await VideoUtils.run_ffmpeg_command(cmd)
        return success
        
    @staticmethod
    async def apply_grayscale(
        input_path: str, 
        output_path: str
    ) -> bool:
        """
        应用灰度效果
        
        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            
        Returns:
            bool: 是否成功
        """
        # 检查输入文件是否存在
        if not os.path.exists(input_path):
            logger.error(f"Input video file not found: {input_path}")
            return False
            
        # 构建FFmpeg命令
        filter_expr = "format=gray"
        
        cmd = [
            settings.FFMPEG_PATH,
            "-y",  # 覆盖输出文件
            "-i", input_path,
            "-vf", filter_expr,
            "-c:v", "libx264",
            "-c:a", "copy",
            output_path
        ]
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 执行命令
        success, _ = await VideoUtils.run_ffmpeg_command(cmd)
        return success
        
    @staticmethod
    async def apply_sepia(
        input_path: str, 
        output_path: str
    ) -> bool:
        """
        应用复古效果
        
        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            
        Returns:
            bool: 是否成功
        """
        # 检查输入文件是否存在
        if not os.path.exists(input_path):
            logger.error(f"Input video file not found: {input_path}")
            return False
            
        # 构建FFmpeg命令
        # 使用colorchannelmixer滤镜创建复古效果
        filter_expr = "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131"
        
        cmd = [
            settings.FFMPEG_PATH,
            "-y",  # 覆盖输出文件
            "-i", input_path,
            "-vf", filter_expr,
            "-c:v", "libx264",
            "-c:a", "copy",
            output_path
        ]
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 执行命令
        success, _ = await VideoUtils.run_ffmpeg_command(cmd)
        return success
        
    @staticmethod
    async def apply_vignette(
        input_path: str, 
        output_path: str, 
        amount: float
    ) -> bool:
        """
        应用暗角效果
        
        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            amount: 暗角强度（0-1）
            
        Returns:
            bool: 是否成功
        """
        # 检查输入文件是否存在
        if not os.path.exists(input_path):
            logger.error(f"Input video file not found: {input_path}")
            return False
            
        # 构建FFmpeg命令
        # 使用vignette滤镜
        angle = 1 - amount  # 角度值越小，暗角效果越强
        filter_expr = f"vignette=angle={angle}:mode=backward"
        
        cmd = [
            settings.FFMPEG_PATH,
            "-y",  # 覆盖输出文件
            "-i", input_path,
            "-vf", filter_expr,
            "-c:v", "libx264",
            "-c:a", "copy",
            output_path
        ]
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 执行命令
        success, _ = await VideoUtils.run_ffmpeg_command(cmd)
        return success
    
    # 转场相关方法
    @staticmethod
    async def apply_fade_transition(
        video1_path: str,
        video2_path: str,
        output_path: str,
        fade_type: str = "fade",
        duration: float = 1.0
    ) -> bool:
        """
        应用淡入淡出类转场效果
        
        Args:
            video1_path: 第一个视频路径
            video2_path: 第二个视频路径
            output_path: 输出视频路径
            fade_type: 淡化类型（fade/dissolve/crossfade）
            duration: 转场持续时间（秒）
            
        Returns:
            bool: 是否成功
        """
        # 检查输入文件是否存在
        if not os.path.exists(video1_path) or not os.path.exists(video2_path):
            logger.error(f"Input video file not found: {video1_path} or {video2_path}")
            return False
            
        # 获取视频信息
        try:
            video1_info = await VideoUtils.get_video_info(video1_path)
            video2_info = await VideoUtils.get_video_info(video2_path)
            
            video1_duration = video1_info["duration"]
            
            # 确保转场时间不超过视频时长
            if duration > video1_duration:
                duration = video1_duration / 2
                logger.warning(f"Transition duration adjusted to {duration}s")
            
            # 检查是否有音频流
            has_audio = False
            for stream in video1_info["streams"]:
                if stream.get("codec_type") == "audio":
                    has_audio = True
                    break
                
        except Exception as e:
            logger.error(f"Failed to get video info: {str(e)}")
            # 继续执行，使用默认值
            video1_duration = 0
            has_audio = False
        
        # 根据不同的淡化类型选择不同的滤镜
        if fade_type == "dissolve":
            # 溶解效果：第一个视频淡出，第二个视频淡入，有重叠
            filter_complex = (
                f"[0:v]trim=0:{video1_duration},setpts=PTS-STARTPTS[v1];"
                f"[1:v]trim=0:{duration},setpts=PTS-STARTPTS[v2];"
                f"[v1]fade=t=out:st={video1_duration-duration}:d={duration}[fadeout];"
                f"[v2]fade=t=in:st=0:d={duration}[fadein];"
                f"[fadeout][fadein]overlay[outv]"
            )
        elif fade_type == "crossfade":
            # 交叉淡化：两个视频平滑过渡
            filter_complex = (
                f"[0:v]format=pix_fmts=yuva420p,fade=t=out:st={video1_duration-duration}:d={duration}:alpha=1,setpts=PTS-STARTPTS[va];"
                f"[1:v]format=pix_fmts=yuva420p,fade=t=in:st=0:d={duration}:alpha=1,setpts=PTS-STARTPTS[vb];"
                f"[va][vb]overlay=format=yuv420[outv]"
            )
        else:  # 默认fade
            # 简单淡入淡出：第一个视频结束时淡出，第二个视频开始时淡入，无重叠
            filter_complex = (
                f"[0:v]fade=t=out:st={video1_duration-duration}:d={duration}[fadeout];"
                f"[1:v]fade=t=in:st=0:d={duration}[fadein];"
                f"[fadeout][fadein]concat=n=2:v=1:a=0[outv]"
            )
            
        # 构建FFmpeg命令
        cmd = [
            settings.FFMPEG_PATH,
            "-y",  # 覆盖输出文件
            "-i", video1_path,
            "-i", video2_path,
            "-filter_complex", filter_complex,
            "-map", "[outv]"
        ]
        
        # 添加音频映射（如果有音频）
        if has_audio:
            cmd.extend(["-map", "0:a"])  # 使用第一个视频的音频
        
        # 添加编码器选项
        cmd.extend(["-c:v", "libx264"])
        if has_audio:
            cmd.extend(["-c:a", "aac"])
        
        # 添加输出路径
        cmd.append(output_path)
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 执行命令
        success, _ = await VideoUtils.run_ffmpeg_command(cmd)
        return success
        
    @staticmethod
    async def apply_wipe_transition(
        video1_path: str,
        video2_path: str,
        output_path: str,
        direction: str = "left-to-right",
        duration: float = 1.0
    ) -> bool:
        """
        应用擦除转场效果
        
        Args:
            video1_path: 第一个视频路径
            video2_path: 第二个视频路径
            output_path: 输出视频路径
            direction: 擦除方向（left-to-right/right-to-left/top-to-bottom/bottom-to-top）
            duration: 转场持续时间（秒）
            
        Returns:
            bool: 是否成功
        """
        # 检查输入文件是否存在
        if not os.path.exists(video1_path) or not os.path.exists(video2_path):
            logger.error(f"Input video file not found: {video1_path} or {video2_path}")
            return False
            
        # 获取视频信息
        try:
            video1_info = await VideoUtils.get_video_info(video1_path)
            video1_duration = video1_info["duration"]
            
            # 确保转场时间不超过视频时长
            if duration > video1_duration:
                duration = video1_duration / 2
                logger.warning(f"Transition duration adjusted to {duration}s")
                
            # 检查是否有音频流
            has_audio = False
            for stream in video1_info["streams"]:
                if stream.get("codec_type") == "audio":
                    has_audio = True
                    break
                
        except Exception as e:
            logger.error(f"Failed to get video info: {str(e)}")
            # 继续执行，使用默认值
            video1_duration = 0
            has_audio = False
        
        # 根据方向设置擦除参数
        if direction == "left-to-right":
            wipe_expr = f"'if(gte(X,(W*T/{duration})),B,A)'"
        elif direction == "right-to-left":
            wipe_expr = f"'if(lte(X,(W*(1-T/{duration}))),B,A)'"
        elif direction == "top-to-bottom":
            wipe_expr = f"'if(gte(Y,(H*T/{duration})),B,A)'"
        else:  # bottom-to-top
            wipe_expr = f"'if(lte(Y,(H*(1-T/{duration}))),B,A)'"
            
        # 构建FFmpeg命令
        cmd = [
            settings.FFMPEG_PATH,
            "-y",  # 覆盖输出文件
            "-i", video1_path,
            "-i", video2_path,
            "-filter_complex", (
                f"[0:v][1:v]blend=all_expr={wipe_expr}:enable='between(t,{video1_duration-duration},{video1_duration})'"
            )
        ]
        
        # 添加音频映射（如果有音频）
        if has_audio:
            cmd.extend(["-map", "0:a"])  # 使用第一个视频的音频
        
        # 添加编码器选项
        cmd.extend(["-c:v", "libx264"])
        if has_audio:
            cmd.extend(["-c:a", "aac"])
        
        # 添加输出路径
        cmd.append(output_path)
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 执行命令
        success, _ = await VideoUtils.run_ffmpeg_command(cmd)
        return success
        
    @staticmethod
    async def apply_slide_transition(
        video1_path: str,
        video2_path: str,
        output_path: str,
        direction: str = "left",
        duration: float = 1.0
    ) -> bool:
        """
        应用滑动转场效果
        
        Args:
            video1_path: 第一个视频路径
            video2_path: 第二个视频路径
            output_path: 输出视频路径
            direction: 滑动方向（left/right/up/down）
            duration: 转场持续时间（秒）
            
        Returns:
            bool: 是否成功
        """
        # 检查输入文件是否存在
        if not os.path.exists(video1_path) or not os.path.exists(video2_path):
            logger.error(f"Input video file not found: {video1_path} or {video2_path}")
            return False
            
        # 获取视频信息
        try:
            video1_info = await VideoUtils.get_video_info(video1_path)
            video1_duration = video1_info["duration"]
            
            # 确保转场时间不超过视频时长
            if duration > video1_duration:
                duration = video1_duration / 2
                logger.warning(f"Transition duration adjusted to {duration}s")
                
            # 检查是否有音频流
            has_audio = False
            for stream in video1_info["streams"]:
                if stream.get("codec_type") == "audio":
                    has_audio = True
                    break
                
        except Exception as e:
            logger.error(f"Failed to get video info: {str(e)}")
            # 继续执行，使用默认值
            video1_duration = 0
            has_audio = False
        
        # 根据方向设置滑动参数
        if direction == "left":
            slide_expr = f"x=W-W*min(1,max(0,(t-{video1_duration-duration})/{duration}))"
        elif direction == "right":
            slide_expr = f"x=-W+W*min(1,max(0,(t-{video1_duration-duration})/{duration}))"
        elif direction == "up":
            slide_expr = f"y=H-H*min(1,max(0,(t-{video1_duration-duration})/{duration}))"
        else:  # down
            slide_expr = f"y=-H+H*min(1,max(0,(t-{video1_duration-duration})/{duration}))"
            
        # 构建FFmpeg命令
        cmd = [
            settings.FFMPEG_PATH,
            "-y",  # 覆盖输出文件
            "-i", video1_path,
            "-i", video2_path,
            "-filter_complex", (
                f"[1:v]setpts=PTS-STARTPTS+{video1_duration-duration}/TB[v1];"
                f"[0:v][v1]overlay={slide_expr}:shortest=1[outv]"
            ),
            "-map", "[outv]"
        ]
        
        # 添加音频映射（如果有音频）
        if has_audio:
            cmd.extend(["-map", "0:a"])  # 使用第一个视频的音频
        
        # 添加编码器选项
        cmd.extend(["-c:v", "libx264"])
        if has_audio:
            cmd.extend(["-c:a", "aac"])
        
        # 添加输出路径
        cmd.append(output_path)
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 执行命令
        success, _ = await VideoUtils.run_ffmpeg_command(cmd)
        return success
        
    @staticmethod
    async def apply_zoom_transition(
        video1_path: str,
        video2_path: str,
        output_path: str,
        direction: str = "in",
        duration: float = 1.0
    ) -> bool:
        """
        应用缩放转场效果
        
        Args:
            video1_path: 第一个视频路径
            video2_path: 第二个视频路径
            output_path: 输出视频路径
            direction: 缩放方向（in/out）
            duration: 转场持续时间（秒）
            
        Returns:
            bool: 是否成功
        """
        # 检查输入文件是否存在
        if not os.path.exists(video1_path) or not os.path.exists(video2_path):
            logger.error(f"Input video file not found: {video1_path} or {video2_path}")
            return False
            
        # 获取视频信息
        try:
            video1_info = await VideoUtils.get_video_info(video1_path)
            video1_duration = video1_info["duration"]
            
            # 确保转场时间不超过视频时长
            if duration > video1_duration:
                duration = video1_duration / 2
                logger.warning(f"Transition duration adjusted to {duration}s")
                
            # 检查是否有音频流
            has_audio = False
            for stream in video1_info["streams"]:
                if stream.get("codec_type") == "audio":
                    has_audio = True
                    break
                
        except Exception as e:
            logger.error(f"Failed to get video info: {str(e)}")
            # 继续执行，使用默认值
            video1_duration = 0
            has_audio = False
        
        # 根据方向设置缩放参数
        if direction == "in":
            # 缩放入场：第二个视频从小到大
            zoom_expr = (
                f"[1:v]scale=2*iw:-1,zoompan=z='min(pzoom+0.04,1.5)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"fps=30:s=hd720,setpts=PTS-STARTPTS+{video1_duration-duration}/TB[zoom];"
                f"[0:v][zoom]overlay=shortest=1[outv]"
            )
        else:  # out
            # 缩放出场：第一个视频从大到小，第二个视频显现
            zoom_expr = (
                f"[0:v]scale=2*iw:-1,zoompan=z='if(lte(zoom,1.0),1.5,max(1.0,zoom-0.04))':d=1:"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':fps=30:s=hd720[zoom];"
                f"[zoom][1:v]overlay=shortest=1:enable='gte(t,{video1_duration-duration})'[outv]"
            )
            
        # 构建FFmpeg命令
        cmd = [
            settings.FFMPEG_PATH,
            "-y",  # 覆盖输出文件
            "-i", video1_path,
            "-i", video2_path,
            "-filter_complex", zoom_expr,
            "-map", "[outv]"
        ]
        
        # 添加音频映射（如果有音频）
        if has_audio:
            cmd.extend(["-map", "0:a"])  # 使用第一个视频的音频
        
        # 添加编码器选项
        cmd.extend(["-c:v", "libx264"])
        if has_audio:
            cmd.extend(["-c:a", "aac"])
        
        # 添加输出路径
        cmd.append(output_path)
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 执行命令
        success, _ = await VideoUtils.run_ffmpeg_command(cmd)
        return success
        
    @staticmethod
    async def apply_rotate_transition(
        video1_path: str,
        video2_path: str,
        output_path: str,
        direction: str = "clockwise",
        duration: float = 1.0
    ) -> bool:
        """
        应用旋转转场效果
        
        Args:
            video1_path: 第一个视频路径
            video2_path: 第二个视频路径
            output_path: 输出视频路径
            direction: 旋转方向（clockwise/counterclockwise）
            duration: 转场持续时间（秒）
            
        Returns:
            bool: 是否成功
        """
        # 检查输入文件是否存在
        if not os.path.exists(video1_path) or not os.path.exists(video2_path):
            logger.error(f"Input video file not found: {video1_path} or {video2_path}")
            return False
            
        # 获取视频信息
        try:
            video1_info = await VideoUtils.get_video_info(video1_path)
            video1_duration = video1_info["duration"]
            
            # 确保转场时间不超过视频时长
            if duration > video1_duration:
                duration = video1_duration / 2
                logger.warning(f"Transition duration adjusted to {duration}s")
                
            # 检查是否有音频流
            has_audio = False
            for stream in video1_info["streams"]:
                if stream.get("codec_type") == "audio":
                    has_audio = True
                    break
                
        except Exception as e:
            logger.error(f"Failed to get video info: {str(e)}")
            # 继续执行，使用默认值
            video1_duration = 0
            has_audio = False
        
        # 根据方向设置旋转参数
        angle_factor = 1 if direction == "clockwise" else -1
        
        # 构建FFmpeg命令
        cmd = [
            settings.FFMPEG_PATH,
            "-y",  # 覆盖输出文件
            "-i", video1_path,
            "-i", video2_path,
            "-filter_complex", (
                f"[0:v]rotate='if(gte(t,{video1_duration-duration}),{angle_factor}*90*(t-{video1_duration-duration})/{duration},0)',"
                f"format=yuva420p,fade=t=out:st={video1_duration-duration}:d={duration}:alpha=1[rotate1];"
                f"[1:v]rotate='if(lte(t,{duration}),-{angle_factor}*90*(1-t/{duration}),0)',"
                f"format=yuva420p,fade=t=in:st=0:d={duration}:alpha=1,setpts=PTS-STARTPTS+{video1_duration-duration}/TB[rotate2];"
                f"[rotate1][rotate2]overlay[outv]"
            ),
            "-map", "[outv]"
        ]
        
        # 添加音频映射（如果有音频）
        if has_audio:
            cmd.extend(["-map", "0:a"])  # 使用第一个视频的音频
        
        # 添加编码器选项
        cmd.extend(["-c:v", "libx264"])
        if has_audio:
            cmd.extend(["-c:a", "aac"])
        
        # 添加输出路径
        cmd.append(output_path)
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 执行命令
        success, _ = await VideoUtils.run_ffmpeg_command(cmd)
        return success
        
    @staticmethod
    async def apply_flash_transition(
        video1_path: str,
        video2_path: str,
        output_path: str,
        intensity: float = 1.0,
        duration: float = 0.5
    ) -> bool:
        """
        应用闪烁转场效果
        
        Args:
            video1_path: 第一个视频路径
            video2_path: 第二个视频路径
            output_path: 输出视频路径
            intensity: 闪烁强度（0-2）
            duration: 转场持续时间（秒）
            
        Returns:
            bool: 是否成功
        """
        # 检查输入文件是否存在
        if not os.path.exists(video1_path) or not os.path.exists(video2_path):
            logger.error(f"Input video file not found: {video1_path} or {video2_path}")
            return False
            
        # 获取视频信息
        try:
            video1_info = await VideoUtils.get_video_info(video1_path)
            video1_duration = video1_info["duration"]
            
            # 确保转场时间不超过视频时长
            if duration > video1_duration:
                duration = video1_duration / 2
                logger.warning(f"Transition duration adjusted to {duration}s")
                
            # 检查是否有音频流
            has_audio = False
            for stream in video1_info["streams"]:
                if stream.get("codec_type") == "audio":
                    has_audio = True
                    break
                
        except Exception as e:
            logger.error(f"Failed to get video info: {str(e)}")
            # 继续执行，使用默认值
            video1_duration = 0
            has_audio = False
        
        # 构建FFmpeg命令
        flash_time = duration / 2  # 闪烁持续时间
        cmd = [
            settings.FFMPEG_PATH,
            "-y",  # 覆盖输出文件
            "-i", video1_path,
            "-i", video2_path,
            "-filter_complex", (
                f"[0:v]trim=0:{video1_duration}[v1];"
                f"[v1]curves=lighter:{intensity}:enable='between(t,{video1_duration-flash_time},{video1_duration})'[flash1];"
                f"[1:v]trim=0:{duration},setpts=PTS-STARTPTS+{video1_duration-duration}/TB[v2];"
                f"[v2]curves=lighter:{intensity}:enable='between(t,0,{flash_time})'[flash2];"
                f"[flash1][flash2]concat=n=2:v=1:a=0[outv]"
            ),
            "-map", "[outv]"
        ]
        
        # 添加音频映射（如果有音频）
        if has_audio:
            cmd.extend(["-map", "0:a"])  # 使用第一个视频的音频
        
        # 添加编码器选项
        cmd.extend(["-c:v", "libx264"])
        if has_audio:
            cmd.extend(["-c:a", "aac"])
        
        # 添加输出路径
        cmd.append(output_path)
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 执行命令
        success, _ = await VideoUtils.run_ffmpeg_command(cmd)
        return success 