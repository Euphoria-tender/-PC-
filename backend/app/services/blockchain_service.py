"""
文化DNA —— 非遗作品确权溯源系统
区块链服务模块
负责与 Hyperledger Fabric 2.2 链码交互，使用 fabric-sdk-py 库
"""
import os
import json
import logging
import threading
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════
# Fabric SDK 客户端管理器
# ══════════════════════════════════════════════════════════════════

class FabricClientManager:
    """
    Fabric 客户端管理器（单例）

    负责：
    - 加载网络连接配置文件
    - 创建并缓存 Fabric Client 实例
    - 获取组织管理员用户
    - 提供通道和链码调用入口

    线程安全：使用锁保护客户端初始化过程
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._client = None
        self._org_admin = None
        self._network_config = None
        self._channel_name = None
        self._chaincode_name = None
        self._peers = None
        self._initialized = True

    def _load_config(self) -> Tuple[str, str, str]:
        """
        加载 Fabric 网络配置

        Returns:
            (network_config_path, channel_name, chaincode_name) 元组
        """
        network_config = os.environ.get(
            "FABRIC_NETWORK_CONFIG",
            os.path.join(
                os.path.dirname(__file__), "..", "..", "..",
                "blockchain", "connection.json"
            )
        )
        # 解析为绝对路径
        network_config = os.path.abspath(network_config)

        channel_name = os.environ.get("FABRIC_CHANNEL", "culturaldnachannel")
        chaincode_name = os.environ.get("FABRIC_CHAINCODE", "artworkcc")

        return network_config, channel_name, chaincode_name

    def init_client(self) -> bool:
        """
        初始化 Fabric 客户端（线程安全）

        流程：
        1. 加载连接配置
        2. 创建 Client 实例
        3. 获取组织管理员用户凭证
        4. 验证通道和链码可访问性

        Returns:
            初始化是否成功
        """
        if self._client is not None:
            return True

        with self._lock:
            # 双重检查
            if self._client is not None:
                return True

            try:
                network_config, channel_name, chaincode_name = self._load_config()

                # 检查配置文件是否存在
                if not os.path.exists(network_config):
                    logger.error(
                        "Fabric 连接配置文件不存在: %s，将使用降级模式",
                        network_config
                    )
                    return False

                self._network_config = network_config
                self._channel_name = channel_name
                self._chaincode_name = chaincode_name

                # 导入 fabric-sdk-py 并创建客户端
                try:
                    from hfc.fabric import Client
                except ImportError:
                    logger.error(
                        "fabric-sdk-py 未安装，请执行: pip install fabric-sdk-py"
                    )
                    return False

                # 创建客户端实例
                self._client = Client(net_profile=network_config)

                # 获取组织管理员用户
                # 使用 Org1 的管理员身份与链码交互
                try:
                    self._org_admin = self._client.get_user(
                        'org1.example.com', 'Admin'
                    )
                except Exception:
                    logger.warning(
                        "无法获取 Admin 用户，尝试创建新用户..."
                    )
                    # 尝试使用 CA 创建管理员
                    try:
                        from hfc.fabric.cacert import CAClient
                        ca_client = CAClient(
                            'https://localhost:7054',
                            tls_ca_certs=os.path.join(
                                os.path.dirname(network_config),
                                'organizations/peerOrganizations/org1.example.com/'
                                'tlsca/tlsca.org1.example.com-cert.pem'
                            )
                        )
                        self._org_admin = ca_client.enroll(
                            'admin', 'adminpw'
                        )
                    except Exception as e2:
                        logger.error("创建管理员用户失败: %s", str(e2))
                        return False

                # 获取通道 Peer 节点列表
                try:
                    self._peers = self._client.get_peers(
                        org='org1.example.com'
                    )
                    if not self._peers:
                        # 从配置中手动获取 peer 地址
                        self._peers = ['peer0.org1.example.com']
                except Exception:
                    self._peers = ['peer0.org1.example.com']

                logger.info(
                    "Fabric 客户端初始化成功 | 通道: %s | 链码: %s | 配置: %s",
                    channel_name, chaincode_name, network_config
                )
                return True

            except Exception as e:
                logger.error("Fabric 客户端初始化失败: %s", str(e))
                self._client = None
                return False

    def get_client(self):
        """获取 Fabric Client 实例"""
        if self._client is None:
            self.init_client()
        return self._client

    def get_org_admin(self):
        """获取组织管理员用户"""
        return self._org_admin

    @property
    def channel_name(self) -> str:
        return self._channel_name or "culturaldnachannel"

    @property
    def chaincode_name(self) -> str:
        return self._chaincode_name or "artworkcc"

    @property
    def peers(self) -> list:
        return self._peers or ["peer0.org1.example.com"]


# 全局客户端管理器单例
_fabric_manager = FabricClientManager()


# ══════════════════════════════════════════════════════════════════
# 链码调用封装
# ══════════════════════════════════════════════════════════════════

def _invoke_chaincode(fcn: str, args: list) -> Optional[Dict[str, Any]]:
    """
    调用链码 Invoke 方法（写入交易）

    封装了客户端获取、请求构建、响应解析、异常处理

    Args:
        fcn: 链码方法名（如 "CreateWork"）
        args: 链码方法参数列表（全部为字符串）

    Returns:
        解析后的交易结果字典，失败返回 None
    """
    manager = _fabric_manager
    if not manager.init_client():
        logger.error("Fabric 客户端未就绪，无法调用链码 Invoke")
        return None

    client = manager.get_client()
    org_admin = manager.get_org_admin()

    if client is None or org_admin is None:
        logger.error("Fabric 客户端或管理员用户未就绪")
        return None

    try:
        # 执行链码调用
        response = client.chaincode_invoke(
            requestor=org_admin,
            channel_name=manager.channel_name,
            peers=manager.peers,
            cc_name=manager.chaincode_name,
            fcn=fcn,
            args=args,
            wait_for_tx_event=True,    # 等待交易确认
            wait_for_tx_event_timeout=60,  # 超时 60 秒
        )

        # 解析响应
        if response is None:
            logger.error("链码调用返回空响应 | fcn=%s", fcn)
            return None

        # fabric-sdk-py 返回格式：{ 'tx_id': '...', 'status': 200, 'payload': b'...' }
        # 或直接返回 bytes
        payload = None
        if isinstance(response, dict):
            payload = response.get('payload')
            tx_id = response.get('tx_id', '')
        elif isinstance(response, bytes):
            payload = response
            tx_id = ''
        else:
            payload = response
            tx_id = ''

        result = {"tx_id": tx_id}

        # 尝试解析 payload 为 JSON
        if payload:
            if isinstance(payload, bytes):
                payload_str = payload.decode("utf-8")
            else:
                payload_str = str(payload)
            try:
                parsed = json.loads(payload_str)
                if isinstance(parsed, dict):
                    result.update(parsed)
            except (json.JSONDecodeError, ValueError):
                result["payload"] = payload_str

        logger.info("链码调用成功 | fcn=%s | tx_id=%s", fcn, result.get("tx_id", ""))
        return result

    except Exception as e:
        logger.error("链码调用异常 | fcn=%s | args=%s | error=%s", fcn, args, str(e))
        return None


def _query_chaincode(fcn: str, args: list) -> Optional[Dict[str, Any]]:
    """
    调用链码 Query 方法（读取查询）

    与 Invoke 不同，Query 不产生交易，仅读取世界状态

    Args:
        fcn: 链码方法名（如 "QueryWork"）
        args: 链码方法参数列表（全部为字符串）

    Returns:
        解析后的查询结果字典，失败返回 None
    """
    manager = _fabric_manager
    if not manager.init_client():
        logger.error("Fabric 客户端未就绪，无法调用链码 Query")
        return None

    client = manager.get_client()
    org_admin = manager.get_org_admin()

    if client is None or org_admin is None:
        logger.error("Fabric 客户端或管理员用户未就绪")
        return None

    try:
        # 执行链码查询
        response = client.chaincode_query(
            requestor=org_admin,
            channel_name=manager.channel_name,
            peers=manager.peers,
            cc_name=manager.chaincode_name,
            fcn=fcn,
            args=args,
        )

        if response is None:
            logger.error("链码查询返回空响应 | fcn=%s", fcn)
            return None

        # 解析载荷
        payload = None
        if isinstance(response, dict):
            payload = response.get('payload')
        elif isinstance(response, bytes):
            payload = response
        else:
            payload = response

        if payload is None:
            return None

        # 转为字符串
        if isinstance(payload, bytes):
            payload_str = payload.decode("utf-8")
        else:
            payload_str = str(payload)

        # 解析 JSON
        try:
            result = json.loads(payload_str)
            return result
        except (json.JSONDecodeError, ValueError):
            logger.warning("链码查询返回非JSON数据 | fcn=%s | raw=%s", fcn, payload_str[:200])
            return {"raw": payload_str}

    except Exception as e:
        logger.error("链码查询异常 | fcn=%s | args=%s | error=%s", fcn, args, str(e))
        return None


# ══════════════════════════════════════════════════════════════════
# 对外 API（供 app/api/ 层调用）
# ══════════════════════════════════════════════════════════════════

def upload_to_blockchain(
    work_id: str,
    dna_hash: str,
    certificate_no: str,
    metadata: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    将作品DNA信息写入 Hyperledger Fabric 区块链

    调用链码：CreateWork(workId, dnaHash, owner, metadata, certificate)

    Args:
        work_id: 作品唯一编号
        dna_hash: DNA指纹SHA-256哈希
        certificate_no: 证书编号
        metadata: 作品元数据字典

    Returns:
        {
            "tx_id": "交易ID",
            "block_height": 区块高度（链码支持时返回）,
            "chain_code": "链码名称",
            "channel_name": "通道名称",
            "status": "success",
            "timestamp": "ISO时间戳"
        }
        上链失败返回 None
    """
    try:
        # 提取 owner 信息
        owner = str(metadata.get("owner", ""))
        metadata_json = json.dumps(metadata, ensure_ascii=False)

        # 调用链码
        result = _invoke_chaincode(
            fcn="CreateWork",
            args=[work_id, dna_hash, owner, metadata_json, certificate_no],
        )

        if result is None:
            return None

        # 构建返回结果
        return {
            "tx_id": result.get("txId", result.get("tx_id", "")),
            "block_height": result.get("blockHeight", result.get("block_height", 0)),
            "chain_code": _fabric_manager.chaincode_name,
            "channel_name": _fabric_manager.channel_name,
            "status": result.get("status", "success"),
            "timestamp": result.get("timestamp", ""),
        }

    except Exception as e:
        logger.error("上链存证失败: %s", str(e))
        return None


def query_from_blockchain(work_id: str) -> Optional[Dict[str, Any]]:
    """
    从区块链查询作品存证记录

    调用链码：QueryWork(workId)

    Args:
        work_id: 作品唯一编号

    Returns:
        {
            "workId": "作品编号",
            "dnaHash": "DNA哈希",
            "owner": "所有者ID",
            "metadata": {...},
            "certificate": "证书编号",
            "status": "存证状态",
            "createdAt": "创建时间",
            "updatedAt": "更新时间"
        }
        查询失败返回 None
    """
    try:
        result = _query_chaincode(
            fcn="QueryWork",
            args=[work_id],
        )

        if result is None:
            return None

        # 链码返回的 Artwork 结构直接即为查询结果
        # 补充字段映射
        return {
            "work_id": result.get("workId", work_id),
            "dna_hash": result.get("dnaHash", ""),
            "owner": result.get("owner", ""),
            "metadata": result.get("metadata", ""),
            "certificate_no": result.get("certificate", ""),
            "status": result.get("status", ""),
            "timestamp": result.get("createdAt", ""),
            "created_at": result.get("createdAt", ""),
            "updated_at": result.get("updatedAt", ""),
        }

    except Exception as e:
        logger.error("链上查询失败: %s", str(e))
        return None


def transfer_ownership(
    work_id: str,
    new_owner: str
) -> Optional[Dict[str, Any]]:
    """
    在区块链上执行作品所有权转让

    调用链码：TransferOwnership(workId, newOwner)

    Args:
        work_id: 作品唯一编号
        new_owner: 新所有者用户ID

    Returns:
        {
            "tx_id": "交易ID",
            "work_id": "作品编号",
            "from_owner": "转让方",
            "to_owner": "受让方",
            "timestamp": "转让时间"
        }
        转让失败返回 None
    """
    try:
        result = _invoke_chaincode(
            fcn="TransferOwnership",
            args=[work_id, str(new_owner)],
        )

        if result is None:
            return None

        return {
            "tx_id": result.get("txId", result.get("tx_id", "")),
            "work_id": result.get("workId", work_id),
            "from_owner": result.get("fromOwner", ""),
            "to_owner": result.get("toOwner", str(new_owner)),
            "timestamp": result.get("timestamp", ""),
        }

    except Exception as e:
        logger.error("所有权转让失败: %s", str(e))
        return None


def verify_dna_on_chain(work_id: str, input_hash: str) -> bool:
    """
    在区块链上验证DNA哈希是否匹配

    调用链码：VerifyDNA(workId, inputHash)

    Args:
        work_id: 作品唯一编号
        input_hash: 待验证的DNA哈希值

    Returns:
        True 表示哈希匹配（真品），False 表示不匹配
    """
    try:
        result = _query_chaincode(
            fcn="VerifyDNA",
            args=[work_id, input_hash],
        )

        if result is None:
            return False

        # 链码返回 { "match": true/false, "chainHash": "...", ... }
        return result.get("match", False)

    except Exception as e:
        logger.error("链上DNA验证失败: %s", str(e))
        return False


def verify_certificate_on_chain(certificate_no: str, work_id: str = None) -> Optional[Dict[str, Any]]:
    """
    在区块链上验证证书真伪

    通过 workId 查询链上记录，对比证书编号和 DNA 哈希是否一致

    Args:
        certificate_no: 证书编号
        work_id: 作品唯一编号（从数据库获取后传入）

    Returns:
        {
            "certificate_no": "证书编号",
            "is_valid": True/False,
            "chain_record": { "tx_id": "...", "block_height": 0, "timestamp": "..." }
        }
    """
    try:
        if not work_id:
            logger.warning("缺少 work_id，无法链上验证证书: %s", certificate_no)
            return {
                "certificate_no": certificate_no,
                "is_valid": False,
                "chain_record": {
                    "tx_id": "",
                    "block_height": 0,
                    "timestamp": "",
                }
            }

        # 从链上查询作品记录
        chain_data = query_from_blockchain(work_id)
        if chain_data is None:
            logger.warning("链上未找到作品记录: %s", work_id)
            return {
                "certificate_no": certificate_no,
                "is_valid": False,
                "chain_record": {
                    "tx_id": "",
                    "block_height": 0,
                    "timestamp": "",
                }
            }

        # 验证链上证书编号是否匹配
        chain_cert_no = chain_data.get("certificate_no", "")
        is_valid = chain_cert_no == certificate_no

        return {
            "certificate_no": certificate_no,
            "is_valid": is_valid,
            "chain_record": {
                "tx_id": chain_data.get("tx_id", chain_data.get("work_id", "")),
                "block_height": chain_data.get("block_height", 0),
                "timestamp": chain_data.get("timestamp", chain_data.get("created_at", "")),
            }
        }

    except Exception as e:
        logger.error("证书验证失败: %s", str(e))
        return None


def get_work_history(work_id: str) -> Optional[list]:
    """
    查询作品在链上的历史变更记录

    调用链码：GetWorkHistory(workId)

    Args:
        work_id: 作品唯一编号

    Returns:
        历史记录列表，每项包含 txId, timestamp, isDelete, record
        查询失败返回 None
    """
    try:
        result = _query_chaincode(
            fcn="GetWorkHistory",
            args=[work_id],
        )

        if result is None:
            return None

        # 链码返回 JSON 字符串，如果是 dict 则直接返回
        if isinstance(result, dict) and "raw" in result:
            return json.loads(result["raw"])
        return result if isinstance(result, list) else []

    except Exception as e:
        logger.error("查询作品历史失败: %s", str(e))
        return None


def is_available() -> bool:
    """
    检查 Fabric 网络是否可用

    用于服务健康检查端点

    Returns:
        True 表示 Fabric 网络已连接
    """
    return _fabric_manager.init_client()