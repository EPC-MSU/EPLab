from enum import Enum
from typing import List, Optional
from epcore.ivmeasurer import IVMeasurerASA, IVMeasurerBase, IVMeasurerIVM10, IVMeasurerVirtual, IVMeasurerVirtualASA


class MeasurerType(Enum):
    """
    Class with types of measurers.
    """

    ASA = "ASA"
    ASA_VIRTUAL = "virtualasa"
    IVM10 = "IVM10"
    IVM10_VIRTUAL = "virtual"


class ProductName(Enum):
    """
    Class with names of available products for application.
    """

    EYEPOINT_A2 = "EyePoint a2"
    EYEPOINT_H10 = "EyePoint H10"
    EYEPOINT_S2 = "EyePoint S2"
    EYEPOINT_U21 = "EyePoint u21"
    EYEPOINT_U22 = "EyePoint u22"

    @classmethod
    def check_replaceability(cls, product_1: "ProductName", product_2: "ProductName") -> bool:
        """
        :param product_1: first product name;
        :param product_2: second product name.
        :return: True if the given products are replaceable.
        """

        if product_1 == product_2:
            return True

        eyepoints_with_2_channels = cls.EYEPOINT_S2, cls.EYEPOINT_U22
        if product_1 in eyepoints_with_2_channels and product_2 in eyepoints_with_2_channels:
            return True

        eyepoints_with_1_channel = cls.EYEPOINT_A2, cls.EYEPOINT_U21
        if product_1 in eyepoints_with_1_channel and product_2 in eyepoints_with_1_channel:
            return True

        return False

    @classmethod
    def get_default_product_name_for_measurers(cls, measurers: List[IVMeasurerBase]) -> Optional["ProductName"]:
        """
        :param measurers: IV-measurers.
        :return: default name of product for given IV-measurers.
        """

        def check_asa(measurer_: IVMeasurerBase) -> bool:
            return type(measurer_) in (IVMeasurerASA, IVMeasurerVirtualASA)

        def check_ivm10(measurer_: IVMeasurerBase) -> bool:
            return type(measurer_) in (IVMeasurerIVM10, IVMeasurerVirtual)

        product_name = None
        not_none_measurers = list(filter(lambda x: x is not None, measurers))
        if len(not_none_measurers) == 1:
            measurer = not_none_measurers[0]
            if check_asa(measurer):
                product_name = cls.EYEPOINT_H10
            elif check_ivm10(measurer):
                product_name = cls.EYEPOINT_A2
        elif len(not_none_measurers) == 2 and len(list(filter(check_ivm10, not_none_measurers))) == 2:
            product_name = cls.EYEPOINT_U22

        if product_name is None:
            raise ValueError("Unknown default name of product")
        return product_name

    @classmethod
    def get_default_product_name_for_uris(cls, uris: List[str]) -> Optional["ProductName"]:
        """
        :param uris: list of URIs.
        :return: name of a product whose measurers may have given URIs.
        """

        from connection_window.urichecker import URIChecker

        product_name = None
        not_empty_uris = list(filter(lambda x: bool(x), uris))
        if len(not_empty_uris) == 1:
            uri = not_empty_uris[0]
            if URIChecker.check_asa(uri):
                product_name = cls.EYEPOINT_H10
            elif URIChecker.check_ivm10(uri):
                product_name = cls.EYEPOINT_A2
        elif len(not_empty_uris) == 2 and len(list(filter(URIChecker.check_ivm10, not_empty_uris))) == 2:
            product_name = cls.EYEPOINT_U22

        if product_name is None:
            raise ValueError("Unknown default name of product")
        return product_name

    @classmethod
    def get_measurer_type_by_product_name(cls, product_name: "ProductName") -> Optional[MeasurerType]:
        """
        Method returns type of measurer by name of product.
        :param product_name: name of product.
        :return: type of measurer.
        """

        if product_name == cls.EYEPOINT_H10:
            return MeasurerType.ASA
        if product_name in (cls.EYEPOINT_A2, cls.EYEPOINT_U21, cls.EYEPOINT_U22, cls.EYEPOINT_S2):
            return MeasurerType.IVM10
        return None

    @classmethod
    def get_product_name_by_string(cls, product_name: str) -> Optional["ProductName"]:
        """
        :param product_name: product name as a string.
        :return: product name.
        """

        if not product_name:
            return None

        for product in cls.get_product_names_for_platform():
            if product.name.lower() == product_name.lower():
                return product
        return None

    @classmethod
    def get_product_names_for_platform(cls) -> List["ProductName"]:
        """
        Method returns names of products for platform of system.
        :return: names of products.
        """

        return [cls.EYEPOINT_A2, cls.EYEPOINT_U21, cls.EYEPOINT_U22, cls.EYEPOINT_S2, cls.EYEPOINT_H10]

    @classmethod
    def get_single_channel_products(cls) -> List["ProductName"]:
        """
        Method returns names of products with single channel (measurer).
        :return: names of products.
        """

        return [cls.EYEPOINT_A2, cls.EYEPOINT_U21, cls.EYEPOINT_H10]
