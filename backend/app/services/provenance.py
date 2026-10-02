"""Offline provenance; answers are deterministic and never delegated to an LLM."""
import json
import csv
from functools import lru_cache
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / 'data/provenance'


def load_provenance():
    return {name: json.loads((ROOT / f'{name}.json').read_text()) for name in ['source_registry', 'field_provenance', 'demo_manifest', 'lane_provenance']}


def provenance_answer(message):
    q = re.sub(r'[^a-z0-9+ -]', '', message.lower())
    kind = None
    if ('kul-del' in q or 'kul to del' in q) and any(w in q for w in ['real', 'actual', 'public', 'confirmed']): kind = 'lane'
    elif any(w in q for w in ['freighters', 'freighter']) and any(w in q for w in ['source', 'where', 'number']): kind = 'fleet'
    elif any(w in q for w in ['partners', '55+']) and any(w in q for w in ['source', 'where', 'number']): kind = 'partners'
    elif 'fuel' in q and any(w in q for w in ['source', 'where', 'public', 'data']): kind = 'fuel'
    elif 'optimized cost' in q and any(w in q for w in ['how', 'calculated', 'formula']): kind = 'optimizer'
    elif any(w in q for w in ['saving', 'savings']) and any(w in q for w in ['where did', 'calculated', 'how is', 'come from']): kind = 'saving'
    elif 'dataset' in q and any(w in q for w in ['generated', 'how was', 'generation']): kind = 'generation'
    elif any(w in q for w in ['synthetic', 'provenance', 'assumptions', 'sources', 'data is public']) or ('actual teleport shipment' in q): kind = 'classification'
    if kind is None: return None
    p = load_provenance(); sources = {s['source_id']: s for s in p['source_registry']}; fields = p['field_provenance']; manifest = p['demo_manifest']
    def cite(id):
        s = sources[id]
        return f'{s["title"]}: {s["url"]}'
    disclaimer = manifest['note']
    if kind == 'saving':
        answer = f'The displayed potential saving is DERIVED in the active scope: {fields["potential_saving"]["formula"]}. Recorded synthetic cost minus lowest feasible synthetic candidate cost is floored at zero per shipment, then summed. Savings %: {fields["saving_percent"]["formula"]}. Network and fuel assumptions use public calibration. {disclaimer}'
    elif kind == 'optimizer':
        answer = f'Optimized cost is DERIVED_BY_OPTIMIZER: {fields["optimized_cost"]["formula"]}. Candidates must have valid nonnegative cost, availability, sufficient capacity, feasible SLA and a departure on or after shipment date. Tie-breaks: departure date, carrier, option ID. Landed cost = {fields["total_landed_cost"]["formula"]}. Every commercial input is synthetic. {disclaimer}'
    elif kind in ['fleet', 'partners']:
        facts = sources['teleport_network_2026']['facts_used']
        answer = (f'Teleport lists {facts["owned_freighters"]} owned freighters, type {facts["fleet_type"]}.' if kind == 'fleet' else f'Teleport lists {facts["air_partners_min"]}+ air partners; the demo represents a smaller synthetic subset.') + ' ' + cite('teleport_network_2026') + ' Network snapshot is public; individual demo assignments and capacities are synthetic.'
    elif kind == 'fuel':
        facts = sources['iata_fuel_2026']['facts_used']
        answer = f'IATA forecasts approximately USD {facts["jet_fuel_average_usd_per_barrel"]}/barrel for 2026 and {facts["fuel_operating_expenses_percent"]}% of operating expenses. This is a full-year forecast, not actual daily observations. Jan–Jun values are SYNTHETIC SERIES CALIBRATED TO PUBLIC 2026 BENCHMARK. {cite("iata_fuel_2026")}. Teleport calibrates the weekly, regional USD/kg mechanism only; no September FSC rates are applied to Jan–Jun. {cite("teleport_fsc_reference")}. Formula: {fields["fuel_surcharge"]["formula"]}.'
    elif kind == 'lane':
        lane = p['lane_provenance']['KUL-DEL']; answer = f'KUL-DEL: {lane["classification"]}. {lane["note"]} Airport geography: {cite("ourairports")}. No confirmed direct historical Teleport route is asserted.'
    elif kind == 'generation':
        answer = f'Demo dataset {manifest["dataset_version"]}, generator {manifest["generator_version"]}, fixed random seed {manifest["random_seed"]}; period {manifest["demo_period"]}; {manifest["shipment_count"]} synthetic shipments and {manifest["candidate_option_count"]} synthetic options. Versioned offline public snapshots calibrate network, geography and fuel; costs, choices and feasibility are simulated; unchanged deterministic optimizer calculates results. {disclaimer}'
    else:
        synthetic = ', '.join(k for k,v in fields.items() if v['classification'].startswith('SYNTHETIC'))
        answer = f'No. Shipment-level records are synthetic demonstration data, not actual Teleport shipment history. PUBLIC FACTS: company disclosures, network fleet and partner counts, industry fuel benchmark and airport metadata. SYNTHETIC ASSUMPTIONS: {synthetic}. Candidate quotes, booking capacity, SLA and rejected options are simulated. DERIVED METRICS: optimized cost, recommendation, potential saving, savings %, lane/carrier aggregation, monthly trend and rate mix. Sources: ' + '; '.join(cite(id) for id in sources) + '. ' + disclaimer
    return answer, p


@lru_cache(maxsize=1)
def cost_inputs_by_shipment():
    grouped = {}
    with (ROOT / "cost_inputs.csv").open() as file:
        for row in csv.DictReader(file):
            row = {k: v if k in ["option_id", "shipment_id"] else float(v) for k,v in row.items()}
            grouped.setdefault(row["shipment_id"], []).append(row)
    return grouped


def shipment_provenance(shipment):
    provenance = load_provenance()
    lane = f'{shipment["origin"]}-{shipment["destination"]}'
    return dict(fields=provenance["field_provenance"],
        lane=provenance["lane_provenance"].get(lane),
        cost_inputs=cost_inputs_by_shipment().get(shipment["shipment_id"], []))
