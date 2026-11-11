import hashlib,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def evidence():return json.loads((ROOT/'reports/characterization.json').read_text())

def test_unmodified_pdk_models():
    p=json.loads((ROOT/'models/provenance.json').read_text())
    for name,digest in p['files_sha256'].items():assert hashlib.sha256((ROOT/'models'/name).read_bytes()).hexdigest()==digest

def test_pvt_matrix_complete():
    rows=evidence()['pvt_conditions'];assert len(rows)==45
    assert len({(r['corner'],r['vdd_v'],r['temp_c']) for r in rows})==45
    assert all(4<r['boost_at_nyquist_db']<6 for r in rows)

def test_dc_to_peak_gain_relation():
    n=evidence()['nominal'];assert n['peak_gain_db']>n['nyquist_gain_db']>n['dc_gain_db']
    assert 5e8<n['peak_frequency_hz']<2e9

def test_degenerating_resistance_tradeoff():
    rows=[r for r in evidence()['tuning_sweep'] if r['cs_f']==.4e-12];rows.sort(key=lambda r:r['rs_ohm'])
    assert len(rows)==5
    assert all(a['dc_gain_db']>b['dc_gain_db'] for a,b in zip(rows,rows[1:]))

def test_stable_fit_and_link_eye():
    r=evidence()['linearized_link'];assert r['fit_max_relative_complex_error_10khz_to_4ghz']<.01
    assert all(p>0 for p in r['fit_poles_hz'])
    assert r['after']['vertical_opening_v']>r['before']['vertical_opening_v']>0
    assert r['before']['evaluated_bits']==r['after']['evaluated_bits']==6080

def test_no_noise_or_jitter_claim_in_link():
    assert 'no random jitter or noise' in evidence()['linearized_link']['model']
    assert evidence()['linearized_link']['dc_gain_normalized']

def test_noise_and_power_are_finite_positive():
    j=evidence();assert 0<j['nominal']['power_w']<.002
    assert 0<j['noise']['input_noise_rms_v']<.01

def test_report_matches_current_circuit():
    assert evidence()['circuit_sha256']==hashlib.sha256((ROOT/'circuits/ctle.spice').read_bytes()).hexdigest()
