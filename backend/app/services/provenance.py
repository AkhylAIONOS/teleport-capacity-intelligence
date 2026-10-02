"""Offline provenance; answers are deterministic and never delegated to an LLM."""
import json
import csv
from functools import lru_cache
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / 'data/provenance'


def load_provenance():
    return {name: json.loads((ROOT / f'{name}.json').read_text()) for name in ['source_registry', 'field_provenance', 'demo_manifest', 'lane_provenance']}


def provenance_kind(message):
    """Recognize explanation requests before analytics ranking or an optional LLM."""
    q = re.sub(r'[^a-z0-9+ -]', '', message.lower())
    if ('kul-del' in q or 'kul to del' in q) and any(w in q for w in ['real', 'actual', 'public', 'confirmed']):
        return 'lane'
    if any(w in q for w in ['freighters', 'freighter']) and any(w in q for w in ['source', 'where', 'number']):
        return 'fleet'
    if any(w in q for w in ['partners', '55+']) and any(w in q for w in ['source', 'where', 'number']):
        return 'partners'
    if 'fuel' in q and (any(w in q for w in ['coefficient', 'constant', 'generator formula']) or ('formula' in q and any(w in q for w in ['exact', 'precise', 'numeric', 'full', 'detailed']))):
        return 'fuel_formula'
    if 'fuel' in q and any(w in q for w in ['source', 'where', 'public', 'data', 'formula', 'calculated', 'methodology']):
        return 'fuel'
    if 'optimized cost' in q and any(w in q for w in ['how', 'calculated', 'formula']):
        return 'optimizer'
    if any(w in q for w in ['saving', 'savings']) and any(w in q for w in ['where did', 'where does', 'calculated', 'how is', 'how are', 'come from', 'explain this', 'explain the']):
        return 'saving'
    if 'dataset' in q and any(w in q for w in ['generated', 'how was', 'generation']):
        return 'generation'
    if 'actual teleport shipment' in q or ('shipment records' in q and any(w in q for w in ['real', 'actual'])):
        return 'records'
    if 'sources' in q or 'source list' in q:
        return 'sources'
    if any(w in q for w in ['synthetic', 'provenance', 'assumptions', 'data is public']):
        return 'classification'
    return None


def date_label(value):
    from datetime import date
    parsed = date.fromisoformat(str(value))
    return f'{parsed:%b} {parsed.day}, {parsed.year}'


def savings_scope(filters):
    """Describe existing filters without changing them or applying chat context."""
    values = filters.model_dump(exclude_none=True) if filters is not None else {}
    labels = {
        'start_date': 'From', 'end_date': 'Through', 'origin': 'Origin',
        'destination': 'Destination', 'lane': 'Lane', 'carrier': 'Actual carrier',
        'recommended_carrier': 'Recommended carrier', 'rate_type': 'Actual rate type',
        'recommended_rate_type': 'Recommended rate type', 'min_saving': 'Minimum saving',
        'search': 'Search', 'shipment_ids': 'Selected shipments',
    }
    parts = []
    for key, value in values.items():
        if value in (None, '', 0, []):
            continue
        if key in ['start_date', 'end_date']:
            value = date_label(value)
        elif key == 'min_saving':
            value = f'${value:,.2f}'
        elif key == 'shipment_ids':
            value = ', '.join(value)
        parts.append(f'{labels[key]}: {value}')
    return 'Active scope — ' + '; '.join(parts) if parts else 'Overall current dataset (no dashboard filters)'


def provenance_answer(message, summary=None, filters=None):
    kind = provenance_kind(message)
    if kind is None:
        return None
    p = load_provenance()
    sources = {s['source_id']: s for s in p['source_registry']}
    fields = p['field_provenance']
    manifest = p['demo_manifest']

    def cite(id):
        source = sources[id]
        return f'{source["title"]}: {source["url"]}'

    disclaimer = manifest['note']
    if kind == 'saving':
        metrics = summary if summary is not None else {**manifest['summary'], 'shipment_count': manifest['shipment_count']}
        answer = (
            f'{savings_scope(filters)}: {metrics["shipment_count"]:,} shipments, '
            f'${metrics["potential_saving"]:,.2f} potential savings ({metrics["saving_percent"]:.2f}% of actual spend).\n\n'
            'Potential saving per shipment = max(actual simulated cost - lowest feasible optimized cost, 0). '
            'Aggregate savings = sum of shipment potential savings in the active scope. '
            'If no option is feasible, the historical simulated cost is retained and the saving is zero. '
            'Shipment-level commercial values are synthetic; public sources calibrate network, geography and fuel assumptions. '
            'This is a derived demo metric, not actual Teleport historical savings.'
        )
    elif kind == 'optimizer':
        answer = f'Optimized cost is DERIVED_BY_OPTIMIZER: {fields["optimized_cost"]["formula"]}. Candidates must have valid nonnegative cost, availability, sufficient capacity, feasible SLA and a departure on or after shipment date. Tie-breaks: departure date, carrier, option ID. Landed cost = {fields["total_landed_cost"]["formula"]}. Every commercial input is synthetic. {disclaimer}'
    elif kind in ['fleet', 'partners']:
        facts = sources['teleport_network_2026']['facts_used']
        answer = (f'Teleport lists {facts["owned_freighters"]} owned freighters, type {facts["fleet_type"]}.' if kind == 'fleet' else f'Teleport lists {facts["air_partners_min"]}+ air partners; the demo represents a smaller synthetic subset.') + ' ' + cite('teleport_network_2026') + ' Network snapshot is public; individual demo assignments and capacities are synthetic.'
    elif kind == 'fuel':
        facts = sources['iata_fuel_2026']['facts_used']
        answer = (
            f'The public calibration is IATA’s 2026 fuel outlook: approximately USD {facts["jet_fuel_average_usd_per_barrel"]}/barrel '
            f'and {facts["fuel_operating_expenses_percent"]}% of airline operating expenses. {cite("iata_fuel_2026")}.\n\n'
            'Jan–Jun fuel values are a synthetic series calibrated to that full-year forecast, not actual IATA daily observations. '
            'Teleport’s FSC reference calibrates the weekly, regional USD/kg mechanism; no September rates are applied to Jan–Jun. '
            f'{cite("teleport_fsc_reference")}.\n\n'
            'Conceptual methodology: shipment weight × fuel-index adjustment × regional/lane calibration. '
            'Ask “show the exact fuel formula” for the generator coefficients.'
        )
    elif kind == 'fuel_formula':
        answer = (
            'Exact synthetic fuel formula: ' + fields['fuel_surcharge']['formula'] + '. '
            'The coefficient and lane factors are synthetic calibration assumptions, not official Teleport rates. '
            'Lane factors: ' + '; '.join(f'{region}: {factor}' for region, factor in manifest['calibration']['lane_factors'].items()) + '. '
            'The candidate multiplier is simulated per option; exact inputs are available in the shipment audit. '
            f'{cite("iata_fuel_2026")}. {cite("teleport_fsc_reference")}.'
        )
    elif kind == 'lane':
        lane = p['lane_provenance']['KUL-DEL']
        answer = f'KUL-DEL: {lane["classification"]}. {lane["note"]} Airport geography: {cite("ourairports")}. No confirmed direct historical Teleport route is asserted.'
    elif kind == 'generation':
        period = manifest['demo_period']
        answer = (
            f'Dataset {manifest["dataset_version"]} was created with Generator {manifest["generator_version"]} '
            f'and fixed random seed {manifest["random_seed"]}. '
            f'It covers {date_label(period["start"])} – {date_label(period["end"])}, '
            f'with {manifest["shipment_count"]:,} synthetic shipments and {manifest["candidate_option_count"]:,} candidate options. '
            'Versioned local public-source snapshots calibrate network, geography and fuel assumptions. '
            'Shipment costs, carrier choices, capacity and SLA are simulated; the deterministic optimizer calculates recommendations and savings. '
            'These are demonstration records, not actual Teleport shipment history.'
        )
    elif kind == 'records':
        answer = (
            'No. These are synthetic demonstration records, not actual Teleport shipment history. '
            'Shipment weights, carrier quotes, capacity, SLA and historical choices are simulated. '
            'Public Teleport, IATA and airport sources calibrate network, geography and fuel assumptions. '
            'Recommendations and savings are calculated from those simulated records.'
        )
    elif kind == 'sources':
        uses = [
            ('teleport_1h_2026', 'Teleport 1H 2026 Results', 'company-level disclosures and publicly named partner relationships'),
            ('teleport_network_2026', 'Teleport Network', 'fleet type, owned freighter count and network scale'),
            ('teleport_routes_2022', 'Teleport historical cargo destinations', 'historic destination geography; not current direct schedules'),
            ('teleport_fsc_reference', 'Teleport FSC mechanism', 'weekly, regional USD/kg structure; not historical Jan–Jun rates'),
            ('iata_fuel_2026', 'IATA 2026 Fuel Outlook', 'full-year fuel benchmark for the synthetic fuel series'),
            ('ourairports', 'OurAirports', 'public airport codes, names, location and coordinates'),
        ]
        answer = 'Sources used for this dashboard:\n' + '\n'.join(
            f'- {title} — {use}. {sources[id]["url"]}' for id, title, use in uses
        ) + '\n\nThese public sources calibrate synthetic demonstration records; they do not supply shipment-level commercial data.'
    else:
        answer = (
            'PUBLIC\nTeleport company disclosures, network facts and historical destination references; '
            'the Teleport fuel surcharge mechanism, IATA fuel benchmark and OurAirports airport metadata.\n\n'
            'SYNTHETIC\nIndividual shipments, weights, carrier assignments and quotes, contract/spot prices, '
            'booking capacity, SLA, historical choices and the Jan–Jun fuel series. These are simulated demonstration records.\n\n'
            'DERIVED\nLanded costs, optimizer recommendations, optimized spend, potential savings, savings percentages, '
            'lane/carrier summaries, monthly trends and rate mix.'
        )
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
