"""
图片去重器 — 文档级图片存储去重。

遵守 V1_LESSONS 3.4/3.26 约束：
- 物理图文档级去重：IoU/中心距离
- 题-图关联允许多对多：物理图存储只保留一份，question_images 关联允许一条或多条
- 无 page/bbox 时记录 missing_figure，不整页兜底
- 无显式证据的跨题广播仍要抑制

详见 Docs/01_Product/T3_IMPLEMENTATION.md §9 Task 2.2。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.domains.document.schemas_l1 import L1Image

logger = logging.getLogger(__name__)


# 去重参数
_IOU_THRESHOLD = 0.5  # IoU 阈值：高于此值认为是同一图片
_CENTER_DISTANCE_THRESHOLD = 50.0  # 中心距离阈值（像素）：低于此值认为是同一图片


@dataclass
class DeduplicationResult:
    """去重结果。"""

    original_count: int  # 原始图片数
    deduplicated_count: int  # 去重后图片数
    duplicates: list[DeduplicationPair] = field(default_factory=list)  # 重复对
    figure_mapping: dict[str, str] = field(default_factory=dict)  # image_id → figure_id


@dataclass
class DeduplicationPair:
    """重复图片对。"""

    kept_image_id: str  # 保留的图片 ID
    removed_image_id: str  # 被移除的图片 ID
    similarity: float  # 相似度（IoU 或 1 - 归一化距离）
    method: str  # "iou" 或 "center_distance"


def _bbox_center(bbox: dict | None) -> tuple[float, float] | None:
    """计算 bbox 中心点坐标。"""
    if not bbox:
        return None
    x_center = (bbox["x1"] + bbox["x2"]) / 2
    y_center = (bbox["y1"] + bbox["y2"]) / 2
    return (x_center, y_center)


def _bbox_iou(box_a: dict | None, box_b: dict | None) -> float:
    """计算两个 bbox 的 IoU。任一 bbox 为 None 返回 0。"""
    if not box_a or not box_b:
        return 0.0
    x1 = max(box_a["x1"], box_b["x1"])
    y1 = max(box_a["y1"], box_b["y1"])
    x2 = min(box_a["x2"], box_b["x2"])
    y2 = min(box_a["y2"], box_b["y2"])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = (box_a["x2"] - box_a["x1"]) * (box_a["y2"] - box_a["y1"])
    area_b = (box_b["x2"] - box_b["x1"]) * (box_b["y2"] - box_b["y1"])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _center_distance(box_a: dict | None, box_b: dict | None) -> float:
    """计算两个 bbox 中心点的欧氏距离。"""
    center_a = _bbox_center(box_a)
    center_b = _bbox_center(box_b)
    if not center_a or not center_b:
        return float("inf")
    return ((center_a[0] - center_b[0]) ** 2 + (center_a[1] - center_b[1]) ** 2) ** 0.5


def _compute_image_hash(image: L1Image) -> str:
    """计算图片的感知哈希（用于快速预筛选）。

    基于 bbox 位置和尺寸生成哈希，相同位置和尺寸的图片会被分到同一桶。
    """
    if not image.bbox:
        return f"no_bbox_{image.page_no}"
    # 将 bbox 量化到 10 像素网格，生成哈希
    quantized = (
        round(image.bbox["x1"] / 10) * 10,
        round(image.bbox["y1"] / 10) * 10,
        round(image.bbox["x2"] / 10) * 10,
        round(image.bbox["y2"] / 10) * 10,
    )
    return f"{image.page_no}_{quantized}"


def deduplicate_images(
    images: list[L1Image],
    *,
    iou_threshold: float = _IOU_THRESHOLD,
    center_distance_threshold: float = _CENTER_DISTANCE_THRESHOLD,
) -> tuple[list[L1Image], DeduplicationResult]:
    """对图片列表进行文档级去重。

    去重策略：
    1. 按页码分组（不同页的图片不比较）
    2. 按感知哈希预分桶（相同位置和尺寸的图片进入同一桶）
    3. 桶内两两比较 IoU 和中心距离
    4. 为保留的图片分配 figure_id

    注意：合并阶段已选择单一 canonical source（PP-StructureV3），
    因此去重器只需处理同源图片，无需跨源比较。

    Args:
        images: 待去重的图片列表
        iou_threshold: IoU 阈值，高于此值认为是同一图片
        center_distance_threshold: 中心距离阈值（像素），低于此值认为是同一图片

    Returns:
        (去重后的图片列表, 去重结果)
    """
    if not images:
        return [], DeduplicationResult(original_count=0, deduplicated_count=0)

    original_count = len(images)
    duplicates: list[DeduplicationPair] = []

    # 按页码分组
    images_by_page: dict[int, list[L1Image]] = {}
    for img in images:
        images_by_page.setdefault(img.page_no, []).append(img)

    # 按感知哈希预分桶
    kept_images: list[L1Image] = []
    removed_ids: set[str] = set()

    for page_no, page_images in images_by_page.items():
        # 按哈希分桶
        hash_buckets: dict[str, list[L1Image]] = {}
        for img in page_images:
            h = _compute_image_hash(img)
            hash_buckets.setdefault(h, []).append(img)

        # 桶内两两比较
        for bucket_hash, bucket_images in hash_buckets.items():
            if len(bucket_images) <= 1:
                # 桶内只有一张图片，直接保留
                kept_images.append(bucket_images[0])
                continue

            # 桶内多张图片，两两比较
            bucket_kept: list[L1Image] = []
            for img in bucket_images:
                if img.image_id in removed_ids:
                    continue

                is_duplicate = False
                for kept_img in bucket_kept:
                    # 计算 IoU
                    iou = _bbox_iou(img.bbox, kept_img.bbox)
                    if iou >= iou_threshold:
                        # IoU 超过阈值，认为是同一图片
                        removed_ids.add(img.image_id)
                        duplicates.append(DeduplicationPair(
                            kept_image_id=kept_img.image_id,
                            removed_image_id=img.image_id,
                            similarity=iou,
                            method="iou",
                        ))
                        is_duplicate = True
                        break

                    # 计算中心距离
                    dist = _center_distance(img.bbox, kept_img.bbox)
                    if dist <= center_distance_threshold:
                        # 中心距离在阈值内，认为是同一图片
                        removed_ids.add(img.image_id)
                        duplicates.append(DeduplicationPair(
                            kept_image_id=kept_img.image_id,
                            removed_image_id=img.image_id,
                            similarity=1.0 - dist / center_distance_threshold,
                            method="center_distance",
                        ))
                        is_duplicate = True
                        break

                if not is_duplicate:
                    bucket_kept.append(img)

            kept_images.extend(bucket_kept)

    # 为保留的图片分配 figure_id
    figure_mapping: dict[str, str] = {}
    figure_counter = 1
    for img in kept_images:
        if img.figure_id:
            # 已有 figure_id，保留
            figure_mapping[img.image_id] = img.figure_id
        else:
            # 分配新的 figure_id
            figure_id = f"FIG{figure_counter:03d}"
            img.figure_id = figure_id
            figure_mapping[img.image_id] = figure_id
            figure_counter += 1

    result = DeduplicationResult(
        original_count=original_count,
        deduplicated_count=len(kept_images),
        duplicates=duplicates,
        figure_mapping=figure_mapping,
    )

    if duplicates:
        logger.info(
            "image_dedup original=%d deduplicated=%d duplicates=%d",
            original_count, len(kept_images), len(duplicates),
        )

    return kept_images, result
