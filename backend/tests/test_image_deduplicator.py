"""
图片去重器单元测试。

测试覆盖：
- 空列表处理
- 单张图片
- 相同位置图片去重（IoU）
- 不同位置图片保留
- Native 优先保留
- figure_id 分配
"""

from app.domains.document.image_deduplicator import (
    deduplicate_images,
    _bbox_iou,
    _center_distance,
)
from app.domains.document.schemas_l1 import L1Image


def test_empty_list():
    """空列表返回空结果。"""
    images, result = deduplicate_images([])
    assert images == []
    assert result.original_count == 0
    assert result.deduplicated_count == 0


def test_single_image():
    """单张图片直接保留。"""
    img = L1Image(
        image_id="P1IMG001", page_no=1,
        bbox={"x1": 10, "y1": 10, "x2": 100, "y2": 100},
        source="native",
    )
    images, result = deduplicate_images([img])
    assert len(images) == 1
    assert result.original_count == 1
    assert result.deduplicated_count == 1
    assert result.figure_mapping["P1IMG001"] == "FIG001"


def test_identical_bbox_dedup():
    """相同 bbox 的同源图片去重。"""
    img1 = L1Image(
        image_id="P1IMG001", page_no=1,
        bbox={"x1": 10, "y1": 10, "x2": 100, "y2": 100},
        source="native",
    )
    img2 = L1Image(
        image_id="P1IMG002", page_no=1,
        bbox={"x1": 10, "y1": 10, "x2": 100, "y2": 100},
        source="native",
    )
    images, result = deduplicate_images([img1, img2])
    assert len(images) == 1
    assert result.deduplicated_count == 1
    assert len(result.duplicates) == 1
    assert result.duplicates[0].kept_image_id == "P1IMG001"
    assert result.duplicates[0].removed_image_id == "P1IMG002"


def test_different_position_keep_both():
    """不同位置的图片都保留。"""
    img1 = L1Image(
        image_id="P1IMG001", page_no=1,
        bbox={"x1": 10, "y1": 10, "x2": 100, "y2": 100},
        source="native",
    )
    img2 = L1Image(
        image_id="P1IMG002", page_no=1,
        bbox={"x1": 200, "y1": 200, "x2": 300, "y2": 300},
        source="native",
    )
    images, result = deduplicate_images([img1, img2])
    assert len(images) == 2
    assert result.deduplicated_count == 2
    assert len(result.duplicates) == 0


def test_native_preferred():
    """同源内去重保留第一个。"""
    img1 = L1Image(
        image_id="P1IMG001", page_no=1,
        bbox={"x1": 10, "y1": 10, "x2": 100, "y2": 100},
        source="ppsv3",
    )
    img2 = L1Image(
        image_id="P1IMG002", page_no=1,
        bbox={"x1": 12, "y1": 12, "x2": 98, "y2": 98},
        source="ppsv3",
    )
    images, result = deduplicate_images([img1, img2])
    assert len(images) == 1
    assert images[0].image_id == "P1IMG001"


def test_no_bbox_images():
    """无 bbox 的图片按页码分组保留。"""
    img1 = L1Image(
        image_id="P1IMG001", page_no=1,
        bbox=None, source="ppsv3",
    )
    img2 = L1Image(
        image_id="P1IMG002", page_no=1,
        bbox=None, source="ppsv3",
    )
    images, result = deduplicate_images([img1, img2])
    # 无 bbox 的图片不会被 IoU/中心距离匹配，都会保留
    assert len(images) == 2


def test_bbox_iou():
    """IoU 计算正确。"""
    box_a = {"x1": 0, "y1": 0, "x2": 100, "y2": 100}
    box_b = {"x1": 50, "y1": 50, "x2": 150, "y2": 150}
    iou = _bbox_iou(box_a, box_b)
    # 交集面积 = 50*50 = 2500，并集面积 = 10000+10000-2500 = 17500
    # IoU = 2500/17500 ≈ 0.143
    assert 0.14 < iou < 0.15


def test_center_distance():
    """中心距离计算正确。"""
    box_a = {"x1": 0, "y1": 0, "x2": 100, "y2": 100}
    box_b = {"x1": 100, "y1": 0, "x2": 200, "y2": 100}
    dist = _center_distance(box_a, box_b)
    # 中心点 A=(50,50), B=(150,50), 距离=100
    assert dist == 100.0


def test_figure_id_sequential():
    """figure_id 按顺序分配。"""
    images = [
        L1Image(image_id=f"P1IMG{i:03d}", page_no=1,
                bbox={"x1": i*100, "y1": 0, "x2": i*100+50, "y2": 50},
                source="native")
        for i in range(5)
    ]
    deduped, result = deduplicate_images(images)
    assert len(deduped) == 5
    figure_ids = [img.figure_id for img in deduped]
    assert figure_ids == ["FIG001", "FIG002", "FIG003", "FIG004", "FIG005"]
