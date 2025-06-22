import os
import numpy as np
import librosa
from typing import List, Dict, Any, Tuple
from pathlib import Path
from ..core.config import settings
from ..core.logging import logger


class MusicUtils:
    """音乐处理工具类"""
    
    @staticmethod
    def get_music_duration(music_path: str) -> float:
        """
        获取音乐时长
        
        Args:
            music_path: 音乐文件路径
            
        Returns:
            float: 音乐时长（秒）
        """
        try:
            y, sr = librosa.load(music_path, sr=None)
            duration = librosa.get_duration(y=y, sr=sr)
            return float(duration)
        except Exception as e:
            logger.error(f"Error getting music duration: {str(e)}")
            raise
    
    @staticmethod
    def detect_beats(music_path: str, threshold: float = 0.1) -> List[float]:
        """
        检测音乐节拍点
        
        Args:
            music_path: 音乐文件路径
            threshold: 节拍检测阈值，值越大检测的节拍越少
            
        Returns:
            List[float]: 节拍时间点列表（秒）
        """
        try:
            # 加载音频文件
            y, sr = librosa.load(music_path, sr=None)
            
            # 获取节拍位置
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
            
            # 将帧位置转换为时间（秒）
            beat_times = librosa.frames_to_time(beat_frames, sr=sr)
            
            # 将numpy类型转换为Python原生类型
            tempo_float = float(tempo)
            beat_times_list = [float(t) for t in beat_times]
            
            logger.info(f"Detected {len(beat_times_list)} beats at tempo {tempo_float:.2f} BPM")
            return beat_times_list
        except Exception as e:
            logger.error(f"Error detecting beats: {str(e)}")
            raise
    
    @staticmethod
    def detect_onsets(music_path: str, threshold: float = 0.5) -> List[float]:
        """
        检测音乐起始点（音符开始的位置）
        
        Args:
            music_path: 音乐文件路径
            threshold: 检测阈值，值越大检测的起始点越少
            
        Returns:
            List[float]: 起始时间点列表（秒）
        """
        try:
            # 加载音频文件
            y, sr = librosa.load(music_path, sr=None)
            
            # 计算起始点检测函数
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
            
            # 根据API文档正确调用onset_detect
            # 不再使用threshold参数，而是通过peak_pick的参数控制敏感度
            onset_frames = librosa.onset.onset_detect(
                onset_envelope=onset_env, 
                sr=sr,
                backtrack=False,
                # 通过kwargs传递peak_pick的参数
                delta=threshold  # 使用delta参数替代threshold，delta控制峰值检测阈值
            )
            
            # 将帧位置转换为时间（秒）
            onset_times = librosa.frames_to_time(onset_frames, sr=sr)
            
            # 将numpy类型转换为Python原生类型
            onset_times_list = [float(t) for t in onset_times]
            
            logger.info(f"Detected {len(onset_times_list)} onsets")
            return onset_times_list
        except Exception as e:
            logger.error(f"Error detecting onsets: {str(e)}")
            raise
    
    @staticmethod
    def detect_rhythm_points(
        music_path: str, 
        beat_threshold: float = 0.1,
        onset_threshold: float = 0.5,
        combine: bool = True
    ) -> List[float]:
        """
        检测音乐节奏点（结合节拍和起始点）
        
        Args:
            music_path: 音乐文件路径
            beat_threshold: 节拍检测阈值
            onset_threshold: 起始点检测阈值
            combine: 是否合并节拍和起始点
            
        Returns:
            List[float]: 节奏时间点列表（秒）
        """
        try:
            # 获取节拍点
            beats = MusicUtils.detect_beats(music_path, beat_threshold)
            
            # 获取起始点
            onsets = MusicUtils.detect_onsets(music_path, onset_threshold)
            
            if combine:
                # 合并节拍和起始点，并去重
                combined = sorted(list(set(beats + onsets)))
                
                # 过滤掉太近的点（小于0.1秒）
                filtered = [combined[0]]
                for point in combined[1:]:
                    if point - filtered[-1] >= 0.1:
                        filtered.append(point)
                
                logger.info(f"Combined {len(beats)} beats and {len(onsets)} onsets into {len(filtered)} rhythm points")
                return filtered
            else:
                # 只返回节拍点
                return beats
        except Exception as e:
            logger.error(f"Error detecting rhythm points: {str(e)}")
            raise
    
    @staticmethod
    def analyze_music_segments(
        music_path: str,
        segment_count: int = 8
    ) -> List[Dict[str, Any]]:
        """
        分析音乐分段
        
        Args:
            music_path: 音乐文件路径
            segment_count: 分段数量
            
        Returns:
            List[Dict[str, Any]]: 分段信息列表
        """
        try:
            # 加载音频文件
            y, sr = librosa.load(music_path, sr=None)
            
            # 获取音乐总时长
            duration = librosa.get_duration(y=y, sr=sr)
            
            # 计算分段时长
            segment_duration = float(duration) / segment_count
            
            segments = []
            for i in range(segment_count):
                start_time = i * segment_duration
                end_time = (i + 1) * segment_duration
                
                # 提取分段音频
                start_sample = int(start_time * sr)
                end_sample = int(end_time * sr)
                segment_y = y[start_sample:end_sample]
                
                # 计算分段能量
                energy = np.sum(segment_y**2) / len(segment_y)
                
                # 计算分段节奏强度
                tempo, _ = librosa.beat.beat_track(y=segment_y, sr=sr)
                
                segments.append({
                    "index": i,
                    "start_time": float(start_time),
                    "end_time": float(end_time),
                    "duration": float(segment_duration),
                    "energy": float(energy),
                    "tempo": float(tempo)
                })
            
            logger.info(f"Analyzed music into {segment_count} segments")
            return segments
        except Exception as e:
            logger.error(f"Error analyzing music segments: {str(e)}")
            raise
    
    @staticmethod
    def get_music_energy_profile(
        music_path: str,
        frame_length: int = 2048,
        hop_length: int = 512
    ) -> Dict[str, Any]:
        """
        获取音乐能量分布
        
        Args:
            music_path: 音乐文件路径
            frame_length: 帧长度
            hop_length: 帧间隔
            
        Returns:
            Dict[str, Any]: 能量分布信息
        """
        try:
            # 加载音频文件
            y, sr = librosa.load(music_path, sr=None)
            
            # 计算RMS能量
            rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
            
            # 时间点
            times = librosa.times_like(rms, sr=sr, hop_length=hop_length)
            
            # 计算统计信息
            mean_energy = float(np.mean(rms))
            max_energy = float(np.max(rms))
            min_energy = float(np.min(rms))
            std_energy = float(np.std(rms))
            
            # 根据API文档正确调用peak_pick
            peak_indices = librosa.util.peak_pick(
                x=rms, 
                pre_max=3, 
                post_max=3, 
                pre_avg=3, 
                post_avg=5, 
                delta=0.5, 
                wait=10
            )
            peak_times = times[peak_indices]
            peak_energies = rms[peak_indices]
            
            peaks = [{"time": float(time), "energy": float(energy)} for time, energy in zip(peak_times, peak_energies)]
            
            return {
                "mean_energy": mean_energy,
                "max_energy": max_energy,
                "min_energy": min_energy,
                "std_energy": std_energy,
                "energy_profile": [float(e) for e in rms],
                "time_points": [float(t) for t in times],
                "peaks": peaks
            }
        except Exception as e:
            logger.error(f"Error getting music energy profile: {str(e)}")
            raise 