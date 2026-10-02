import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
from app.models.analytics import ChatRequest
from app.services.provenance import load_provenance

BACKEND = Path(__file__).resolve().parents[1]
QUESTIONS = [
    'Where did this savings number come from?',
    'How is potential saving calculated?',
    'What data is public and what is synthetic?',
    'What is the source of the fuel data?',
    'Where did the 3 freighters number come from?',
    'Where did the 55+ airline partners number come from?',
    'Are these actual Teleport shipment records?',
    'Is KUL-DEL a real Teleport route?',
    'Which assumptions are synthetic?',
    'Show the sources used for this dashboard.',
    'How is optimized cost calculated?',
    'How was this demo dataset generated?',
]


def test_sources_and_manifest(analytics):
    p = load_provenance()
    registry = p['source_registry']
    assert len(registry) == 6
    for source in registry:
        assert source['publisher'] and source['url'].startswith('https://')
        assert source['source_type'] in ['OFFICIAL_TELEPORT', 'OFFICIAL_INDUSTRY', 'OPEN_DATA']
        assert source['retrieved_at'] and source['facts_used']
        assert (BACKEND / 'data/sources' / source['snapshot']).exists()
    manifest = p['demo_manifest']
    assert manifest['random_seed'] == 20261002
    assert manifest['shipment_count'] == len(analytics.df) == 2000
    assert manifest['candidate_option_count'] == len(analytics.loader.options)
    assert manifest['summary'] == {k: analytics.get_overall_summary()[k] for k in manifest['summary']}
    assert 5 <= manifest['summary']['saving_percent'] <= 10
    owned = {c for c in analytics.loader.options.carrier if c.startswith('Own Freighter')}
    assert owned == {f'Own Freighter {i}' for i in range(1,4)}
    assert all(manifest['carriers'][c]['fleet_type'] == 'A321F' for c in owned)
    assert manifest['carriers']['Emirates SkyCargo']['classification'] == 'SYNTHETIC_DEMO_CARRIER'
    assert analytics.get_shipment_analysis('TP-88213')


def test_field_and_route_provenance():
    p = load_provenance(); fields = p['field_provenance']
    for name in ['weight_kg', 'actual_carrier', 'capacity_available_kg', 'sla_feasible', 'base_cost']:
        assert fields[name]['classification'].startswith('SYNTHETIC')
    for name in ['potential_saving', 'actual_paid', 'optimized_cost', 'fuel_surcharge']:
        assert fields[name]['classification'].startswith('DERIVED')
        assert fields[name]['formula']
    ids = {s['source_id'] for s in p['source_registry']}
    for lane, value in p['lane_provenance'].items():
        assert set(value['source_ids']) <= ids
        if value['classification'] == 'PUBLICLY_DOCUMENTED_ROUTE':
            assert value['source_ids'] == ['teleport_routes_2022']
            assert lane.startswith('KUL-')
    assert p['lane_provenance']['KUL-DEL']['classification'] == 'SYNTHETIC_DEMO_LANE'
    assert 'not claimed' in p['lane_provenance']['KUL-DEL']['note']


def test_generation_reproducible(tmp_path):
    runs = [tmp_path / 'one', tmp_path / 'two']
    for folder in runs:
        subprocess.run([sys.executable, str(BACKEND / 'scripts/generate_demo.py'), '--output-dir', str(folder), '--generated-at', '2026-10-02T00:00:00Z'], check=True, capture_output=True)
    for name in ['shipments.csv', 'carrier_options.csv', 'fuel_index.csv', 'provenance/demo_manifest.json', 'provenance/cost_inputs.csv']:
        assert (runs[0] / name).read_bytes() == (runs[1] / name).read_bytes()
        if name.endswith('.csv'):
            assert (runs[0] / name).read_bytes() == (BACKEND / 'data' / name).read_bytes()


def test_fuel_formula(analytics):
    fuel = analytics.loader.fuel.set_index('date').fuel_index
    for _, shipment in analytics.loader.shipments.iloc[:50].iterrows():
        lane_factor = 1.18 if shipment.destination in ['DEL', 'BOM', 'MAA', 'BLR'] else 1.35 if shipment.destination in ['SYD','ICN','HND'] else 1
        assert shipment.actual_fuel_surcharge == round(shipment.weight_kg * max(fuel.loc[shipment.shipment_date] - 90, 0) * .006 * lane_factor, 2)
        assert shipment.actual_paid == round(shipment.actual_base_cost + shipment.actual_fuel_surcharge + shipment.actual_other_cost, 2)
    assert analytics.loader.fuel.fuel_index.mean() == pytest.approx(152, abs=5)
    assert analytics.loader.fuel.fuel_index.nunique() <= 26


@pytest.mark.parametrize('question', QUESTIONS)
def test_provenance_questions(ai, monkeypatch, question):
    def fail(*args): raise AssertionError('Provenance must never reach the LLM')
    monkeypatch.setattr(ai.provider, 'parse', fail)
    r = ai.chat(ChatRequest(message=question, context={'last_lane':'KUL-BOM'}))
    assert r.intent == 'DATA_PROVENANCE' and r.provider == 'deterministic'
    assert r.context == {'last_lane':'KUL-BOM'}
    assert 'synthetic' in r.answer.lower()
    assert 'actual teleport shipment history' not in r.answer.lower().replace('not actual teleport shipment history', '')
    assert r.metrics['provenance'] == load_provenance()


def test_provenance_endpoints(client):
    assert client.get('/api/dashboard/provenance').json() == load_provenance()
    cells = client.get('/api/dashboard/lane-heatmap').json()
    assert all(row['provenance']['classification'] == 'SYNTHETIC_DEMO_LANE' for row in cells if row['lane'] == 'KUL-DEL')


def test_refresh_failure_preserves_snapshots(tmp_path, monkeypatch):
    import shutil
    spec = importlib.util.spec_from_file_location('refresh', BACKEND / 'scripts/refresh_public_sources.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    data = tmp_path / 'data'; shutil.copytree(BACKEND / 'data/sources', data / 'sources'); shutil.copytree(BACKEND / 'data/provenance', data / 'provenance')
    monkeypatch.setattr(module, 'DATA', data)
    before = {p.relative_to(data): p.read_bytes() for p in data.rglob('*') if p.is_file()}
    def offline(*args, **kwargs): raise OSError('offline')
    monkeypatch.setattr(module, 'urlopen', offline)
    assert module.refresh(fetch=True) == 6
    assert before == {p.relative_to(data): p.read_bytes() for p in data.rglob('*') if p.is_file()}
    assert module.refresh() == 0


def test_required_twenty_question_journey(ai):
    questions = [
        'How much could we have saved?', 'Give me a monthly summary.',
        'Which lane has the highest savings opportunity?', 'Why?', 'Show me those shipments.',
        'Compare KUL-BOM and KUL-DEL.', 'Which has the higher savings percentage?',
        'Compare MASkargo and Emirates on KUL-BOM.', 'Compare spot vs contract.',
        'What rate mix would the engine recommend?', 'Show top 10 shipments with highest missed savings.',
        'Show shipments where saving exceeds $500.', 'Show June shipments above $300 saving.',
        'Analyze shipment TP-88213.', 'What was the cheapest option for TP-88213?',
        'Why was this carrier recommended?', 'Which carriers have the biggest savings opportunities?',
        'How much did we spend with Emirates?', 'Show performance for MASkargo.', 'What are the key findings?',
    ]
    context = {}
    for question in questions:
        response = ai.chat(ChatRequest(message=question, context=context))
        assert response.confidence == 'high', (question, response.answer)
        assert response.intent != 'DATA_PROVENANCE'
        assert response.metrics or response.table
        context = response.context


def test_exact_option_cost_receipts(client, analytics):
    from app.services.provenance import cost_inputs_by_shipment
    receipts = {row["option_id"]: row for rows in cost_inputs_by_shipment().values() for row in rows}
    assert len(receipts) == len(analytics.loader.options)
    for _, option in analytics.loader.options.iterrows():
        r = receipts[option.option_id]
        assert option.fuel_surcharge == round(r["weight_kg"] * max(r["weekly_fuel_index"] - r["benchmark_usd_per_barrel"], 0) * r["synthetic_fuel_coefficient"] * r["synthetic_lane_factor"] * r["synthetic_candidate_multiplier"], 2)
        assert option.base_cost == round(r["synthetic_market_base"] * r["synthetic_candidate_multiplier"], 2)
        assert option.other_cost == round(r["synthetic_market_other"] * r["synthetic_candidate_multiplier"], 2)
    detail = client.get('/api/shipments/TP-88213').json()
    assert detail['provenance']['cost_inputs']
    assert detail['provenance']['lane']['classification'] == 'PUBLICLY_DOCUMENTED_ROUTE'
