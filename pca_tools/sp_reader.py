import glob
import os
import struct
import numpy as np
import pandas as pd

def _block_info(data):
    if len(data) != 6:
        raise ValueError("'data' should be 6 bytes. Got {} instead.".format(len(data)))
    return struct.unpack('<Hi', data)

def _decode_5104(data):
    text = []
    start_byte = 0
    while start_byte + 2 < len(data):
        tag = data[start_byte:start_byte + 2]
        if tag == b'#u':
            start_byte += 2
            text_size = struct.unpack('<h', data[start_byte:start_byte + 2])[0]
            start_byte += 2
            text.append(data[start_byte:start_byte + text_size].decode('utf-8', errors='ignore'))
            start_byte += text_size
            start_byte += 6
        elif tag == b'$u':
            start_byte += 2
            text.append(struct.unpack('<h', data[start_byte:start_byte + 2])[0])
            start_byte += 2
            start_byte += 6
        elif tag == b',u':
            start_byte += 2
            text.append(struct.unpack('<h', data[start_byte:start_byte + 2])[0])
            start_byte += 2
        else:
            start_byte += 1

    meta = {}
    keys = [
        ('analyst', 0),
        ('date', 2),
        ('image_name', 4),
        ('instrument_model', 5),
        ('instrument_serial_number', 6),
        ('instrument_software_version', 7),
        ('accumulations', 9),
        ('detector', 11),
        ('source', 12),
        ('beam_splitter', 13),
        ('apodization', 15),
        ('spectrum_type', 16),
        ('beam_type', 17),
        ('phase_correction', 20),
        ('ir_accessory', 26),
        ('igram_type', 28),
        ('scan_direction', 29),
        ('background_scans', 32)
    ]
    for key, idx in keys:
        if idx < len(text):
            meta[key] = text[idx]
    return meta

def _decode_25739(data):
    start_byte = 0
    n_bytes = 2
    if len(data) < start_byte + n_bytes:
        return {}
    var_id = struct.unpack('<H', data[start_byte:start_byte + n_bytes])[0]
    if var_id == 29987:
        start_byte += n_bytes
        n_bytes = 2
        if len(data) < start_byte + n_bytes:
            return {}
        var_size = struct.unpack('<H', data[start_byte:start_byte + n_bytes])[0]
        start_byte += n_bytes
        n_bytes = var_size
        if len(data) < start_byte + n_bytes:
            return {}
        return {'file_path': data[start_byte:start_byte + n_bytes].decode('utf-8', errors='ignore')}
    return {}

def _decode_35698(data):
    start_byte = 0
    n_bytes = 2
    if len(data) < start_byte + n_bytes:
        return {}
    var_id = struct.unpack('<H', data[start_byte:start_byte + n_bytes])[0]
    if var_id == 29981:
        start_byte += n_bytes
        n_bytes = 16
        if len(data) < start_byte + n_bytes:
            return {}
        min_wavelength, max_wavelength = struct.unpack('<dd', data[start_byte:start_byte + n_bytes])
        return {'min_wavelength': min_wavelength, 'max_wavelength': max_wavelength}
    return {}

def _decode_35699(data):
    start_byte = 0
    n_bytes = 2
    if len(data) < start_byte + n_bytes:
        return {}
    var_id = struct.unpack('<H', data[start_byte:start_byte + n_bytes])[0]
    if var_id == 29981:
        start_byte += n_bytes
        n_bytes = 16
        if len(data) < start_byte + n_bytes:
            return {}
        min_absolute, max_absolute = struct.unpack('<dd', data[start_byte:start_byte + n_bytes])
        return {'min_absolute': min_absolute, 'max_absolute': max_absolute}
    return {}

def _decode_35700(data):
    start_byte = 0
    n_bytes = 2
    if len(data) < start_byte + n_bytes:
        return {}
    var_id = struct.unpack('<H', data[start_byte:start_byte + n_bytes])[0]
    if var_id == 29979:
        start_byte += n_bytes
        n_bytes = 8
        if len(data) < start_byte + n_bytes:
            return {}
        wavelength_step = struct.unpack('<d', data[start_byte:start_byte + n_bytes])[0]
        return {'wavelength_step': wavelength_step}
    return {}

def _decode_35701(data):
    start_byte = 0
    n_bytes = 2
    if len(data) < start_byte + n_bytes:
        return {}
    var_id = struct.unpack('<H', data[start_byte:start_byte + n_bytes])[0]
    if var_id == 29995:
        start_byte += n_bytes
        n_bytes = 4
        if len(data) < start_byte + n_bytes:
            return {}
        n_points = struct.unpack('<I', data[start_byte:start_byte + n_bytes])[0]
        return {'n_points': n_points}
    return {}

def _decode_35708(data):
    start_byte = 0
    n_bytes = 2
    if len(data) < start_byte + n_bytes:
        return None
    var_id = struct.unpack('<H', data[start_byte:start_byte + n_bytes])[0]
    if var_id == 29974:
        start_byte += n_bytes
        n_bytes = 4
        if len(data) < start_byte + n_bytes:
            return None
        var_size = struct.unpack('<I', data[start_byte:start_byte + n_bytes])[0]
        start_byte += n_bytes
        n_bytes = var_size
        if len(data) < start_byte + n_bytes:
            return None
        return np.frombuffer(data[start_byte:start_byte + n_bytes], dtype=np.float64)
    return None

FUNC_DECODE = {
    25739: _decode_25739,
    35698: _decode_35698,
    35699: _decode_35699,
    35700: _decode_35700,
    35701: _decode_35701,
    35708: _decode_35708
}

def read_sp(sp_file_path):
    """
    Read a PerkinElmer .sp binary file.
    """
    with open(sp_file_path, 'rb') as f:
        content = f.read()

    start_byte = 0
    n_bytes = 4
    signature = content[start_byte:start_byte + n_bytes]
    if signature != b'PEPE':
        raise ValueError("Invalid SP file signature")

    start_byte += n_bytes
    n_bytes = 40
    description = content[start_byte:start_byte + n_bytes].decode('utf-8', errors='ignore')

    meta = {'signature': signature, 'description': description}
    spectrum = []

    NBP = []
    start_byte += n_bytes
    n_bytes = 6
    if start_byte + n_bytes > len(content):
        raise ValueError("File is too short to read block info")
    block_id, block_size = _block_info(content[start_byte:start_byte + n_bytes])
    start_byte += n_bytes
    NBP.append(start_byte + block_size)
    while block_id != 122 and start_byte < len(content) - 2:
        next_block_id = content[start_byte:start_byte + 2]
        if len(next_block_id) == 2 and next_block_id[1] == 117:
            start_byte = NBP[-1]
            NBP = NBP[:-1]
            while len(NBP) > 0 and start_byte >= NBP[-1]:
                NBP = NBP[:-1]
        else:
            if start_byte + n_bytes > len(content):
                break
            block_id, block_size = _block_info(content[start_byte:start_byte + n_bytes])
            start_byte += n_bytes
            NBP.append(start_byte + block_size)

    if start_byte + block_size <= len(content):
        meta.update(_decode_5104(content[start_byte:start_byte + block_size]))

    start_byte = NBP[1]
    while start_byte + 6 <= len(content):
        n_bytes = 6
        block_id, block_size = _block_info(content[start_byte:start_byte + n_bytes])
        start_byte += n_bytes
        if start_byte + block_size > len(content):
            break
        if block_id in FUNC_DECODE.keys():
            decoded_data = FUNC_DECODE[block_id](content[start_byte:start_byte + block_size])
            if isinstance(decoded_data, dict):
                meta.update(decoded_data)
            else:
                spectrum = decoded_data
        start_byte += block_size

    wavelength = np.linspace(meta['min_wavelength'],
                             meta['max_wavelength'],
                             meta['n_points'])
    
    meta['filename'] = os.path.basename(sp_file_path)
    return spectrum, wavelength, meta

def load_sp_data(pathname: str, excel_name: str = None) -> pd.DataFrame:
    """
    Finds all .sp files recursively in the pathname, reads them, and loads them into a pandas DataFrame.
    """
    sp_files = glob.glob(os.path.join(pathname, "**/*.sp"), recursive=True)
    if not sp_files:
        raise FileNotFoundError(f"No .sp files found in {pathname}")

    data = []
    names = []
    wavelengths = None

    for sp_file in sp_files:
        names.append(os.path.basename(sp_file).replace(".sp", ""))
        spectrum, wl, meta = read_sp(sp_file)
        data.append(spectrum)
        if wavelengths is None:
            wavelengths = wl

    df = pd.DataFrame(data, columns=wavelengths)
    df.insert(0, "Name", names)

    if excel_name:
        excel_path = os.path.join(pathname, f"{excel_name}.xlsx")
        df.to_excel(excel_path, index=False)
    return df
