from crawler.core_carrier.items import ExportErrorData
from crawler.core_carrier.base import CARRIER_RESULT_STATUS_ERROR


class Verifier:
    def verify(self, results):
        assert results[0] == ExportErrorData(
            mbl_no="NKAI90055900",
            status=CARRIER_RESULT_STATUS_ERROR,
            detail="Data was not found",
        )
