from abc import ABC, abstractmethod

from erpguard.canonical.enums import CanonicalAction, ERPType
from erpguard.canonical.objects import SalesOrder


class ERPAdapter(ABC):
    @abstractmethod
    def get_erp_type(self) -> ERPType:
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_sales_order(self, order_id: str) -> SalesOrder:
        raise NotImplementedError

    @abstractmethod
    def get_sales_order_by_reference(self, reference: str) -> SalesOrder:
        raise NotImplementedError

    @abstractmethod
    def inspect_permissions(
        self,
        actor_id: str,
        canonical_action: CanonicalAction,
        target_object: str,
        target_id: str,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def list_supported_actions(self) -> list[CanonicalAction]:
        raise NotImplementedError
