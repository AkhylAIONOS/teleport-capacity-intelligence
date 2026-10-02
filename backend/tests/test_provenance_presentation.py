"""Presentation-only regression coverage; no generator invocation."""
import re

import pytest
from app.models.analytics import ChatRequest, Filters
from app.services.provenance import load_provenance


@pytest.mark.parametrize('question', [
    'Where did this savings number come from?',
    'Where did these savings come from?',
    'Explain this savings number.',
    'How is potential saving calculated?',
])
def test_savings_explanation_precedes_ranking(ai, monkeypatch, question):
    def forbidden(*args, **kwargs):
        raise AssertionError('Savings provenance must not rank lanes or call a provider')
    monkeypatch.setattr(ai.provider, 'parse', forbidden)
    monkeypatch.setattr(ai.analytics, 'get_top_lanes', forbidden)
    context = {'last_lane': 'KUL-DEL'}  # Stale conversation context is not a dashboard filter.
    response = ai.chat(ChatRequest(message=question, context=context))
    assert response.intent == 'DATA_PROVENANCE'
    assert response.provider == 'deterministic'
    assert 'Overall current dataset (no dashboard filters)' in response.answer
    assert '2,000 shipments' in response.answer
    assert '$936,109.97' in response.answer and '6.70%' in response.answer
    assert 'max(actual simulated cost - lowest feasible optimized cost, 0)' in response.answer
    assert 'sum of shipment potential savings in the active scope' in response.answer
    assert 'network, geography and fuel' in response.answer
    assert 'synthetic' in response.answer and 'not actual Teleport historical savings' in response.answer
    assert response.context == context and response.filters == {}


@pytest.mark.parametrize('values, labels', [
    ({'lane':'KUL-BOM'}, ['Lane: KUL-BOM']),
    ({'carrier':'MASkargo'}, ['Actual carrier: MASkargo']),
    ({'recommended_carrier':'MASkargo'}, ['Recommended carrier: MASkargo']),
    ({'origin':'KUL', 'destination':'DEL'}, ['Origin: KUL', 'Destination: DEL']),
    ({'start_date':'2026-06-01', 'end_date':'2026-06-30'}, ['From: Jun 1, 2026', 'Through: Jun 30, 2026']),
    ({'rate_type':'Spot', 'recommended_rate_type':'Contract'}, ['Actual rate type: Spot', 'Recommended rate type: Contract']),
    ({'min_saving':500}, ['Minimum saving: $500.00']),
    ({'search':'TP-88213'}, ['Search: TP-88213']),
    ({'shipment_ids':['TP-88213']}, ['Selected shipments: TP-88213']),
    ({'lane':'UNKNOWN-LANE'}, ['Lane: UNKNOWN-LANE']),
])
def test_savings_explains_exact_dashboard_scope(ai, analytics, values, labels):
    filters = Filters(**values)
    before = filters.model_dump()
    expected = analytics.get_overall_summary(filters)
    response = ai.chat(ChatRequest(message='Where did this savings number come from?', filters=filters))
    assert response.intent == 'DATA_PROVENANCE'
    assert response.answer.startswith('Active scope —')
    assert all(label in response.answer for label in labels)
    assert f'{expected["shipment_count"]:,} shipments' in response.answer
    assert f'${expected["potential_saving"]:,.2f}' in response.answer
    assert f'{expected["saving_percent"]:.2f}%' in response.answer
    assert response.data_scope['shipment_count'] == expected['shipment_count']
    assert filters.model_dump() == before and response.filters == {}


def test_three_short_public_synthetic_derived_sections(ai):
    answer = ai.chat(ChatRequest(message='What data is public and what is synthetic?')).answer
    assert [line for line in answer.splitlines() if line in ['PUBLIC','SYNTHETIC','DERIVED']] == ['PUBLIC','SYNTHETIC','DERIVED']
    assert len(answer.split()) < 110
    assert not answer.startswith('No')
    assert not re.search(r'\b\w+_\w+\b', answer)
    assert 'https://' not in answer


def test_real_records_answer_is_short_and_direct(ai):
    answer = ai.chat(ChatRequest(message='Are these actual Teleport shipment records?')).answer
    assert answer.startswith('No.')
    assert len(re.findall(r'[^.!?]+[.!?]', answer)) == 5
    assert len(answer.split()) < 75
    assert 'synthetic' in answer and 'not actual Teleport shipment history' in answer
    assert 'https://' not in answer and 'Sources:' not in answer


def test_sources_have_names_uses_and_registry_links(ai):
    answer = ai.chat(ChatRequest(message='Show the sources used for this dashboard.')).answer
    names = ['Teleport 1H 2026 Results', 'Teleport Network', 'Teleport historical cargo destinations', 'Teleport FSC mechanism', 'IATA 2026 Fuel Outlook', 'OurAirports']
    assert answer.startswith('Sources used for this dashboard:')
    assert not answer.startswith('No')
    lines = [line for line in answer.splitlines() if line.startswith('- ')]
    assert len(lines) == len(names) == 6
    for name, line, source in zip(names, lines, load_provenance()['source_registry']):
        assert line.startswith('- ' + name + ' — ')
        assert source['url'] in line
    assert 'company-level disclosures' in answer and 'fleet type' in answer
    assert 'historic destination geography' in answer and 'weekly, regional USD/kg' in answer
    assert 'synthetic fuel series' in answer and 'coordinates' in answer


@pytest.mark.parametrize('question', ['What is the source of the fuel data?', 'What is the exact source of the fuel data?', 'How is fuel surcharge calculated?', 'Show the fuel formula'])
def test_fuel_source_hides_internal_constants(ai, question):
    answer = ai.chat(ChatRequest(message=question)).answer
    assert 'USD 152/barrel' in answer and '31.4%' in answer
    assert 'not actual IATA daily observations' in answer
    assert 'no September rates are applied to Jan–Jun' in answer
    assert 'shipment weight × fuel-index adjustment × regional/lane calibration' in answer
    assert '0.006' not in answer and '1.18' not in answer
    assert 'fuel_surcharge' not in answer and 'candidate_multiplier' not in answer
    assert 'www.iata.org' in answer and 'help.teleport.it' in answer


@pytest.mark.parametrize('question', ['show the exact fuel formula', 'Explain the exact formula for fuel', 'Show the fuel generator coefficients', 'Show the precise fuel formula', 'Show the fuel formula in full'])
def test_exact_fuel_formula_requires_explicit_request(ai, question):
    answer = ai.chat(ChatRequest(message=question)).answer
    provenance = load_provenance()
    assert provenance['field_provenance']['fuel_surcharge']['formula'] in answer
    assert '0.006' in answer and '1.18' in answer
    assert 'synthetic calibration assumptions, not official Teleport rates' in answer


def test_generation_uses_human_dates_and_manifest_numbers(ai):
    answer = ai.chat(ChatRequest(message='How was this demo dataset generated?')).answer
    for text in ['Dataset 2.0', 'Generator 2.0', 'seed 20261002', 'Jan 1, 2026 – Jun 30, 2026', '2,000 synthetic shipments', '13,147 candidate options']:
        assert text in answer
    assert '{' not in answer and '}' not in answer and "'start'" not in answer


def test_preserved_fleet_and_lane_answers(ai):
    p = load_provenance()
    sources = {s['source_id']:s for s in p['source_registry']}
    fleet = ai.chat(ChatRequest(message='Where did the 3 freighters number come from?')).answer
    assert 'Teleport lists 3 owned freighters, type A321F.' in fleet
    assert sources['teleport_network_2026']['url'] in fleet
    lane = ai.chat(ChatRequest(message='Is KUL-DEL a real Teleport route?')).answer
    assert 'KUL-DEL: SYNTHETIC_DEMO_LANE' in lane
    assert p['lane_provenance']['KUL-DEL']['note'] in lane
    assert 'No confirmed direct historical Teleport route is asserted.' in lane


def test_chat_endpoint_savings_presentation(client):
    response = client.post('/api/ai/chat', json={'message':'Where did this savings number come from?', 'filters': {'lane':'KUL-DEL'}}).json()
    assert response['intent'] == 'DATA_PROVENANCE'
    assert 'Lane: KUL-DEL' in response['answer']
    summary = client.get('/api/dashboard/summary?lane=KUL-DEL').json()
    assert f'${summary["potential_saving"]:,.2f}' in response['answer']
