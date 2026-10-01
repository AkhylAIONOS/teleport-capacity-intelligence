from pathlib import Path
import numpy as np
import pandas as pd
from app.config import (
    DATA_DIR,
    COLUMN_MAP,
    SHIPMENT_COLUMNS,
    OPTION_COLUMNS,
    FUEL_COLUMNS,
)


class DataValidationError(ValueError):
    pass


class DataLoader:
    """Maps external columns once, audits raw rows, quarantines unsafe records."""

    def __init__(self, data_dir=DATA_DIR, column_map=None):
        self.data_dir = Path(data_dir)
        self.column_map = column_map or COLUMN_MAP
        self.quality = {}
        self.shipments = self.load_shipments()
        self.options = self.load_options()
        self.fuel = self._load("fuel_index", FUEL_COLUMNS)
        self.normalize_data(self.fuel, ["fuel_index", "fuel_price_usd"], ["date"])
        self.quality["fuel_rows_loaded"] = len(self.fuel)
        self.quality["invalid_fuel_rows"] = int(
            (
                self.fuel.isna().any(axis=1)
                | self.fuel[["fuel_index", "fuel_price_usd"]].lt(0).any(axis=1)
            ).sum()
        )
        self.quality["shipments_without_candidate_options"] = int(
            (~self.shipments.shipment_id.isin(self.options.shipment_id)).sum()
        )
        self.quality["orphan_options"] = int(
            (~self.options.shipment_id.isin(self.shipments.shipment_id)).sum()
        )
        self.quality["usable_shipments"] = len(self.shipments)
        self.quality["usable_options"] = len(self.options)

    def validate_schema(self, df, columns, name):
        missing = sorted(set(columns) - set(df.columns))
        if missing:
            raise DataValidationError(
                f'{name}.csv: missing required columns: {", ".join(missing)}. Configure COLUMN_MAP_FILE to map source columns.'
            )

    def _load(self, name, columns):
        path = self.data_dir / f"{name}.csv"
        if not path.exists():
            raise DataValidationError(f"Dataset not found: {path}")
        try:
            df = pd.read_csv(path, dtype=str)
        except pd.errors.EmptyDataError:
            raise DataValidationError(
                f"{name}.csv is missing a header; provide canonical column headers even for empty data."
            )
        mapping = self.column_map.get(name, {})
        df = df.rename(
            columns={source: canonical for canonical, source in mapping.items()}
        )
        self.validate_schema(df, columns, name)
        return df[columns].copy()

    def normalize_data(self, df, numeric, dates):
        for col in numeric:
            df[col] = pd.to_numeric(df[col], errors="coerce").replace(
                [np.inf, -np.inf], np.nan
            )
        for col in dates:
            df[col] = (
                pd.to_datetime(df[col], errors="coerce", utc=True)
                .dt.tz_localize(None)
                .dt.normalize()
            )
        return df

    def load_shipments(self):
        df = self._load("shipments", SHIPMENT_COLUMNS)
        costs = [
            "actual_base_cost",
            "actual_fuel_surcharge",
            "actual_other_cost",
            "actual_paid",
        ]
        dates = ["shipment_date", "actual_departure_date"]
        self.normalize_data(df, costs + ["weight_kg", "volume_cbm"], dates)
        missing_carrier = df.actual_carrier.isna() | df.actual_carrier.fillna(
            ""
        ).str.strip().eq("")
        invalid_cost = df[costs].isna().any(axis=1) | df[costs].lt(0).any(axis=1)
        mismatch = (df.actual_paid - df[costs[:3]].sum(axis=1)).abs().gt(0.011)
        invalid_dates = df[dates].isna().any(axis=1) | (
            df.actual_departure_date < df.shipment_date
        )
        invalid_capacity = (
            df.weight_kg.isna()
            | df.weight_kg.le(0)
            | df.volume_cbm.isna()
            | df.volume_cbm.lt(0)
        )
        duplicate = df.shipment_id.duplicated(keep=False)
        missing_id = df.shipment_id.isna() | df.shipment_id.fillna("").astype(
            str
        ).str.strip().eq("")
        missing_lane = df[["origin", "destination"]].isna().any(axis=1)
        invalid_rate = ~df.actual_rate_type.isin(["Contract", "Spot", "Owned"])
        self.quality.update(
            shipment_rows_loaded=len(df),
            missing_costs=int(invalid_cost.sum()),
            missing_carriers=int(missing_carrier.sum()),
            invalid_dates=int(invalid_dates.sum()),
            invalid_capacities=int(invalid_capacity.sum()),
            duplicate_shipment_ids=int(duplicate.sum()),
            inconsistent_actual_totals=int(mismatch.sum()),
            missing_shipment_ids=int(missing_id.sum()),
            missing_lanes=int(missing_lane.sum()),
            invalid_rate_types=int(invalid_rate.sum()),
        )
        safe = ~(
            invalid_cost
            | mismatch
            | missing_carrier
            | invalid_dates
            | invalid_capacity
            | duplicate
            | missing_id
            | missing_lane
            | invalid_rate
        )
        self.quality["quarantined_shipments"] = int((~safe).sum())
        df = df.loc[safe].copy()
        for c in ["origin", "destination"]:
            df[c] = df[c].astype(str).str.strip().str.upper()
        df["lane"] = df.origin + "-" + df.destination
        return df

    def load_options(self):
        df = self._load("carrier_options", OPTION_COLUMNS)
        costs = ["base_cost", "fuel_surcharge", "other_cost", "total_landed_cost"]
        self.normalize_data(
            df,
            costs + ["capacity_available_kg", "required_capacity_kg"],
            ["departure_date"],
        )
        for col in ["available", "sla_feasible"]:
            df[col] = (
                df[col]
                .astype(str)
                .str.lower()
                .str.strip()
                .map({"true": True, "false": False, "1": True, "0": False})
                .fillna(False)
                .astype(bool)
            )
        missing = df[costs].isna().any(axis=1) | df[costs].lt(0).any(axis=1)
        mismatch = (df.total_landed_cost - df[costs[:3]].sum(axis=1)).abs().gt(0.011)
        capacities = (
            df[["capacity_available_kg", "required_capacity_kg"]].isna().any(axis=1)
            | df.capacity_available_kg.lt(0)
            | df.required_capacity_kg.le(0)
        )
        carriers = df.carrier.isna() | df.carrier.fillna("").str.strip().eq("")
        dates = df.departure_date.isna()
        invalid_identity = (
            df.option_id.isna()
            | df.option_id.duplicated(keep=False)
            | df.shipment_id.isna()
            | ~df.rate_type.isin(["Contract", "Spot", "Owned"])
        )
        self.quality.update(
            carrier_option_rows_loaded=len(df),
            missing_option_costs=int(missing.sum()),
            inconsistent_option_totals=int(mismatch.sum()),
            invalid_option_capacities=int(capacities.sum()),
            invalid_option_dates=int(dates.sum()),
            missing_option_carriers=int(carriers.sum()),
            invalid_option_ids_or_rate_types=int(invalid_identity.sum()),
        )
        df["data_valid"] = ~(
            missing | mismatch | capacities | carriers | dates | invalid_identity
        )
        return df
