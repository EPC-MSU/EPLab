from enum import Enum
from typing import List, Optional, Tuple
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
    def get_default_product_name_for_measurers(cls, measurers: List[IVMeasurerBase]) -> Optional["ProductName"]:
        """
        Method returns default name of product for given measurers.
        :param measurers: measurers.
        :return: name of product.
        """

        product_name = None
        for measurer in measurers:
            if isinstance(measurer, (IVMeasurerASA, IVMeasurerVirtualASA)) and product_name in (None, cls.EYEPOINT_H10):
                product_name = cls.EYEPOINT_H10
            elif (isinstance(measurer, (IVMeasurerIVM10, IVMeasurerVirtual)) and
                  product_name in (None, cls.EYEPOINT_A2)):
                product_name = cls.EYEPOINT_A2
            else:
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
    def get_product_names_for_platform(cls) -> List["ProductName"]:
        """
        Method returns names of products for platform of system.
        :return: names of products.
        """

        return [cls.EYEPOINT_A2, cls.EYEPOINT_U21, cls.EYEPOINT_U22, cls.EYEPOINT_S2, cls.EYEPOINT_H10]

    @classmethod
    def get_single_channel_products(cls) -> Tuple["ProductName", "ProductName", "ProductName"]:
        """
        Method returns names of products with single channel (measurer).
        :return: names of products.
        """

        return cls.EYEPOINT_A2, cls.EYEPOINT_U21, cls.EYEPOINT_H10
