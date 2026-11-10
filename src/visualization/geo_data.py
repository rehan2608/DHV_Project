"""
Geographic Coordinate Data and Mapping for Indian Educational Institutions (Phase 7 & 8).
Provides precise latitude and longitude mappings for Indian states, union territories,
and primary educational cities to power publication-quality geographic Plotly visualizations.
"""

from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Centroid coordinates for Indian States and Union Territories (lat, lon)
STATE_COORDINATES: Dict[str, Tuple[float, float]] = {
    "andaman and nicobar islands": (11.7401, 92.6586),
    "andhra pradesh": (15.9129, 79.7400),
    "arunachal pradesh": (28.2180, 94.7278),
    "assam": (26.2006, 92.9376),
    "bihar": (25.0961, 85.3131),
    "chandigarh": (30.7333, 76.7794),
    "chhattisgarh": (21.2787, 81.8661),
    "dadra and nagar haveli and daman and diu": (20.1809, 73.0169),
    "delhi": (28.7041, 77.1025),
    "goa": (15.2993, 74.1240),
    "gujarat": (22.2587, 71.1924),
    "haryana": (29.0588, 76.0856),
    "himachal pradesh": (31.1048, 77.1734),
    "jammu and kashmir": (33.7782, 76.5762),
    "jharkhand": (23.6102, 85.2799),
    "karnataka": (15.3173, 75.7139),
    "kerala": (10.8505, 76.2711),
    "ladakh": (34.1526, 77.5771),
    "lakshadweep": (10.5667, 72.6417),
    "madhya pradesh": (22.9734, 78.6569),
    "maharashtra": (19.7515, 75.7139),
    "manipur": (24.6637, 93.9063),
    "meghalaya": (25.4670, 91.3662),
    "mizoram": (23.1645, 92.9376),
    "nagaland": (26.1584, 94.5624),
    "odisha": (20.9517, 85.0985),
    "puducherry": (11.9416, 79.8083),
    "punjab": (31.1471, 75.3412),
    "rajasthan": (27.0238, 74.2179),
    "sikkim": (27.5330, 88.5122),
    "tamil nadu": (11.1271, 78.6569),
    "telangana": (18.1124, 79.0193),
    "tripura": (23.9408, 91.9882),
    "uttar pradesh": (26.8467, 80.9462),
    "uttarakhand": (30.0668, 79.0193),
    "west bengal": (22.9868, 87.8550),
}

# Accurate coordinates for major Indian educational hubs / institute cities (lat, lon)
CITY_COORDINATES: Dict[str, Tuple[float, float]] = {
    # Top Tier IIT / NIT / IIM / Central Uni Hubs
    "chennai": (13.0827, 80.2707),
    "madras": (13.0827, 80.2707),
    "new delhi": (28.6139, 77.2090),
    "delhi": (28.7041, 77.1025),
    "mumbai": (19.0760, 72.8777),
    "bombay": (19.0760, 72.8777),
    "kanpur": (26.4499, 80.3319),
    "kharagpur": (22.3460, 87.2320),
    "roorkee": (29.8543, 77.8880),
    "hyderabad": (17.3850, 78.4867),
    "guwahati": (26.1445, 91.7362),
    "tiruchirappalli": (10.7905, 78.7047),
    "trichy": (10.7905, 78.7047),
    "varanasi": (25.3176, 82.9739),
    "banaras": (25.3176, 82.9739),
    "bengaluru": (12.9716, 77.5946),
    "bangalore": (12.9716, 77.5946),
    "pune": (18.5204, 73.8567),
    "kolkata": (22.5726, 88.3639),
    "calcutta": (22.5726, 88.3639),
    "ahmedabad": (23.0225, 72.5714),
    "jaipur": (26.9124, 75.7873),
    "coimbatore": (11.0168, 76.9558),
    "pilani": (28.3667, 75.6000),
    "bhubaneswar": (20.2961, 85.8245),
    "kozhikode": (11.2588, 75.7804),
    "calicut": (11.2588, 75.7804),
    "indore": (22.7196, 75.8577),
    "surathkal": (13.0119, 74.7936),
    "mangalore": (12.9141, 74.8560),
    "mangaluru": (12.9141, 74.8560),
    "rourkela": (22.2604, 84.8536),
    "dhanbad": (23.7957, 86.4304),
    "gandhinagar": (23.2156, 72.6369),
    "patna": (25.5941, 85.1376),
    "vellore": (12.9165, 79.1325),
    "manipal": (13.3409, 74.7421),
    "thiruvananthapuram": (8.5241, 76.9366),
    "trivandrum": (8.5241, 76.9366),
    "chandigarh": (30.7333, 76.7794),
    "mohali": (30.7046, 76.7179),
    "jodhpur": (26.2389, 73.0243),
    "kurukshetra": (29.9695, 76.8783),
    "silchar": (24.8333, 92.7789),
    "warangal": (17.9784, 79.6006),
    "prayagraj": (25.4358, 81.8463),
    "allahabad": (25.4358, 81.8463),
    "bhopal": (23.2599, 77.4126),
    "lucknow": (26.8467, 80.9462),
    "aligarh": (27.8974, 78.0880),
    "nagpur": (21.1458, 79.0882),
    "srinagar": (34.0837, 74.7973),
    "jammu": (32.7266, 74.8570),
    "ranchi": (23.3441, 85.3096),
    "raipur": (21.2514, 81.6296),
    "amritsar": (31.6340, 74.8723),
    "jalandhar": (31.3260, 75.5762),
    "ludhiana": (30.9010, 75.8573),
    "dehradun": (30.3165, 78.0322),
    "gwalior": (26.2183, 78.1828),
    "jabalpur": (23.1815, 79.9864),
    "surat": (21.1702, 72.8311),
    "vadodara": (22.3072, 73.1812),
    "kochi": (9.9312, 76.2673),
    "cochin": (9.9312, 76.2673),
    "shillong": (25.5788, 91.8933),
    "agartala": (23.8315, 91.2868),
    "gangtok": (27.3389, 88.6065),
    "shimla": (31.1048, 77.1734),
    "mandi": (31.7087, 76.9320),
    "dharwad": (15.4589, 75.0078),
    "belagavi": (15.8497, 74.4977),
    "mysuru": (12.2958, 76.6394),
    "mysore": (12.2958, 76.6394),
    "palakkad": (10.7867, 76.6548),
    "madurai": (9.9252, 78.1198),
    "salem": (11.6643, 78.1460),
    "thanjavur": (10.7870, 79.1378),
    "tirupati": (13.6288, 79.4192),
    "visakhapatnam": (17.6868, 83.2185),
    "vijayawada": (16.5062, 80.6480),
    "guntur": (16.3067, 80.4365),
    "noida": (28.5355, 77.3910),
    "greater noida": (28.4744, 77.5040),
    "gurugram": (28.4595, 77.0266),
    "gurgaon": (28.4595, 77.0266),
}

# Central coordinate of India
INDIA_CENTER = (21.7679, 78.8718)


def get_coordinates(city: Optional[str] = None, state: Optional[str] = None) -> Tuple[float, float]:
    """
    Resolves geographic (lat, lon) coordinates for an institution or region.
    Tries city-level resolution first, falls back to state centroid, and defaults to India center.
    """
    if city:
        city_norm = str(city).strip().lower()
        if city_norm in CITY_COORDINATES:
            return CITY_COORDINATES[city_norm]
        # Check partial match (e.g. "Chennai 600036" or "New Delhi")
        for cname, coords in CITY_COORDINATES.items():
            if cname in city_norm or city_norm in cname:
                return coords

    if state:
        state_norm = str(state).strip().lower()
        if state_norm in STATE_COORDINATES:
            return STATE_COORDINATES[state_norm]
        for sname, coords in STATE_COORDINATES.items():
            if sname in state_norm or state_norm in sname:
                return coords

    return INDIA_CENTER

