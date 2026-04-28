# D2eDf
Converter from M&amp;I D-file structure to EDF
# 🧠 D2EDF – Convert `.d` Files to EDF

This script converts proprietary `.d` files (BrainScope / D-file format) into standard **EDF (European Data Format)** using Python. It also includes optional **downsampling**, **artifact removal**, and **basic signal statistics**.

---

## 🚀 Features

- Load `.d` files via GUI dialog
- Extract channel names using regex parsing
- Convert to **EDF+ format**
- Optional **decimation (downsampling)**
- Automatic **outlier detection & interpolation**
- Per-channel statistics:
  - Min / Max
  - Mean / STD
  - Time of extrema
- Simple GUI prompts (Tkinter)

---

## 📦 Requirements

Install required Python packages:

```bash
pip install mne numpy pyedflib scipy
```

Also requires:
- Custom module: `ddd` (used for reading `.d` files)

---

## 📂 Usage

Run the script:

```bash
python D2EDF.py
```

### Workflow:

1. Select a `.d` file  
2. Script reads header and extracts channels  
3. Choose:  
   - Convert to EDF? (`y/n`)  
   - Apply decimation? (`y/n`)  
4. Select output directory  
5. Script processes data and saves `.edf` file  

---

## ⚙️ Processing Steps

### 1. Data Loading
- Uses:
  - `ddd.getDRheader()`
  - `ddd.getDRdata()`

### 2. Channel Extraction
- Regex-based parsing of channel names (EEG, EKG, EOG, etc.)

### 3. Optional Downsampling
- FIR decimation via:
  - `scipy.signal.decimate`

### 4. Artifact Removal
- Outliers detected using:
  - Standard deviation (`std`) or
  - Median absolute deviation (`mad`)
- Outliers are replaced with NaN and interpolated linearly

### 5. Statistics
- Computes per-channel:
  - Min / Max / Mean / STD
  - Time of extrema

### 6. EDF Export
- Uses `pyedflib`
- Saves as EDF+ with:
  - Channel labels
  - Sampling frequency
  - Physical/digital ranges

---

## 📁 Output

Output file format:

```
<filename>W_2500sf.edf
```

---

## ⚠️ Notes

- All channels are currently treated as EEG (`ch_types='eeg'`)
- If your `.d` file contains both raw and filtered signals, you may need to select a subset manually:
  ```python
  raw = mne.io.RawArray(data_ds, info)
  # Example alternative:
  # raw = mne.io.RawArray(data_ds[1::2], info)
  ```
- Physical min/max values are currently set globally, not per channel

---

## 🛠️ Possible Improvements

- Add CLI arguments (argparse) instead of GUI prompts  
- Separate channel types (EEG, EOG, ECG, etc.)  
- Add annotations and metadata support  
- Improve channel selection logic  
- Add logging and error handling  
- Speed up processing for large datasets  

---

## 👤 Author

- AI for readme - but human being checked the code. 
