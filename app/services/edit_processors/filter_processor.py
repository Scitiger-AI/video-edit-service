from typing import Dict, Any, List
import os
from . import register_processor
from .base import EditProcessor
from ...core.logging import logger
from ...core.config import settings
from ...utils.video_utils import VideoUtils


@register_processor
class FilterProcessor(EditProcessor):
    """视频滤镜处理器"""
    
    @property
    def processor_name(self) -> str:
        return "filter"
    
    @property
    def supported_operations(self) -> List[str]:
        return [
            "brightness",    # 亮度调整
            "contrast",      # 对比度调整
            "saturation",    # 饱和度调整
            "blur",          # 模糊效果
            "sharpen",       # 锐化效果
            "grayscale",     # 灰度效果
            "sepia",         # 复古效果
            "vignette"       # 暗角效果
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
        
        # 验证视频路径
        if "video_path" not in parameters:
            raise ValueError("Missing required parameter: video_path")
            
        # 检查文件是否存在
        if not os.path.exists(parameters["video_path"]):
            raise ValueError(f"Video file not found: {parameters['video_path']}")
        
        # 根据不同滤镜类型验证参数
        if operation in ["brightness", "contrast", "saturation"]:
            # 验证调整参数
            if "level" not in parameters:
                raise ValueError(f"Missing required parameter: level for {operation}")
            
            # 确保level是数字
            try:
                parameters["level"] = float(parameters["level"])
            except (ValueError, TypeError):
                raise ValueError(f"{operation} level must be a number")
                
            if not -100 <= parameters["level"] <= 100:
                raise ValueError(f"{operation} level must be between -100 and 100")
        elif operation == "blur":
            # 验证模糊参数
            if "radius" not in parameters:
                parameters["radius"] = 5
            else:
                # 确保radius是数字
                try:
                    parameters["radius"] = float(parameters["radius"])
                except (ValueError, TypeError):
                    raise ValueError("Blur radius must be a number")
                    
            if parameters["radius"] < 0:
                raise ValueError("Blur radius must be non-negative")
        elif operation == "sharpen":
            # 验证锐化参数
            if "amount" not in parameters:
                parameters["amount"] = 1.0
            else:
                # 确保amount是数字
                try:
                    parameters["amount"] = float(parameters["amount"])
                except (ValueError, TypeError):
                    raise ValueError("Sharpen amount must be a number")
                    
            if parameters["amount"] < 0:
                raise ValueError("Sharpen amount must be non-negative")
        elif operation in ["grayscale", "sepia"]:
            # 这些滤镜不需要额外参数
            pass
        elif operation == "vignette":
            # 验证暗角参数
            if "amount" not in parameters:
                parameters["amount"] = 0.3
            else:
                # 确保amount是数字
                try:
                    parameters["amount"] = float(parameters["amount"])
                except (ValueError, TypeError):
                    raise ValueError("Vignette amount must be a number")
                    
            if not 0 <= parameters["amount"] <= 1:
                raise ValueError("Vignette amount must be between 0 and 1")
            
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
        logger.info(f"Applying {operation} filter to video")
        
        # 实现视频滤镜逻辑
        if operation in ["brightness", "contrast", "saturation"]:
            # 实现亮度/对比度/饱和度调整
            return await self._adjust_video_property(operation, parameters)
        elif operation == "blur":
            # 实现模糊效果
            return await self._apply_blur(parameters)
        elif operation == "sharpen":
            # 实现锐化效果
            return await self._apply_sharpen(parameters)
        elif operation == "grayscale":
            # 实现灰度效果
            return await self._apply_grayscale(parameters)
        elif operation == "sepia":
            # 实现复古效果
            return await self._apply_sepia(parameters)
        elif operation == "vignette":
            # 实现暗角效果
            return await self._apply_vignette(parameters)
        else:
            raise ValueError(f"Unsupported operation: {operation}")
    
    async def _adjust_video_property(self, property_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """调整视频属性（亮度/对比度/饱和度）"""
        level = parameters["level"]
        video_path = parameters["video_path"]
        
        logger.info(f"Adjusting video {video_path} {property_name} by {level}")
        
        # 获取输出路径
        output_path = VideoUtils.get_output_path(self.processor_name, property_name)
        
        # 执行视频属性调整
        success = await VideoUtils.adjust_video_property(
            input_path=video_path,
            output_path=output_path,
            property_name=property_name,
            level=level
        )
        
        if not success:
            raise RuntimeError(f"Failed to adjust video {property_name}: {video_path}")
        
        # 获取处理后的视频信息
        video_info = await VideoUtils.get_video_info(output_path)
        
        # 检查视频是否有效
        if video_info["duration"] == 0 or not video_info["streams"]:
            raise RuntimeError(f"Generated video is invalid: {output_path}")
        
        return {
            "status": "success",
            "operation": property_name,
            "output_path": output_path,
            "level": level,
            "duration": video_info["duration"],
            "size": video_info["size"],
            "video_info": video_info
        }
    
    async def _apply_blur(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """应用模糊效果"""
        radius = parameters.get("radius", 5)
        video_path = parameters["video_path"]
        
        logger.info(f"Applying blur to video {video_path} with radius {radius}")
        
        # 获取输出路径
        output_path = VideoUtils.get_output_path(self.processor_name, "blur")
        
        # 执行视频模糊
        success = await VideoUtils.apply_blur(
            input_path=video_path,
            output_path=output_path,
            radius=radius
        )
        
        if not success:
            raise RuntimeError(f"Failed to apply blur to video: {video_path}")
        
        # 获取处理后的视频信息
        video_info = await VideoUtils.get_video_info(output_path)
        
        # 检查视频是否有效
        if video_info["duration"] == 0 or not video_info["streams"]:
            raise RuntimeError(f"Generated video is invalid: {output_path}")
        
        return {
            "status": "success",
            "operation": "blur",
            "output_path": output_path,
            "radius": radius,
            "duration": video_info["duration"],
            "size": video_info["size"],
            "video_info": video_info
        }
    
    async def _apply_sharpen(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """应用锐化效果"""
        amount = parameters.get("amount", 1.0)
        video_path = parameters["video_path"]
        
        logger.info(f"Applying sharpen to video {video_path} with amount {amount}")
        
        # 获取输出路径
        output_path = VideoUtils.get_output_path(self.processor_name, "sharpen")
        
        # 执行视频锐化
        success = await VideoUtils.apply_sharpen(
            input_path=video_path,
            output_path=output_path,
            amount=amount
        )
        
        if not success:
            raise RuntimeError(f"Failed to apply sharpen to video: {video_path}")
        
        # 获取处理后的视频信息
        video_info = await VideoUtils.get_video_info(output_path)
        
        # 检查视频是否有效
        if video_info["duration"] == 0 or not video_info["streams"]:
            raise RuntimeError(f"Generated video is invalid: {output_path}")
        
        return {
            "status": "success",
            "operation": "sharpen",
            "output_path": output_path,
            "amount": amount,
            "duration": video_info["duration"],
            "size": video_info["size"],
            "video_info": video_info
        }
    
    async def _apply_grayscale(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """应用灰度效果"""
        video_path = parameters["video_path"]
        
        logger.info(f"Applying grayscale to video {video_path}")
        
        # 获取输出路径
        output_path = VideoUtils.get_output_path(self.processor_name, "grayscale")
        
        # 执行视频灰度处理
        success = await VideoUtils.apply_grayscale(
            input_path=video_path,
            output_path=output_path
        )
        
        if not success:
            raise RuntimeError(f"Failed to apply grayscale to video: {video_path}")
        
        # 获取处理后的视频信息
        video_info = await VideoUtils.get_video_info(output_path)
        
        # 检查视频是否有效
        if video_info["duration"] == 0 or not video_info["streams"]:
            raise RuntimeError(f"Generated video is invalid: {output_path}")
        
        return {
            "status": "success",
            "operation": "grayscale",
            "output_path": output_path,
            "duration": video_info["duration"],
            "size": video_info["size"],
            "video_info": video_info
        }
    
    async def _apply_sepia(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """应用复古效果"""
        video_path = parameters["video_path"]
        
        logger.info(f"Applying sepia to video {video_path}")
        
        # 获取输出路径
        output_path = VideoUtils.get_output_path(self.processor_name, "sepia")
        
        # 执行视频复古效果处理
        success = await VideoUtils.apply_sepia(
            input_path=video_path,
            output_path=output_path
        )
        
        if not success:
            raise RuntimeError(f"Failed to apply sepia to video: {video_path}")
        
        # 获取处理后的视频信息
        video_info = await VideoUtils.get_video_info(output_path)
        
        # 检查视频是否有效
        if video_info["duration"] == 0 or not video_info["streams"]:
            raise RuntimeError(f"Generated video is invalid: {output_path}")
        
        return {
            "status": "success",
            "operation": "sepia",
            "output_path": output_path,
            "duration": video_info["duration"],
            "size": video_info["size"],
            "video_info": video_info
        }
    
    async def _apply_vignette(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """应用暗角效果"""
        amount = parameters.get("amount", 0.3)
        video_path = parameters["video_path"]
        
        logger.info(f"Applying vignette to video {video_path} with amount {amount}")
        
        # 获取输出路径
        output_path = VideoUtils.get_output_path(self.processor_name, "vignette")
        
        # 执行视频暗角效果处理
        success = await VideoUtils.apply_vignette(
            input_path=video_path,
            output_path=output_path,
            amount=amount
        )
        
        if not success:
            raise RuntimeError(f"Failed to apply vignette to video: {video_path}")
        
        # 获取处理后的视频信息
        video_info = await VideoUtils.get_video_info(output_path)
        
        # 检查视频是否有效
        if video_info["duration"] == 0 or not video_info["streams"]:
            raise RuntimeError(f"Generated video is invalid: {output_path}")
        
        return {
            "status": "success",
            "operation": "vignette",
            "output_path": output_path,
            "amount": amount,
            "duration": video_info["duration"],
            "size": video_info["size"],
            "video_info": video_info
        } 