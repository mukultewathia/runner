import math
import re
import sys
from datetime import datetime

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000 # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def parse_gpx(gpx_path, lap_size_m):
    with open(gpx_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    blocks = content.split('</trkpt>')
    trackpoints = []
    lat_lon_re = re.compile(r'<trkpt\s+lat=["\'](-?\d+\.\d+)["\']\s+lon=["\'](-?\d+\.\d+)["\']')
    time_re = re.compile(r'<time>([^<]+)</time>')
    hr_re = re.compile(r'<ns3:hr>([^<]+)</ns3:hr>|<hr>([^<]+)</hr>')
    cad_re = re.compile(r'<ns3:cad>([^<]+)</ns3:cad>|<cad>([^<]+)</cad>')
    
    for block in blocks:
        match_lat = lat_lon_re.search(block)
        if not match_lat: continue
        lat, lon = float(match_lat.group(1)), float(match_lat.group(2))
        match_time = time_re.search(block)
        if not match_time: continue
        time_str = match_time.group(1)
        if time_str.endswith('Z'): time_str = time_str[:-1] + '+00:00'
        
        hr = float(match_hr.group(1) or match_hr.group(2)) if (match_hr := hr_re.search(block)) else None
        # Multiply by 2.0 to convert single-foot sensor cadence to standard SPM
        cad = float(match_cad.group(1) or match_cad.group(2)) * 2.0 if (match_cad := cad_re.search(block)) else None
        
        trackpoints.append({
            'lat': lat, 'lon': lon, 'time': datetime.fromisoformat(time_str), 'hr': hr, 'cad': cad
        })
        
    print(f"--- Telemetry Splits (Custom Lap Size: {lap_size_m}m) ---")
    print(f"| Lap | Distance (km) | Duration | Pace (/km) | Avg HR | Max HR | Cadence | Stride |")
    print(f"|---|---|---|---|---|---|---|---|")
    
    lap_num = 1
    current_lap_dist = 0.0
    current_lap_time = 0.0
    current_lap_hrs = []
    current_lap_cads = []
    
    for i in range(1, len(trackpoints)):
        pt1, pt2 = trackpoints[i-1], trackpoints[i]
        dist = haversine(pt1['lat'], pt1['lon'], pt2['lat'], pt2['lon'])
        time_diff = (pt2['time'] - pt1['time']).total_seconds()
        
        if time_diff > 0 and dist / time_diff > 15.0: continue # Skip GPS noise
        
        current_lap_dist += dist
        current_lap_time += time_diff
        if pt2['hr'] is not None: current_lap_hrs.append(pt2['hr'])
        if pt2['cad'] is not None and pt2['cad'] > 0: current_lap_cads.append(pt2['cad'])
        
        if current_lap_dist >= lap_size_m:
            print_lap(lap_num, current_lap_dist, current_lap_time, current_lap_hrs, current_lap_cads)
            lap_num += 1
            current_lap_dist = 0.0
            current_lap_time = 0.0
            current_lap_hrs = []
            current_lap_cads = []
            
    if current_lap_dist > 50.0:
        print_lap(lap_num, current_lap_dist, current_lap_time, current_lap_hrs, current_lap_cads)

def print_lap(num, dist, time_sec, hrs, cads):
    avg_hr = sum(hrs)/len(hrs) if hrs else 0
    max_hr = max(hrs) if hrs else 0
    avg_cad = sum(cads)/len(cads) if cads else 0
    steps = avg_cad * (time_sec / 60.0)
    stride = dist / steps if steps > 0 else 0
    
    pace_sec = time_sec / (dist / 1000.0)
    pace_min, pace_sec = divmod(int(pace_sec), 60)
    dur_min, dur_sec = divmod(int(time_sec), 60)
    print(f"| {num} | {dist/1000.0:.3f} | {dur_min:02d}:{dur_sec:02d} | {pace_min}:{pace_sec:02d} | {avg_hr:.1f} | {max_hr:.1f} | {avg_cad:.1f} | {stride:.2f} |")

if __name__ == '__main__':
    # Argument 1: GPX filepath, Argument 2: Lap size in meters (default 1000.0)
    if len(sys.argv) < 2:
        print("Usage: python3 parse_gpx.py <gpx_file_path> [lap_size_meters]")
        sys.exit(1)
    path = sys.argv[1]
    lap_size = float(sys.argv[2]) if len(sys.argv) > 2 else 1000.0
    parse_gpx(path, lap_size)
