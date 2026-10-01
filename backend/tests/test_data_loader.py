import pandas as pd
import pytest
from app.services.data_loader import DataLoader, DataValidationError
from app.config import DATA_DIR, COLUMN_MAP
from app.services.analytics_service import AnalyticsService


def copy_data(tmp_path):
    for name in ["shipments", "carrier_options", "fuel_index"]:
        pd.read_csv(DATA_DIR / f"{name}.csv").head(10).to_csv(
            tmp_path / f"{name}.csv", index=False
        )


def test_missing_schema(tmp_path):
    copy_data(tmp_path)
    p = tmp_path / "shipments.csv"
    df = pd.read_csv(p)
    df.drop(columns="actual_paid").to_csv(p, index=False)
    with pytest.raises(DataValidationError, match="actual_paid"):
        DataLoader(tmp_path)


def test_mapping(tmp_path):
    copy_data(tmp_path)
    p = tmp_path / "shipments.csv"
    df = pd.read_csv(p)
    df.rename(columns={"actual_paid": "real_paid"}).to_csv(p, index=False)
    mapping = {k: dict(v) for k, v in COLUMN_MAP.items()}
    mapping["shipments"]["actual_paid"] = "real_paid"
    loader = DataLoader(tmp_path, mapping)
    assert len(loader.shipments) == 10


def test_quality(tmp_path):
    copy_data(tmp_path)
    p = tmp_path / "shipments.csv"
    df = pd.read_csv(p)
    df.loc[0, "actual_paid"] = -1
    df.loc[1, "shipment_date"] = "bad"
    df.loc[2, "actual_carrier"] = None
    df.loc[3, "shipment_id"] = df.loc[4, "shipment_id"]
    df.to_csv(p, index=False)
    loader = DataLoader(tmp_path)
    assert loader.quality["missing_costs"] == 1
    assert loader.quality["invalid_dates"] == 1
    assert loader.quality["missing_carriers"] == 1
    assert loader.quality["duplicate_shipment_ids"] == 2
    assert len(loader.shipments) == 5


def test_empty_csv(tmp_path):
    for name in ["shipments", "carrier_options", "fuel_index"]:
        pd.read_csv(DATA_DIR / f"{name}.csv").iloc[:0].to_csv(
            tmp_path / f"{name}.csv", index=False
        )
    a = AnalyticsService(DataLoader(tmp_path))
    assert a.get_overall_summary()["actual_spend"] == 0
    assert a.shipments()["rows"] == []
    assert a.metadata()["lanes"] == []


def test_inconsistent_costs_rejected(tmp_path):
    copy_data(tmp_path)
    p = tmp_path / "carrier_options.csv"
    df = pd.read_csv(p)
    df.loc[0, "total_landed_cost"] = 1
    df.to_csv(p, index=False)
    loader = DataLoader(tmp_path)
    assert loader.quality["inconsistent_option_totals"] == 1
    assert not loader.options.iloc[0].data_valid


def test_source_ids_keep_leading_zeros(tmp_path):
    copy_data(tmp_path)
    p = tmp_path / "shipments.csv"
    df = pd.read_csv(p)
    df["shipment_id"] = [f"{i:05}" for i in range(len(df))]
    df.to_csv(p, index=False)
    loader = DataLoader(tmp_path)
    assert loader.shipments.iloc[0].shipment_id == "00000"
