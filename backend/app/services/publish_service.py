"""
文化DNA —— 非遗作品确权溯源系统
「上传到网络」发布服务

将上传作品（元数据 + DNA 哈希）发布到网络：
1. 优先上传到本机 IPFS 节点（127.0.0.1:5001，HTTP API），获取内容寻址 CID；
2. IPFS 节点不可用（未安装/未启动/连接失败）时，优雅降级为本地离线存证：
   用 SHA-256 生成自校验的内容标识，并把发布快照落盘到 published/ 目录。

说明：IPFS 上传走标准 HTTP API（POST /api/v0/add），无需额外依赖 ipfshttpclient。
"""
import os
import json
import hashlib
import logging

import requests

logger = logging.getLogger(__name__)

_IPFS_ADD_PATH = "/api/v0/add"
_IPFS_TIMEOUT = 5


def _ipfs_add_bytes(data: bytes, host: str = "127.0.0.1", port: int = 5001) -> str:
    """
    向本机 IPFS 节点上传一段字节内容，返回 CID

    Args:
        data: 待上传的字节内容（JSON 元数据）
        host: IPFS 主机（默认 127.0.0.1）
        port: IPFS API 端口（默认 5001）

    Returns:
        CID 字符串（如 QmXxx...）；失败返回 None
    """
    try:
        url = f"http://{host}:{port}{_IPFS_ADD_PATH}"
        resp = requests.post(
            url,
            files={"file": ("cultural_dna_metadata.json", data)},
            timeout=_IPFS_TIMEOUT,
        )

        if resp.status_code != 200:
            logger.warning("IPFS add 失败: HTTP %s", resp.status_code)
            return None

        body = resp.json()
        cid = body.get("Hash") or body.get("hash")
        if not cid:
            logger.warning("IPFS add 响应中缺少 CID: %s", str(body)[:200])
        return cid

    except Exception as e:
        logger.warning("IPFS 节点不可用: %s", str(e))
        return None


def _local_deposit(data: bytes, data_dir: str = None):
    """
    本地离线存证：将发布快照写入 published/<sha256>.json，返回本地内容标识

    Returns:
        (local_id, path) 元组
        local_id: "local_<sha256 前40位>"
        path: 落盘文件绝对路径
    """
    sha = hashlib.sha256(data).hexdigest()
    pub_dir = os.path.join(data_dir, "published") if data_dir else "published"
    os.makedirs(pub_dir, exist_ok=True)

    path = os.path.join(pub_dir, f"{sha}.json")
    if not os.path.exists(path):
        with open(path, "wb") as f:
            f.write(data)

    return f"local_{sha[:40]}", path


def publish_work(
    metadata: dict,
    ipfs_host: str = "127.0.0.1",
    ipfs_port: int = 5001,
    data_dir: str = None,
) -> dict:
    """
    将作品元数据发布到网络

    Args:
        metadata: 作品元数据字典（含 dna_hash、title、category、images 等）
        ipfs_host: IPFS 主机
        ipfs_port: IPFS 端口
        data_dir: 数据目录（用于本地降级存证落盘）

    Returns:
        {
            "publish_type": "ipfs" | "local",
            "cid": "内容寻址标识",
            "resource_url": "可访问地址",
            "message": "说明",
        }
    """
    payload = json.dumps(metadata, ensure_ascii=False).encode("utf-8")

    # 1. 优先尝试 IPFS 网络上传
    cid = _ipfs_add_bytes(payload, ipfs_host, ipfs_port)
    if cid:
        logger.info("作品已发布到 IPFS: %s (cid=%s)", metadata.get("title"), cid)
        return {
            "publish_type": "ipfs",
            "cid": cid,
            "resource_url": f"ipfs://{cid}",
            "message": "已发布到 IPFS 网络",
        }

    # 2. 降级：本地离线存证
    local_id, path = _local_deposit(payload, data_dir)
    logger.info("IPFS 不可用，作品降级为本地离线存证: %s (%s)", metadata.get("title"), local_id)
    return {
        "publish_type": "local",
        "cid": local_id,
        "resource_url": f"file://{os.path.abspath(path)}",
        "message": "IPFS 节点不可用，已降级为本地离线存证",
    }