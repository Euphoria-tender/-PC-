"""
文化DNA —— 非遗作品确权溯源系统
模型模块统一导出
"""
from app.models.user import TUser
from app.models.artwork import TArtwork
from app.models.fingerprint import TFingerprint
from app.models.chain_record import TChainRecord
from app.models.ownership_transfer import TOwnershipTransfer
from app.models.verification_log import TVerificationLog
from app.models.reference_image import TReferenceImage
from app.models.publish_record import TPublishRecord
from app.models.role_application import TRoleApplication

__all__ = [
    "TUser",
    "TArtwork",
    "TFingerprint",
    "TChainRecord",
    "TOwnershipTransfer",
    "TVerificationLog",
    "TReferenceImage",
    "TPublishRecord",
    "TRoleApplication",
]