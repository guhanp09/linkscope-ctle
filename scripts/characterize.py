#!/usr/bin/env python3
"""Transistor AC/noise characterization and linearized NRZ channel experiments."""
from __future__ import annotations
import hashlib,itertools,json,subprocess
from pathlib import Path
import numpy as np
from scipy.signal import lfilter, cont2discrete, tf2sos, sosfilt
from scipy.optimize import least_squares
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build';REPORTS=ROOT/'reports'

def simulate(name,rs=750,cs=.4e-12,corner='tt',vdd=1.8,temp=27,mode='ac'):
    out=BUILD/name;out.mkdir(parents=True,exist_ok=True)
    analysis=f'ac dec 80 10k 100G\nlet hre=real(v(outp,outn))\nlet him=imag(v(outp,outn))\nwrdata {out}/ac.dat hre him'
    if mode=='noise':analysis=f'noise v(outp,outn) VDIFF dec 60 100k 10G\nsetplot noise1\nwrdata {out}/noise.dat inoise_spectrum onoise_spectrum'
    deck=f'''CTLE characterization {name}
.option scale=1e-6
.temp {temp}
.include "{ROOT}/models/{corner}.spice"
.include "{ROOT}/circuits/ctle.spice"
VDD vdd 0 {vdd}
VDIFF diff 0 dc 0 ac 1
EINP inp 0 value={{1.2+v(diff)/2}}
EINN inn 0 value={{1.2-v(diff)/2}}
Xeq inp inn outp outn vdd 0 ctle rs={rs} cs={cs}
.control
set noaskquit
set wr_singlescale
set wr_vecnames
op
let supply=-i(vdd)
wrdata {out}/op.dat v(outp) v(outn) v(xeq.tail) supply
{analysis}
quit
.endc
.end
'''
    p=out/'test.cir';p.write_text(deck)
    r=subprocess.run(['ngspice','-b',str(p)],cwd=ROOT,capture_output=True,text=True,timeout=30);(out/'ngspice.log').write_text(r.stdout+r.stderr)
    if r.returncode or 'Error' in r.stderr:raise RuntimeError(name+' '+r.stderr[-1000:])
    op=np.loadtxt(out/'op.dat',skiprows=1,ndmin=2)[0]
    result={'name':name,'rs_ohm':rs,'cs_f':cs,'corner':corner,'vdd_v':vdd,'temp_c':temp,'power_w':float(op[4]*vdd),'output_common_mode_v':float((op[1]+op[2])/2)}
    if mode=='ac':
        a=np.loadtxt(out/'ac.dat',skiprows=1);h=a[:,1]+1j*a[:,2];gain=20*np.log10(abs(h));i=int(np.argmax(gain))
        result.update(dc_gain_db=float(gain[0]),peak_gain_db=float(gain[i]),peak_frequency_hz=float(a[i,0]),nyquist_gain_db=float(np.interp(np.log10(5e8),np.log10(a[:,0]),gain)),boost_at_nyquist_db=float(np.interp(np.log10(5e8),np.log10(a[:,0]),gain)-gain[0]))
    else:
        a=np.loadtxt(out/'noise.dat',skiprows=1);result['input_noise_rms_v']=float(np.sqrt(np.trapezoid(a[:,1]**2,a[:,0])));result['noise_band_hz']=[1e5,1e10]
    return result

def channel_experiment(ac_file,name):
    # This is a small-signal link calculation using a SPICE-derived CTLE, not
    # transistor transient simulation or BER characterization.
    rng=np.random.default_rng(41);bits=rng.integers(0,2,8192);sps=32;rate=1e9;fs=sps*rate
    symbols=2*bits-1;tx=np.repeat(symbols,sps).astype(float)*.01
    # Stable first-order lowpass channel; discrete pole chosen by exact decay.
    fc=1.8e8;pole=np.exp(-2*np.pi*fc/fs);rx=lfilter([1-pole],[1,-pole],tx)
    a=np.loadtxt(ac_file,skiprows=1);measured=a[:,1]+1j*a[:,2]
    mask=a[:,0]<4e9;freq=a[mask,0];target=measured[mask];scaled_s=1j*freq/1e9
    def fitted(x):
        g,z,p1,p2,p3=np.exp(x)
        return g*(1+scaled_s/z)/((1+scaled_s/p1)*(1+scaled_s/p2)*(1+scaled_s/p3))
    def residual(x):
        delta=(fitted(x)-target)/np.maximum(abs(target),.1)
        return np.r_[delta.real,delta.imag]
    fit=least_squares(residual,np.log([.83,.26,.9,2,15]),max_nfev=5000)
    g,z,p1,p2,p3=np.exp(fit.x)
    max_relative_error=float(np.max(abs(fitted(fit.x)-target)/abs(target)))
    assert max_relative_error<.01,'CTLE rational fit exceeds 1% complex error'
    # Stable real-pole fit avoids the noncausal pre-response produced by direct
    # finite-band FFT interpolation. Scale continuous time by 2*pi*1GHz.
    denominator=np.polymul(np.polymul([1/p1,1],[1/p2,1]),[1/p3,1])
    numerator=[g/z,g]
    bd,ad,_=cont2discrete((numerator,denominator),2*np.pi*1e9/fs,method='bilinear')
    eq=sosfilt(tf2sos(bd[0],ad),rx)/g
    def eye(y):
        metrics=[]
        # Search receiver sampling phase using the same deterministic training
        # subset for each path. Evaluate on the disjoint remaining symbols.
        for phase in range(sps):
            samples=y[np.arange(256,2048)*sps+phase];b=bits[256:2048]
            opening=np.percentile(samples[b==1],1)-np.percentile(samples[b==0],99);metrics.append(opening)
        phase=int(np.argmax(metrics));samples=y[np.arange(2048,len(bits)-64)*sps+phase];b=bits[2048:len(bits)-64]
        return {'phase_samples':phase,'vertical_opening_v':float(np.percentile(samples[b==1],1)-np.percentile(samples[b==0],99)),
                'midrail_errors':int(np.sum((samples>0)!=b)),'evaluated_bits':len(samples)}
    result={'model':'1 Gbit/s NRZ; 180 MHz one-pole channel; 10 mV symbols; no random jitter or noise',
            'before':eye(rx),'after':eye(eq),'dc_gain_normalized':True,'fit_max_relative_complex_error_10khz_to_4ghz':max_relative_error,'fit_poles_hz':[float(p1*1e9),float(p2*1e9),float(p3*1e9)],'fit_zero_hz':float(z*1e9)}
    fig,axes=plt.subplots(1,2,figsize=(10,3.7),sharey=True)
    for ax,y,label in zip(axes,[rx,eq],['Channel output','With SPICE-derived CTLE']):
        for k in range(2048,2248):ax.plot(np.arange(2*sps)/sps,y[k*sps:(k+2)*sps]*1e3,color='#245b9a',alpha=.13,lw=.65)
        ax.set(title=label,xlabel='Time (UI)');ax.grid(alpha=.2)
    axes[0].set_ylabel('Voltage (mV), equal DC gain');fig.tight_layout();fig.savefig(REPORTS/(name+'-eye.png'),dpi=170);plt.close(fig)
    return result

def main():
    REPORTS.mkdir(exist_ok=True);nominal=simulate('nominal');print(nominal,flush=True)
    sweep=[]
    for i,(r,c) in enumerate(itertools.product([250,500,750,1000,1500],[.1e-12,.2e-12,.4e-12,.8e-12])):
        sweep.append(simulate(f'tune-{i}',r,c))
    corners=[]
    for i,(c,v,t) in enumerate(itertools.product(['tt','ss','ff','sf','fs'],[1.71,1.8,1.89],[-40,27,85])):
        corners.append(simulate(f'pvt-{i}',corner=c,vdd=v,temp=t))
    noise=simulate('noise',mode='noise')
    link=channel_experiment(BUILD/'nominal/ac.dat','nominal')
    a=np.loadtxt(BUILD/'nominal/ac.dat',skiprows=1);h=a[:,1]+1j*a[:,2]
    fig,ax=plt.subplots(figsize=(8,4));ax.semilogx(a[:,0],20*np.log10(abs(h)));ax.axvline(5e8,color='gray',ls='--',label='1 Gbit/s Nyquist');ax.set(xlabel='Frequency (Hz)',ylabel='Differential gain (dB)',title='SKY130 source-degenerated CTLE');ax.legend();ax.grid(alpha=.2);fig.tight_layout();fig.savefig(REPORTS/'frequency-response.png',dpi=160);plt.close(fig)
    summary={'nominal':nominal,'tuning_sweep':sweep,'pvt_conditions':corners,'noise':noise,'linearized_link':link,
             'circuit_sha256':hashlib.sha256((ROOT/'circuits/ctle.spice').read_bytes()).hexdigest(),
             'pvt_summary':{'conditions':len(corners),'nyquist_boost_min_db':min(x['boost_at_nyquist_db'] for x in corners),'nyquist_boost_max_db':max(x['boost_at_nyquist_db'] for x in corners)}}
    (REPORTS/'characterization.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n');print(summary['pvt_summary'],link,flush=True)
if __name__=='__main__': main()
