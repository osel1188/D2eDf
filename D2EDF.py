
import mne
import numpy as np
import pyedflib
import os
from pathlib import Path
import ddd
import re
from scipy.signal import decimate
import gc
import pickle
import tkinter as tk
from tkinter import ttk, filedialog




WD = filedialog.askopenfilename(title="select .d File", filetypes=[("D file", "*.d")])
print(f"Loading file :: ________  {WD}  _________")


h = ddd.getDRheader(WD)


pattern = r"""
        (?:[A-Z]+'?\d+)              # O1, O'1, B'12
        |(?:EKG\d+)                  # EKG1
        |(?:EOG\d+)                  # EOG1
        |(?:MS\d+)                   # MS1
        |(?:[A-Z]z)                  # Fz, Cz, Pz
        |(?:CAL|SDT|EVT)             # special tags
        |(?:e[A-Z]?\d+)              # eA12
        |(?:[A-Z][a-z]+'?[a-z]?(?:[A-Z](?![a-z]))?\d*)  # FIXED
    """
ch_names = re.findall(pattern, h['xheader']['channel_names'], re.VERBOSE)
print(f"File with channes:  {ch_names}")


save = input("Do you want to convert file to EDF? [y/n]: ")
if str(save) == "y":
    saveDir = filedialog.askdirectory(title="Select Save dir:")
    fs = h['sheader']['fsamp']
    lenOfFil = h['sheader']['nsamp']
    data = ddd.getDRdata(h, ch=list(range(1, h['sheader']['nchan'] + 1)),s1=0,s2=lenOfFil)

    # Create a simple Raw object
    dec = input("Do you want to decimate data? [y/n]: ")
    # Downsample factor (e.g., 10 → from 1000 Hz to 100 Hz)
    if str(dec) == "y":
        factor = 10

        # Downsample each channel
        data_ds = decimate(data, factor, axis=1, ftype='fir')
        sfreq = fs/factor
    else:
        data_ds = data
        sfreq = fs



    if data.shape[0] != len(ch_names):
        missing = data.shape[0] - len(ch_names)
        
        raise ValueError("Channel extraction FAILS")

            
    info = mne.create_info(ch_names=ch_names, sfreq=sfreq, ch_types='eeg')
    #raw = mne.io.RawArray(data[1::3], info)
    raw = mne.io.RawArray(data_ds, info)   # --   HERE you have to use [1::2] bcs you want to pick filtered one - There are saved also raw and filtered data -- You take just every second signal  

    data = raw.get_data()  # shape: (n_channels, n_times)
    clean_data = data.copy()

    # Parameters
    threshold_factor = 7  # You can adjust this
    method = 'std'  # 'std' or 'mad'

    # Detect and remove outliers per channel
    for ch in range(clean_data.shape[0]):
        signal = clean_data[ch]
        
        if method == 'std':
            mean = np.mean(signal)
            std = np.std(signal)
            threshold = threshold_factor * std
        elif method == 'mad':
            median = np.median(signal)
            mad = np.median(np.abs(signal - median))
            threshold = threshold_factor * mad / 0.6745  # robust estimate of std
        else:
            raise ValueError("Unknown method")

        # Find outliers
        if method == 'std':
            outliers = np.abs(signal - mean) > threshold
        else:
            outliers = np.abs(signal - median) > threshold

        # Replace outliers with NaNs
        clean_data[ch, outliers] = np.nan

    # Optionally interpolate over NaNs (here with linear interpolation)
    for ch in range(clean_data.shape[0]):
        sig = clean_data[ch]
        nans = np.isnan(sig)
        if np.any(nans):
            clean_data[ch, nans] = np.interp(np.flatnonzero(nans),
                                            np.flatnonzero(~nans),
                                            sig[~nans])

    # Set cleaned data back
    raw._data = clean_data
    # Downsample to 2000 Hz
    #raw.resample(2000)

    # Analyze data
    play = raw._data
    print(type(play))
    print(play.shape)
    max_values = play.max(axis=1)
    min_values = play.min(axis=1)
    mean_values = play.mean(axis=1)
    std_values = play.std(axis=1)
    lenght_d = play.shape[1]
    print(lenght_d)
    sec = lenght_d/sfreq
    min = sec/60

    min = np.floor(min)

    # Print summary of each channel
    for i, ch_name in enumerate(raw.ch_names):
        print(f"Channel {ch_name}:")
        print(f"  Max: {max_values[i]:.2f}")
        print(f"  Min: {min_values[i]:.2f}")
        print(f"  Mean: {mean_values[i]:.2f}")
        print(f"  Std: {std_values[i]:.2f}")

    # Find the time of max and min values
    sfreq = raw.info['sfreq']
    times = np.arange(play.shape[1]) / sfreq
    max_times = times[np.argmax(play, axis=1)]
    min_times = times[np.argmin(play, axis=1)]

    # Print times of extrema
    for i, ch_name in enumerate(raw.ch_names):
        print(f"Channel {ch_name}:")
        print(f"  Max at {max_times[i]:.2f} s")
        print(f"  Min at {min_times[i]:.2f} s")

    # Scale data if necessary (e.g., from volts to microvolts)
    #scaling_factor = 1e3
    #scaled_data = play / scaling_factor

    # Save to EDF using pyedflib

    filename = os.path.basename(WD)


    name = filename[:-2]
    
    
    edf_file = Path(Path(saveDir)/name)
    edf_file = str(edf_file)
    print(edf_file)
    n_channels = play.shape[0]
    signal_headers = []

    # Create signal headers for each channel
    for ch_name in raw.info['ch_names']:
        
        signal_headers.append({
            'label': ch_name,
            'dimension': 'uV',
            'sample_frequency': sfreq,
            'physical_min': np.min(play),
            'physical_max': np.max(play),
            'digital_min': -32768,
            'digital_max': 32767,
            'transducer': '',
            'prefilter': ''
        })



    # for seky in range(0,int(np.floor(sec/duration_of_Edf-1))):
    #     print(play[:,int(seky*sfreq*duration_of_Edf):int((seky*sfreq*duration_of_Edf)+(1*sfreq*duration_of_Edf))].shape)
        

    # Write the EDF file
    with pyedflib.EdfWriter(edf_file+"W_2500sf.edf", n_channels, file_type=pyedflib.FILETYPE_EDFPLUS) as edf:
        edf.setSignalHeaders(signal_headers)
        edf.writeSamples(play)
        edf.close()

    print(f"CREATED::::\033[95m{edf_file}\033[0m####################")
    gc.collect()