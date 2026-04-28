

def getPrec(h):
    ftype = h['sheader']['ftype']
    d_val = h['sheader']['d_val']

    if ftype == 'D':
        cell_size = d_val['data_cell_size']
        if cell_size == 2:
            return 'int16', 2
        elif cell_size == 3:
            return 'int32', 4
        else:
            return 'uint8', 1
    elif ftype == 'R':
        return 'float32', 4
    else:
        return 'uint8', 1



# Header parsing is long and requires a separate step. Let me know if you'd like the `get_DRheader` part converted next.

# Example structure of a simplified D-file header parser for demonstration purposes.
# This does not cover all edge cases and assumes a specific header format.
import struct
import numpy as np
from datetime import datetime, timedelta

def getDRheader(filename):
    h = {'filename': filename}
    try:
        with open(filename, 'rb') as f:
            # --- STANDARD HEADER ---
            h['sheader'] = {}
            h['sheader']['sign'] = f.read(15).decode('ascii')
            h['sheader']['ftype'] = f.read(1).decode('ascii')
            if h['sheader']['ftype'] not in ['D', 'R', '\x00']:
                print(f"unknown file type {h['sheader']['ftype']}")
                return None

            h['sheader']['nchan'] = struct.unpack('B', f.read(1))[0]
            h['sheader']['naux'] = struct.unpack('B', f.read(1))[0]
            h['sheader']['fsamp'] = struct.unpack('<H', f.read(2))[0]
            h['sheader']['nsamp'] = struct.unpack('<I', f.read(4))[0]
            d_val = struct.unpack('B', f.read(1))[0]
            h['sheader']['d_val'] = {
                'value': d_val,
                'data_invalid': (d_val >> 7) & 1,
                'data_packed': (d_val >> 6) & 1,
                'block_structure': (d_val >> 5) & 1,
                'polarity': (d_val >> 4) & 1,
                'data_calib': (d_val >> 3) & 1,
                'data_modified': (d_val >> 2) & 1,
                'data_cell_size': d_val & 0x3
            }
            h['sheader']['unit'] = struct.unpack('B', f.read(1))[0]
            h['sheader']['zero'] = struct.unpack('<H', f.read(2))[0]
            h['sheader']['data_org'] = 16 * struct.unpack('<H', f.read(2))[0]
            h['sheader']['data_xhdr_org'] = 16 * struct.unpack('<h', f.read(2))[0]

            # --- EXTENDED HEADER ---
            if h['sheader']['data_xhdr_org']:
                f.seek(h['sheader']['data_xhdr_org'], 0)
                h['xheader'] = {}
                while True:
                    try:
                        mnemo = struct.unpack('<H', f.read(2))[0]
                        if mnemo == 0:
                            h['datapos'] = f.tell()
                            break
                        length = struct.unpack('<H', f.read(2))[0]
                        data = f.read(length)
                        if mnemo == 20035:  # CN - channel names
                            h['xheader']['channel_names'] = data.decode('ascii').strip().replace('\x00', '')
                        elif mnemo == 21318:  # FS - frequency of sampling
                            vals = struct.unpack('<2h', data)
                            h['xheader']['freq'] = {
                                'val': vals,
                                'Fsamp': vals[0] / vals[1] if vals[1] != 0 else 0
                            }
                        elif mnemo == 17481:  # ID - patient ID
                            pid = struct.unpack('<I', data[:4])[0]
                            bval = f"{pid:032b}"
                            psn = int(bval[18:], 2)
                            day = int(bval[11:16], 2)
                            mon = int(bval[7:11], 2)
                            year = int(bval[:7], 2)
                            h['xheader']['patient_id'] = {
                                'ismale': bval[16] == '0',
                                'bday': day,
                                'bmonth': mon % 50,
                                'byear': year + 1900 + (2000 if bval[17] == '1' else 0),
                                'id': f"{year:02}{mon:02}{day:02}/{psn:04}"
                            }
                        elif mnemo == 18772:  # TI - time info
                            timestamp = struct.unpack('<I', data[:4])[0]
                            epoch = datetime(1970, 1, 1)
                            dt = epoch + timedelta(seconds=timestamp)
                            h['xheader']['date'] = {
                                'val': timestamp,
                                'yy': dt.year,
                                'mon': dt.month,
                                'dd': dt.day,
                                'hh': dt.hour,
                                'min': dt.minute,
                                'ss': dt.second
                            }
                        else:
                            # store raw for now
                            h['xheader'][f'unknown_{mnemo}'] = data
                    except struct.error:
                        break
            else:
                h['xheader'] = {}
                h['datapos'] = f.tell()

            # Optional: add tag table parsing here if needed

    except IOError:
        print(f"Can't open {filename}")
        return None

    return h

import numpy as np


def getDRdata(h, ch, s1, s2):
    """
    Reads data from BrainScope D-file.

    Parameters:
        h (dict): Header dictionary returned by getDRheader
        ch (list of int): Channel indices (1-based)
        s1 (int): Start sample index (1-based)
        s2 (int): End sample index (inclusive, 1-based)

    Returns:
        np.ndarray: data of shape (len(ch), s2 - s1 + 1)
    """
    filename = h['filename']
    prec, nb = getPrec(h)

    # Calculate file position
    data_org = h['sheader']['data_org']
    nchan = h['sheader']['nchan']
    start_byte = data_org + (s1 - 1) * nb * nchan
    nsamples = s2 - s1 + 1

    try:
        with open(filename, 'rb') as f:
            f.seek(start_byte)
            dd = np.fromfile(f, dtype=prec, count=nsamples * nchan)
    except Exception as e:
        print(f"Error when reading data: {e}")
        return None

    if dd.size != nsamples * nchan:
        print("Unexpected EOF or incomplete data.")
        return None

    dd = dd.reshape((nchan, nsamples), order='F')  # MATLAB uses column-major order

    if not ch:
        return dd
    else:
        ch = [c - 1 for c in ch]  # Convert 1-based MATLAB indices to 0-based Python
        return dd[ch, :]



def readDR(fns=None):
    """
    Reads BrainScope .d file(s) and returns header and ExG data.
    Usage:
        h, exg = readDR('path/to/file.d')
    """

    if fns is None:
        raise ValueError("No file specified. GUI file picker not implemented in this version.")

    if isinstance(fns, str):
        fns = [fns]

    results = []

    for fn in fns:
        exg = []

        # Read header
        h = getDRheader(fn)

        # Read in 80MB chunks
        nB = 8 * 2**20 // 2  # 80 MB / 2 (int16 bytes) = 4194304
        nDataPoints = nB // h['sheader']['nchan']
        total_samples = h['sheader']['nsamp']
        chunks = [nDataPoints] * (total_samples // nDataPoints)
        if total_samples % nDataPoints > 0:
            chunks.append(total_samples % nDataPoints)

        # Read data chunk by chunk
        start = 1
        for i, blk in enumerate(chunks):
            stop = start + blk - 1
            data = getDRdata(h, list(range(1, h['sheader']['nchan'] + 1)), start, stop)
            if h['sheader']['d_val']['data_calib']:
                data += h['sheader']['zero']
            exg.append(data)
            start = stop + 1
            pct = 100 * (i + 1) / len(chunks)
            print(f"\r{pct:4.1f}% done", end='')

        print("\nDONE\n")
        results.append((h, np.hstack(exg)))

    if len(results) == 1:
        return results[0]
    else:
        return results  # List of (header, exg) tuples




# Re-test full integration now that get_DRheader is implemented

# první možnost 111
#h_test, data_test = readDR("C:\\Users\\Sindel\\Documents\\epiweek\\d.file\\Easrec-service25_250519-1152.d")
#data_test.shape if data_test is not None else "Failed to load data"


### Druhá možnost 
# h = getDRheader("C:\\Users\\Sindel\\Documents\\epiweek\\d.file\\Easrec-service25_250519-1152.d")
# print(h['sheader'])
# print(h['xheader']['channel_names'])
#s1 od 
#s2 do
# data = getDRdata(h, ch=list(range(1, h['sheader']['nchan'] + 1)), s1=1, s2=50000)
# print(data.shape)
# ###


# import matplotlib.pyplot as plt

# plt.figure()
# plt.plot(data[0])
# plt.show()

